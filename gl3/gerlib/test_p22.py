# -*- coding: utf-8 -*-
"""Test GLPRU (implicitni rovnice primky, pruseciky po segmentech) a
P22 (K-ty prusecik primky s krivkou).

Zdroj: P22.FOR + GLPRU.FOR (dodano uzivatelem). GLDPL3 (resic kubiky)
nedodan - nahrazeno uz existujici obecnou real_roots_in_range (P42)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line, Spline
from gerlib.glpru import implicit_line, line_curve_intersections
from gerlib.p22 import intersection


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- implicit_line: vodorovna primka y=3 (bod (0,3), smer (1,0)) ---
    rr = implicit_line(Line(Point(0.0, 3.0, 0.0), Vector(1.0, 0.0, 0.0)))
    # f(x,y) = rr0*x+rr1*y+rr2 = 0 musi platit pro (x,3) pro libovolne x
    check(math.isclose(rr[0] * 5.0 + rr[1] * 3.0 + rr[2], 0.0, abs_tol=1e-9),
          "implicit_line: bod na primce splnuje implicitni rovnici")
    check(not math.isclose(rr[0] * 5.0 + rr[1] * 4.0 + rr[2], 0.0, abs_tol=1e-6),
          "implicit_line: bod mimo primku rovnici nesplnuje")

    # --- primka jako degenerovana kubika, prusecik s jinou primkou (K=1) ---
    seg_p0, seg_p1 = Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)
    seg_t0 = seg_t1 = Vector(10.0, 0.0, 0.0)
    line_spline = Spline([seg_p0, seg_p1], [seg_t0, seg_t1])
    vertical = Line(Point(4.0, -5.0, 0.0), Vector(0.0, 1.0, 0.0))  # x=4
    hit = intersection(line_spline, vertical, 1)
    check(math.isclose(hit.x, 4.0) and math.isclose(hit.y, 0.0), "P22: prusecik primky s primkou (x=4, y=0)")

    # --- parabola y=x^2 (presna Hermitova reprezentace, viz test_d50.py) ---
    # vodorovna primka y=0.5 protina parabolu v x=+-sqrt(0.5), ale segment
    # pokryva jen t=x v <0,1>, takze jen JEDEN prusecik (x=sqrt(0.5))
    p0, p1 = Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)
    t0, t1 = Vector(1.0, 0.0, 0.0), Vector(1.0, 2.0, 0.0)
    parabola = Spline([p0, p1], [t0, t1])
    horiz = Line(Point(0.0, 0.5, 0.0), Vector(1.0, 0.0, 0.0))
    hits = line_curve_intersections(parabola, horiz)
    check(len(hits) == 1, "P22: primka y=0.5 protina otevrenou parabolu jen jednou (druhy koren mimo <0,1>)")
    check(math.isclose(hits[0][2].x, math.sqrt(0.5), rel_tol=1e-6),
          "P22: x-souradnice pruseciku souhlasi s analytickym vzorcem sqrt(0.5)")

    # primka, ktera parabolu vubec neprotne (nad vrcholem otevrene nahoru)
    miss = Line(Point(0.0, -1.0, 0.0), Vector(1.0, 0.0, 0.0))  # y=-1, parabola ma y>=0
    check(len(line_curve_intersections(parabola, miss)) == 0, "P22: primka mimo dosah krivky -> zadny prusecik")

    # --- vice segmentu, dva pruseciky, K vybira poradi ---
    # dve rovne useky tvorici stupinky: (0,0)-(2,0) a (2,0)-(4,2) (lomena primka)
    pts3 = [Point(0.0, 0.0, 0.0), Point(2.0, 0.0, 0.0), Point(4.0, 2.0, 0.0)]
    tans3 = [Vector(2.0, 0.0, 0.0), Vector(2.0, 0.0, 0.0), Vector(2.0, 2.0, 0.0)]
    broken_line = Spline(pts3, tans3)
    diag = Line(Point(0.0, 1.0, 0.0), Vector(1.0, 0.0, 0.0))  # y=1
    hits2 = line_curve_intersections(broken_line, diag)
    check(len(hits2) == 1, "P22: y=1 protina lomenou primku jen na druhem useku (prvni je na y=0)")
    check(math.isclose(hits2[0][2].y, 1.0), "P22: prusecik ma y=1")

    # --- prusecik presne v uzlu (spoji segmentu) - nesmi se zdvojit ---
    through_node = Line(Point(2.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0))  # x=2, prochazi uzlem (2,0)
    hits3 = line_curve_intersections(broken_line, through_node)
    check(len(hits3) == 1, "P22: primka presne uzlem ma jen JEDEN prusecik (deduplikovano)")

    # --- chybove stavy ---
    try:
        intersection(line_spline, vertical, 0)
        check(False, "P22: K=0 melo vyhodit ValueError (237)")
    except ValueError:
        check(True, "P22: K=0 -> ValueError (237)")

    try:
        intersection(line_spline, vertical, 5)
        check(False, "P22: K vetsi nez pocet pruseciku melo vyhodit ValueError (237)")
    except ValueError:
        check(True, "P22: K prilis velke -> ValueError (237)")

    print("Vse OK.")


if __name__ == "__main__":
    main()
