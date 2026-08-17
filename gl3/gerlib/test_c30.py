# -*- coding: utf-8 -*-
"""Test C30 (kruznice daneho polomeru tecna k primce a prochazejici
bodem, viz G10.md 'C30 - Kruznice daneho polomeru tecna k primce
prochazejici bodem', Fortran C430.FOR).

Testy overuji predevsim GEOMETRICKOU SPRAVNOST vysledku (skutecna
tecnost k primce, spravny polomer, kruznice prochazi bodem P) a poradi
K=0/K=1 podle pozice dotykoveho bodu podel kladneho smeru primky -
stejny styl jako test_c32_c33_c34.py.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line
from gerlib.c30 import tangent_through_point
from gerlib.errors import NoSolution


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def dist_point_line(px, py, line):
    """Kolma vzdalenost bodu (px,py) od primky (bod+smer)."""
    ox, oy = line.origin.x, line.origin.y
    dx, dy = line.direction.x, line.direction.y
    dlen = math.hypot(dx, dy)
    cross = (px - ox) * dy - (py - oy) * dx
    return abs(cross) / dlen


def dist_points(p, q):
    return math.hypot(p.x - q.x, p.y - q.y)


def main():
    axis_x = Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0))

    # --- bod mimo primku, obe reseni existuji (DIST <= 2*D) ---
    p_off = Point(0.0, 3.0, 0.0)
    radius = 5.0
    c0 = tangent_through_point(p_off, axis_x, radius, 0)
    c1 = tangent_through_point(p_off, axis_x, radius, 1)
    for label, c in (("K=0", c0), ("K=1", c1)):
        check(math.isclose(c.radius, radius), "%s: spravny polomer" % label)
        check(math.isclose(dist_point_line(c.center.x, c.center.y, axis_x), radius, rel_tol=1e-9),
              "%s: kruznice je tecna k primce" % label)
        check(math.isclose(dist_points(c.center, p_off), radius, rel_tol=1e-9),
              "%s: kruznice prochazi bodem P" % label)
    check(c0.center.x < c1.center.x,
          "K=0 ma dotykovy bod driv v kladnem smeru primky nez K=1")
    check(not math.isclose(c0.center.x, c1.center.x), "K=0 a K=1 davaji ruzne kruznice (obecny pripad)")

    # --- bod na opacne strane primky - stejna logika, jen zrcadlove ---
    p_off2 = Point(0.0, -3.0, 0.0)
    c0b = tangent_through_point(p_off2, axis_x, radius, 0)
    c1b = tangent_through_point(p_off2, axis_x, radius, 1)
    check(math.isclose(dist_points(c0b.center, p_off2), radius, rel_tol=1e-9),
          "bod pod primkou, K=0: kruznice prochazi P")
    check(math.isclose(dist_points(c1b.center, p_off2), radius, rel_tol=1e-9),
          "bod pod primkou, K=1: kruznice prochazi P")

    # --- obecna (ne osove rovnobezna) primka ---
    l_gen = Line(Point(1.0, 1.0, 0.0), Vector(0.6, 0.8, 0.0))
    p_gen = Point(5.0, 5.0, 0.0)
    r_gen = 4.0
    cg0 = tangent_through_point(p_gen, l_gen, r_gen, 0)
    cg1 = tangent_through_point(p_gen, l_gen, r_gen, 1)
    for label, c in (("K=0", cg0), ("K=1", cg1)):
        check(math.isclose(dist_point_line(c.center.x, c.center.y, l_gen), r_gen, rel_tol=1e-9),
              "obecna primka %s: kruznice je tecna" % label)
        check(math.isclose(dist_points(c.center, p_gen), r_gen, rel_tol=1e-9),
              "obecna primka %s: kruznice prochazi P" % label)

    # --- bod lezi PRIMO na primce - je dotykovym bodem, K=0 vlevo, K=1 vpravo ---
    p_on = Point(2.0, 0.0, 0.0)
    r_on = 3.0
    con0 = tangent_through_point(p_on, axis_x, r_on, 0)
    con1 = tangent_through_point(p_on, axis_x, r_on, 1)
    check(math.isclose(con0.center.x, 2.0) and math.isclose(con0.center.y, r_on),
          "bod na primce, K=0 (vlevo): stred (2, +r)")
    check(math.isclose(con1.center.x, 2.0) and math.isclose(con1.center.y, -r_on),
          "bod na primce, K=1 (vpravo): stred (2, -r)")
    check(math.isclose(dist_points(con0.center, p_on), r_on, rel_tol=1e-9),
          "bod na primce, K=0: kruznice prochazi P (dotykovym bodem)")

    # --- hranicni pripad: DIST == 2*D presne -> jedine reseni, K=0 i K=1 stejne ---
    p_edge = Point(0.0, 2.0 * radius, 0.0)
    ce0 = tangent_through_point(p_edge, axis_x, radius, 0)
    ce1 = tangent_through_point(p_edge, axis_x, radius, 1)
    check(math.isclose(ce0.center.x, ce1.center.x) and math.isclose(ce0.center.y, ce1.center.y),
          "hranicni pripad DIST=2*D: K=0 a K=1 davaji stejnou (jedinou) kruznici")
    check(math.isclose(dist_points(ce0.center, p_edge), radius, rel_tol=1e-9),
          "hranicni pripad: kruznice prochazi P")

    # --- bod dal nez prumer (2*D) - zadne reseni ---
    try:
        tangent_through_point(Point(0.0, 100.0, 0.0), axis_x, radius, 0)
        check(False, "bod prilis daleko mel vyhodit NoSolution")
    except NoSolution:
        check(True, "bod prilis daleko (DIST > 2*D) -> NoSolution")

    # --- prakticky nulovy polomer -> chyba ---
    try:
        tangent_through_point(Point(0.0, 3.0, 0.0), axis_x, 0.0005, 0)
        check(False, "prakticky nulovy polomer mel vyhodit ValueError")
    except ValueError:
        check(True, "prakticky nulovy polomer -> ValueError")

    print("Vse OK.")


if __name__ == "__main__":
    main()
