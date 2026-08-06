# -*- coding: utf-8 -*-
"""Test S01 (GLSPL, chordalni parametrizace) - porovnani se S03 na
realnych datech z TEHLO/E374, plus overeni serializace a exportu."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib import make_spline, make_spline1
from gerlib.serialize import serialize, deserialize


def hermite_point(p0, p1, t0, t1, t):
    h00 = 2 * t**3 - 3 * t**2 + 1
    h10 = t**3 - 2 * t**2 + t
    h01 = -2 * t**3 + 3 * t**2
    h11 = t**3 - t**2
    x = h00 * p0.x + h10 * t0.x + h01 * p1.x + h11 * t1.x
    y = h00 * p0.y + h10 * t0.y + h01 * p1.y + h11 * t1.y
    return x, y


def sample_spline(spline, samples_per_segment=20):
    """Vzorkuje libovolnou Spline (S03 i S01 - pouziva
    segment_tangent_pair(), takze funguje pro oba stejne)."""
    pts = []
    n = len(spline.points) - 1
    for i in range(n):
        t0, t1 = spline.segment_tangent_pair(i)
        p0, p1 = spline.points[i], spline.points[i + 1]
        for k in range(samples_per_segment):
            t = k / samples_per_segment
            pts.append(hermite_point(p0, p1, t0, t1, t))
    pts.append((spline.points[-1].x, spline.points[-1].y))
    return pts


def main():
    from gl3_lang import parse_program
    from gl3_interpreter import Interpreter

    # vlastni fixture kopie v gl3test/, ne "zive" gl3sys/gl3data/gl3examples
    # adresare (ty jsou v plne rezii uzivatele - viz konverzace/README)
    root_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    gl3test_dir = os.path.join(root_dir, "gl3test")

    def load(directory, name):
        with open(os.path.join(directory, name), "r", encoding="utf-8", errors="replace") as f:
            return parse_program(f.read())

    tehlo = load(gl3test_dir, "TEHLO.GL3")
    hlo = load(gl3test_dir, "HLO.GL3")
    interp = Interpreter(registry={"TEHLO": tehlo, "HLO": hlo})
    result = interp.run(tehlo, inputs={"BJM": os.path.join(gl3test_dir, "E374.TXT"), "DH": 15.2})
    points = result["S"].points  # stejna vstupni mnozina bodu pro obe varianty

    spline_uniform = make_spline(points, len(points))
    spline_chordal = make_spline1(points, len(points))

    assert spline_uniform.opcode == "S03" and spline_uniform.parametrization == "uniform"
    assert spline_chordal.opcode == "S01" and spline_chordal.parametrization == "chordal"
    assert spline_chordal.segment_tangents is not None
    assert spline_uniform.segment_tangents is None
    print("Vlajka puvodu: S03 -> opcode=%r parametrization=%r" %
          (spline_uniform.opcode, spline_uniform.parametrization))
    print("Vlajka puvodu: S01 -> opcode=%r parametrization=%r" %
          (spline_chordal.opcode, spline_chordal.parametrization))

    # --- segment_tangent_pair musi davat SPOLECNOU tecnu u S03 (obe strany
    # stejne), ale u S01 obecne RUZNOU tecnu na kazde strane uzlu ---
    t_end_prev, t_start_next = None, None
    differs = 0
    for i in range(len(points) - 2):
        _, t_end_i = spline_chordal.segment_tangent_pair(i)
        t_start_ip1, _ = spline_chordal.segment_tangent_pair(i + 1)
        if (round(t_end_i.x, 9), round(t_end_i.y, 9)) != (round(t_start_ip1.x, 9), round(t_start_ip1.y, 9)):
            differs += 1
    print("S01: pocet vnitrnich uzlu, kde se tecna lisi po stranach segmentu: %d / %d"
          % (differs, len(points) - 2))
    assert differs > 0, "u nerovnomerne rozmistenych bodu (profil) by se tecny mely lisit"

    for i in range(len(points) - 1):
        t0, t1 = spline_uniform.segment_tangent_pair(i)
        t0b, t1b = (spline_uniform.tangents[i], spline_uniform.tangents[i + 1])
        assert (t0.x, t0.y) == (t0b.x, t0b.y) and (t1.x, t1.y) == (t1b.x, t1b.y)
    print("S03: segment_tangent_pair() dava stejnou tecnu jako stary pristup (tangents[i]/[i+1]): OK")

    # --- numericke srovnani vysledne krivky S01 vs S03 ---
    pts_uniform = sample_spline(spline_uniform)
    pts_chordal = sample_spline(spline_chordal)
    assert len(pts_uniform) == len(pts_chordal)
    max_dev = max(
        ((ux - cx) ** 2 + (uy - cy) ** 2) ** 0.5
        for (ux, uy), (cx, cy) in zip(pts_uniform, pts_chordal)
    )
    print("Max. odchylka S01 (chordalni) vs S03 (uniformni) na profilu E374: %.4f mm" % max_dev)
    assert max_dev > 1e-6, "ocekavame realny rozdil mezi metodami (jinak by neco bylo spatne)"

    # --- serializace/deserializace S01 (vc. segment_tangents) ---
    data = serialize(spline_chordal)
    assert data["opcode"] == "S01" and data["parametrization"] == "chordal"
    assert data["segment_tangents"] is not None
    restored = deserialize(data)
    assert restored.opcode == "S01"
    assert restored.segment_tangents is not None
    assert len(restored.segment_tangents) == len(spline_chordal.segment_tangents)
    t0r, t1r = restored.segment_tangent_pair(5)
    t0o, t1o = spline_chordal.segment_tangent_pair(5)
    assert abs(t0r.x - t0o.x) < 1e-12 and abs(t1r.y - t1o.y) < 1e-12
    print("Serializace/deserializace S01 (vc. segment_tangents): OK")

    # --- export (gl3fc) - stejna cesta jako S03, ale pres segment_tangents ---
    import types as _pytypes
    fake_freecad = _pytypes.ModuleType("FreeCAD")

    class _V(object):
        def __init__(self, x, y, z=0.0):
            self.x, self.y, self.z = x, y, z

        def __add__(self, o):
            return _V(self.x + o.x, self.y + o.y, self.z + o.z)

        def __sub__(self, o):
            return _V(self.x - o.x, self.y - o.y, self.z - o.z)

        def __mul__(self, s):
            return _V(self.x * s, self.y * s, self.z * s)

    fake_freecad.Vector = _V

    fake_part = _pytypes.ModuleType("Part")

    class _BSpline(object):
        def buildFromPolesMultsKnots(self, poles, mults, knots, periodic, degree):
            self.poles, self.mults, self.knots = poles, mults, knots

        def toShape(self):
            return ("BSplineEdge", self.poles, self.mults, self.knots)

    fake_part.BSplineCurve = _BSpline
    fake_part.BezierCurve = None
    fake_part.Circle = None

    sys.modules["FreeCAD"] = fake_freecad
    sys.modules["Part"] = fake_part
    from gl3fc.gl3_export import build_shape

    kind, poles, mults, knots = build_shape(data)
    assert kind == "BSplineEdge"
    n_seg = len(points) - 1
    assert len(poles) == 3 * n_seg + 1
    print("Export S01 -> jedna BSplineCurve hrana (%d polu, %d segmentu): OK" % (len(poles), n_seg))

    print()
    print("VSE OK - S01 (GLSPL, chordalni) funguje samostatne vedle S03 (uniformni),")
    print("nese vlastni vlajku puvodu, ma jinou (obecne) tecnu po stranach segmentu,")
    print("a da numericky odlisnou krivku na realnem profilu.")


if __name__ == "__main__":
    main()
