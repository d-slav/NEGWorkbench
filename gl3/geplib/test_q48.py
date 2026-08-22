# -*- coding: utf-8 -*-
"""
test_q48.py - Testy operace Q48 (vyjmuty uzlovy bod retezce nebo
krivky, viz G10.md 'Q48 - Vyjmuty uzlovy bod retezce nebo krivky';
prostorova obdoba P48 - viz gerlib/p48.py).

Klicovy rozdil oproti P48: Q48 NESMI ztratit Z-slozku (P48 ji na
vystupu tvrde nuluje - pro rovinny retezec/krivku E/S neskodne, pro
prostorovy H/T by to byla skutecna ztrata dat).

Pri implementaci se navic nasel a opravil sdileny latentni bug v
gerlib.p48._node_index_and_flag: K se nekonvertovalo na int pred
indexovanim seznamu bodu, takze K jako FLOAT (jak ho vzdy predava
realny GL3 interpret - napr. 2.0, ne "cisty" int 2) spadlo na
"list indices must be integers". Test niz i test_npo_p48.py to overuji.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from geplib.h02 import make_chain3
from geplib.t01 import make_spatial_spline
from geplib.q48 import chain_node3, spline_node3, curve_node3
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-9):
    return abs(a - b) < eps


def pt_isclose(p, x, y, z, eps=1e-9):
    return isclose(p.x, x, eps) and isclose(p.y, y, eps) and isclose(p.z, z, eps)


def main():
    h = make_chain3(Point(0.0, 0.0, 0.0), Point(1.0, 2.0, 3.0), Point(4.0, 5.0, 6.0))

    # --- zakladni pripady, K jako int ---
    p1, idx1, end1 = chain_node3(h, 1)
    check(pt_isclose(p1, 0.0, 0.0, 0.0) and idx1 == 1 and end1 is False, "H uzel K=1")
    p2, idx2, end2 = chain_node3(h, 2)
    check(pt_isclose(p2, 1.0, 2.0, 3.0) and idx2 == 2 and end2 is False, "H uzel K=2")
    p3, idx3, end3 = chain_node3(h, 3)
    check(pt_isclose(p3, 4.0, 5.0, 6.0) and idx3 == 2 and end3 is True,
          "H uzel K=N (posledni): index=N-1, is_end=True (jako P48)")

    # --- KLICOVY rozdil oproti P48: Z-slozka se NEZTRACI ---
    check(p2.z == 3.0, "Q48 zachovava Z-slozku (na rozdil od P48, ktere ji nuluje)")

    # --- K jako FLOAT (realny GL3 interpret) - byval to latentni bug ---
    p2f, _, _ = chain_node3(h, 2.0)
    check(pt_isclose(p2f, 1.0, 2.0, 3.0), "K jako float (2.0) funguje stejne jako int 2")

    # --- chybove stavy ---
    try:
        chain_node3(h, 0)
        check(False, "K=0 mel vyhodit ValueError")
    except ValueError:
        check(True, "K=0 -> ValueError (256)")
    try:
        chain_node3(h, 4)
        check(False, "K=N+1 mel vyhodit ValueError")
    except ValueError:
        check(True, "K=N+1 -> ValueError (256)")

    # --- prostorova krivka (T) ---
    t = make_spatial_spline([Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 5.0), Point(2.0, 0.0, 10.0)], 3)
    q1, _, _ = spline_node3(t, 1)
    q2, _, _ = spline_node3(t, 2)
    q3, _, end3t = spline_node3(t, 3)
    check(pt_isclose(q1, 0.0, 0.0, 0.0), "T uzel K=1")
    check(pt_isclose(q2, 1.0, 1.0, 5.0), "T uzel K=2 (zachovana Z)")
    check(pt_isclose(q3, 2.0, 0.0, 10.0) and end3t is True, "T uzel K=N (posledni)")

    # --- dispatch podle typu (curve_node3) ---
    check(pt_isclose(curve_node3(h, 2), 1.0, 2.0, 3.0), "curve_node3 na Curve (H)")
    check(pt_isclose(curve_node3(t, 2), 1.0, 1.0, 5.0), "curve_node3 na Spline (T)")
    try:
        curve_node3("not a curve", 1)
        check(False, "spatny typ mel vyhodit TypeError")
    except TypeError:
        check(True, "spatny typ objektu -> TypeError")

    # --- test pres realny GL3 zdrojovy text (K prichazi jako float) ---
    gl3_code = """
SUBRO/TESTQ48/out:QM1,out:QM2,out:QM3
QA=Q00>0.0,0.0,0.0
QB=Q00>1.0,2.0,3.0
QC=Q00>4.0,5.0,6.0
HM=H02>QA,QB,QC
DIMEN,Q(3)
Q(1)=Q00>0.0,0.0,0.0
Q(2)=Q00>1.0,1.0,5.0
Q(3)=Q00>2.0,0.0,10.0
TM=T01>Q(1),3.0
QM1=Q48>HM,2.0
QM2=Q48>TM,3.0
QM3=Q48>HM,1.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(pt_isclose(env["QM1"], 1.0, 2.0, 3.0), "GL3: Q48 na retezci H (K=2.0)")
    check(pt_isclose(env["QM2"], 2.0, 0.0, 10.0), "GL3: Q48 na krivce T (K=3.0, posledni)")
    check(pt_isclose(env["QM3"], 0.0, 0.0, 0.0), "GL3: Q48 na retezci H (K=1.0)")

    # --- NPO (pocet uzlovych bodu) funguje i na prostorovem retezci/krivce
    # BEZE ZMENY (uz je to genericke pres .points, viz gerlib/npo.py) ---
    from gerlib.npo import point_count
    check(point_count(h) == 3, "NPO funguje na prostorovem retezci (H)")
    check(point_count(t) == 3, "NPO funguje na prostorove krivce (T)")

    gl3_npo_code = """
SUBRO/TESTNPO3D/out:N1,out:N2
QA=Q00>0.0,0.0,0.0
QB=Q00>1.0,2.0,3.0
QC=Q00>4.0,5.0,6.0
HM=H02>QA,QB,QC
DIMEN,Q(4)
Q(1)=Q00>0.0,0.0,0.0
Q(2)=Q00>1.0,1.0,5.0
Q(3)=Q00>2.0,0.0,10.0
Q(4)=Q00>3.0,3.0,15.0
TM=T01>Q(1),4.0
N1=NPO>HM
N2=NPO>TM
RETSUB
END
"""
    npo_program = parse_program(gl3_npo_code)
    npo_interp = Interpreter()
    npo_env = npo_interp.run(npo_program, {})
    check(npo_env["N1"] == 3, "GL3: NPO na retezci H vraci 3")
    check(npo_env["N2"] == 4, "GL3: NPO na krivce T vraci 4")

    print("\nVSE OK - Q48 (geplib.q48) je plne funkcni a NPO funguje i na H/T.")


if __name__ == "__main__":
    main()
