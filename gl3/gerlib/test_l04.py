# -*- coding: utf-8 -*-
"""Test L04 (primka dvema body) - viz G10.md 'L04 - Primka dvema body'."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib.l04 import line_through_two_points


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # Zakladni pripad - primka body (0,0) a (3,4)
    line = line_through_two_points(Point(0.0, 0.0, 0.0), Point(3.0, 4.0, 0.0))
    check(line.origin.x == 0.0 and line.origin.y == 0.0, "L04: pruchozi bod = P1")
    check(math.isclose(line.direction.x, 0.6) and math.isclose(line.direction.y, 0.8),
          "L04: jednotkovy smerovy vektor P1->P2")

    # Z-slozka P1 se prenasi beze zmeny
    line_z = line_through_two_points(Point(1.0, 2.0, 5.0), Point(4.0, 6.0, -3.0))
    check(line_z.origin.z == 5.0, "L04: Z-slozka pruchoziho bodu = Z bodu P1")

    # Smluvni orientace nezavisi na poradi bodu (P1,P2) vs (P2,P1)
    p1, p2 = Point(0.0, 0.0, 0.0), Point(3.0, 4.0, 0.0)
    forward = line_through_two_points(p1, p2)
    backward = line_through_two_points(p2, p1)
    check(math.isclose(forward.direction.x, backward.direction.x)
          and math.isclose(forward.direction.y, backward.direction.y),
          "L04: smer nezavisi na poradi P1/P2 (smluvni orientace)")

    # Hranicni pripad - vzdalenost tesne NAD limitem 0.001 je jeste OK
    ok_line = line_through_two_points(Point(0.0, 0.0, 0.0), Point(0.002, 0.0, 0.0))
    check(math.isclose(abs(ok_line.direction.x), 1.0), "L04: vzdalenost > 0.001 je OK")

    # Totozne (nebo temer totozne, < 0.001) body -> chyba
    try:
        line_through_two_points(Point(1.0, 1.0, 0.0), Point(1.0, 1.0, 0.0))
        check(False, "L04: totozne body mely vyhodit ValueError")
    except ValueError:
        check(True, "L04: totozne body -> ValueError")

    try:
        line_through_two_points(Point(1.0, 1.0, 0.0), Point(1.0005, 1.0, 0.0))
        check(False, "L04: body blize nez 0.001 mely vyhodit ValueError")
    except ValueError:
        check(True, "L04: body blize nez 0.001 -> ValueError")

    print("Vse OK.")


if __name__ == "__main__":
    main()
