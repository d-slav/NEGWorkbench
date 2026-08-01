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


def _build_curve(slot):
    points_slot = slot.get("points")
    vectors = [_vector3(item) for item in _array_items(points_slot)]
    defined_vectors = [v for v in vectors if v is not None]
    if len(defined_vectors) < 2:
        raise ValueError("GL3Export: retezec (Curve) ma min nez 2 definovane body")
    edges = []
    for i in range(len(vectors) - 1):
        if vectors[i] is None or vectors[i + 1] is None:
            continue  # nedefinovana mezera - segment se preskoci
        edges.append(Part.makeLine(vectors[i], vectors[i + 1]))
    return Part.Wire(edges)


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
        raise NotImplementedError(
            "GL3Export: export pole typu '%s' zatim neni podporovan" % (item_kind,)
        )

    builder = _BUILDERS.get(kind)
    if builder is None:
        raise NotImplementedError(
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
        #    Presunuto do create() (zavolano PRED prvnim doc.recompute()),
        #    kde se to vyresi jako soucast te same, jeste neprobehle davky.

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
    # claimChildren()) - Source se timhle zaradi do SAME recompute davky
    # (misto aby to delal execute() teto Export instance UPROSTRED
    # recomputu, coz FreeCAD hlasilo jako "still touched after recompute" -
    # viz komentar v execute() vyse).
    try:
        source.touch()
    except AttributeError:
        pass

    return obj
