# -*- coding: utf-8 -*-
"""
test_v34.py - Testy procedury V34 (jednotkova normala 2D krivky v
obecnem bode, viz G10.md, Fortran V34.FOR). V37.FOR nebyl dodan (viz
gerlib/v37.py hlavicka pro odvozeni jeho ucelu), ale V34 samotne bylo
overeno 1:1 - V37 (tecna) + V231/perpendicular_vector (rotace 90°).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib.s01 import make_spline
from gerlib.glkoe import segment_coefficients
from gerlib.glfun import evaluate
from gerlib.v34 import curve_normal_at_point
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def main():
    # --- primy usek podel osy x - normala musi byt (0,+-1) ---
    straight = make_spline([Point(0.0, 0.0), Point(10.0, 0.0)], 2)
    mid = Point(5.0, 0.0)

    n_left = curve_normal_at_point(mid, straight, 0)
    n_right = curve_normal_at_point(mid, straight, 1)
    check(isclose(n_left.x, 0.0) and isclose(n_left.y, 1.0), "K=0 (vlevo) na ose x smeruje nahoru (+y)")
    check(isclose(n_right.x, 0.0) and isclose(n_right.y, -1.0), "K=1 (vpravo) na ose x smeruje dolu (-y)")
    check(isclose(math.hypot(n_left.x, n_left.y), 1.0), "normala je jednotkova")

    # --- zvlnena krivka, bod NENI uzel (interior bod segmentu) ---
    wavy = make_spline([Point(0.0, 0.0), Point(1.0, 1.0), Point(2.0, 0.0), Point(3.0, 1.0)], 4)
    p0, p1 = wavy.points[0], wavy.points[1]
    t0, t1 = wavy.segment_tangent_pair(0)
    coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
    x, y = evaluate(coeffs, 0.5, order=0)
    mid_point = Point(x, y, 0.0)

    normal = curve_normal_at_point(mid_point, wavy, 0)
    check(isclose(math.hypot(normal.x, normal.y), 1.0), "zvlnena krivka: normala v interior bode je jednotkova")

    # ortogonalita k tecne (numericka derivace)
    x2, y2 = evaluate(coeffs, 0.5 + 1e-6, order=0)
    tx, ty = x2 - x, y2 - y
    dot = normal.x * tx + normal.y * ty
    check(abs(dot) < 1e-6, "normala je kolma na tecnu krivky")

    # --- opacne K davaji opacne vektory ---
    n0 = curve_normal_at_point(mid_point, wavy, 0)
    n1 = curve_normal_at_point(mid_point, wavy, 1)
    check(isclose(n0.x, -n1.x) and isclose(n0.y, -n1.y), "K=0 a K=1 davaji opacne orientovane vektory")

    # --- bod primo v uzlu krivky ---
    n_node = curve_normal_at_point(wavy.points[1], wavy, 0)
    check(isclose(math.hypot(n_node.x, n_node.y), 1.0), "normala v uzlu krivky je jednotkova")

    # --- bod nelezici na krivce -> chyba ---
    try:
        curve_normal_at_point(Point(99.0, 99.0), straight, 0)
        check(False, "bod mimo krivku mel vyhodit ValueError")
    except ValueError as e:
        check("272" in str(e), "bod mimo krivku -> ValueError (puvodni IER=272)")

    # --- test pres realny GL3 zdrojovy text ---
    gl3_code = """
SUBRO/TESTV34/out:VM1,out:VM2
DIMEN,P(2)
P(1)=P00>0.0,0.0
P(2)=P00>10.0,0.0
S1=S01>P(1),2.0
Q=P00>5.0,0.0
VM1=V34>Q,S1,0.0
VM2=V34>Q,S1,1.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(isclose(env["VM1"].y, 1.0), "GL3: K=0 smeruje nahoru")
    check(isclose(env["VM2"].y, -1.0), "GL3: K=1 smeruje dolu")

    print("\nVSE OK - V34 (gerlib.v34) je plne funkcni.")


if __name__ == "__main__":
    main()
