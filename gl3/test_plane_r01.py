# -*- coding: utf-8 -*-
"""
test_plane_r01.py - Testy tridy Plane a operace R01 (RM=R01>>U,D).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from gerlib import Point, Vector, Line
from geplib import Plane, make_plane_r01
from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gerlib.serialize import serialize, deserialize


def _assert_close(a, b, msg, eps=1e-9):
    assert abs(a - b) < eps, "%s: %r != %r (rozdil %r)" % (msg, a, b, abs(a - b))


def _assert_vec_close(v, x, y, z, msg, eps=1e-9):
    _assert_close(v.x, x, msg + " (x)", eps)
    _assert_close(v.y, y, msg + " (y)", eps)
    _assert_close(v.z, z, msg + " (z)", eps)


def test_plane_class():
    # 1. Zakladni inicializace tridy Plane
    p = Point(1.0, 2.0, 3.0)
    n = Vector(0.0, 0.0, 1.0)
    plane = Plane(p, n)
    assert plane.origin.x == 1.0 and plane.origin.y == 2.0 and plane.origin.z == 3.0
    assert plane.normal.x == 0.0 and plane.normal.y == 0.0 and plane.normal.z == 1.0
    assert "Plane(" in repr(plane)

    # 2. Koeficienty obecne rovnice roviny (a*x + b*y + c*z + d = 0)
    a, b, c, d = plane.equation_coefficients()
    _assert_close(a, 0.0, "koeficient a")
    _assert_close(b, 0.0, "koeficient b")
    _assert_close(c, 1.0, "koeficient c")
    _assert_close(d, -3.0, "koeficient d (pro z=3 je 0*x + 0*y + 1*3 + d = 0 => d = -3)")

    # 3. Vzdalenost bodu od roviny (distance_to_point)
    pt_above = Point(1.0, 2.0, 5.0)
    pt_below = Point(1.0, 2.0, 1.0)
    pt_on = Point(5.0, -10.0, 3.0)
    _assert_close(plane.distance_to_point(pt_above), 2.0, "vzdalenost bodu nad rovinou")
    _assert_close(plane.distance_to_point(pt_below), -2.0, "vzdalenost bodu pod rovinou")
    _assert_close(plane.distance_to_point(pt_on), 0.0, "bod lezici v rovine")

    # 4. Kolmy prumet bodu do roviny (project_point)
    proj = plane.project_point(Point(10.0, 20.0, 50.0))
    _assert_vec_close(proj, 10.0, 20.0, 3.0, "prumet bodu do roviny z=3")

    print("test_plane_class(): OK")


def test_r01_operation():
    # 1. Rovina podel osy Z: U = (0, 0, 1), D = 5.0
    pl1 = make_plane_r01(Vector(0, 0, 1), 5.0)
    _assert_vec_close(pl1.normal, 0.0, 0.0, 1.0, "R01 UZ normala")
    _assert_vec_close(pl1.origin, 0.0, 0.0, 5.0, "R01 UZ origin")

    # 2. Smluvni orientace pro opacny smer U = (0, 0, -10), D = 5.0
    # Z-slozka je zaporna, pri canonical_unit_vector3 se otoci na (0, 0, 1)
    pl2 = make_plane_r01(Vector(0, 0, -10), 5.0)
    _assert_vec_close(pl2.normal, 0.0, 0.0, 1.0, "R01 UZN normala po smluvni orientaci")
    _assert_vec_close(pl2.origin, 0.0, 0.0, 5.0, "R01 UZN origin po smluvni orientaci")

    # 3. Obecny vektor vyzadujici normalizaci a otoceni: U = (-3, 4, 0), D = 10.0
    # Delka = 5. Normalizovano = (-0.6, 0.8, 0).
    # Protoze nx = -0.6 < -1e-6, smluvni orientace otoci vektor na (0.6, -0.8, 0).
    # Origin = 10 * (0.6, -0.8, 0) = (6.0, -8.0, 0.0).
    pl3 = make_plane_r01(Vector(-3, 4, 0), 10.0)
    _assert_vec_close(pl3.normal, 0.6, -0.8, 0.0, "R01 obecny vektor normala")
    _assert_vec_close(pl3.origin, 6.0, -8.0, 0.0, "R01 obecny vektor origin")

    # 4. Volani pres classmethod Plane.r01
    pl4 = Plane.r01(Vector(0, 10, 0), 2.5)
    _assert_vec_close(pl4.normal, 0.0, 1.0, 0.0, "Plane.r01 normala")
    _assert_vec_close(pl4.origin, 0.0, 2.5, 0.0, "Plane.r01 origin")

    # 5. Podpora Point a Line jako normal_ref
    pl_pt = make_plane_r01(Point(0, 0, 2), 4.0)
    _assert_vec_close(pl_pt.normal, 0.0, 0.0, 1.0, "R01 z Point")
    _assert_vec_close(pl_pt.origin, 0.0, 0.0, 4.0, "R01 z Point origin")

    line = Line(Point(1, 1, 1), Vector(1, 0, 0))
    pl_ln = make_plane_r01(line, 3.0)
    _assert_vec_close(pl_ln.normal, 1.0, 0.0, 0.0, "R01 z Line")
    _assert_vec_close(pl_ln.origin, 3.0, 0.0, 0.0, "R01 z Line origin")

    # 6. Chybovy stav: nulovy vektor
    try:
        make_plane_r01(Vector(0, 0, 0), 5.0)
        assert False, "Melo vyhodit ValueError pro nulovy vektor"
    except ValueError as e:
        assert "nulovy" in str(e).lower()

    print("test_r01_operation(): OK")


def test_gl3_interpreter_r01():
    # Overeni spusteni R01 v GL3 programu
    gl3_code = """
SUBRO/TESTR01/out:R1,out:R2
U1=U00>0.0,0.0,5.0
R1=R01>U1,12.0
U2=U00>-30.0,40.0,0.0
R2=R01>U2,20.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    assert "R1" in env, "R1 musi byt v env"
    assert "R2" in env, "R2 musi byt v env"

    r1 = env["R1"]
    assert isinstance(r1, Plane), "R1 musi byt instance Plane"
    _assert_vec_close(r1.normal, 0.0, 0.0, 1.0, "GL3 R1 normala")
    _assert_vec_close(r1.origin, 0.0, 0.0, 12.0, "GL3 R1 origin")

    r2 = env["R2"]
    assert isinstance(r2, Plane), "R2 musi byt instance Plane"
    _assert_vec_close(r2.normal, 0.6, -0.8, 0.0, "GL3 R2 normala")
    _assert_vec_close(r2.origin, 12.0, -16.0, 0.0, "GL3 R2 origin")

    print("test_gl3_interpreter_r01(): OK")


def test_serialize_plane():
    pl = Plane.r01(Vector(0, 0, 1), 7.5)
    data = serialize(pl)
    assert data["defined"] is True
    assert data["type"] == "Plane"
    assert data["origin"]["type"] == "Point"
    assert data["origin"]["z"] == 7.5
    assert data["normal"]["type"] == "Vector"
    assert data["normal"]["z"] == 1.0

    restored = deserialize(data)
    assert isinstance(restored, Plane)
    _assert_vec_close(restored.normal, 0.0, 0.0, 1.0, "deserialized normal")
    _assert_vec_close(restored.origin, 0.0, 0.0, 7.5, "deserialized origin")

    print("test_serialize_plane(): OK")


def main():
    test_plane_class()
    test_r01_operation()
    test_gl3_interpreter_r01()
    test_serialize_plane()
    print("\nVSE OK - trida Plane a operace R01 (geplib.plane / geplib.r01) jsou plne funkcni.")


if __name__ == "__main__":
    main()
