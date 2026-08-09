# -*- coding: utf-8 -*-
"""Test C32 (tecna ke 2 primkam), C33 (tecna k primce+kruznici),
C34 (tecna ke 2 kruznicim).

Zdroj: zadny Fortran nedodan - odvozeno ze slovniho popisu. Testy proto
overuji predevsim GEOMETRICKOU SPRAVNOST vysledku (skutecna tecnost,
spravny polomer, spravny typ dotyku) - to je nezavisle overitelne bez
ohledu na to, jestli je uhodnuta konvence baleni KK/KKK spravne. Presny
vyznam K1 u C33 je vyslovne oznacen jako nejisty (viz c33.py)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line, Circle
from gerlib.c32 import tangent_to_two_lines
from gerlib.c33 import tangent_to_line_and_circle
from gerlib.c34 import tangent_to_two_circles


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
    # --- C32: dve kolme primky (osy x a y) ---
    l1 = Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0))  # osa x
    l2 = Line(Point(0.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0))  # osa y
    radius = 3.0
    seen_centers = set()
    for kk in (0, 1, 10, 11):
        c = tangent_to_two_lines(l1, l2, radius, kk)
        check(math.isclose(dist_point_line(c.center.x, c.center.y, l1), radius, rel_tol=1e-9),
              "C32 kk=%d: stred je ve spravne vzdalenosti od L1" % kk)
        check(math.isclose(dist_point_line(c.center.x, c.center.y, l2), radius, rel_tol=1e-9),
              "C32 kk=%d: stred je ve spravne vzdalenosti od L2" % kk)
        check(math.isclose(c.radius, radius), "C32 kk=%d: spravny polomer" % kk)
        check(abs(c.center.x) == radius and abs(c.center.y) == radius,
              "C32 kk=%d: stred v ocekavanem rohu (+-R,+-R) pro kolme osy" % kk)
        seen_centers.add((round(c.center.x, 6), round(c.center.y, 6)))
    check(len(seen_centers) == 4, "C32: ctyri ruzne kk davaji 4 ruzne (vsechny rohy) kruznice")

    # rovnobezne primky -> chyba
    l3 = Line(Point(0.0, 5.0, 0.0), Vector(1.0, 0.0, 0.0))
    try:
        tangent_to_two_lines(l1, l3, radius, 0)
        check(False, "C32: rovnobezne primky mely vyhodit chybu")
    except ValueError:
        check(True, "C32: rovnobezne primky -> ValueError")

    # --- C34: dve kruznice, overeni tecnosti pro vsechny kombinace K3,K2 ---
    c1 = Circle(Point(0.0, 0.0, 0.0), 5.0)
    c2 = Circle(Point(12.0, 0.0, 0.0), 5.0)
    radius34 = 3.0
    for k3 in (0, 1):
        for k2 in (0, 1):
            for k1 in (0, 1):
                kkk = 100 * k3 + 10 * k2 + k1
                try:
                    cm = tangent_to_two_circles(c1, c2, radius34, kkk)
                except ValueError:
                    continue  # geometricky nemozna kombinace (napr. moc daleko)
                expected_d1 = c1.radius + radius34 if k3 else abs(c1.radius - radius34)
                expected_d2 = c2.radius + radius34 if k2 else abs(c2.radius - radius34)
                check(math.isclose(dist_points(cm.center, c1.center), expected_d1, rel_tol=1e-6),
                      "C34 kkk=%03d: spravna vzdalenost od C1 (typ dotyku K3=%d)" % (kkk, k3))
                check(math.isclose(dist_points(cm.center, c2.center), expected_d2, rel_tol=1e-6),
                      "C34 kkk=%03d: spravna vzdalenost od C2 (typ dotyku K2=%d)" % (kkk, k2))
                check(math.isclose(cm.radius, radius34), "C34 kkk=%03d: spravny polomer" % kkk)

    cm_left = tangent_to_two_circles(c1, c2, radius34, 110)   # K3=1,K2=1,K1=0
    cm_right = tangent_to_two_circles(c1, c2, radius34, 111)  # K3=1,K2=1,K1=1
    check(not (math.isclose(cm_left.center.x, cm_right.center.x) and
               math.isclose(cm_left.center.y, cm_right.center.y)),
          "C34: K1=0 a K1=1 davaji ruzne (zrcadlove) stredy")
    check(math.isclose(cm_left.center.y, -cm_right.center.y, rel_tol=1e-6) and
          math.isclose(cm_left.center.x, cm_right.center.x, rel_tol=1e-6),
          "C34: K1=0/1 jsou zrcadlove podle spojnice stredu C1-C2 (osa x)")

    # --- C33: primka + kruznice, overeni tecnosti ---
    line = Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0))  # osa x
    circ = Circle(Point(0.0, 5.0, 0.0), 4.0)
    radius33 = 2.0
    found_any = False
    for k3 in (0, 1):
        for k2 in (0, 1):
            for k1 in (0, 1):
                kkk = 100 * k3 + 10 * k2 + k1
                try:
                    cm = tangent_to_line_and_circle(line, circ, radius33, kkk)
                except ValueError:
                    continue
                found_any = True
                check(math.isclose(dist_point_line(cm.center.x, cm.center.y, line), radius33, rel_tol=1e-6),
                      "C33 kkk=%03d: stred ve spravne vzdalenosti od primky" % kkk)
                expected_d = circ.radius + radius33 if k2 else abs(circ.radius - radius33)
                check(math.isclose(dist_points(cm.center, circ.center), expected_d, rel_tol=1e-6),
                      "C33 kkk=%03d: stred ve spravne vzdalenosti od kruznice (typ dotyku K2=%d)" % (kkk, k2))
                check(math.isclose(cm.radius, radius33), "C33 kkk=%03d: spravny polomer" % kkk)
    check(found_any, "C33: aspon jedna kombinace K dala platnou kruznici")

    print("Vse OK.")


if __name__ == "__main__":
    main()
