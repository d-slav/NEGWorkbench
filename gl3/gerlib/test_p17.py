# -*- coding: utf-8 -*-
"""
test_p17.py - Testy procedury P17 (bod od bodu ve vzdalenosti
rovnobezne s primkou, viz G10.md 'P17 - Bod od bodu ve vzdalenosti
rovnobezne s primkou', Fortran P117.FOR).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line
from gerlib.p17 import point_parallel_to_line
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
    p = Point(1.0, 1.0, 0.0)
    axis_x = Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0))

    r_default = point_parallel_to_line(p, axis_x, 5.0)
    check(pt_isclose(r_default, 6.0, 1.0), "default K=1 (kladny smer)")

    r_k1 = point_parallel_to_line(p, axis_x, 5.0, 1)
    check(pt_isclose(r_k1, 6.0, 1.0), "explicitni K=1")

    r_k0 = point_parallel_to_line(p, axis_x, 5.0, 0)
    check(pt_isclose(r_k0, -4.0, 1.0), "K=0 (zaporny smer)")

    # sikma primka (jednotkovy smer 0.6,0.8 - "3-4-5" trojuhelnik)
    l_diag = Line(Point(0.0, 0.0, 0.0), Vector(0.6, 0.8, 0.0))
    r_diag = point_parallel_to_line(Point(0.0, 0.0, 0.0), l_diag, 10.0, 1)
    check(pt_isclose(r_diag, 6.0, 8.0), "sikma primka, K=1")
    r_diag0 = point_parallel_to_line(Point(0.0, 0.0, 0.0), l_diag, 10.0, 0)
    check(pt_isclose(r_diag0, -6.0, -8.0), "sikma primka, K=0")

    # vysledna vzdalenost od P musi byt presne D
    d = math.hypot(r_diag.x - 0.0, r_diag.y - 0.0)
    check(isclose(d, 10.0), "vzdalenost od P je presne D")

    # D=0 vraci P beze zmeny
    r_zero = point_parallel_to_line(p, axis_x, 0.0, 1)
    check(pt_isclose(r_zero, 1.0, 1.0), "D=0 vraci vychozi bod")

    # test pres realny GL3 zdrojovy text
    gl3_code = """
SUBRO/TESTP17/out:PM1,out:PM2
P0=P00>0.0,0.0
V1=U00>1.0,0.0,0.0
L1=L02>P0,V1
PM1=P17>P0,L1,5.0
PM2=P17>P0,L1,5.0,0.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(pt_isclose(env["PM1"], 5.0, 0.0), "GL3: default K=1")
    check(pt_isclose(env["PM2"], -5.0, 0.0), "GL3: explicitni K=0")

    print("\nVSE OK - P17 (gerlib.p17) je plne funkcni.")


if __name__ == "__main__":
    main()
