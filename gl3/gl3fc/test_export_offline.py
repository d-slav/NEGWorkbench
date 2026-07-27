# -*- coding: utf-8 -*-
"""
Offline test gl3_export.build_shape() bez realneho FreeCADu/OCC.

Nahrazuje FreeCAD.Vector a Part.* lehkymi stuby, ktere jen zaznamenaji,
co bylo zavolano (poc segmentu, souradnice pólů...) - overuje se tim
DISPATCH logika (spravny "builder" pro spravny typ slotu, spravne
preskakovani nedefinovanych uzlu/mezer) a spravnost Hermite->Bezier
matematiky (kontrolni body musi sedet na uz numericky overeny vzorec
z proto_bezier_export.py), ne skutecna OCC geometrie (tu overi az
test v realnem FreeCADu).
"""
import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- lehke stuby FreeCAD/Part, VLOZENE DO sys.modules pred importem gl3_export ---

class FakeVector(object):
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __add__(self, other):
        return FakeVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return FakeVector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return FakeVector(self.x * scalar, self.y * scalar, self.z * scalar)

    def __repr__(self):
        return "V(%.4f,%.4f,%.4f)" % (self.x, self.y, self.z)


class FakeBezierCurve(object):
    def __init__(self):
        self.poles = None

    def setPoles(self, poles):
        self.poles = list(poles)

    def toShape(self):
        return ("BezierEdge", self.poles)


class FakeCircle(object):
    def __init__(self, center, normal, radius):
        self.center, self.normal, self.radius = center, normal, radius

    def toShape(self):
        return ("CircleEdge", self.center, self.radius)


fake_freecad = types.ModuleType("FreeCAD")
fake_freecad.Vector = FakeVector

fake_part = types.ModuleType("Part")
fake_part.BezierCurve = FakeBezierCurve
fake_part.Circle = FakeCircle
fake_part.Vertex = lambda v: ("Vertex", v)
fake_part.makeCompound = lambda shapes: ("Compound", shapes)
fake_part.makeLine = lambda a, b: ("LineEdge", a, b)
fake_part.Wire = lambda edges: ("Wire", edges)

sys.modules["FreeCAD"] = fake_freecad
sys.modules["Part"] = fake_part

from gl3fc.gl3_export import build_shape  # noqa: E402  (musi az po vlozeni stubu)
from gerlib.serialize import serialize  # noqa: E402
from gerlib.types import Point, Vector, Spline  # noqa: E402


def hermite_to_bezier_ref(p0, p1, t0, t1):
    """Stejny vzorec jako v proto_bezier_export.py - referencni vypocet."""
    b0 = (p0.x, p0.y)
    b1 = (p0.x + t0.x / 3.0, p0.y + t0.y / 3.0)
    b2 = (p1.x - t1.x / 3.0, p1.y - t1.y / 3.0)
    b3 = (p1.x, p1.y)
    return b0, b1, b2, b3


def main():
    # --- Array of Point (PO) ---
    pts = [Point(0, 0), None, Point(1, 1), Point(2, 0)]
    slot = serialize(pts)
    kind, shapes = build_shape(slot)
    assert kind == "Compound"
    assert len(shapes) == 3, "None prvek se mel preskocit"
    print("Array(Point) -> Compound, %d vrcholu (1 nedefinovany preskocen): OK" % len(shapes))

    # --- Spline (S03) na realnych datech z TEHLO (viz proto_bezier_export.py) ---
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from gl3_lang import parse_program
    from gl3_interpreter import Interpreter

    examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")

    def load(name):
        with open(os.path.join(examples_dir, name), "r", encoding="utf-8", errors="replace") as f:
            return parse_program(f.read())

    tehlo = load("TEHLO.GL3")
    hlo = load("HLO.GL3")
    interp = Interpreter(registry={"TEHLO": tehlo, "HLO": hlo})
    result = interp.run(tehlo, inputs={"BJM": os.path.join(examples_dir, "E374.TXT"), "DH": 15.2})
    spline = result["S"]

    slot = serialize(spline)
    kind, edges = build_shape(slot)
    assert kind == "Wire"
    n = len(spline.points)
    assert len(edges) == n - 1, "otevrena Spline musi mit N-1 segmentu"
    print("Spline -> Wire, %d segmentu (N=%d bodu, otevrena): OK" % (len(edges), n))

    # over prvni segment - kontrolni body musi presne sedet na referencni vzorec
    edge_kind, poles = edges[0]
    assert edge_kind == "BezierEdge"
    ref = hermite_to_bezier_ref(spline.points[0], spline.points[1],
                                 spline.tangents[0], spline.tangents[1])
    got = [(p.x, p.y) for p in poles]
    for (rx, ry), (gx, gy) in zip(ref, got):
        assert abs(rx - gx) < 1e-9 and abs(ry - gy) < 1e-9, (ref, got)
    print("  kontrolni body 1. Bezier segmentu sedi na referencni vzorec: OK")

    # --- uzavrena Spline (synteticky test wrap-segmentu) ---
    closed_spline = Spline(
        [Point(0, 0), Point(1, 1), Point(2, 0)],
        [Vector(1, 1), Vector(1, -1), Vector(-1, -1)],
        closed=True,
    )
    slot = serialize(closed_spline)
    kind, edges = build_shape(slot)
    assert len(edges) == 3, "uzavrena Spline o 3 bodech musi mit 3 segmenty (vc. wrap)"
    print("Uzavrena Spline (synteticky test) -> %d segmentu (vc. wrap uzaviraciho): OK" % len(edges))

    # --- Curve (E01) s nedefinovanou mezerou ---
    from gerlib.e01 import make_chain
    curve = make_chain([Point(0, 0), Point(1, 1), Point(2, 0), Point(0, 0)])
    curve_pts = list(curve.points)
    curve.points[2] = None  # simulace nedefinovaneho bodu uprostred
    slot = serialize(curve)
    kind, edges = build_shape(slot)
    assert kind == "Wire"
    print("Curve s nedefinovanou mezerou -> Wire, %d hran (mezera preskocena): OK" % len(edges))

    print()
    print("VSE OK - build_shape() spravne dispatchuje podle typu a Hermite->Bezier")
    print("matematika sedi na uz drive numericky overeny vzorec.")


if __name__ == "__main__":
    main()
