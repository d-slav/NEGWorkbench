# -*- coding: utf-8 -*-
"""
test_t01.py - Testy operace T01 (otevrena prostorova krivka mnozinou
K bodu s okrajovymi tecnymi vektory, secnova parametrizace - viz
G10.md 'T01 - Otevrena krivka prolozena mnozinou K bodu s okrajovymi
tecnymi vektory'; prostorova obdoba S01).

T01 je tenky wrapper nad gerlib.s01.make_spline (viz geplib/t01.py),
takze testy hlavne overuji: (1) spravnou provenience (opcode='T01'),
(2) ze funguje i s NENULOVOU Z-slozkou (3D, na rozdil od S01, kde je
Z v testovych datech typicky 0), (3) sdilene chovani se S01 (K=2 bez/
s tecnami, chybejici tecny na okrajich, horni mez K<=300), (4) test
pres realny GL3 zdrojovy text vc. DIMEN pole Q.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector
from geplib.t01 import make_spatial_spline
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-9):
    return abs(a - b) < eps


def vec_isclose(v, x, y, z, eps=1e-9):
    return isclose(v.x, x, eps) and isclose(v.y, y, eps) and isclose(v.z, z, eps)


def main():
    # --- zakladni 3D krivka (nenulova Z), zadne okrajove tecny ---
    pts = [Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 1.0), Point(2.0, 0.0, 2.0), Point(3.0, 1.0, 3.0)]
    sp = make_spatial_spline(pts, 4)
    check(sp.opcode == "T01", "provenience: opcode == 'T01'")
    check(sp.parametrization == "chordal", "provenience: parametrizace 'chordal' (stejna jako S01)")
    check(len(sp.points) == 4, "krivka ma 4 uzlove body")
    check(sp.points[2].z == 2.0, "Z-slozka uzlu se prenasi beze zmeny (skutecne 3D)")
    check(len(sp.segment_tangents) == 3, "krivka ma 3 segmenty (4 body)")

    # --- K=2 bez tecen -> primy usek (sekanta) ---
    sp_line = make_spatial_spline([Point(0.0, 0.0, 0.0), Point(1.0, 2.0, 3.0)], 2)
    t0, t1 = sp_line.segment_tangent_pair(0)
    check(vec_isclose(t0, 1.0, 2.0, 3.0) and vec_isclose(t1, 1.0, 2.0, 3.0),
          "K=2 bez tecen: primy usek, tecna = sekanta (3D)")

    # --- K=2 s explicitnimi tecnami ---
    sp_line2 = make_spatial_spline(
        [Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0)], 2,
        Vector(0.0, 1.0, 0.5), Vector(0.0, -1.0, 0.5),
    )
    t0b, t1b = sp_line2.segment_tangent_pair(0)
    check(vec_isclose(t0b, 0.0, 1.0, 0.5), "K=2 s tecnami: pocatecni tecna zachovana (smer, ne sekanta)")
    check(vec_isclose(t1b, 0.0, -1.0, 0.5), "K=2 s tecnami: koncova tecna zachovana")

    # --- K>2 bez okrajovych tecen: relaxovana okrajova podminka (nesmi spadnout) ---
    sp_relaxed = make_spatial_spline(
        [Point(0.0, 0.0, 0.0), Point(1.0, 2.0, 0.0), Point(2.0, 0.0, 1.0), Point(3.0, 2.0, 1.0)], 4,
    )
    check(len(sp_relaxed.segment_tangents) == 3, "K>2 bez okrajovych tecen: krivka se sestavi (relaxovana okrajova podminka)")

    # --- horni mez K<=300 (viz G07.md, sdileno s S01) ---
    try:
        make_spatial_spline([Point(float(i), 0.0, 0.0) for i in range(400)], 400)
        check(False, "K=400 melo vyhodit ValueError (K<=300)")
    except ValueError as e:
        check("T01" in str(e), "K>300 -> ValueError se spravnym oznacenim opcode (T01, ne S01)")

    # --- test pres realny GL3 zdrojovy text (vc. DIMEN pole Q) ---
    gl3_code = """
SUBRO/TESTT01/out:TM1,out:TM2
DIMEN,Q(4)
Q(1)=Q00>0.0,0.0,0.0
Q(2)=Q00>1.0,1.0,1.0
Q(3)=Q00>2.0,0.0,2.0
Q(4)=Q00>3.0,1.0,3.0
TM1=T01>Q(1),4.0
U1=U00>0.0,1.0,0.0
U2=U00>0.0,-1.0,0.0
DIMEN,QQ(2)
QQ(1)=Q00>0.0,0.0,0.0
QQ(2)=Q00>1.0,0.0,0.0
TM2=T01>QQ(1),2.0,U1,U2
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    tm1 = env["TM1"]
    check(tm1.opcode == "T01", "GL3: TM1 opcode == 'T01'")
    check([(p.x, p.y, p.z) for p in tm1.points] == [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (2.0, 0.0, 2.0), (3.0, 1.0, 3.0)],
          "GL3: TM1 uzlove body odpovidaji poli Q")

    tm2 = env["TM2"]
    gt0, gt1 = tm2.segment_tangent_pair(0)
    check(vec_isclose(gt0, 0.0, 1.0, 0.0) and vec_isclose(gt1, 0.0, -1.0, 0.0),
          "GL3: TM2 (K=2, U1/U2) ma spravne okrajove tecny")

    print("\nVSE OK - T01 (geplib.t01) je plne funkcni.")


if __name__ == "__main__":
    main()
