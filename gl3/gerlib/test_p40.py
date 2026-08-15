# -*- coding: utf-8 -*-
"""
test_p40.py - Testy procedury P40 (patni bod kolmice z bodu na primku).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib import Point, Vector, Line, foot_point_on_line, point_line
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def _assert_close(a, b, msg, eps=1e-6):
    assert abs(a - b) < eps, "%s: %r != %r (rozdil %r)" % (msg, a, b, abs(a - b))


def _assert_pt_close(p, x, y, msg, eps=1e-6):
    _assert_close(p.x, x, msg + " (x)", eps)
    _assert_close(p.y, y, msg + " (y)", eps)


def test_foot_point_basic():
    # 1. Kolmice z (5, 5) na osu X (primka prochazejici (0,0) ve smeru (1,0))
    p = Point(5.0, 5.0)
    lx = Line(Point(0.0, 0.0), Vector(1.0, 0.0))
    foot = foot_point_on_line(p, lx)
    _assert_pt_close(foot, 5.0, 0.0, "Patni bod na ose X")

    # 2. Kolmice z (5, 5) na osu Y
    ly = Line(Point(0.0, 0.0), Vector(0.0, 1.0))
    foot_y = foot_point_on_line(p, ly)
    _assert_pt_close(foot_y, 0.0, 5.0, "Patni bod na ose Y")

    # 3. Sikma primka y = x (prochazi (0,0), smer (1,1)) z bodu (0, 4) -> (2, 2)
    p_diag = Point(0.0, 4.0)
    l_diag = Line(Point(0.0, 0.0), Vector(1.0, 1.0))
    foot_diag = foot_point_on_line(p_diag, l_diag)
    _assert_pt_close(foot_diag, 2.0, 2.0, "Patni bod na diagonale y=x")

    # 4. Bod jiz lezici na primce: (3, 3) na diagonale y=x -> musi zustat (3, 3)
    p_on = Point(3.0, 3.0)
    foot_on = foot_point_on_line(p_on, l_diag)
    _assert_pt_close(foot_on, 3.0, 3.0, "Bod lezici na primce")

    print("test_foot_point_basic(): OK")


def test_orthogonality_and_distance():
    # Obecna primka a bod
    line = Line(Point(1.2, 3.4), Vector(2.0, -1.5))
    point = Point(-4.5, 7.8)

    foot = foot_point_on_line(point, line)

    # Vzdalenost point - foot musi odpovidat D11 (point_line)
    d_actual = math.hypot(point.x - foot.x, point.y - foot.y)
    d_expected = point_line(point, line)
    _assert_close(d_actual, d_expected, "Vzdalenost k patnimu bodu musi odpovidat D11")

    # Vektor point -> foot musi byt kolmy na smerovy vektor primky
    perp_x = point.x - foot.x
    perp_y = point.y - foot.y
    dot = perp_x * line.direction.x + perp_y * line.direction.y
    _assert_close(dot, 0.0, "Spojnice bodu a paty musi byt kolma na primku")

    print("test_orthogonality_and_distance(): OK")


def test_error_handling():
    try:
        foot_point_on_line(Point(1, 1), Line(Point(0, 0), Vector(0, 0)))
        assert False, "Melo vyhodit ValueError pro nulovy smer primky"
    except ValueError as e:
        assert "nulovy" in str(e).lower()

    print("test_error_handling(): OK")


def test_gl3_interpreter_p40():
    gl3_code = """
SUBRO/TESTP40/out:PF1,out:PF2
P1=P00>5.0,5.0
L1=L02>P0,VX
PF1=P40>P1,L1
P2=P00>0.0,4.0
* Vektor 1,1
V_DIAG=U00>1.0,1.0,0.0
L_DIAG=L02>P0,V_DIAG
PF2=P40>P2,L_DIAG
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    assert "PF1" in env and "PF2" in env
    _assert_pt_close(env["PF1"], 5.0, 0.0, "GL3 PF1 (na ose X)")
    _assert_pt_close(env["PF2"], 2.0, 2.0, "GL3 PF2 (na diagonale)")

    print("test_gl3_interpreter_p40(): OK")


def main():
    test_foot_point_basic()
    test_orthogonality_and_distance()
    test_error_handling()
    test_gl3_interpreter_p40()
    print("\nVSE OK - P40 (gerlib.p40) je plne funkcni.")


if __name__ == "__main__":
    main()
