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
  - composite in: NENI V TETO FAZI PODPOROVAN (architektonicke
    rozhodnuti - composite smi do GL3 jen pres Link z jineho GL3
    objektu, ne jako literal z FC; Link je planovan az pozdeji).
  - composite out: -> App::PropertyPythonObject drzici JSON-safe "slot"
    z gerlib.serialize.serialize() (viz ten modul) - Export modul si ho
    precte bez nutnosti importovat gerlib.
  - skalarni out: -> bezna nativni FC property.

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
from gerlib.serialize import serialize
from gl3fc.gl3_registry import Gl3FileRegistry

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

        if not hasattr(obj, "SourceFile"):
            obj.addProperty(
                "App::PropertyFile",
                "SourceFile",
                "GL3",
                "Cesta k vlastnimu .GL3 souboru (jeho jmeno SUBRO urcuje in:/out:)",
            )
        if not hasattr(obj, "Library"):
            obj.addProperty(
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

    # -----------------------------------------------------------------
    # Synchronizace property podle SUBRO hlavicky
    # -----------------------------------------------------------------
    def _sync_properties(self, obj, subdef):
        for name, _size, direction in subdef.params:
            kind, native_type = classify(name)

            if direction == "in":
                if kind == "composite":
                    raise NotImplementedError(
                        "GL3Program '%s': vstupni parametr '%s' je composite typ - "
                        "composite vstup zatim neni podporovan (planovano pres Link "
                        "na jiny GL3 objekt, viz diskuze o architekture)" % (obj.Name, name)
                    )
                group = "GL3 In"
                doc = "GL3 in: %s" % name
            else:
                group = "GL3 Out"
                doc = "GL3 out: %s" % name
                if kind == "composite":
                    native_type = "App::PropertyPythonObject"

            if not hasattr(obj, name):
                obj.addProperty(native_type, name, group, doc)

    # -----------------------------------------------------------------
    # Vstupy pro Interpreter.run()
    # -----------------------------------------------------------------
    def _gather_inputs(self, obj, subdef):
        inputs = {}
        for name, _size, direction in subdef.params:
            if direction == "in":
                inputs[name] = getattr(obj, name)
        return inputs

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
                setattr(obj, name, serialize(value))
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
            if getattr(candidate, "Source", None) is obj:
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
    obj.SourceFile = source_file
    if library is not None:
        obj.Library = library
    return obj
