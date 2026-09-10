# -*- coding: utf-8 -*-
"""
test_t03.py - Testy operace T03 (otevrena hranicni krivka plochy
prolozena body, parametrizace 0-1 - viz G10.md 'T03 - Otevrena
hranicni krivka plochy prolozena body parametrizovana 0-1';
prostorova obdoba S03).

T03 je tenky wrapper nad gerlib.s03.make_spline (viz geplib/t03.py -
zadani uzivatele: T03 pouziva stejny fortranovy zdroj jako S03), takze
testy hlavne overuji: (1) spravnou provenience (opcode='T03',
parametrizace 'uniform'), (2) 3D (nenulova Z), (3) KLICOVY rozdil
oproti T01: delka U1/UK NA TVAR MA VLIV (na rozdil od T01, kde se
delka ignoruje - viz test_t01.py a oprava v gerlib/s01.py), (4) N
(kazdy N-ty bod), (5) test pres realny GL3 zdrojovy text.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector
from geplib.t03 import make_spatial_spline
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
    check(sp.opcode == "T03", "provenience: opcode == 'T03'")
    check(sp.parametrization == "uniform", "provenience: parametrizace 'uniform' (stejna jako S03, NE 'chordal' jako T01)")
    check(len(sp.points) == 4, "krivka ma 4 uzlove body")
    check(sp.points[2].z == 2.0, "Z-slozka uzlu se prenasi beze zmeny (skutecne 3D)")

    # --- K=2 bez tecen -> primy usek (sekanta) ---
    sp_line = make_spatial_spline([Point(0.0, 0.0, 0.0), Point(1.0, 2.0, 3.0)], 2)
    check(vec_isclose(sp_line.tangents[0], 1.0, 2.0, 3.0), "K=2 bez tecen: tecna = sekanta (3D)")

    # --- KLICOVY rozdil oproti T01: DELKA U1/UK NA TVAR MA VLIV ---
    short_u = Vector(0.0, 1.0, 0.0)
    long_u = Vector(0.0, 5.0, 0.0)
    sp_short = make_spatial_spline([Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0)], 2, short_u, short_u)
    sp_long = make_spatial_spline([Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0)], 2, long_u, long_u)
    check(vec_isclose(sp_short.tangents[0], 0.0, 1.0, 0.0), "K=2: kratsi U1 se POUZIJE beze zmeny (na rozdil od T01)")
    check(vec_isclose(sp_long.tangents[0], 0.0, 5.0, 0.0), "K=2: 5x delsi U1 dava JINY (5x vetsi) vysledek - delka MA vliv")

    # --- N: kazdy N-ty bod puvodniho pole ---
    all_pts = [Point(float(i), 0.0, 0.0) for i in range(9)]  # 0..8
    sp_n = make_spatial_spline(all_pts, 3, n=4)  # Q(1), Q(5), Q(9) -> indexy 0,4,8
    check(
        [(p.x, p.y, p.z) for p in sp_n.points] == [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (8.0, 0.0, 0.0)],
        "N=4: vybere kazdy 4. bod (Q(1),Q(5),Q(9))",
    )

    # --- horni mez K<=128 (viz G10.md, sdileno s S03/S02) ---
    try:
        make_spatial_spline([Point(float(i), 0.0, 0.0) for i in range(129)], 129)
        check(False, "K=129 melo vyhodit ValueError (K<=128)")
    except ValueError as e:
        check("T03" in str(e), "K>128 -> ValueError se spravnym oznacenim opcode (T03, ne S03)")

    # --- test pres realny GL3 zdrojovy text ---
    gl3_code = """
SUBRO/TESTT03/out:TM1,out:TM2
DIMEN,Q(4)
Q(1)=Q00>0.0,0.0,0.0
Q(2)=Q00>1.0,1.0,1.0
Q(3)=Q00>2.0,0.0,2.0
Q(4)=Q00>3.0,1.0,3.0
TM1=T03>Q(1),4.0
U1=U00>0.0,5.0,0.0
U2=U00>0.0,-5.0,0.0
DIMEN,QQ(2)
QQ(1)=Q00>0.0,0.0,0.0
QQ(2)=Q00>1.0,0.0,0.0
TM2=T03>QQ(1),2.0,U1,U2
RETSUB
END
"""
    program = parse_program(gl3_code)
    env = Interpreter().run(program, {})

    tm1 = env["TM1"]
    check(tm1.opcode == "T03", "GL3: TM1 opcode == 'T03'")
    check([(p.x, p.y, p.z) for p in tm1.points] == [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (2.0, 0.0, 2.0), (3.0, 1.0, 3.0)],
          "GL3: TM1 uzlove body odpovidaji poli Q")

    tm2 = env["TM2"]
    check(vec_isclose(tm2.tangents[0], 0.0, 5.0, 0.0), "GL3: TM2 (K=2, U1=(0,5,0)) - DELKA U1 se respektuje")

    print("\nVSE OK - T03 (geplib.t03) je plne funkcni.")


if __name__ == "__main__":
    main()
