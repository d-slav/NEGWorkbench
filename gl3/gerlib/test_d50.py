# -*- coding: utf-8 -*-
"""Test RKSEG (polomer krivosti segmentu) a D50 (polomer krivosti v
bode nejblizsim danemu bodu, bez GLPAT - viz d50.py).

Testovaci krivka: Hermituv segment sestrojeny tak, aby PRESNE
reprezentoval parabolu y=x^2 pro t v <0,1> (C(t)=(t,t^2)) - polomer
krivosti paraboly ma znamy uzavreny vzorec R=(1+4x^2)^1.5/2, takze jde
nezavisle overit spravnost RKSEG/D50 (ne jen konzistenci se sebou
samym)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Spline
from gerlib.glkoe import segment_coefficients
from gerlib.glfun import evaluate
from gerlib.rkseg import curvature_radius_at
from gerlib.d50 import nearest_point_on_curve, radius_of_curvature


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def parabola_radius(x):
    """Analyticky polomer krivosti y=x^2 v bode x (nezavisla kontrola)."""
    return (1.0 + 4.0 * x * x) ** 1.5 / 2.0


def main():
    # Hermituv segment presne reprezentujici y=x^2 na <0,1> (odvozeno
    # resenim P0,P1,T0,T1 z pozadovanych kubickych koeficientu - viz
    # komentar v ulozene historii konverzace / lze si overit dosazenim
    # do segment_coefficients nize)
    p0, p1 = Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)
    t0, t1 = Vector(1.0, 0.0, 0.0), Vector(1.0, 2.0, 0.0)
    coeffs = segment_coefficients(p0, p1, t0, t1, k=2)

    # over, ze segment opravdu odpovida C(t)=(t,t^2)
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        xy = evaluate(coeffs, t, order=0)
        check(math.isclose(xy[0], t, abs_tol=1e-9) and math.isclose(xy[1], t * t, abs_tol=1e-9),
              "priprava: segment presne reprezentuje y=x^2 v t=%.2f" % t)

    # --- RKSEG: primo v parametru t, porovnani s analytickym vzorcem ---
    for t in (0.0, 0.3, 0.5, 0.8, 1.0):
        r = curvature_radius_at(coeffs, t)
        expected = parabola_radius(t)  # x=t na teto krivce
        check(math.isclose(r, expected, rel_tol=1e-6),
              "RKSEG: polomer krivosti v t=%.2f souhlasi s analytickym vzorcem paraboly (%.5f vs %.5f)"
              % (t, r, expected))

    # --- degenerovany (primy) segment -> sentinel 1e6 ---
    line_coeffs = segment_coefficients(Point(0, 0, 0), Point(10, 0, 0),
                                        Vector(10, 0, 0), Vector(10, 0, 0), k=2)
    r_line = curvature_radius_at(line_coeffs, 0.5)
    check(math.isclose(r_line, 1e6), "RKSEG: primy usek -> sentinel 1e6 (nekonecny polomer)")

    # --- D50: cely retezec vc. hledani nejblizsiho bodu (bez GLPAT) ---
    parabola_spline = Spline([p0, p1], [t0, t1])

    # bod PRESNE na krivce (jako by prisel z P42/P48) - t=0.5 -> (0.5,0.25)
    on_curve = Point(0.5, 0.25, 0.0)
    r_d50 = radius_of_curvature(parabola_spline, on_curve)
    check(math.isclose(r_d50, parabola_radius(0.5), rel_tol=1e-5),
          "D50: polomer krivosti pro bod presne na krivce souhlasi s analytickym vzorcem")

    # bod MIMO krivku - D50 by mel najit nejblizsi bod a spocitat krivost tam
    off_curve = Point(0.5, 0.3, 0.0)  # kousek nad parabolou
    seg_idx, t_found = nearest_point_on_curve(parabola_spline, off_curve)
    check(seg_idx == 1, "D50: nejblizsi bod je na (jedinem) segmentu 1")
    check(0.0 <= t_found <= 1.0, "D50: nalezeny parametr t je v rozsahu <0,1>")

    # --- vicesegmentova krivka: uzel jako nejblizsi bod ---
    pts3 = [Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0), Point(2.0, 0.0, 0.0)]
    tans3 = [Vector(1.0, 1.0, 0.0), Vector(1.0, 0.0, 0.0), Vector(1.0, -1.0, 0.0)]
    multi_spline = Spline(pts3, tans3)
    # bod velmi blizko prostrednimu uzlu (1,1) - ocekavame segment 1 (t=1) nebo 2 (t=0)
    near_middle = Point(1.0, 1.01, 0.0)
    seg_m, t_m = nearest_point_on_curve(multi_spline, near_middle)
    check(seg_m in (1, 2), "D50: bod u prostredniho uzlu patri jednomu z pripojenych segmentu")

    print("Vse OK.")


if __name__ == "__main__":
    main()
