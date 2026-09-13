# -*- coding: utf-8 -*-
"""
test_t47.py - Testy operace T47 (spojeni dvou 3D krivek, viz G10.md
'T47 - Spojeni dvou 3D krivek'; prostorova obdoba S47).

T47 je tenky wrapper nad gerlib.s47.make_joined_spline (viz
geplib/t47.py - S47 a T47 pochazeji ze stejneho zdrojoveho souboru
S47.FOR podle zadani uzivatele), takze testy hlavne overuji spravnou
provenience (opcode='T47'), 3D (nenulova Z) a integraci pres realny
GL3 zdrojovy text.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector
from geplib.t01 import make_spatial_spline as make_t01
from geplib.t47 import make_joined_spatial_spline
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


def main():
    # --- 3D krivky (nenulova Z), ruzne tecny na obou stranach spoje ---
    t1 = make_t01([Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 5.0)], 2, u1=Vector(1, 0, 0), uk=Vector(1, 1, 1))
    t2 = make_t01([Point(10.0, 0.0, 5.0), Point(20.0, 0.0, 5.0)], 2, u1=Vector(1, -1, 0), uk=Vector(1, 0, 0))
    own_end_t1 = t1.segment_tangent_pair(0)[1]
    own_start_t2 = t2.segment_tangent_pair(0)[0]

    joined = make_joined_spatial_spline(t1, t2, 0)
    check(joined.opcode == "T47", "provenience: opcode == 'T47'")
    check(len(joined.points) == 3, "spojena krivka ma 3 uzly")
    check(joined.points[1].z == 5.0, "Z-slozka spolecneho bodu se prenasi beze zmeny (skutecne 3D)")

    t_end1 = joined.segment_tangent_pair(0)[1]
    t_start2 = joined.segment_tangent_pair(1)[0]
    check(
        (round(t_end1.x, 9), round(t_end1.y, 9), round(t_end1.z, 9))
        == (round(own_end_t1.x, 9), round(own_end_t1.y, 9), round(own_end_t1.z, 9)),
        "K=0: konec T1 ve spoji ma svou vlastni tecnu",
    )
    check(
        (round(t_start2.x, 9), round(t_start2.y, 9), round(t_start2.z, 9))
        == (round(own_start_t2.x, 9), round(own_start_t2.y, 9), round(own_start_t2.z, 9)),
        "K=0: zacatek T2 ve spoji ma svou vlastni tecnu",
    )

    joined_k1 = make_joined_spatial_spline(t1, t2, 1)
    t_end1_k1 = joined_k1.segment_tangent_pair(0)[1]
    t_start2_k1 = joined_k1.segment_tangent_pair(1)[0]
    check(
        (round(t_end1_k1.x, 9), round(t_end1_k1.y, 9)) == (round(t_start2_k1.x, 9), round(t_start2_k1.y, 9)),
        "K=1: obe strany spoje maji stejnou (T1 own) tecnu",
    )

    # --- test pres realny GL3 zdrojovy text ---
    gl3_code = """
SUBRO/TESTT47/out:TJ
DIMEN,Q(2)
DIMEN,QQ(2)
Q(1)=Q00>0.0,0.0,0.0
Q(2)=Q00>10.0,0.0,5.0
T1=T01>Q(1),2
QQ(1)=Q00>10.0,0.0,5.0
QQ(2)=Q00>20.0,0.0,5.0
T2=T01>QQ(1),2
TJ=T47>T1,T2,2
RETSUB
END
"""
    program = parse_program(gl3_code)
    env = Interpreter().run(program, {})
    tj = env["TJ"]
    check(tj.opcode == "T47", "GL3: TJ opcode == 'T47'")
    check(
        [(round(p.x, 6), round(p.y, 6), round(p.z, 6)) for p in tj.points]
        == [(0.0, 0.0, 0.0), (10.0, 0.0, 5.0), (20.0, 0.0, 5.0)],
        "GL3: TJ uzlove body odpovidaji T1 nasledovanemu T2",
    )

    print("\nVSE OK - T47 (geplib.t47) je plne funkcni.")


if __name__ == "__main__":
    main()
