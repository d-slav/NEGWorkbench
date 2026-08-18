# -*- coding: utf-8 -*-
"""
test_q38.py - Testy operace Q38 (prusecik krivky s rovinou, viz
G10.md 'Q38 - Prusecik krivky s rovinou', Fortran Q38.FOR + GLPRU.FOR).
Q38.FOR jen priprava vstupu a volani GLPRU s K=3 - STEJNA procedura,
kterou uz pouziva P22 (K=2, primka x 2D krivka) - viz gerlib/glpru.py
(_hyperplane_curve_intersections, sdilene jadro) pro presny popis
algoritmu a obou vrstev deduplikace, overenych proti dodanemu zdroji.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector
from geplib.t01 import make_spatial_spline
from geplib.q38 import curve_plane_intersection
from geplib.plane import make_plane_r01
from gerlib.errors import NoSolution
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def pt_isclose(p, x, y, z, eps=1e-6):
    return isclose(p.x, x, eps) and isclose(p.y, y, eps) and isclose(p.z, z, eps)


def main():
    plane_z0 = make_plane_r01(Vector(0.0, 0.0, 1.0), 0.0)  # rovina z=0

    # --- primy usek (K=2) protinajici rovinu presne v pulce ---
    straight = make_spatial_spline([Point(0.0, 0.0, -1.0), Point(0.0, 0.0, 1.0)], 2)
    p = curve_plane_intersection(straight, plane_z0, 1)
    check(pt_isclose(p, 0.0, 0.0, 0.0), "primy usek: prusecik presne v pulce")

    # --- zvlnena krivka (K=4), vice pruseciku, spravne poradi ---
    wavy = make_spatial_spline(
        [Point(0.0, 0.0, -1.0), Point(1.0, 0.0, 1.0), Point(2.0, 0.0, -1.0), Point(3.0, 0.0, 1.0)], 4,
    )
    prev_x = -1e9
    for k in (1, 2, 3):
        pk = curve_plane_intersection(wavy, plane_z0, k)
        check(isclose(pk.z, 0.0), "zvlnena krivka: prusecik %d lezi v rovine (z=0)" % k)
        check(pk.x > prev_x, "zvlnena krivka: prusecik %d je dal v poradi X nez predchozi" % k)
        prev_x = pk.x
    try:
        curve_plane_intersection(wavy, plane_z0, 4)
        check(False, "4. prusecik nemel existovat")
    except NoSolution:
        check(True, "zvlnena krivka: 4. prusecik neexistuje -> NoSolution")

    # --- rovina mimo dosah krivky - zadny prusecik ---
    plane_far = make_plane_r01(Vector(0.0, 0.0, 1.0), 100.0)  # rovina z=100
    try:
        curve_plane_intersection(straight, plane_far, 1)
        check(False, "rovina mimo dosah mela vyhodit NoSolution")
    except NoSolution:
        check(True, "rovina mimo dosah krivky -> NoSolution")

    # --- prusecik presne ve sdilenem uzlu dvou segmentu - jen JEDNOU ---
    shared_node = make_spatial_spline(
        [Point(0.0, 0.0, -1.0), Point(1.0, 0.0, 0.0), Point(2.0, 0.0, -1.0)], 3,
    )
    ps = curve_plane_intersection(shared_node, plane_z0, 1)
    check(pt_isclose(ps, 1.0, 0.0, 0.0), "sdileny uzel: 1. prusecik je stredni bod (1,0,0)")
    try:
        curve_plane_intersection(shared_node, plane_z0, 2)
        check(False, "sdileny uzel nesmi byt zapocitan dvakrat")
    except NoSolution:
        check(True, "sdileny uzel: zapocitan jen jednou (2. neexistuje)")

    # --- prusecik presne na POSLEDNIM bode cele krivky (posledni segment) ---
    ends_at_plane = make_spatial_spline(
        [Point(0.0, 0.0, -2.0), Point(1.0, 0.0, -1.0), Point(2.0, 0.0, 0.0)], 3,
    )
    pe = curve_plane_intersection(ends_at_plane, plane_z0, 1)
    check(pt_isclose(pe, 2.0, 0.0, 0.0), "posledni segment konci presne v rovine - musi se zapocitat")

    # --- sdilene jadro s P22: overit, ze Q38 opravdu pouziva GLPRU (K=3) ---
    from gerlib.glpru import plane_curve_intersections
    hits = plane_curve_intersections(wavy, plane_z0)
    check(len(hits) == 3, "plane_curve_intersections (K=3) vraci stejne pruseciky jako curve_plane_intersection")
    check(pt_isclose(hits[0][2], curve_plane_intersection(wavy, plane_z0, 1).x,
                      curve_plane_intersection(wavy, plane_z0, 1).y,
                      curve_plane_intersection(wavy, plane_z0, 1).z),
          "Q38 a primy dotaz na GLPRU davaji stejny 1. prusecik")

    # --- test pres realny GL3 zdrojovy text (vc. DIMEN, T01, R01) ---
    gl3_code = """
SUBRO/TESTQ38/out:QM1,out:QM2
DIMEN,Q(4)
Q(1)=Q00>0.0,0.0,-1.0
Q(2)=Q00>1.0,0.0,1.0
Q(3)=Q00>2.0,0.0,-1.0
Q(4)=Q00>3.0,0.0,1.0
TM=T01>Q(1),4.0
U1=U00>0.0,0.0,1.0
RM=R01>U1,0.0
QM1=Q38>TM,RM,1.0
QM2=Q38>TM,RM,2.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(isclose(env["QM1"].z, 0.0), "GL3: 1. prusecik v rovine")
    check(isclose(env["QM2"].z, 0.0), "GL3: 2. prusecik v rovine")
    check(env["QM1"].x < env["QM2"].x, "GL3: pruseciky ve spravnem poradi")

    print("\nVSE OK - Q38 (geplib.q38) je plne funkcni.")


if __name__ == "__main__":
    main()
