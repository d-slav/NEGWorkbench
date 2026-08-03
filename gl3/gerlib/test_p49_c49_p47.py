# -*- coding: utf-8 -*-
"""Test P49 (kopie bodu), C49 (kopie kruznice), P47 (stred kruznice).

Bez puvodniho Fortran zdroje - trivialni operace zadane primo
uzivatelem, testujeme hlavne "hodnotova kopie, ne sdilena reference"."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Circle
from gerlib.p49 import copy_point
from gerlib.c49 import copy_circle
from gerlib.p47 import circle_center


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # P49 - hodnoty souhlasi
    p = Point(1.0, 2.0, 3.0)
    pm = copy_point(p)
    check(pm.x == p.x and pm.y == p.y and pm.z == p.z, "P49: hodnoty kopie souhlasi s originalem")
    check(pm is not p, "P49: kopie je jina instance nez original")
    pm.x = 99.0
    check(p.x == 1.0, "P49: zmena kopie neovlivni original")

    # C49 - hodnoty souhlasi (vc. stredu a normaly), jina instance
    c = Circle(Point(5.0, 6.0, 0.0), 2.5, Vector(0.0, 0.0, 1.0))
    cm = copy_circle(c)
    check(cm.radius == c.radius, "C49: polomer kopie souhlasi")
    check(cm.center.x == c.center.x and cm.center.y == c.center.y, "C49: stred kopie souhlasi")
    check(cm is not c, "C49: kopie je jina instance nez original")
    check(cm.center is not c.center, "C49: i stred je hodnotova kopie, ne sdileny Point")
    cm.center.x = 999.0
    check(c.center.x == 5.0, "C49: zmena stredu kopie neovlivni original")

    # P47 - stred kruznice, hodnotova kopie
    c2 = Circle(Point(-3.0, 4.0, 0.0), 1.0)
    center = circle_center(c2)
    check(center.x == -3.0 and center.y == 4.0, "P47: vraci spravny stred")
    check(center is not c2.center, "P47: vraceny stred je hodnotova kopie, ne primy odkaz")
    center.x = 42.0
    check(c2.center.x == -3.0, "P47: zmena vysledku neovlivni puvodni kruznici")

    print("Vse OK.")


if __name__ == "__main__":
    main()
