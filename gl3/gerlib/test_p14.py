# -*- coding: utf-8 -*-
"""
test_p14.py - Testy procedury P14 (bod na primce souradnici x(y),
viz G10.md 'P14 - Bod na primce souradnici x (y)'). Stejny styl jako
test_p40.py/test_p43.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib import Point, Vector, Line, point_on_line_by_coord
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def _assert_close(a, b, msg, eps=1e-6):
    assert abs(a - b) < eps, "%s: %r != %r (rozdil %r)" % (msg, a, b, abs(a - b))


def _assert_pt_close(p, x, y, msg, eps=1e-6):
    _assert_close(p.x, x, msg + " (x)", eps)
    _assert_close(p.y, y, msg + " (y)", eps)


def test_basic():
    # Diagonala y=x, K=0 (x=5) -> (5,5); K=1 (y=3) -> (3,3)
    l_diag = Line(Point(0.0, 0.0), Vector(1.0, 1.0))
    p_x = point_on_line_by_coord(5.0, l_diag, 0)
    _assert_pt_close(p_x, 5.0, 5.0, "K=0 (x=5) na diagonale")
    p_y = point_on_line_by_coord(3.0, l_diag, 1)
    _assert_pt_close(p_y, 3.0, 3.0, "K=1 (y=3) na diagonale")

    # Obecna primka, ne pres pocatek
    l_gen = Line(Point(1.0, 2.0), Vector(2.0, 1.0))  # x=1+2t, y=2+t
    p_gen = point_on_line_by_coord(5.0, l_gen, 0)  # 5=1+2t -> t=2 -> y=4
    _assert_pt_close(p_gen, 5.0, 4.0, "K=0 na obecne primce")

    # Z-slozka pruchoziho bodu se prenasi beze zmeny
    l_z = Line(Point(0.0, 0.0, 7.5), Vector(1.0, 1.0))
    p_z = point_on_line_by_coord(2.0, l_z, 0)
    _assert_close(p_z.z, 7.5, "Z-slozka se prenasi beze zmeny")

    print("test_basic(): OK")


def test_vertical_horizontal_lines():
    # Svisla primka (x = konst.) - K=0 nema reseni (nebo nekonecno reseni)
    l_vert = Line(Point(2.0, 0.0), Vector(0.0, 1.0))
    try:
        point_on_line_by_coord(5.0, l_vert, 0)
        assert False, "K=0 na svisle primce mel vyhodit ValueError"
    except ValueError as e:
        assert "kolm" in str(e).lower()

    # ale K=1 na svisle primce je v poradku (x zustava konstantni = 2)
    p = point_on_line_by_coord(7.0, l_vert, 1)
    _assert_pt_close(p, 2.0, 7.0, "K=1 na svisle primce")

    # Vodorovna primka (y = konst.) - K=1 nema reseni
    l_horiz = Line(Point(0.0, 3.0), Vector(1.0, 0.0))
    try:
        point_on_line_by_coord(1.0, l_horiz, 1)
        assert False, "K=1 na vodorovne primce mel vyhodit ValueError"
    except ValueError as e:
        assert "kolm" in str(e).lower()

    p2 = point_on_line_by_coord(9.0, l_horiz, 0)
    _assert_pt_close(p2, 9.0, 3.0, "K=0 na vodorovne primce")

    print("test_vertical_horizontal_lines(): OK")


def test_error_handling():
    l = Line(Point(0.0, 0.0), Vector(1.0, 1.0))
    try:
        point_on_line_by_coord(1.0, l, 2)
        assert False, "K mimo {0,1} mel vyhodit ValueError"
    except ValueError:
        pass

    print("test_error_handling(): OK")


def test_gl3_interpreter_p14():
    gl3_code = """
SUBRO/TESTP14/out:PF1,out:PF2
P0=P00>0.0,0.0
V_DIAG=U00>1.0,1.0,0.0
L_DIAG=L02>P0,V_DIAG
PF1=P14>5.0,L_DIAG,0.0

P1=P00>2.0,0.0
VY=U00>0.0,1.0,0.0
L_VERT=L02>P1,VY
PF2=P14>7.0,L_VERT,1.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    assert "PF1" in env and "PF2" in env
    _assert_pt_close(env["PF1"], 5.0, 5.0, "GL3 PF1 (diagonala, K=0)")
    _assert_pt_close(env["PF2"], 2.0, 7.0, "GL3 PF2 (svisla primka, K=1)")

    print("test_gl3_interpreter_p14(): OK")


def main():
    test_basic()
    test_vertical_horizontal_lines()
    test_error_handling()
    test_gl3_interpreter_p14()
    print("\nVSE OK - P14 (gerlib.p14) je plne funkcni.")


if __name__ == "__main__":
    main()
