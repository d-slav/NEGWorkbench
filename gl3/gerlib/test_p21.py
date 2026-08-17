# -*- coding: utf-8 -*-
"""
test_p21.py - Testy procedury P21 (prusecik primky s kruznici, viz
G10.md 'P21 - Prusecik primky s kruznici', Fortran P121.FOR).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line, Circle
from gerlib.p21 import line_circle_intersection_point
from gerlib.errors import NoSolution
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def pt_isclose(p, x, y, eps=1e-6):
    return isclose(p.x, x, eps) and isclose(p.y, y, eps)


def main():
    circle = Circle(Point(0.0, 0.0, 0.0), 5.0)

    # primka prochazejici stredem (osa x) - klasicka secna
    secant = Line(Point(-10.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0))
    p0 = line_circle_intersection_point(secant, circle, 0)
    p1 = line_circle_intersection_point(secant, circle, 1)
    check(pt_isclose(p0, -5.0, 0.0), "secna: K=0 (zaporna strana)")
    check(pt_isclose(p1, 5.0, 0.0), "secna: K=1 (kladna strana)")

    # obe reseni musi lezet presne na kruznici
    for p in (p0, p1):
        check(isclose(math.hypot(p.x, p.y), 5.0), "reseni lezi presne na kruznici")

    # tecna primka - oba body totozne, K nezalezi
    tangent = Line(Point(-10.0, 5.0, 0.0), Vector(1.0, 0.0, 0.0))
    t0 = line_circle_intersection_point(tangent, circle, 0)
    t1 = line_circle_intersection_point(tangent, circle, 1)
    check(pt_isclose(t0, 0.0, 5.0) and pt_isclose(t1, 0.0, 5.0),
          "tecna primka: K=0 i K=1 davaji stejny (jediny) bod dotyku")

    # primka mimo kruznici - zadny prusecik
    outside = Line(Point(-10.0, 100.0, 0.0), Vector(1.0, 0.0, 0.0))
    try:
        line_circle_intersection_point(outside, circle, 0)
        check(False, "primka mimo kruznici mela vyhodit NoSolution")
    except NoSolution:
        check(True, "primka mimo kruznici -> NoSolution")

    # sikma secna (obecna primka, ne osove rovnobezna)
    oblique = Line(Point(-10.0, -10.0, 0.0), Vector(1.0, 1.0, 0.0))
    o0 = line_circle_intersection_point(oblique, circle, 0)
    o1 = line_circle_intersection_point(oblique, circle, 1)
    check(isclose(math.hypot(o0.x, o0.y), 5.0), "sikma secna: K=0 lezi na kruznici")
    check(isclose(math.hypot(o1.x, o1.y), 5.0), "sikma secna: K=1 lezi na kruznici")
    check(o0.x < o1.x, "sikma secna: K=0 je na zaporne (mensi t) strane primky")

    # test pres realny GL3 zdrojovy text
    gl3_code = """
SUBRO/TESTP21/out:PM1,out:PM2
CC=C00>0.0,0.0,5.0
PA=P00>-10.0,0.0
VX=U00>1.0,0.0,0.0
L1=L02>PA,VX
PM1=P21>L1,CC,0.0
PM2=P21>L1,CC,1.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(pt_isclose(env["PM1"], -5.0, 0.0), "GL3: K=0")
    check(pt_isclose(env["PM2"], 5.0, 0.0), "GL3: K=1")

    print("\nVSE OK - P21 (gerlib.p21) je plne funkcni.")


if __name__ == "__main__":
    main()
