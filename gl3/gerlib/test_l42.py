# -*- coding: utf-8 -*-
"""
test_l42.py - Testy procedury L42 (primka kolma ke krivce bodem, viz
G10.md 'L42 - Primka kolma ke krivce bodem', Fortran L42.FOR - primy
prepis: skladani jiz existujicich P42 + V34 + L02).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib.s01 import make_spline
from gerlib.l42 import perpendicular_to_curve
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def main():
    straight = make_spline([Point(0.0, 0.0), Point(10.0, 0.0)], 2)
    P = Point(5.0, 3.0, 0.0)  # vnejsi bod nad primym usekem

    line = perpendicular_to_curve(P, straight, 1)
    check(isclose(line.origin.x, 5.0) and isclose(line.origin.y, 3.0),
          "primka prochazi PUVODNIM bodem P, ne patnim bodem")
    check(abs(line.direction.x) < 1e-9 and abs(abs(line.direction.y) - 1.0) < 1e-9,
          "smer primky je kolmy ke krivce (ose x)")

    # --- K vetsi nez pocet patnich bodu -> chyba ---
    try:
        perpendicular_to_curve(P, straight, 5)
        check(False, "K presahujici pocet patnich bodu mel vyhodit ValueError")
    except ValueError as e:
        check("290" in str(e), "K mimo rozsah -> ValueError (puvodni IER=290)")

    # --- zvlnena krivka s vice patnimi body - K vybira spravny ---
    wavy = make_spline([Point(0.0, 0.0), Point(1.0, 2.0), Point(2.0, 0.0), Point(3.0, 2.0), Point(4.0, 0.0)], 5)
    Pw = Point(2.0, 1.0, 0.0)
    line1 = perpendicular_to_curve(Pw, wavy, 1)
    check(isclose(line1.origin.x, 2.0) and isclose(line1.origin.y, 1.0),
          "zvlnena krivka: primka prochazi puvodnim bodem P")

    # --- primka je opravdu normala krivky v patnim bode (kolma na tecnu tam) ---
    from gerlib.p42 import nearest_point
    from gerlib.v37 import curve_tangent_at_point
    foot = nearest_point(wavy, Pw, 1)
    tangent = curve_tangent_at_point(wavy, foot)
    dot = line1.direction.x * tangent.x + line1.direction.y * tangent.y
    check(abs(dot) < 1e-6, "smer primky je kolmy na tecnu krivky v patnim bode")

    # --- test pres realny GL3 zdrojovy text ---
    gl3_code = """
SUBRO/TESTL42/out:LM
DIMEN,P(2)
P(1)=P00>0.0,0.0
P(2)=P00>10.0,0.0
S1=S01>P(1),2.0
Q=P00>5.0,3.0
LM=L42>Q,S1,1.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(isclose(env["LM"].origin.x, 5.0) and isclose(env["LM"].origin.y, 3.0),
          "GL3: primka prochazi puvodnim bodem")

    print("\nVSE OK - L42 (gerlib.l42) je plne funkcni.")


if __name__ == "__main__":
    main()
