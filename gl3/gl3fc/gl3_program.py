# -*- coding: utf-8 -*-
"""
gl3_program.py - GL3Program: FreeCAD objekt (typ 1 z diskuze) - jeden
hlavni SUBRO, ktery FreeCAD skutecne spousti (execute()) a jehoz
vystupni property jsou k dispozici Export modulu.

Vstupy/vystupy se generuji AUTOMATICKY z SUBRO hlavicky vlastniho
.GL3 souboru (in:/out: anotace - viz gl3_lang.parse_subro_header):
  - skalarni/textove in: -> bezna nativni FC property (App::PropertyFloat/
    Integer/PropertyString - viz gl3_ops.classify), edituje se v beznem
    Property editoru, pripadne navazatelna na FC Expression.
    (Textove "B"-prefixove in: parametry - napr. BSTR - jsou obecny text
    (App::PropertyString), NE soubor - GL3 samo typ "B" nerozlisuje na
    "jmeno souboru" vs. "libovolny text", jsou to jazykove stejna vec.
    Vyjimka: hint '-f' v hlavicce (in-f:BJM, viz gl3_lang.parse_subro_header)
    rika "tenhle konkretni text JE jmeno souboru" - pro TAKOVY in-f:
    parametr se pouzije App::PropertyFile (hezke file-browse tlacitko v
    Property editoru), NE App::PropertyFileIncluded - ten by soubor
    zkopiroval/vlozil primo do .FCStd dokumentu a pri cteni pouzival
    docasnou rozbalenou kopii v temp adresari FreeCADu, misto aby pouzil
    vybrany soubor primo. U out:/out-f: se hint NIKDY nepromitne do FC
    property - "vystupni property = jmeno souboru" ve FreeCADu nedava
    smysl, viz diskuze s uzivatelem - '-f' tam ma jen dokumentacni
    hodnotu pro vnitrni volani SUBRO.)
  - composite in: -> JEDNA App::PropertyString property (stejne jmeno
    jako parametr, napr. "P") drzici referenci ve formatu
    'JmenoObjektu.JmenoVystupu' (napr. 'TEHLO002.PO') na composite vystup
    JINEHO GL3 objektu (typicky GL3Program), NEBO primo na seznam bodu
    z bezne FreeCAD geometrie, napr. 'Wire001.Points' (Draft BSpline/
    Wire - App::PropertyVectorList). Druhy pripad se pozna podle toho,
    ze cilova property neni retezec (JSON), ale seznam objektu s x/y/z
    (viz _looks_like_vector_list) - zadna diskretizace/aproximace, body
    se prevedou primo tak, jak je uzivatel v modelu umistil. Citelna,
    editovatelna, da se vlozit odkudkoli. Pod kapotou se drzi skryta
    App::PropertyLink "<jmeno>_Link" (viz gl3_props.add_hidden_link/
    parse_ref),
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
recomputy (krome levke "nezmenilo se nic?" kontroly pred samotnym
ctenim/behem - viz execute()).

"Skryty retezec" (INI...CLOSE, vc. vsech vnorenych CALL - viz
gl3_interpreter.py) se vykresluje PRIMO na tomto objektu: GL3Program je
Part::FeaturePython, takze uz ma svuj vlastni nativni Shape - zadny
samostatny GL3Export objekt ani JSON property tu neni potreba (na
rozdil od pojmenovanych composite out: vystupu, ktere porad potrebuji
GL3Export, chce-li je uzivatel materializovat jako samostatny FreeCAD
objekt).
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gl3_ops import classify
import gl3_placeholders
from gl3fc.gl3_placeholder_context import static_placeholders
from gerlib.serialize import dump_json, load_json, serialize
from gerlib.types import Point
from gl3fc.gl3_registry import Gl3FileRegistry
from gl3fc.gl3_props import add_property, add_hidden_link, parse_ref, icon_path
from gl3fc.gl3_export import build_shape

try:
    import FreeCAD as App
    import Part
except ImportError:  # umoznuje syntax-check/testy mimo FreeCAD
    App = None
    Part = None

_MISSING = object()  # sentinel pro "property s timhle jmenem neexistuje"


def _log_warning(msg):
    if App is not None:
        App.Console.PrintWarning(msg + "\n")
    else:
        print("WARNING:", msg)


def _looks_like_vector_list(raw):
    """True, kdyz 'raw' vypada jako seznam FreeCAD Vector objektu (napr.
    Draft BSpline/Wire '.Points' - App::PropertyVectorList): kazdy prvek
    ma x/y/z atributy. Prazdny seznam se NEpovazuje za seznam bodu
    (nejednoznacne vuci JSON ceste - radsi jasna chyba nez tiche [])."""
    if not isinstance(raw, (list, tuple)) or len(raw) == 0:
        return False
    return all(hasattr(v, "x") and hasattr(v, "y") and hasattr(v, "z") for v in raw)


def resolve_source_file_path(obj):
    """Vyresi obj.SourceFile (${workbench_path}/${fc_file_path} - viz
    gl3_placeholders.py) na absolutni cestu k .GL3 souboru. Sdileno mezi
    execute() (hlavni beh) a NEG_EditProgram prikazem (gl3_commands.py -
    potrebuje stejnou cestu k sestaveni ${gl3_file_path}/${gl3_file_name}
    pro EditCommand), aby se logika resolvovani nedublovala a
    nerozjizdela.

    Vyhazuje ValueError se srozumitelnou zpravou (vc. jmena objektu),
    je-li SourceFile prazdny, neresolvovatelny (neznamy/nedostupny
    zastupny text), nebo nevede-li na existujici soubor na disku."""
    placeholder_values = static_placeholders(obj)
    raw_path = obj.SourceFile
    try:
        # ${gl3_file_path}/${gl3_file_name} tu nedavaji smysl (je to
        # CESTA/JMENO TOHOTO souboru, ktery se prave zjistuje) - kdyby je
        # nekdo presto pouzil, vyhodi jasnou chybu "neni v tomto kontextu
        # k dispozici", ne tichy spatny vysledek.
        path = gl3_placeholders.substitute(
            raw_path, dict(placeholder_values, gl3_file_path=None, gl3_file_name=None)
        )
    except ValueError as e:
        raise ValueError("GL3Program '%s': SourceFile - %s" % (obj.Name, e))
    if not path or not os.path.isfile(path):
        raise ValueError(
            "GL3Program '%s': SourceFile neni nastaven na existujici .GL3 soubor"
            % (obj.Name,)
        )
    return path


def resolve_edit_command(obj):
    """Vyresi obj.EditCommand (zadani uzivatele - shellovy prikaz pro
    NEG_EditProgram, viz gl3_commands.py) na finalni retezec pripraveny
    ke spusteni: ${workbench_path}/${fc_file_path} jako obvykle (viz
    static_placeholders), navic ${gl3_file_path}/${gl3_file_name} -
    adresar/jmeno AKTUALNIHO (jiz vyreseneho - viz resolve_source_file_path)
    SourceFile teto SUBRO. Na rozdil od stejnojmennych zastupnych textu
    uvnitr IDEV (viz gl3_interpreter.py) tu NEJDE o bezici interpret
    (SUBRO/CALL) - vzdy jde jen o SourceFile TOHOTO objektu."""
    source_path = resolve_source_file_path(obj)
    values = dict(
        static_placeholders(obj),
        gl3_file_path=os.path.dirname(source_path),
        gl3_file_name=os.path.basename(source_path),
    )
    try:
        return gl3_placeholders.substitute(obj.EditCommand, values)
    except ValueError as e:
        raise ValueError("GL3Program '%s': EditCommand - %s" % (obj.Name, e))


class GL3Program(object):
    """Proxy pro Part::FeaturePython objekt typu GL3Program."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "GL3Program"
        # Signatura (viz execute()) posledniho USPESNEHO execute() -
        # pouziva se k preskoceni draheho znovunacteni/beh interpretu, kdyz
        # execute() bylo vyvolano jen vedlejsim ucinkem (touch() z jinych
        # duvodu nez skutecna zmena zavislosti - viz gl3_export.create()).
        self._exec_cache = None

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

        # RecomputeOnOpenDoc (vychozi True = puvodni chovani beze zmeny) -
        # viz diskuze s uzivatelem: self._exec_cache prezije jen v ramci
        # jedne session (neni soucasti __getstate__/__setstate__ nize -
        # zamerne, viz jejich komentar), takze prvni execute() po KAZDEM
        # otevreni dokumentu vzdy udela plny (mozna drahy) beh, i kdyz se
        # od ulozeni nezmenilo vubec nic - to je bezpecny vychozi stav
        # (zachyti zmeny v .GL3 zavislostech pres CALL i zmeny samotneho
        # interpretu/doplnku, ktere cache nesleduje).
        #
        # Vypnutim (False) na VLASTNI ZODPOVEDNOST uzivatel rika "vim, ze
        # jsem od posledniho ulozeni nic needitoval, preskakuj prepocet po
        # otevreni, pokud se fakticky nic nezmenilo" - k tomu navic
        # potrebujeme signaturu posledniho uspesneho behu, ktera PREZIJE
        # ulozeni/otevreni (viz _ExecCache nize - narozdil od
        # self._exec_cache je to skutecna FC property).
        is_new = not hasattr(obj, "RecomputeOnOpenDoc")
        add_property(
            obj,
            "App::PropertyBool",
            "RecomputeOnOpenDoc",
            "GL3 Options",
            "Po otevreni dokumentu VZDY prepocitat, i kdyz se od ulozeni "
            "nic nezmenilo (bezpecny vychozi stav - zachyti zmeny .GL3 "
            "zavislosti pres CALL i zmeny doplnku samotneho, ktere "
            "nasledujici kontrola nesleduje). Vypni jen pokud vis jiste, "
            "ze od ulozeni nic (vc. zavislosti pres CALL) needitoval - pak "
            "se prepocet po otevreni preskoci, pokud se obsah SourceFile "
            "(mtime), Library ani hodnoty in: parametru nezmenily.",
        )
        if is_new:
            obj.RecomputeOnOpenDoc = True

        # EditCommand (zadani uzivatele) - shellovy prikaz, kterym
        # NEG_EditProgram (gl3_commands.py) otevre SourceFile v externim
        # editoru po stisku tlacitka; ${gl3_file_path}/${gl3_file_name}
        # (viz resolve_source_file_path + gl3_placeholders.py) se resolvuji
        # z JIZ vyresene absolutni cesty SourceFile (ne z bezicicho
        # interpretu - tahle property s zadnym behem programu nesouvisi).
        is_new = not hasattr(obj, "EditCommand")
        add_property(
            obj,
            "App::PropertyString",
            "EditCommand",
            "GL3 Options",
            "Shellovy prikaz spousteny tlacitkem 'Edit GL3 Program' - "
            "${workbench_path}/${fc_file_path}/${gl3_file_path}/"
            "${gl3_file_name} se nahradi (posledni dva jsou adresar/jmeno "
            "AKTUALNIHO SourceFile, vc. pripony).",
        )
        if is_new:
            obj.EditCommand = "edit ${gl3_file_path}/${gl3_file_name}"

        # Interni (Hidden) - JSON signatura posledniho uspesneho execute()
        # (viz konec execute()), na rozdil od self._exec_cache PREZIJE
        # ulozeni/otevreni dokumentu (skutecna FC property) - cte se jen
        # kdyz je RecomputeOnOpenDoc == False (viz execute()). Skupina
        # "GL3 Options" (NE "GL3"!) - "GL3" je ve trigger setu onChanged()
        # (viz nize), a zapis do teto property se deje PRIMO UVNITR
        # execute(), takze by ve skupine "GL3" zpusobil dalsi zbytecny
        # (nebo cyklicky) prepocet pri kazdem uspesnem behu.
        if not hasattr(obj, "_ExecCache"):
            obj.addProperty(
                "App::PropertyString",
                "_ExecCache",
                "GL3 Options",
                "Interni: JSON signatura posledniho uspesneho behu - "
                "nemenit rucne.",
            )
            try:
                obj.setPropertyStatus("_ExecCache", "Hidden")
            except AttributeError:
                pass
            obj._ExecCache = ""

    # -----------------------------------------------------------------
    # Hlavni vypocet
    # -----------------------------------------------------------------
    def execute(self, obj):
        """Tenky wrapper okolo _execute_impl() - pri vyjimce ji znovu
        vyhodi CERSTVOU (misto propagace puvodni hluboko z interpretu).
        FreeCAD pri kazde vyjimce prosakujici z execute() vypise CELY
        Python traceback do Report View (jeho obecne chovani pro VSECHNY
        scriptovane objekty, ne neco specifickeho pro nas, a nejde
        potlacit uplne) - opakovanym vyhozenim PRAVE TADY se z nej
        alespon setne cela hloubka interniho volaciho retezce interpretu
        (interp.run -> _exec_block -> _exec_stmt -> _exec_data -> ...),
        ktera pro autora GL3 programu nema zadnou informacni hodnotu.
        'from None' navic potlaci pripojeni puvodniho tracebacku jako
        "During handling of the above exception...". Zprava vyjimky
        (str(e)) zustava presne stejna, jen se zkracuje CESTA, kterou k
        uzivateli dorazi.

        type(e)(str(e)) predpoklada standardni jednoargumentovy
        konstruktor (plati pro vsechny nase vlastni vyjimky i vestavene
        ValueError/TypeError/... - viz README.md) - kdyby to pro nejaky
        neocekavany typ (napr. C++ vyjimka z OCC/Part proteklá az sem)
        selhalo, spadne se bezpecne na obecny RuntimeError se stejnou
        zpravou, misto aby tahle "kosmeticka" uprava sama zpusobila
        novou (jinou, matouci) vyjimku."""
        try:
            self._execute_impl(obj)
        except Exception as e:
            try:
                short = type(e)(str(e))
            except Exception:
                short = RuntimeError(str(e))
            raise short from None

    def _execute_impl(self, obj):
        placeholder_values = static_placeholders(obj)
        path = resolve_source_file_path(obj)

        # Rychla kontrola PRED drahym znovunactenim/parsovanim souboru a
        # behem cele interpretu: zmenilo se od posledniho USPESNEHO behu
        # vubec neco, na cem execute() skutecne zavisi (obsah souboru -
        # detekovano pres mtime, pripojena Library, hodnoty vsech in:
        # parametru)? Pokud ne, tenhle execute() byl nejspis vyvolan jen
        # vedlejsim ucinkem FreeCADu (napr. touch() pri pridani noveho
        # GL3Exportu na NEKTERY jiny (pojmenovany) vystup - viz
        # gl3_export.create() - je potreba, aby se novy Export ve strome
        # spravne zaradil jako potomek, ale sam o sobe neznamena, ze SE NA
        # VSTUPECH TOHOTO PROGRAMU cokoliv zmenilo) - preskocit drahou cast
        # a nechat vystupni property i Shape beze zmeny. "Reload GL3
        # Program" tuhle cache vzdy explicitne zneplatni (viz
        # gl3_commands.py), takze rucni vyvolani je porad spolehlive.
        #
        # POZOR - ZNAMY LIMIT: sleduje se jen mtime TOHOTO souboru, ne
        # souboru resolvovanych pres CALL/Library (viz Gl3FileRegistry) -
        # zmena v zavislosti volane pres CALL (napr. HLO.GL3 volane z
        # TEHLO.GL3) se tak nemusi projevit automaticky. Po editaci
        # takoveho souboru pouzij "Reload GL3 Program" (nebo rucni "Mark
        # to recompute" + Refresh) na PRISLUSNYCH programech.
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None
        library_name = getattr(getattr(obj, "Library", None), "Name", None)

        cache = getattr(self, "_exec_cache", None)
        if cache is None and not getattr(obj, "RecomputeOnOpenDoc", True):
            # self._exec_cache je jen v pameti (nulovana pri kazdem
            # otevreni dokumentu - viz __getstate__/__setstate__ nize) -
            # RecomputeOnOpenDoc == False rika, ze uzivatel na vlastni
            # zodpovednost chce zkusit obnovit signaturu POSLEDNIHO
            # uspesneho behu z _ExecCache (skutecna FC property, tu uz
            # otevreni dokumentu prezije).
            persisted = getattr(obj, "_ExecCache", "") or ""
            if persisted:
                try:
                    cache = json.loads(persisted)
                except ValueError:
                    cache = None
        if (
            cache is not None
            and cache["path"] == path
            and cache["mtime"] == mtime
            and cache["library_name"] == library_name
            and all(
                getattr(obj, name, _MISSING) == value
                for name, value in cache["inputs"].items()
            )
        ):
            self._exec_cache = cache
            return

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            subdef = parse_program(f.read())
        subdef.source_path = path  # pro ${gl3_file_path} v IDEV/CALL - viz gl3_interpreter.py

        self._sync_properties(obj, subdef)

        inputs = self._gather_inputs(obj, subdef)
        registry = self._build_registry(obj, subdef)

        interp = Interpreter(registry=registry, path_placeholders=placeholder_values)
        result = interp.run(subdef, inputs=inputs)

        self._store_outputs(obj, subdef, result)

        # "Skryty retezec" (viz zadani uzivatele - INI...CLOSE, vc. vsech
        # vnorenych CALL) se vykresli PRIMO na tomto objektu - stejnou
        # cestou (build_shape na serializovanem "slot" dictu), jakou uz
        # pouziva GL3Export pro pojmenovane composite vystupy (viz
        # gl3_export.py). Zadny mezikrok pres samostatny GL3Export objekt
        # ani JSON property tu neni potreba - GL3Program uz je Part::
        # FeaturePython, takze ma svuj vlastni nativni Shape.
        if interp.hidden_chain is not None:
            obj.Shape = build_shape(serialize(interp.hidden_chain))
        elif Part is not None:
            obj.Shape = Part.Shape()  # nic nenakresleno - prazdny tvar

        # Cache aktualizovat AZ PO uspesnem behu - pri chybe (napr. spatny
        # vstup, vyhozena vyjimka drive v teto funkci) se nesmi nic
        # cachovat, aby dalsi pokus (po oprave) spolehlive spustil skutecny
        # beh znovu, misto aby omylem "uspesne" preskocil na zaklade
        # stareho/neplatneho stavu.
        self._exec_cache = {
            "path": path,
            "mtime": mtime,
            "library_name": library_name,
            "inputs": {
                name: getattr(obj, name, None)
                for name, _size, direction, _hint in subdef.params
                if direction == "in"
            },
        }
        # Stejna signatura navic i jako skutecna FC property (_ExecCache) -
        # ta na rozdil od self._exec_cache PREZIJE ulozeni/otevreni
        # dokumentu, viz RecomputeOnOpenDoc vyse. Selhani serializace
        # (nemelo by nastat - "inputs" jsou vzdy scalar/string hodnoty
        # FC properties, viz _gather_inputs) se tise ignoruje - v
        # nejhorsim pripade se priste jen provede plny beh znovu.
        try:
            obj._ExecCache = json.dumps(self._exec_cache)
        except (TypeError, ValueError):
            pass

        # POZOR: zde uz NENASTAVUJEME vobj.Visibility = True (drive se tu
        # opakovane nastavovalo na kazdem execute(), z duvodu "objekt
        # zustava opticky neviditelny, dokud se dokument neulozi a znovu
        # nenacte" - ale tim se pri kazdem recomputu prepsalo i rucni
        # schovani objektu uzivatelem, coz je skutecny bug. Visibility se
        # nastavuje jen JEDNOU, pri vytvoreni - viz create() nize.
        # GL3Program uz ted MA vlastni Shape (viz vyse - skryty retezec z
        # INI...CLOSE) - stejny "nastav jen jednou pri vytvoreni" pristup
        # k Visibility ale porad plati, viz duvod vyse.

    def onChanged(self, obj, prop):
        link_name = self._shadow_link_name(prop)
        if hasattr(obj, link_name):
            self._resync_composite_link(obj, prop)

        # Auto-recompute: zmena VSTUPU (SourceFile/Library/GL3 In - vc.
        # composite in: textove reference) ma rovnou spustit prepocet
        # tohoto objektu (a tim padem i navazanych GL3Export, ktere na
        # nem zavisi) - jinak by uzivatel musel po kazde zmene parametru
        # rucne kliknout Refresh. Skryte "_Link" shadow property (viz
        # vyse) vynechavame - to je interni bookkeeping, ne uzivatelska
        # zmena, a uz se vyresilo pri resyncu radek vyse.
        if prop.endswith("_Link"):
            return
        if prop == "_ExecCache":
            # Interni bookkeeping (viz __init__) - zapisuje se PRIMO
            # uvnitr execute(), nikdy uzivatelska zmena; navic uz je ve
            # skupine mimo trigger set nize, tohle je jen pro jistotu
            # explicitni (kdyby se skupina nekdy prehodila).
            return
        try:
            group = obj.getGroupOfProperty(prop)
        except AttributeError:
            return
        if group not in ("GL3", "GL3 In"):
            return
        try:
            obj.Document.recompute()
        except AttributeError:
            pass  # napr. objekt jeste neni plne pripojeny k dokumentu

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
        src_obj_name, _output_name, _index = parse_ref(ref)
        new_source = None
        if src_obj_name is not None and getattr(obj, "Document", None) is not None:
            new_source = obj.Document.getObject(src_obj_name)
        if getattr(obj, link_name, None) is not new_source:
            setattr(obj, link_name, new_source)

    # -----------------------------------------------------------------
    # Synchronizace property podle SUBRO hlavicky
    # -----------------------------------------------------------------
    def _sync_properties(self, obj, subdef):
        current_names = set()
        for name, _size, direction, hint in subdef.params:
            current_names.add(name)
            kind, native_type = classify(name)
            if direction == "in" and hint == "file":
                # '-f' hint (viz gl3_lang.parse_subro_header) - jen pro
                # in: (out:/out-f: nikdy - vystupni "property = jmeno
                # souboru" ve FreeCADu nedava smysl, viz diskuze s
                # uzivatelem). Jinak by "B" bylo vzdy App::PropertyString
                # (obecny text - viz gl3_ops.TYPE_PREFIX_INFO).
                native_type = "App::PropertyFile"

            if direction == "in":
                if kind == "composite":
                    group = "GL3 In"
                    doc = (
                        "GL3 in: %s - odkaz na composite vystup jineho GL3 objektu "
                        "NEBO na seznam bodu z FreeCAD geometrie (napr. Draft "
                        "BSpline/Wire '.Points'), format 'JmenoObjektu.JmenoVystupu' "
                        "(napr. 'TEHLO002.PO' nebo 'Wire001.Points'), volitelne s "
                        "indexem prvku pole '(N)' (1 = prvni), napr. "
                        "'TEHLO002.PO(1)'" % name
                    )
                    add_property(obj, "App::PropertyString", name, group, doc)
                    link_name = self._shadow_link_name(name)
                    current_names.add(link_name)
                    add_hidden_link(
                        obj, link_name, group,
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

        self._remove_stale_properties(obj, current_names)

    @staticmethod
    def _remove_stale_properties(obj, current_names):
        """Odstrani GL3 In/Out property (vc. shadow '_Link'), ktere uz
        nejsou v aktualni SUBRO hlavicce - reaguje na SMAZANI parametru
        ze zdrojoveho .GL3 souboru (viz "Reload GL3 Program"). Property
        skupiny "GL3" (SourceFile, Library) se nikdy neodstranuji - ty
        nejsou odvozene z hlavicky."""
        try:
            properties = list(obj.PropertiesList)
        except AttributeError:
            return
        for name in properties:
            if name in current_names:
                continue
            try:
                group = obj.getGroupOfProperty(name)
            except AttributeError:
                continue
            if group not in ("GL3 In", "GL3 Out"):
                continue
            try:
                obj.removeProperty(name)
            except AttributeError:
                pass

    # -----------------------------------------------------------------
    # Vstupy pro Interpreter.run()
    # -----------------------------------------------------------------
    def _gather_inputs(self, obj, subdef):
        inputs = {}
        for name, _size, direction, _hint in subdef.params:
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
        src_obj_name, output_name, index = parse_ref(ref)
        if src_obj_name is None:
            raise ValueError(
                "GL3Program '%s': vstup '%s' musi byt ve formatu "
                "'JmenoObjektu.JmenoVystupu' nebo 'JmenoObjektu.JmenoVystupu(Index)' "
                "(napr. 'TEHLO002.PO' nebo 'TEHLO002.PO(1)'), je: %r"
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
        if isinstance(raw, str):
            try:
                value = load_json(raw)
            except ValueError as exc:
                raise ValueError(
                    "GL3Program '%s': property '%s' na '%s' neni platny JSON (vstup '%s'): %s"
                    % (obj.Name, output_name, source.Name, name, exc)
                )
        elif _looks_like_vector_list(raw):
            # Nekomponovany vstup rovnou z FreeCAD geometrie - typicky
            # Draft BSpline/Wire '.Points' (App::PropertyVectorList).
            # Zadny GL3 JSON tady neni - jen prime prevedeni bodu, ktere
            # uzivatel v modelu skutecne umistil. Zachovava se presnost
            # (zadna diskretizace/aproximace) - viz modulovy docstring.
            value = [Point(v.x, v.y, v.z) for v in raw]
        else:
            raise ValueError(
                "GL3Program '%s': property '%s' na '%s' neni ani JSON text "
                "(composite vystup jineho GL3 objektu), ani seznam bodu "
                "(napr. Draft BSpline/Wire '.Points') - vstup '%s' nelze rozresit"
                % (obj.Name, output_name, source.Name, name)
            )

        if index is not None:
            # deserialize() vraci "Array" jako obycejny Python list (viz
            # gerlib/serialize.py) - index (1 = prvni prvek) vybere jeden
            # jeho prvek misto cele pole, napr. kdyz composite in: ocekava
            # jeden Point, ale zdrojovy vystup je cele pole bodu.
            if not isinstance(value, list):
                raise ValueError(
                    "GL3Program '%s': index '(%d)' u vstupu '%s' lze pouzit jen "
                    "na Array vystup - '%s' na '%s' neni pole"
                    % (obj.Name, index, name, output_name, source.Name)
                )
            if not (1 <= index <= len(value)):
                raise ValueError(
                    "GL3Program '%s': index %d mimo rozsah u vstupu '%s' - '%s' "
                    "na '%s' ma %d prvku (index je od 1 = prvni prvek)"
                    % (obj.Name, index, name, output_name, source.Name, len(value))
                )
            value = value[index - 1]

        return value

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
        for name, _size, direction, _hint in subdef.params:
            if direction != "out":
                continue
            kind, native_type = classify(name)
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

            if native_type == "App::PropertyInteger":
                # Interpret vzdy pocita s Python float (i celociselne I/J/K
                # promenne - viz gl3_lang.Num), ale App::PropertyInteger
                # nekterych verzi FreeCADu striktne odmitne setattr s
                # float ("type must be int, not float") - je potreba
                # explicitni prevod, ktery driv chybel.
                value = int(round(value))

            setattr(obj, name, value)

    def onDocumentRestored(self, obj):
        self.Type = "GL3Program"


class ViewProviderGL3Program(object):
    """Minimalni ViewProvider - vlastni ikona (viz getIcon()) + claimChildren.

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
        return icon_path("program.svg")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def claimChildren(self):
        obj = self.Object
        doc = obj.Document
        children = []
        for candidate in doc.Objects:
            if candidate is obj:
                continue
            # Rozpoznani GL3Export kandidata pres jeho FC property (Source +
            # Input), NE pres Proxy.Type. Proxy.Type je jen Python atribut
            # nastaveny az v __init__()/onDocumentRestored() - po OTEVRENI
            # ULOZENEHO DOKUMENTU neni zaruceno poradi, ve kterem FreeCAD
            # zavola onDocumentRestored() na VSECHNY objekty vs. kdy zavola
            # claimChildren() na tenhle ViewProvider (typicky se strom stavi
            # hned pri nacteni). Pokud claimChildren() probehne DRIV, nez
            # GL3Export kandidat stihne dostat svuj Proxy.Type (jeste None),
            # export se po otevreni dokumentu objevi ve strome NA STEJNE
            # UROVNI jako GL3Program, misto jako jeho potomek - presne
            # pozorovany bug. FC property (Source, Input) jsou naproti tomu
            # soucasti stavu SAMOTNEHO objektu (ulozene/obnovene primo z
            # dokumentu), takze jsou spolehlive pritomne uz v okamziku, kdy
            # se strom poprve stavi, bez ohledu na to, kdy se Python Proxy
            # re-attachuje.
            if not (hasattr(candidate, "Source") and hasattr(candidate, "Input")):
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
