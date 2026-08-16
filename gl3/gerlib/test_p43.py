# -*- coding: utf-8 -*-
"""
test_p43.py - Testy procedury P43 (patni bod na primce ze stredu
kruznice, viz G10.md 'P43 - Patni bod na primce ze stredu kruznice').
Stejny styl jako test_p40.py.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib import Point, Vector, Line, Circle, foot_point_from_circle_center, foot_point_on_line
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def _assert_close(a, b, msg, eps=1e-6):
    assert abs(a - b) < eps, "%s: %r != %r (rozdil %r)" % (msg, a, b, abs(a - b))


def _assert_pt_close(p, x, y, msg, eps=1e-6):
    _assert_close(p.x, x, msg + " (x)", eps)
    _assert_close(p.y, y, msg + " (y)", eps)


def test_foot_point_basic():
    # 1. Stred (5,5), primka = osa X -> patni bod (5,0)
    c = Circle(Point(5.0, 5.0), 2.0)
    lx = Line(Point(0.0, 0.0), Vector(1.0, 0.0))
    foot = foot_point_from_circle_center(c, lx)
    _assert_pt_close(foot, 5.0, 0.0, "Patni bod ze stredu (5,5) na osu X")

    # 2. Stejne jako P40 primo se stredem jako bodem (P43 je jen kombinace P47+P40)
    foot_p40 = foot_point_on_line(c.center, lx)
    _assert_pt_close(foot, foot_p40.x, foot_p40.y, "P43 odpovida P40(stred, primka)")

    # 3. Stred lezici primo na primce -> patni bod = stred
    c_on = Circle(Point(3.0, 0.0), 1.0)
    foot_on = foot_point_from_circle_center(c_on, lx)
    _assert_pt_close(foot_on, 3.0, 0.0, "Stred lezici na primce -> patni bod = stred")

    # 4. Sikma primka y = x, stred kruznice (0,4) -> patni bod (2,2)
    l_diag = Line(Point(0.0, 0.0), Vector(1.0, 1.0))
    c_diag = Circle(Point(0.0, 4.0), 5.0)
    foot_diag = foot_point_from_circle_center(c_diag, l_diag)
    _assert_pt_close(foot_diag, 2.0, 2.0, "Patni bod na diagonale y=x")

    print("test_foot_point_basic(): OK")


def test_orthogonality():
    line = Line(Point(1.2, 3.4), Vector(2.0, -1.5))
    circle = Circle(Point(-4.5, 7.8), 3.0)

    foot = foot_point_from_circle_center(circle, line)

    perp_x = circle.center.x - foot.x
    perp_y = circle.center.y - foot.y
    dot = perp_x * line.direction.x + perp_y * line.direction.y
    _assert_close(dot, 0.0, "Spojnice stredu a paty musi byt kolma na primku")

    print("test_orthogonality(): OK")


def test_error_handling():
    try:
        foot_point_from_circle_center(Circle(Point(1, 1), 1.0), Line(Point(0, 0), Vector(0, 0)))
        assert False, "Melo vyhodit ValueError pro nulovy smer primky"
    except ValueError as e:
        assert "nulovy" in str(e).lower()

    print("test_error_handling(): OK")


def test_gl3_interpreter_p43():
    gl3_code = """
SUBRO/TESTP43/out:PF1,out:PF2
CC1=C00>5.0,5.0,2.0
P0=P00>0.0,0.0
VX=U00>1.0,0.0,0.0
L1=L02>P0,VX
PF1=P43>CC1,L1

CC2=C00>0.0,4.0,5.0
V_DIAG=U00>1.0,1.0,0.0
L_DIAG=L02>P0,V_DIAG
PF2=P43>CC2,L_DIAG
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    assert "PF1" in env and "PF2" in env
    _assert_pt_close(env["PF1"], 5.0, 0.0, "GL3 PF1 (stred (5,5) na osu X)")
    _assert_pt_close(env["PF2"], 2.0, 2.0, "GL3 PF2 (stred (0,4) na diagonale)")

    print("test_gl3_interpreter_p43(): OK")


def main():
    test_foot_point_basic()
    test_orthogonality()
    test_error_handling()
    test_gl3_interpreter_p43()
    print("\nVSE OK - P43 (gerlib.p43) je plne funkcni.")


if __name__ == "__main__":
    main()
