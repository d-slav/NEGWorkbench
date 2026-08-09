# -*- coding: utf-8 -*-
"""Test P00 (bod souradnicemi), C00 (kruznice souradnicemi stredu),
C01 (kruznice bodem a polomerem)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib.p00 import point_from_coords
from gerlib.c00 import circle_from_coords
from gerlib.c01 import circle_from_point


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    p = point_from_coords(3.0, 4.0)
    check(p.x == 3.0 and p.y == 4.0 and p.z == 0.0, "P00: bod (3,4,0)")

    c = circle_from_coords(1.0, 2.0, 5.0)
    check(c.center.x == 1.0 and c.center.y == 2.0 and c.radius == 5.0,
          "C00: kruznice stred (1,2), polomer 5")

    c2 = circle_from_point(Point(7.0, 8.0, 0.0), 2.5)
    check(c2.center.x == 7.0 and c2.center.y == 8.0 and c2.radius == 2.5,
          "C01: kruznice bodem (7,8) a polomerem 2.5")

    print("Vse OK.")


if __name__ == "__main__":
    main()
