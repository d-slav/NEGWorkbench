# -*- coding: utf-8 -*-
"""
gl3_program.py - GL3Program: FreeCAD objekt (typ 1 z diskuze) - jeden
hlavni SUBRO, ktery FreeCAD skutecne spousti (execute()) a jehoz
vystupni property jsou k dispozici Export modulu.

Vstupy/vystupy se generuji AUTOMATICKY z SUBRO hlavicky vlastniho
.GL3 souboru (in:/out: anotace - viz gl3_lang.parse_subro_header):
  - skalarni/textove in: -> bezna nativni FC property (App::PropertyFloat/
    Integer/PropertyFileIncluded - viz gl3_ops.classify), edituje se v
    beznem Property editoru, pripadne navazatelna na FC Expression.
  - composite in: -> JEDNA App::PropertyString property (stejne jmeno
    jako parametr, napr. "P") drzici referenci ve formatu
    'JmenoObjektu.JmenoVystupu' (napr. 'TEHLO002.PO') na composite vystup
    JINEHO GL3 objektu (typicky GL3Program) - citelna, editovatelna, da
    se vlozit odkudkoli. Pod kapotou se drzi skryta App::PropertyLink
    "<jmeno>_Link" (viz gl3_props.add_hidden_link/parse_ref),
    synchronizovana pres onChanged() - DUVOD: bez skutecneho Linku by
    FreeCAD nevedel o zavislosti mezi temito dvema objekty ve svem grafu,
    a poradi recompute by prestalo byt garantovane. onChanged() se vola
    SYNCHRONNE hned pri zmene reference (i programove), takze shadow Link
    je aktualni jeste pred tim, nez se sestavi poradi pro dalsi recompute
    (stejny mechanismus jako GL3Export.Source, viz gl3_export.py).
    _gather_inputs() nakonec precte JSON text ze zdroje a
    gerlib.serialize.load_json() ho prevede zpet na skutecny gerlib
    objekt (Point/Array/...), ktery Interpreter.run() ocekava.
  - composite out: -> App::PropertyString drzici SKUTECNY JSON text
    (gerlib.serialize.dump_json(), viz ten modul), status ReadOnly (jde
    o vypocitanou hodnotu, needitovat rucne - ReadOnly ale nebrani
    programatickemu zapisu z execute()). Puvodne App::PropertyPythonObject
    (holy Python dict) - zmeneno, protoze PropertyPythonObject nema v
    Property View zadny editor (property se nezobrazi bez "Show all", a
    i pak je jen zluty needitovatelny fallback - viz gl3_props.py).
    App::PropertyString ma bezny textovy editor (viditelny vzdy, seda
    barva jen diky ReadOnly). Export modul si vystup precte pres
    gerlib.serialize.load_json(text) (nebo primo
    deserialize(json.loads(text)), pripadne jen json.loads(text) pro
    plochy dict-dotaz jako drive is_defined()/["items"]/...).
  - skalarni out: -> bezna nativni FC property, taky ReadOnly.

CALL na dalsi SUBRO (napr. TEHLO -> HLO) se resolvuje LENIVE pres
Gl3FileRegistry postavenem nad pripojenou GL3Library (adresare na
disku, soubor '<JMENO>.GL3'). Bez pripojene Library funguje jen
SUBRO bez CALL (nebo CALL na sebe sama).

Editace .GL3 zdroje je v teto fazi externi (obycejny textovy editor) -
kazdy execute() cte soubor ze disku znovu, zadny interni cache mezi
recomputy.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gl3_ops import classify
from gerlib.serialize import dump_json, load_json
from gl3fc.gl3_registry import Gl3FileRegistry
from gl3fc.gl3_props import add_property, add_hidden_link, parse_ref

try:
    import FreeCAD as App
except ImportError:  # umoznuje syntax-check/testy mimo FreeCAD
    App = None


def _log_warning(msg):
    if App is not None:
        App.Console.PrintWarning(msg + "\n")
    else:
        print("WARNING:", msg)


class GL3Program(object):
    """Proxy pro Part::FeaturePython objekt typu GL3Program."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "GL3Program"

        add_property(
            obj,
            "App::PropertyFile",
            "SourceFile",
            "GL3",
            "Cesta k vlastnimu .GL3 souboru (jeho jmeno SUBRO urcuje in:/out:)",
        )
        add_property(
            obj,
            "App::PropertyLink",
            "Library",
            "GL3",
            "GL3Library pro rozreseni CALL na dalsi SUBRO (nepovinne, jen "
            "pokud vlastni SUBRO nekoho vola)",
        )

    # -----------------------------------------------------------------
    # Hlavni vypocet
    # -----------------------------------------------------------------
    def execute(self, obj):
        path = obj.SourceFile
        if not path or not os.path.isfile(path):
            raise ValueError(
                "GL3Program '%s': SourceFile neni nastaven na existujici .GL3 soubor"
                % (obj.Name,)
            )

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            subdef = parse_program(f.read())

        self._sync_properties(obj, subdef)

        inputs = self._gather_inputs(obj, subdef)
        registry = self._build_registry(obj, subdef)

        interp = Interpreter(registry=registry)
        result = interp.run(subdef, inputs=inputs)

        self._store_outputs(obj, subdef, result)

        # Znovu-nastaveni Visibility AZ TADY (po existenci realneho obsahu) -
        # v realnem FreeCADu se ukazalo, ze nastaveni Visibility=True hned
        # pri vytvoreni objektu (pred prvnim execute(), kdyz jeste nic
        # neexistuje) nemusi spravne prorazit do zobrazeni; objekt zustane
        # opticky neviditelny, dokud se dokument neulozi a znovu nenacte.
        # Opakovane nastaveni AZ PO existenci obsahu tenhle stav spolehlive
        # opravuje.
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True

    def onChanged(self, obj, prop):
        link_name = self._shadow_link_name(prop)
        if hasattr(obj, link_name):
            self._resync_composite_link(obj, prop)

    @staticmethod
    def _shadow_link_name(param_name):
        return "%s_Link" % param_name

    def _resync_composite_link(self, obj, param_name):
        """Prepocita skryty Link '<param_name>_Link' z aktualniho textu
        composite in: reference (viz modulovy docstring)."""
        link_name = self._shadow_link_name(param_name)
        if not hasattr(obj, link_name):
            return
        ref = getattr(obj, param_name, "") or ""
        src_obj_name, _output_name = parse_ref(ref)
        new_source = None
        if src_obj_name is not None and getattr(obj, "Document", None) is not None:
            new_source = obj.Document.getObject(src_obj_name)
        if getattr(obj, link_name, None) is not new_source:
            setattr(obj, link_name, new_source)

    # -----------------------------------------------------------------
    # Synchronizace property podle SUBRO hlavicky
    # -----------------------------------------------------------------
    def _sync_properties(self, obj, subdef):
        for name, _size, direction in subdef.params:
            kind, native_type = classify(name)

            if direction == "in":
                if kind == "composite":
                    group = "GL3 In"
                    doc = (
                        "GL3 in: %s - odkaz na composite vystup jineho GL3 objektu, "
                        "format 'JmenoObjektu.JmenoVystupu' (napr. 'TEHLO002.PO')" % name
                    )
                    add_property(obj, "App::PropertyString", name, group, doc)
                    add_hidden_link(
                        obj, self._shadow_link_name(name), group,
                        "(interni) automaticky odvozeny odkaz pro vstup '%s' - "
                        "nemenit rucne, slouzi jen FreeCAD dependency grafu pro "
                        "spravne poradi recompute" % name,
                    )
                    self._resync_composite_link(obj, name)
                    continue
                group = "GL3 In"
                doc = "GL3 in: %s" % name
            else:
                group = "GL3 Out"
                doc = "GL3 out: %s" % name
                if kind == "composite":
                    native_type = "App::PropertyString"

            add_property(obj, native_type, name, group, doc, read_only=(direction == "out"))

    # -----------------------------------------------------------------
    # Vstupy pro Interpreter.run()
    # -----------------------------------------------------------------
    def _gather_inputs(self, obj, subdef):
        inputs = {}
        for name, _size, direction in subdef.params:
            if direction != "in":
                continue
            kind, _native_type = classify(name)
            if kind == "composite":
                inputs[name] = self._resolve_composite_input(obj, name)
            else:
                inputs[name] = getattr(obj, name)
        return inputs

    def _resolve_composite_input(self, obj, name):
        ref = getattr(obj, name, "") or ""
        src_obj_name, output_name = parse_ref(ref)
        if src_obj_name is None:
            raise ValueError(
                "GL3Program '%s': vstup '%s' musi byt ve formatu "
                "'JmenoObjektu.JmenoVystupu' (napr. 'TEHLO002.PO'), je: %r"
                % (obj.Name, name, ref)
            )

        # Pojistka navic k onChanged() - napr. tesne po otevreni dokumentu,
        # kdyby onChanged() z nejakeho duvodu jeste neproběhlo (viz
        # gl3_export.py - stejny duvod).
        self._resync_composite_link(obj, name)
        source = getattr(obj, self._shadow_link_name(name), None)
        if source is None:
            raise ValueError(
                "GL3Program '%s': objekt '%s' (vstup '%s' = '%s') v dokumentu "
                "neexistuje" % (obj.Name, src_obj_name, name, ref)
            )

        if not hasattr(source, output_name):
            raise ValueError(
                "GL3Program '%s': zdroj '%s' nema property '%s' (vstup '%s' = '%s')"
                % (obj.Name, source.Name, output_name, name, ref)
            )

        raw = getattr(source, output_name)
        if not isinstance(raw, str):
            raise ValueError(
                "GL3Program '%s': property '%s' na '%s' neni retezec (JSON text) - "
                "vstup '%s' ocekava composite vystup jineho GL3 objektu"
                % (obj.Name, output_name, source.Name, name)
            )
        try:
            return load_json(raw)
        except ValueError as exc:
            raise ValueError(
                "GL3Program '%s': property '%s' na '%s' neni platny JSON (vstup '%s'): %s"
                % (obj.Name, output_name, source.Name, name, exc)
            )

    # -----------------------------------------------------------------
    # Registry pro CALL (lenivy, pres pripadnou Library)
    # -----------------------------------------------------------------
    def _build_registry(self, obj, subdef):
        extra = {subdef.name: subdef}
        library = getattr(obj, "Library", None)
        if library is not None and hasattr(library, "Proxy"):
            return library.Proxy.build_registry(library, extra=extra)
        return Gl3FileRegistry(search_entries=[], extra=extra)

    # -----------------------------------------------------------------
    # Ulozeni vystupu zpet do property
    # -----------------------------------------------------------------
    def _store_outputs(self, obj, subdef, result):
        for name, _size, direction in subdef.params:
            if direction != "out":
                continue
            kind, _native_type = classify(name)
            value = result.get(name)

            if kind == "composite":
                # indent=None -> kompaktni JEDNORADKOVY JSON (zadne "\n").
                # dump_json() ma default indent=2 (hodi se pro ulozeni do
                # .json souboru a cteni v textovem editoru), ale v Property
                # View kazdy "\n" v retezci roztahne radek na vic radku -
                # pro zobrazeni v jednom radku chceme kompaktni variantu.
                setattr(obj, name, dump_json(value, indent=None))
                continue

            if value is None:
                _log_warning(
                    "GL3Program '%s': vystupni skalar '%s' vysel nedefinovany "
                    "(None) - puvodni hodnota property se nemeni" % (obj.Name, name)
                )
                continue

            setattr(obj, name, value)

    def onDocumentRestored(self, obj):
        self.Type = "GL3Program"


class ViewProviderGL3Program(object):
    """Minimalni ViewProvider - zatim jen zakladni chovani, bez vlastni ikony.

    claimChildren() zaridi, ze GL3Export objekty (viz gl3fc/gl3_export.py),
    ktere na tento GL3Program odkazuji pres svoji property 'Source', se ve
    stromu zobrazi jako jeho potomci - i kdyz jsou technicky nezavisle
    objekty dokumentu (stejny mechanismus jako PartDesign::Body zobrazuje
    Sketch jako 'svuj'). Zadne nove objekty se pritom nevytvareji a
    nehrozi tak riziko spojene s automatickym vytvarenim/mazanim SUBRO
    child objektu, o kterem jsme diskutovali (varianta D) - tohle je jen
    kosmeticky pohled na uz existujici, nezavisle objekty."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return None

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def claimChildren(self):
        obj = self.Object
        doc = obj.Document
        children = []
        for candidate in doc.Objects:
            proxy = getattr(candidate, "Proxy", None)
            if getattr(proxy, "Type", None) != "GL3Export":
                continue
            source = getattr(candidate, "Source", None)
            # Porovnani pres Name/Document, ne Python 'is' - FreeCAD muze pri
            # kazdem cteni PropertyLink vratit novy Python wrapper okolo
            # stejneho C++ objektu, takze 'is obj' muze spurious selhat.
            if source is not None and source.Name == obj.Name and source.Document == obj.Document:
                children.append(candidate)
        return children

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def create(doc, name, source_file, library=None):
    """Pomocna funkce pro vytvoreni GL3Program objektu v danem dokumentu."""
    obj = doc.addObject("Part::FeaturePython", name)
    GL3Program(obj)
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        ViewProviderGL3Program(obj.ViewObject)
        obj.ViewObject.Visibility = True
    obj.SourceFile = source_file
    if library is not None:
        obj.Library = library
    return obj
