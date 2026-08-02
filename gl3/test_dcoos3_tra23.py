# -*- coding: utf-8 -*-
"""
test_dcoos3_tra23.py - overuje geplib.dcoos3/tra23 (cista geometrie,
zadna zavislost na GL3 interpretru ani FreeCADu).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from gerlib import Point, Vector, Line
from gerlib.types import Spline
from geplib import (
    define_coord_system3, transform_point3, transform_vector3, transform_spline3,
    make_point3, make_vector3,
)


def _assert_close(a, b, msg, eps=1e-9):
    assert abs(a - b) < eps, "%s: %r != %r (rozdil %r)" % (msg, a, b, abs(a - b))


def _assert_point_close(p, x, y, z, msg):
    _assert_close(p.x, x, msg + " (x)")
    _assert_close(p.y, y, msg + " (y)")
    _assert_close(p.z, z, msg + " (z)")


def _assert_unit(v, msg):
    n = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
    _assert_close(n, 1.0, msg + " - ma byt jednotkovy")


def _assert_orthogonal(v1, v2, msg):
    d = v1.x * v2.x + v1.y * v2.y + v1.z * v2.z
    _assert_close(d, 0.0, msg + " - maji byt kolme")


def main():
    # --- 1) zakladni pripad z priklad v zadani: DCOOS3,3,Q5,UX,UY ---
    # Q5 = bod (10,20,30), UX = vektor (1,0,0), UY = vektor (0,1,0)
    # -> ocekavame identickou (posunutou) souradnou soustavu.
    origin = Point(10.0, 20.0, 30.0)
    cs = define_coord_system3(origin, Vector(1.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0))

    _assert_point_close(cs.ex, 1.0, 0.0, 0.0, "ex (UX)")
    _assert_point_close(cs.ey, 0.0, 1.0, 0.0, "ey (UY)")
    _assert_point_close(cs.ez, 0.0, 0.0, 1.0, "ez (dopocitane) - pravotociva soustava")
    print("define_coord_system3(): OK - triviálni pripad (UX/UY) da identickou orientaci")

    # --- 2) ortonormalita a pravotocivost i pro obecny (neosovy) pripad ---
    origin2 = Point(0.0, 0.0, 0.0)
    cs2 = define_coord_system3(origin2, Vector(1.0, 1.0, 0.0), Vector(0.0, 1.0, 1.0))
    for name, v in (("ex", cs2.ex), ("ey", cs2.ey), ("ez", cs2.ez)):
        _assert_unit(v, name)
    _assert_orthogonal(cs2.ex, cs2.ey, "ex/ey")
    _assert_orthogonal(cs2.ex, cs2.ez, "ex/ez")
    _assert_orthogonal(cs2.ey, cs2.ez, "ey/ez")
    # pravotocivost: ez == ex x ey (uz takhle definovano, ale overme cislama)
    cross_x = cs2.ex.y * cs2.ey.z - cs2.ex.z * cs2.ey.y
    cross_y = cs2.ex.z * cs2.ey.x - cs2.ex.x * cs2.ey.z
    cross_z = cs2.ex.x * cs2.ey.y - cs2.ex.y * cs2.ey.x
    _assert_close(cross_x, cs2.ez.x, "ez.x == (ex x ey).x")
    _assert_close(cross_y, cs2.ez.y, "ez.y == (ex x ey).y")
    _assert_close(cross_z, cs2.ez.z, "ez.z == (ex x ey).z")
    print("define_coord_system3(): OK - obecny pripad je ortonormalni a pravotocivy")

    # --- 3) vg2/vg3 jako bod (Q) a jako primka (M), ne jen vektor (U) ---
    origin3 = Point(1.0, 1.0, 1.0)
    cs3_via_point = define_coord_system3(
        origin3, Point(2.0, 1.0, 1.0), Point(1.0, 2.0, 1.0)
    )
    _assert_point_close(cs3_via_point.ex, 1.0, 0.0, 0.0, "ex pres Q (bod)")
    _assert_point_close(cs3_via_point.ey, 0.0, 1.0, 0.0, "ey pres Q (bod)")

    cs3_via_line = define_coord_system3(
        origin3,
        Line(Point(99.0, 99.0, 99.0), Vector(1.0, 0.0, 0.0)),  # M - jen smer se pouzije
        Line(Point(-5.0, -5.0, -5.0), Vector(0.0, 1.0, 0.0)),
    )
    _assert_point_close(cs3_via_line.ex, 1.0, 0.0, 0.0, "ex pres M (primka)")
    _assert_point_close(cs3_via_line.ey, 0.0, 1.0, 0.0, "ey pres M (primka)")
    print("define_coord_system3(): OK - Q (bod) i M (primka) davaji stejny vysledek jako U (vektor)")

    # --- 4) degenerovany pripad - vg3 rovnobezny s osou x' ---
    try:
        define_coord_system3(Point(0, 0, 0), Vector(1, 0, 0), Vector(2, 0, 0))
        raise AssertionError("mel vyhodit ValueError - vg3 rovnobezne s x'")
    except ValueError as e:
        assert "rovnobezny" in str(e)
        print("define_coord_system3() na degenerovanem vstupu: OK - jasna chyba (%s)" % e)

    # --- 5) transform_point3: bod (5, 3, 0) v mistni soustave se stredem
    # (10,20,30) a osami X'=(0,1,0), Y'=(-1,0,0) (otoceni o 90 stupnu) ---
    cs5 = define_coord_system3(
        Point(10.0, 20.0, 30.0), Vector(0.0, 1.0, 0.0), Vector(-1.0, 1.0, 0.0)
    )
    # ex = (0,1,0), h = (-1,1,0), h.ex=1 -> ey_raw = (-1,1,0)-(0,1,0) = (-1,0,0) -> ey=(-1,0,0)
    _assert_point_close(cs5.ex, 0.0, 1.0, 0.0, "cs5.ex")
    _assert_point_close(cs5.ey, -1.0, 0.0, 0.0, "cs5.ey")
    world = transform_point3(Point(5.0, 3.0, 0.0), cs5)
    # world = origin + 5*ex + 3*ey = (10,20,30) + 5*(0,1,0) + 3*(-1,0,0) = (7, 25, 30)
    _assert_point_close(world, 7.0, 25.0, 30.0, "transform_point3()")
    print("transform_point3(): OK - spravne pouziva origin + x*ex + y*ey + z*ez")

    # --- 6) transform_vector3: smerovy vektor se transformuje BEZ posunu ---
    world_vec = transform_vector3(Vector(5.0, 3.0, 0.0), cs5)
    _assert_point_close(world_vec, -3.0, 5.0, 0.0, "transform_vector3() - zadny origin posun")
    print("transform_vector3(): OK - zadny posun (jen rotace)")

    # --- 7) transform_spline3: cela krivka (body i tecny), metadata zachovana ---
    plane_spline = Spline(
        points=[Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0)],
        tangents=[Vector(1.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0)],
        closed=False,
        opcode="S03",
        parametrization="uniform",
    )
    world_spline = transform_spline3(plane_spline, cs5)
    _assert_point_close(world_spline.points[0], 10.0, 20.0, 30.0, "spline bod 0 (origin)")
    _assert_point_close(world_spline.points[1], 10.0, 21.0, 30.0, "spline bod 1 (+1*ex)")
    _assert_point_close(world_spline.tangents[0], 0.0, 1.0, 0.0, "spline tecna (jen rotace)")
    assert world_spline.opcode == "S03" and world_spline.parametrization == "uniform"
    assert world_spline.closed is False
    print("transform_spline3(): OK - transformuje body+tecny, zachova metadata (opcode/param./closed)")

    # --- 8) Q00/U00 - bod/vektor tremi souradnicemi/slozkami ---
    q = make_point3(1.5, -2.0, 3.25)
    _assert_point_close(q, 1.5, -2.0, 3.25, "make_point3() (Q00)")
    u = make_vector3(0.0, 1.0, 0.0)
    _assert_point_close(u, 0.0, 1.0, 0.0, "make_vector3() (U00)")
    print("make_point3()/make_vector3() (Q00/U00): OK")

    print()
    print("VSE OK - DCOOS3/TRA23 geometrie (geplib.dcoos3/geplib.tra23) je spravna.")


if __name__ == "__main__":
    main()
