# -*- coding: utf-8 -*-
"""
gl3_export.py - Export modul (viz shrnuti projektu): z vybraneho
composite vystupu GL3Program objektu vyrobi skutecny nativni FreeCAD
objekt (Part::FeaturePython) s realnym Placement, pouzitelny dal v
Attachmentu/Sketch external geometry/atd.

Cesta je jednosmerna: GL3Program -> GL3Export -> zbytek FreeCADu,
nikdy zpatky (viz architektonicke rozhodnuti). Tenhle modul proto
NEIMPORTUJE gerlib - pracuje jen s JSON-safe "slot" dict formatem z
gerlib.serialize (kazda hodnota {"defined":..., "type":..., ...}),
takze zmena vnitrnich gerlib trid Export modul nijak neovlivni.

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3fc.gl3_props import add_property

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
    return bool(isinstance(slot, dict) and slot.get("defined", False))


def _scalar(slot):
    """Precte skalarni slot ({'defined':True,'value':...}). None, pokud
    nedefinovano."""
    if not _is_defined(slot):
        return None
    return slot["value"]


def _vector3(slot):
    """Point/Vector slot -> FreeCAD.Vector. None, pokud nedefinovano nebo
    kterakoliv souradnice chybi."""
    if not _is_defined(slot):
        return None
    x, y, z = _scalar(slot.get("x")), _scalar(slot.get("y")), _scalar(slot.get("z"))
    if x is None or y is None or z is None:
        return None
    return App.Vector(x, y, z)


def _array_items(slot):
    """Array slot -> list slotu (prazdny list, pokud nedefinovano)."""
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


def _single_bspline_edge(points, tangents):
    """Vsechny uzly definovane, otevrena Spline -> JEDNA Part.BSplineCurve
    hrana (misto N-1 samostatnych Bezier hran spojenych ve Wire).

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
        p0, p1, t0, t1 = points[i], points[i + 1], tangents[i], tangents[i + 1]
        poles.append(p0 + t0 * (1.0 / 3.0))
        poles.append(p1 - t1 * (1.0 / 3.0))
        poles.append(p1)

    knots = list(range(n + 1))
    mults = [4] + [3] * (n - 1) + [4]

    curve = Part.BSplineCurve()
    curve.buildFromPolesMultsKnots(poles, mults, knots, False, 3)
    return curve.toShape()


def _build_spline(slot):
    points_slot = slot.get("points")
    tangents_slot = slot.get("tangents")
    closed = bool(_scalar(slot.get("closed")))

    points = [_vector3(item) for item in _array_items(points_slot)]
    tangents = [_vector3(item) for item in _array_items(tangents_slot)]
    if len(points) != len(tangents):
        raise ValueError(
            "GL3Export: Spline ma nesouhlasny pocet bodu (%d) a tecen (%d)"
            % (len(points), len(tangents))
        )

    all_defined = all(p is not None for p in points) and all(t is not None for t in tangents)

    if all_defined and not closed and len(points) >= 2:
        return _single_bspline_edge(points, tangents)

    # Fallback: nedefinovane mezery, nebo uzavrena Spline (periodicky BSpline
    # zatim neni implementovan) - puvodni pristup po segmentech, kazdy
    # segment vlastni hrana, spojene do Wire.
    pairs = list(zip(range(len(points) - 1), range(1, len(points))))
    if closed and len(points) > 1:
        pairs.append((len(points) - 1, 0))

    edges = []
    for i, j in pairs:
        p0, p1, t0, t1 = points[i], points[j], tangents[i], tangents[j]
        if p0 is None or p1 is None or t0 is None or t1 is None:
            continue  # nedefinovany uzel - segment se preskoci
        edges.append(_hermite_to_bezier_edge(p0, p1, t0, t1))

    if not edges:
        raise ValueError("GL3Export: Spline neobsahuje zadny plne definovany segment")
    return Part.Wire(edges)


def _build_circle(slot):
    center = _vector3(slot.get("center"))
    radius = _scalar(slot.get("radius"))
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
            obj, "App::PropertyLink", "Source", "GL3",
            "GL3Program, ze ktereho se exportuje vystup",
        )
        add_property(
            obj, "App::PropertyString", "OutputName", "GL3",
            "Jmeno vystupni property na Source (napr. 'S' nebo 'PO')",
        )

    def execute(self, obj):
        source = getattr(obj, "Source", None)
        if source is None:
            raise ValueError("GL3Export '%s': Source neni nastaven" % (obj.Name,))

        output_name = getattr(obj, "OutputName", "")
        if not output_name:
            raise ValueError("GL3Export '%s': OutputName neni nastaven" % (obj.Name,))

        if not hasattr(source, output_name):
            raise ValueError(
                "GL3Export '%s': Source '%s' nema property '%s'"
                % (obj.Name, source.Name, output_name)
            )

        slot = getattr(source, output_name)
        if not isinstance(slot, dict):
            raise ValueError(
                "GL3Export '%s': property '%s' na '%s' neni composite (serializovany "
                "slot) - exportovat lze jen composite vystupy GL3Programu"
                % (obj.Name, output_name, source.Name)
            )

        obj.Shape = build_shape(slot)
        # Realny Placement - GL3Program nese svuj lokalni souradny system,
        # Export ho preberá 1:1 (viz architektonicke rozhodnuti: "z vystupu
        # GL3 objektu vyrobi skutecny nativni objekt s realnym Placement").
        obj.Placement = source.Placement

    def onDocumentRestored(self, obj):
        self.Type = "GL3Export"


class ViewProviderGL3Export(object):
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return None

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def create(doc, name, source, output_name):
    """Pomocna funkce pro vytvoreni GL3Export objektu v danem dokumentu."""
    obj = doc.addObject("Part::FeaturePython", name)
    GL3Export(obj)
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        ViewProviderGL3Export(obj.ViewObject)
        obj.ViewObject.Visibility = True
    obj.Source = source
    obj.OutputName = output_name
    return obj
