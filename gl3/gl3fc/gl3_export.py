# -*- coding: utf-8 -*-
"""
gl3_export.py - Export modul (viz shrnuti projektu): z vybraneho
composite vystupu GL3Program objektu vyrobi skutecny nativni FreeCAD
objekt (Part::FeaturePython) s realnym Placement, pouzitelny dal v
Attachmentu/Sketch external geometry/atd.

Cesta je jednosmerna: GL3Program -> GL3Export -> zbytek FreeCADu,
nikdy zpatky (viz architektonicke rozhodnuti). Tenhle modul proto
NEIMPORTUJE gerlib - pracuje jen s JSON-safe "slot" dict formatem z
gerlib.serialize (kazda hodnota {"defined":..., "type":..., ...}).

GL3Program composite "out" property (viz gl3_program.py) je typu
App::PropertyString a drzi tenhle slot jako SKUTECNY JSON text
(gerlib.serialize.dump_json(), kompaktne bez odsazeni) - kvuli
viditelnosti v Property View bez "Show all" (PropertyPythonObject
nema editor). execute() proto text nejdriv precte pres json.loads()
(porad zadna zavislost na gerlib - jen stdlib json), az pak vola
build_shape() na uz hotovem dictu.

Zdroj vystupu (Input): JEDNA textova property ve formatu
'JmenoObjektu.JmenoVystupu' (napr. 'TEHLO002.PO') - citelna, editovatelna,
da se vlozit odkudkoli. Pod kapotou se ale drzi skryta App::PropertyLink
"Source" (viz gl3_props.add_hidden_link/parse_ref), synchronizovana s
Input pres onChanged() - DUVOD: bez skutecneho Linku by FreeCAD
nevedel o zavislosti Export->Program ve svem grafu, a poradi recompute
by prestalo byt garantovane (hrozila by zastarala data po zmene Source
objektu). onChanged() se vola SYNCHRONNE hned pri zmene Input
(i programove, ne jen z GUI), takze Source je aktualni jeste pred tim,
nez se vubec sestavi poradi pro dalsi recompute.

Prevod Spline (S03, kubicky Hermitovsky splajn) na Part.Wire jde pres
presnou identitu Hermite->Bezier (overeno numericky, viz
proto_bezier_export.py - odchylka radu 1e-15, ne aproximace):

    B0 = P_i,  B1 = P_i + T_i/3,  B2 = P_{i+1} - T_{i+1}/3,  B3 = P_{i+1}

Podporovane typy vystupu (podle slot["type"]):
    Point   -> Part.Vertex
    Array (prvky Point) -> compound vrcholu (nedefinovane/None prvky se
              preskoci)
    Array (prvky Curve nebo Spline) -> compound jednotlivych vysledku
              (kazdy prvek pole se postavi stejnym zpusobem jako
              samostatny Curve/Spline nize, nedefinovane prvky pole se
              preskoci)
    Curve   -> polyline (Part.Wire) skrz definovane body v poradi (uzavrenost
              je uz dana shodou prvniho/posledniho bodu - viz E01, zadna
              extra "uzaviraci" hrana neni potreba)
    Spline  -> Part.Wire z kubickych Bezier segmentu (viz vyse), s
              preskocenim segmentu, kde je nektery koncovy uzel nedefinovany
    Circle  -> Part.Circle jako uzavrena hrana
Line/Plane/3D typy (Q/U/R/M/G/T/H/F) zatim NEJSOU podporovany - viz
otevrene otazky v shrnuti projektu (nejednoznacne cislovani slozek).
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3fc.gl3_props import add_property, add_hidden_link, parse_ref, icon_path

try:
    import FreeCAD as App
    import Part
except ImportError:  # umoznuje syntax-check/testy mimo FreeCAD
    App = None
    Part = None


# ---------------------------------------------------------------------------
# Cteni "slot" dict (viz gerlib.serialize) - zadna zavislost na gerlib
# ---------------------------------------------------------------------------

def _is_defined(slot):
    """True pro 'slot' dict s defined=True (top-level vystup nebo prvek
    pole). Bare vnorene pole (Line.origin, Circle.center,...) nemaji
    vlastni 'defined' klic vubec - ty se ctou primo pres _vector3()/
    primym pristupem k dict['field'], ne pres tuhle funkci."""
    return bool(isinstance(slot, dict) and slot.get("defined", False))


def _scalar(slot):
    """Precte skalarni TOP-LEVEL/ARRAY-ITEM slot ({'defined':True,
    'value':...}). None, pokud nedefinovano. Pro skalarni POLE jiz
    definovaneho objektu (napr. Circle['radius'], Spline['closed']) se
    ctou HODNOTY PRIMO (jsou to hole Python hodnoty, ne dalsi slot) -
    tahle funkce se na ne nepouziva."""
    if not _is_defined(slot):
        return None
    return slot["value"]


def _vector3(body):
    """Point/Vector - bud plny slot (top-level/prvek pole, ma 'defined'),
    nebo bare vnorene pole jiz definovaneho objektu (Line.origin,
    Circle.center/normal - bez 'defined', ale se stejnymi 'type'/'x'/'y'/
    'z' klici). V obou pripadech vraci FreeCAD.Vector, nebo None, pokud
    je vstup nedefinovany/chybny."""
    if not isinstance(body, dict):
        return None
    if body.get("defined") is False:  # explicitni nedefinovany slot
        return None
    if body.get("type") not in ("Point", "Vector"):
        return None
    x, y, z = body.get("x"), body.get("y"), body.get("z")
    if x is None or y is None or z is None:
        return None
    return App.Vector(x, y, z)


def _array_items(slot):
    """Array slot ({'defined':True,'type':'Array','items':[...]}) -> list
    slotu (prazdny list, pokud nedefinovano)."""
    if not _is_defined(slot) or slot.get("type") != "Array":
        return []
    return slot.get("items", [])


# ---------------------------------------------------------------------------
# Stavba geometrie podle typu
# ---------------------------------------------------------------------------

def _hermite_to_bezier_edge(p0, p1, t0, t1):
    b0 = p0
    b1 = p0 + t0 * (1.0 / 3.0)
    b2 = p1 - t1 * (1.0 / 3.0)
    b3 = p1
    bez = Part.BezierCurve()
    bez.setPoles([b0, b1, b2, b3])
    return bez.toShape()


def _build_point(slot):
    v = _vector3(slot)
    if v is None:
        raise ValueError("GL3Export: bod je nedefinovany, neni co exportovat")
    return Part.Vertex(v)


def _build_point_array(slot):
    vectors = [_vector3(item) for item in _array_items(slot)]
    vectors = [v for v in vectors if v is not None]
    if not vectors:
        raise ValueError("GL3Export: pole neobsahuje zadny definovany bod")
    return Part.makeCompound([Part.Vertex(v) for v in vectors])


def _build_shape_array(slot, item_kind):
    """Pole retezcu (Curve) nebo krivek (Spline) -> Part.Compound
    jednotlivych vysledku - kazdy definovany prvek pole se postavi
    UPLNE STEJNYM builderem jako pri exportu jednoho samostatneho
    retezce/krivky (viz _build_curve/_build_spline nize, vc. jejich
    vlastniho osetreni mezer/nedefinovanych uzlu u kazdeho prvku
    zvlast), analogicky _build_point_array vyse. Nedefinovane prvky
    pole (viz IFN idiom) se preskoci, stejne jako u pole bodu."""
    builder = _BUILDERS[item_kind]
    shapes = []
    for item in _array_items(slot):
        if not _is_defined(item):
            continue
        shapes.append(builder(item))
    if not shapes:
        raise ValueError(
            "GL3Export: pole neobsahuje zadny definovany prvek typu '%s'" % (item_kind,)
        )
    return Part.makeCompound(shapes)


def _build_curve(slot):
    """Curve -> Part.Wire (nebo Part.Compound vice Part.Wire, jsou-li v
    retezci mezery - viz nize).

    POZOR (puvodni chyba - viz zpetna vazba uzivatele "BRep_API: command
    not done"): skutecne OCC Part.Wire(edges) vyzaduje, aby VSECHNY
    predane hrany tvorily JEDEN souvisly retezec - na rozdil od offline
    testovaciho FakePart (ten zadnou topologii nekontroluje) skutecny OCC
    odmitne sadu hran, ktera obsahuje vic nez jeden nesouvisly kus (coz
    presne nastane, kdyz se mezi hranami jednoduse preskoci mezera/None -
    to, co drive delal tento kod, bylo funkcni jen v testech, ne v
    realnem FreeCADu). Proto se retezec s mezerami rozdeli na jednotlive
    SOUVISLE useky (kazdy min. 2 body) a KAZDY se postavi jako VLASTNI
    Part.Wire zvlast; je-li useku vic nez jeden, vysledek se zabali do
    Part.Compound (validni Shape, zobrazi vsechny kusy najednou)."""
    points_slot = slot.get("points")
    vectors = [_vector3(item) for item in _array_items(points_slot)]
    defined_vectors = [v for v in vectors if v is not None]
    if len(defined_vectors) < 2:
        raise ValueError("GL3Export: retezec (Curve) ma min nez 2 definovane body")

    runs = []
    current = []
    for v in vectors:
        if v is None:
            if len(current) >= 2:
                runs.append(current)
            current = []
        else:
            current.append(v)
    if len(current) >= 2:
        runs.append(current)

    wires = []
    for run in runs:
        edges = [Part.makeLine(run[i], run[i + 1]) for i in range(len(run) - 1)]
        wires.append(Part.Wire(edges))

    if len(wires) == 1:
        return wires[0]
    return Part.makeCompound(wires)


def _single_bspline_edge(points, segment_pairs):
    """Vsechny uzly definovane, otevrena Spline -> JEDNA Part.BSplineCurve
    hrana (misto N-1 samostatnych Bezier hran spojenych ve Wire).

    segment_pairs[i] = (tecna_na_zacatku_segmentu_i, tecna_na_konci_segmentu_i)
    - obecne, funguje stejne pro spolecnou tecnu na uzel (S03) i pro
    rozdilne tecny po stranach uzlu (S01, viz Spline.segment_tangents).

    Pouziva standardni "Bezier segmenty jako jeden BSpline" konstrukci:
    stupen 3, N+1 uzlovych hodnot (0..N), nasobnost 4 na krajich (clamped),
    nasobnost 3 (=stupen) na vnitrnich uzlech. Kontrolni body jsou uplne
    stejne, jako u drivejsiho po-segmentech pristupu (viz
    _hermite_to_bezier_edge) - jde jen o jinak zabaleny, geometricky
    identicky vysledek, tentokrat jako jedna vybiratelna hrana/krivka.
    """
    n = len(points) - 1  # pocet segmentu

    poles = [points[0]]
    for i in range(n):
        p0, p1 = points[i], points[i + 1]
        t0, t1 = segment_pairs[i]
        poles.append(p0 + t0 * (1.0 / 3.0))
        poles.append(p1 - t1 * (1.0 / 3.0))
        poles.append(p1)

    knots = list(range(n + 1))
    mults = [4] + [3] * (n - 1) + [4]

    curve = Part.BSplineCurve()
    curve.buildFromPolesMultsKnots(poles, mults, knots, False, 3)
    return curve.toShape()


def _spline_segment_pairs(slot, n_segments):
    """Vrati seznam n_segments dvojic (t_start,t_end) - z 'segment_tangents'
    (S01, obecne ruzne tecny po stranach uzlu), nebo z 'tangents' (S03,
    stejna tecna sdilena obema segmenty na uzlu), podle toho, co slot
    obsahuje. Prvek je None, pokud dany segment nema plne definovane
    obe tecny (nedefinovany uzel/tecna)."""
    seg_slot = slot.get("segment_tangents")
    if seg_slot is not None:
        pairs = []
        for i in range(n_segments):
            t0_body, t1_body = seg_slot[i]
            t0, t1 = _vector3(t0_body), _vector3(t1_body)
            pairs.append((t0, t1) if (t0 is not None and t1 is not None) else None)
        return pairs

    tangents = [_vector3(item) for item in _array_items(slot.get("tangents"))]
    pairs = []
    for i in range(n_segments):
        t0, t1 = tangents[i], tangents[i + 1]
        pairs.append((t0, t1) if (t0 is not None and t1 is not None) else None)
    return pairs


def _build_spline(slot):
    points_slot = slot.get("points")
    closed = bool(slot.get("closed"))

    points = [_vector3(item) for item in _array_items(points_slot)]
    if len(points) < 2:
        raise ValueError("GL3Export: Spline ma min nez 2 body")

    n_segments = len(points) - 1
    segment_pairs = _spline_segment_pairs(slot, n_segments)

    all_defined = all(p is not None for p in points) and all(pr is not None for pr in segment_pairs)

    if all_defined and not closed and len(points) >= 2:
        return _single_bspline_edge(points, segment_pairs)

    # Fallback: nedefinovane mezery, nebo uzavrena Spline (periodicky BSpline
    # zatim neni implementovan) - puvodni pristup po segmentech, kazdy
    # segment vlastni hrana, spojene do Wire.
    edges = []
    for i in range(n_segments):
        if points[i] is None or points[i + 1] is None or segment_pairs[i] is None:
            continue  # nedefinovany uzel/tecna - segment se preskoci
        t0, t1 = segment_pairs[i]
        edges.append(_hermite_to_bezier_edge(points[i], points[i + 1], t0, t1))

    if closed and len(points) > 1 and points[-1] is not None and points[0] is not None:
        # wrap segment (posledni bod -> prvni) - jen pro spolecnou tecnu na
        # uzel (S03 styl); segment_tangents (S01) periodicky pripad zatim
        # neresi (DSPP/GTRIP nejsou implementovany - viz projektove poznamky).
        tangents = [_vector3(item) for item in _array_items(slot.get("tangents"))]
        if tangents and tangents[-1] is not None and tangents[0] is not None:
            edges.append(_hermite_to_bezier_edge(points[-1], points[0], tangents[-1], tangents[0]))

    if not edges:
        raise ValueError("GL3Export: Spline neobsahuje zadny plne definovany segment")
    return Part.Wire(edges)


def _build_circle(slot):
    center = _vector3(slot.get("center"))
    radius = slot.get("radius")
    normal = _vector3(slot.get("normal")) or App.Vector(0, 0, 1)
    if center is None or radius is None:
        raise ValueError("GL3Export: Circle nema definovany stred nebo polomer")
    circle = Part.Circle(center, normal, radius)
    return circle.toShape()


_BUILDERS = {
    "Point": _build_point,
    "Curve": _build_curve,
    "Spline": _build_spline,
    "Circle": _build_circle,
}


def build_shape(slot):
    """slot (viz gerlib.serialize) -> Part.Shape. Vyhazuje jasnou chybu pro
    nepodporovane/nedefinovane vstupy."""
    if not _is_defined(slot):
        raise ValueError("GL3Export: vybrany vystup je nedefinovany (defined=False)")

    kind = slot.get("type")

    if kind == "Array":
        items = slot.get("items", [])
        item_kind = next((it.get("type") for it in items if _is_defined(it)), None)
        if item_kind == "Point":
            return _build_point_array(slot)
        if item_kind in ("Curve", "Spline"):
            return _build_shape_array(slot, item_kind)
        raise ValueError(
            "GL3Export: export pole typu '%s' zatim neni podporovan" % (item_kind,)
        )

    builder = _BUILDERS.get(kind)
    if builder is None:
        raise ValueError(
            "GL3Export: export typu '%s' zatim neni podporovan "
            "(otevrena otazka v architekture - viz shrnuti projektu)" % (kind,)
        )
    return builder(slot)


# ---------------------------------------------------------------------------
# FreeCAD objekt
# ---------------------------------------------------------------------------

class GL3Export(object):
    """Proxy pro Part::FeaturePython objekt typu GL3Export."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "GL3Export"

        add_property(
            obj, "App::PropertyString", "Input", "GL3",
            "VSTUP tohoto exportu: odkaz na composite vystup jineho GL3 "
            "objektu ve formatu 'JmenoObjektu.JmenoVystupu' (napr. "
            "'TEHLO002.PO'), volitelne s indexem prvku pole '(N)' "
            "(1 = prvni), napr. 'TEHLO002.PO(1)'",
        )
        # Skryty Link, drzeny synchronizovany s Input pres onChanged()
        # (viz modulovy docstring) - NIKDY nenastavovat rucne, jen ke cteni.
        add_hidden_link(
            obj, "Source", "GL3",
            "(interni) automaticky odvozeny odkaz na zdrojovy objekt z "
            "Input - nemenit rucne, slouzi jen FreeCAD dependency "
            "grafu pro spravne poradi recompute",
        )
        self._resync_source(obj)

        # Placement je 100% odvozeny ze Source (viz execute() nize) - kazdy
        # recompute ho prepise, takze rucni editace v Property View by se
        # tise ztratila pri dalsim recomputu. Radeji skryt (misto jen
        # ReadOnly), at neni zdanlive editovatelny bez efektu.
        try:
            obj.setPropertyStatus("Placement", "Hidden")
        except AttributeError:
            pass

    def onChanged(self, obj, prop):
        if prop == "Input":
            self._resync_source(obj)
            # Zmena vstupu ma rovnou spustit prepocet - jinak by uzivatel
            # musel po kazde zmene Input rucne kliknout Refresh (viz
            # stejny duvod v gl3_program.py GL3Program.onChanged()).
            try:
                obj.Document.recompute()
            except AttributeError:
                pass  # napr. objekt jeste neni plne pripojeny k dokumentu

    @staticmethod
    def _resync_source(obj):
        """Prepocita skryty Link 'Source' z aktualniho textu 'Input'."""
        if not hasattr(obj, "Source"):
            return  # jeste pred pridanim property (prvni radek __init__)
        src_obj_name, _output_name, _index = parse_ref(getattr(obj, "Input", "") or "")
        new_source = None
        if src_obj_name is not None and getattr(obj, "Document", None) is not None:
            new_source = obj.Document.getObject(src_obj_name)
        if getattr(obj, "Source", None) is not new_source:
            obj.Source = new_source

    def execute(self, obj):
        """Tenky wrapper okolo _execute_impl() - viz stejnojmenna metoda
        v gl3_program.GL3Program pro presny duvod (zkraceni tracebacku,
        ktery FreeCAD vypisuje do Report View pri kazde vyjimce
        prosakujici z execute()) i pro duvod bezpecnostniho fallbacku na
        RuntimeError."""
        try:
            self._execute_impl(obj)
        except Exception as e:
            try:
                short = type(e)(str(e))
            except Exception:
                short = RuntimeError(str(e))
            raise short from None

    def _execute_impl(self, obj):
        # Pojistka navic k onChanged() - napr. tesne po otevreni dokumentu,
        # kdyby onChanged() z nejakeho duvodu jeste neproběhlo.
        self._resync_source(obj)

        ref = getattr(obj, "Input", "") or ""
        src_obj_name, output_name, index = parse_ref(ref)
        if src_obj_name is None:
            raise ValueError(
                "GL3Export '%s': Input musi byt ve formatu "
                "'JmenoObjektu.JmenoVystupu' nebo 'JmenoObjektu.JmenoVystupu(Index)' "
                "(napr. 'TEHLO002.PO' nebo 'TEHLO002.PO(1)'), je: %r" % (obj.Name, ref)
            )

        source = getattr(obj, "Source", None)
        if source is None:
            raise ValueError(
                "GL3Export '%s': objekt '%s' (z Input '%s') v dokumentu "
                "neexistuje" % (obj.Name, src_obj_name, ref)
            )

        if not hasattr(source, output_name):
            raise ValueError(
                "GL3Export '%s': zdroj '%s' nema property '%s' (Input '%s')"
                % (obj.Name, source.Name, output_name, ref)
            )

        raw = getattr(source, output_name)
        if not isinstance(raw, str):
            raise ValueError(
                "GL3Export '%s': property '%s' na '%s' neni retezec (JSON text) - "
                "exportovat lze jen composite vystupy GL3Programu (viz GL3 Out)"
                % (obj.Name, output_name, source.Name)
            )
        try:
            slot = json.loads(raw)
        except ValueError as exc:
            raise ValueError(
                "GL3Export '%s': property '%s' na '%s' neni platny JSON: %s"
                % (obj.Name, output_name, source.Name, exc)
            )
        if not isinstance(slot, dict):
            raise ValueError(
                "GL3Export '%s': property '%s' na '%s' neni composite (serializovany "
                "slot) - exportovat lze jen composite vystupy GL3Programu"
                % (obj.Name, output_name, source.Name)
            )

        if index is not None:
            if slot.get("type") != "Array":
                raise ValueError(
                    "GL3Export '%s': index '(%d)' v Input lze pouzit jen na "
                    "Array vystup - '%s' na '%s' je typu '%s'"
                    % (obj.Name, index, output_name, source.Name, slot.get("type"))
                )
            items = slot.get("items", [])
            if not (1 <= index <= len(items)):
                raise ValueError(
                    "GL3Export '%s': index %d mimo rozsah - '%s' na '%s' ma %d "
                    "prvku (index je od 1 = prvni prvek)"
                    % (obj.Name, index, output_name, source.Name, len(items))
                )
            slot = items[index - 1]

        obj.Shape = build_shape(slot)
        # Realny Placement - GL3Program nese svuj lokalni souradny system,
        # Export ho preberá 1:1 (viz architektonicke rozhodnuti: "z vystupu
        # GL3 objektu vyrobi skutecny nativni objekt s realnym Placement").
        obj.Placement = source.Placement

        # POZOR: zde uz NENASTAVUJEME vobj.Visibility = True ani
        # nevolame source.touch() - obojí puvodne resilo drobne kosmeticke
        # problemy (neviditelny Shape po prvnim vytvoreni / strom
        # nezobrazujici noveho potomka), ale za cenu 2 realnych bugu:
        # 1) Kazdy recompute prepisoval Visibility na True, i kdyz si
        #    uzivatel objekt rucne schoval (nebo skryl cely Program -
        #    viz ViewProviderGL3Program.onChanged nize) - Visibility se
        #    tedy nastavuje jen JEDNOU, pri vytvoreni (viz create()).
        # 2) source.touch() volany TADY (uvnitr execute() teto Export
        #    instance, tedy UPROSTRED prave probihajiciho recompute) znovu
        #    oznacil Source (GL3Program) jako touched PO TOM, co uz v tomhle
        #    pruchodu byl hotovy - FreeCAD po dokonceni recompute() hlasi
        #    "Unnamed#<Name> still touched after recompute", protoze
        #    nedojde k dalsimu prepoctu, ktery by touched flag zase smazal.
        #    Reseni: source.touch() se vola JEN v create() (viz tam, PRED
        #    prvnim doc.recompute() volanym volajicim) - ne tady.

    def onDocumentRestored(self, obj):
        self.Type = "GL3Export"
        self._resync_source(obj)


class ViewProviderGL3Export(object):
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return icon_path("export.svg")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def create(doc, name, source, output_name, index=None):
    """Pomocna funkce pro vytvoreni GL3Export objektu v danem dokumentu.

    source/output_name/index zustavaji jako oddelene argumenty (pohodlnejsi
    API pro volajici, viz gl3_commands.CreateGL3ExportCommand) - uvnitr se
    ale slozi do JEDNE textove reference 'source.Name.output_name' (+
    volitelne '(index)') ulozene do Input (viz modulovy docstring - duvod
    pro tenhle format)."""
    obj = doc.addObject("Part::FeaturePython", name)
    GL3Export(obj)
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        ViewProviderGL3Export(obj.ViewObject)
        obj.ViewObject.Visibility = True
    ref = "%s.%s" % (source.Name, output_name)
    if index is not None:
        ref = "%s(%d)" % (ref, index)
    obj.Input = ref

    # "touchnuti" Source (JEDNOU, tady, PRED prvnim doc.recompute() volanym
    # volajicim) zajisti, ze strom po tomhle recomputu spravne zobrazi
    # novy Export jako potomka Source (viz ViewProviderGL3Program.
    # claimChildren()) - OVERENO na zivem FreeCADu (viz zpetna vazba), ze
    # bez tohohle se novy Export objevi na STEJNE UROVNI jako Source, misto
    # jako jeho potomek, dokud Source neprojde nejakym DALSIM prepoctem.
    #
    # POZOR: touch() sam o sobe VZDY vynuti volani GL3Program.execute() -
    # to by bylo drahe (znovunacteni .GL3 souboru + beh cele interpretu)
    # pri kazdem pridani exportu, i kdyz se na vstupech Source nic
    # nezmenilo. Reseni je na druhe strane: GL3Program.execute() ma
    # vlastni levnou "nezmenilo se nic podstatneho?" kontrolu (viz
    # gl3_program.GL3Program._exec_cache) a v tom pripade se rychle vrati
    # beze skutecne prace - FreeCAD tak porad dostane svuj "touched ->
    # execute() zavolano -> touched smazano" cyklus (potrebny pro spravne
    # zarazeni ve strome), ale drahou cast prace to presto neudela
    # zbytecne znovu.
    try:
        source.touch()
    except AttributeError:
        pass

    return obj
