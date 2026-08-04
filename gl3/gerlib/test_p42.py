# -*- coding: utf-8 -*-
"""Test GLKOE (Hermitovy koeficienty), GLFUN (vyhodnoceni segmentu),
GLPLY (realne koreny polynomu) a P42 (paty kolmic na krivku).

Zdroj: P42.FOR + GLKOE.FOR + GLFUN.FOR (dodano uzivatelem). GLPLY.FOR
dodano, ale jeho vlastni zavislosti (GLDES/GLPOL/GLVYB) ne - nahrazeno
nezavislym hledacem korenu (Durand-Kerner), viz gerlib/glply.py."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Spline
from gerlib.glkoe import segment_coefficients
from gerlib.glfun import evaluate
from gerlib.glply import polynomial_roots, real_roots_in_range
from gerlib.p42 import foot_points, nearest_point


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- GLKOE + GLFUN: primka jako degenerovana kubika ---
    p0, p1 = Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)
    t0, t1 = Vector(10.0, 0.0, 0.0), Vector(10.0, 0.0, 0.0)
    coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
    # a3=a2=0 pro primku (viz odvozeni v hlavicce glkoe.py)
    check(math.isclose(coeffs[0][0], 0.0, abs_tol=1e-9) and math.isclose(coeffs[0][1], 0.0, abs_tol=1e-9),
          "GLKOE: primka ma nulove kubicke/kvadraticke koeficienty")
    mid = evaluate(coeffs, 0.5, order=0)
    check(math.isclose(mid[0], 5.0) and math.isclose(mid[1], 0.0), "GLFUN: hodnota na primce v t=0.5")
    deriv = evaluate(coeffs, 0.5, order=1)
    check(math.isclose(deriv[0], 10.0) and math.isclose(deriv[1], 0.0), "GLFUN: 1. derivace na primce = smerovy vektor")

    # --- GLPLY: zname koreny ---
    # (t-1)(t-2)(t-3) = t^3 -6t^2+11t-6, sestupne [1,-6,11,-6]
    roots = real_roots_in_range([1.0, -6.0, 11.0, -6.0], 0.0, 4.0)
    check(len(roots) == 3, "GLPLY: nalezeny 3 koreny kubiky")
    check(all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(roots, [1.0, 2.0, 3.0])),
          "GLPLY: koreny jsou 1,2,3 (vzestupne)")
    roots_narrow = real_roots_in_range([1.0, -6.0, 11.0, -6.0], 1.5, 4.0)
    check(len(roots_narrow) == 2 and math.isclose(roots_narrow[0], 2.0) and math.isclose(roots_narrow[1], 3.0),
          "GLPLY: filtrovani podle intervalu funguje")

    # --- P42: patni bod na primce (nejjednodussi pripad, analyticky overitelny) ---
    line_spline = Spline([p0, p1], [t0, t1])
    foot = nearest_point(line_spline, Point(5.0, 3.0, 0.0), 1)
    check(math.isclose(foot.x, 5.0) and math.isclose(foot.y, 0.0), "P42: pata kolmice na primku (5,3)->(5,0)")

    # --- P42: vice segmentu, duplicitni koren na hranici se zahodi ---
    # tri kolinearni body (0,0),(10,0),(20,0), tecny = smer segmentu (primky)
    pts3 = [Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0), Point(20.0, 0.0, 0.0)]
    tans3 = [Vector(10.0, 0.0, 0.0), Vector(10.0, 0.0, 0.0), Vector(10.0, 0.0, 0.0)]
    multi_spline = Spline(pts3, tans3)
    feet = foot_points(multi_spline, Point(10.0, 5.0, 0.0))
    check(len(feet) == 1, "P42: bod primo nad spojem segmentu ma jen JEDNU patu (duplicita zahozena)")
    check(math.isclose(feet[0][2].x, 10.0) and math.isclose(feet[0][2].y, 0.0),
          "P42: pata na spoji segmentu je (10,0)")
    check(feet[0][0] == 2, "P42: pata patri druhemu segmentu (t=0), ne prvnimu (t=1)")

    # --- P42: bod, ktery ma paty na OBOU segmentech (mimo spoj) ---
    feet2 = foot_points(multi_spline, Point(5.0, 5.0, 0.0))
    check(len(feet2) == 1 and math.isclose(feet2[0][2].x, 5.0), "P42: bod nad prvnim segmentem ma patu tam")
    p1_result = nearest_point(multi_spline, Point(5.0, 5.0, 0.0), 1)
    check(math.isclose(p1_result.x, 5.0) and math.isclose(p1_result.y, 0.0), "P42: nearest_point K=1 souhlasi s foot_points")

    # --- chybove stavy ---
    try:
        nearest_point(line_spline, Point(5.0, 3.0, 0.0), 0)
        check(False, "P42: K=0 melo vyhodit ValueError (228)")
    except ValueError:
        check(True, "P42: K=0 -> ValueError (228)")

    try:
        nearest_point(line_spline, Point(5.0, 3.0, 0.0), 5)
        check(False, "P42: K vetsi nez pocet pat melo vyhodit ValueError (230)")
    except ValueError:
        check(True, "P42: K prilis velke -> ValueError (230)")

    # --- perpendikularita: obecna (nedegenerovana) kubika ---
    # segment s vyraznym zakrivenim - tecny nejsou rovnobezne s primkou P0P1
    pa, pb = Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)
    ta, tb = Vector(0.0, 8.0, 0.0), Vector(0.0, -8.0, 0.0)
    curved_spline = Spline([pa, pb], [ta, tb])
    ext_point = Point(4.0, 2.0, 0.0)
    curved_coeffs = segment_coefficients(pa, pb, ta, tb, k=2)
    feet3 = foot_points(curved_spline, ext_point)
    check(len(feet3) >= 1, "P42: zakrivena kubika ma alespon jednu patu")
    for seg_idx, t, foot_pt in feet3:
        # over kolmost: tecna v bode t musi byt kolma na (foot_pt - ext_point)
        tang = evaluate(curved_coeffs, t, order=1)
        dx, dy = foot_pt.x - ext_point.x, foot_pt.y - ext_point.y
        dot = tang[0] * dx + tang[1] * dy
        check(math.isclose(dot, 0.0, abs_tol=1e-6),
              "P42: tecna v nalezenem bode je kolma na spojnici s externim bodem (t=%.4f)" % t)

    print("Vse OK.")


if __name__ == "__main__":
    main()
