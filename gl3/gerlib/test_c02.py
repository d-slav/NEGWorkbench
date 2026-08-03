# -*- coding: utf-8 -*-
"""Test C02 (kruznice tremi body, C402.FOR) a L343 (osa usecky,
odvozeno z kontextu pouziti - viz l343.py)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib.l343 import perpendicular_bisector
from gerlib.c02 import circle_from_3_points


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # L343 - osa usecky: bod na ose je stred, smer kolmy k usecce
    p1, p2 = Point(0.0, 0.0, 0.0), Point(4.0, 0.0, 0.0)
    bis = perpendicular_bisector(p1, p2)
    check(math.isclose(bis.origin.x, 2.0) and math.isclose(bis.origin.y, 0.0),
          "L343: bod na ose je stred usecky")
    check(math.isclose(bis.direction.x, 0.0, abs_tol=1e-9),
          "L343: smer osy je kolmy na vodorovnou usecku (nulova x-slozka)")

    try:
        perpendicular_bisector(Point(1.0, 1.0, 0.0), Point(1.0, 1.0, 0.0))
        check(False, "L343: totozne body mely vyhodit ValueError")
    except ValueError:
        check(True, "L343: totozne body -> ValueError")

    # C02 - trivialni pripad: kruznice o polomeru 5 se stredem v pocatku,
    # tri body na ni (0,5), (5,0), (0,-5) - snadno overitelne z hlavy
    c = circle_from_3_points(Point(0.0, 5.0, 0.0), Point(5.0, 0.0, 0.0), Point(0.0, -5.0, 0.0))
    check(math.isclose(c.center.x, 0.0, abs_tol=1e-9) and math.isclose(c.center.y, 0.0, abs_tol=1e-9),
          "C02: stred v pocatku")
    check(math.isclose(c.radius, 5.0), "C02: polomer 5")

    # C02 - obecny pripad, overeni ze vsechny 3 body maji stejnou vzdalenost od stredu
    a, b, d = Point(1.0, 2.0, 0.0), Point(4.0, 6.0, 0.0), Point(-2.0, 5.0, 0.0)
    c2 = circle_from_3_points(a, b, d)
    ra = math.hypot(a.x - c2.center.x, a.y - c2.center.y)
    rb = math.hypot(b.x - c2.center.x, b.y - c2.center.y)
    rd = math.hypot(d.x - c2.center.x, d.y - c2.center.y)
    check(math.isclose(ra, c2.radius) and math.isclose(rb, c2.radius) and math.isclose(rd, c2.radius),
          "C02: vsechny 3 body jsou od stredu ve stejne vzdalenosti (polomer)")

    # poradi bodu nesmi zmenit vysledek
    c3 = circle_from_3_points(d, a, b)
    check(math.isclose(c3.center.x, c2.center.x) and math.isclose(c3.center.y, c2.center.y)
          and math.isclose(c3.radius, c2.radius), "C02: vysledek nezavisi na poradi bodu")

    # chybove stavy
    try:
        circle_from_3_points(Point(0, 0, 0), Point(0, 0, 0), Point(1, 1, 0))
        check(False, "C02: totozne body 1,2 mely vyhodit ValueError (4021)")
    except ValueError:
        check(True, "C02: totozne body 1,2 -> ValueError (4021)")

    try:
        circle_from_3_points(Point(0, 0, 0), Point(1, 1, 0), Point(1, 1, 0))
        check(False, "C02: totozne body 2,3 mely vyhodit ValueError (4021)")
    except ValueError:
        check(True, "C02: totozne body 2,3 -> ValueError (4021)")

    try:
        circle_from_3_points(Point(0, 0, 0), Point(1, 1, 0), Point(2, 2, 0))
        check(False, "C02: kolinearni body mely vyhodit ValueError (4022)")
    except ValueError:
        check(True, "C02: kolinearni body -> ValueError (4022)")

    print("Vse OK.")


if __name__ == "__main__":
    main()
