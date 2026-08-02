# -*- coding: utf-8 -*-
"""
test_dcoos3_tra23_interpreter.py - overuje DCOOS3/TRA23 na urovni
skutecneho GL3 zdrojoveho textu (parse_program + Interpreter.run()),
ne jen cistou geometrii (viz test_dcoos3_tra23.py pro tu).
"""
import math

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gerlib import Point, Vector
from gerlib.types import Spline


def _assert_close(a, b, msg, eps=1e-9):
    assert abs(a - b) < eps, "%s: %r != %r" % (msg, a, b)


def main():
    # --- 1) pole bodu P -> Q pres DCOOS3+TRA23 (identicka soustava Q0/UX/UY) ---
    src_points = """
SUBRO/TTRA23P/in:P(2),out:Q(2)
DIMEN,Q(2)
DCOOS3,1,Q0,UX,UY
TRA23,Q(1),P(1),2,1
RETSUB
END
"""
    subdef = parse_program(src_points)
    interp = Interpreter()
    env = interp.run(subdef, {"P": [Point(1.0, 2.0, 0.0), Point(3.0, 4.0, 0.0)]})

    q = env["Q"]
    assert isinstance(q, list) and len(q) == 2
    _assert_close(q[0].x, 1.0, "Q(1).x"); _assert_close(q[0].y, 2.0, "Q(1).y"); _assert_close(q[0].z, 0.0, "Q(1).z")
    _assert_close(q[1].x, 3.0, "Q(2).x"); _assert_close(q[1].y, 4.0, "Q(2).y"); _assert_close(q[1].z, 0.0, "Q(2).z")
    print("DCOOS3+TRA23 (pole P->Q, identicka soustava): OK - %r" % [(p.x, p.y, p.z) for p in q])

    # --- 2) totez, ale s POSUNUTOU a POOTOCENOU soustavou (realny test transformace) ---
    src_points_shifted = """
SUBRO/TTRA23P2/in:P(1),out:Q(1)
DIMEN,Q(1)
DCOOS3,1,Q0,UY,UXN
TRA23,Q(1),P(1),1,1
RETSUB
END
"""
    subdef2 = parse_program(src_points_shifted)
    interp2 = Interpreter()
    env2 = interp2.run(subdef2, {"P": [Point(1.0, 0.0, 0.0)]})
    # ex=UY=(0,1,0), h=UXN=(-1,0,0), h.ex=0 -> ey=(-1,0,0) primo (uz kolme)
    # bod (1,0) v mistni s.s. -> origin + 1*ex + 0*ey = (0,0,0)+(0,1,0) = (0,1,0)
    q2 = env2["Q"]
    _assert_close(q2[0].x, 0.0, "otoceny pripad Q(1).x")
    _assert_close(q2[0].y, 1.0, "otoceny pripad Q(1).y")
    _assert_close(q2[0].z, 0.0, "otoceny pripad Q(1).z")
    print("DCOOS3+TRA23 (pole P->Q, otocena soustava UY/UXN): OK - Q(1) = (%r, %r, %r)"
          % (q2[0].x, q2[0].y, q2[0].z))

    # --- 3) cela krivka S -> T (jednotlivy objekt, ne pole) ---
    src_curve = """
SUBRO/TTRA23S/in:S,out:T
DCOOS3,2,Q0,UX,UY
TRA23,T,S,0,2
RETSUB
END
"""
    subdef3 = parse_program(src_curve)
    interp3 = Interpreter()
    plane_spline = Spline(
        points=[Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)],
        tangents=[Vector(1.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)],
        closed=False,
        opcode="S03",
        parametrization="uniform",
    )
    env3 = interp3.run(subdef3, {"S": plane_spline})
    t = env3["T"]
    assert isinstance(t, Spline)
    _assert_close(t.points[1].x, 1.0, "T bod 1 x"); _assert_close(t.points[1].y, 1.0, "T bod 1 y")
    assert t.opcode == "S03" and t.parametrization == "uniform" and t.closed is False
    print("DCOOS3+TRA23 (cela krivka S->T, identicka soustava): OK - metadata zachovana")

    # --- 4) chybovy stav: TRA23 na nedefinovanou souradnicovou soustavu ---
    src_bad_cs = """
SUBRO/TBADCS/in:P(1),out:Q(1)
TRA23,Q(1),P(1),1,7
RETSUB
END
"""
    subdef4 = parse_program(src_bad_cs)
    interp4 = Interpreter()
    try:
        interp4.run(subdef4, {"P": [Point(0.0, 0.0, 0.0)]})
        raise AssertionError("melo vyhodit ValueError - souradnicova soustava 7 neexistuje")
    except ValueError as e:
        assert "nebyla definovana" in str(e)
        print("TRA23 na nedefinovanou soustavu: OK - jasna chyba (%s)" % e)

    # --- 5) chybovy stav: DCOOS3 s cislem soustavy mimo rozsah 1..10 ---
    src_bad_vi = """
SUBRO/TBADVI/out:Q(1)
DCOOS3,11,Q0,UX,UY
RETSUB
END
"""
    subdef5 = parse_program(src_bad_vi)
    interp5 = Interpreter()
    try:
        interp5.run(subdef5, {})
        raise AssertionError("melo vyhodit ValueError - cislo soustavy mimo rozsah 1..10")
    except ValueError as e:
        assert "1..10" in str(e)
        print("DCOOS3 s cislem mimo rozsah: OK - jasna chyba (%s)" % e)

    # --- 6) souradnicove soustavy jsou izolovane mezi behy (novy Interpreter) ---
    interp6a = Interpreter()
    interp6a.run(parse_program("SUBRO/TCS1/out:Q(1)\nDCOOS3,5,Q0,UX,UY\nRETSUB\nEND\n"), {})
    assert 5 in interp6a.coordinate_systems

    interp6b = Interpreter()  # NOVY beh - nema videt souradnicovou soustavu z interp6a
    assert 5 not in interp6b.coordinate_systems
    print("Souradnicove soustavy: OK - izolovane mezi ruznymi behy (novy Interpreter())")

    # --- 7) Q00/U00 pouzite primo v GL3 zdroji (misto builtin konstant) -
    # definice souradnicove soustavy pomoci bodu/vektoru sestavenych za
    # behu z cisel, ne z predpripravenych konstant Q0/UX/UY. ---
    src_q00_u00 = """
SUBRO/TQ00U00/in:P(1),out:Q(1)
DIMEN,Q(1)
QC=Q00>10.0,20.0,30.0
UEX=U00>1.0,0.0,0.0
UEY=U00>0.0,1.0,0.0
DCOOS3,4,QC,UEX,UEY
TRA23,Q(1),P(1),1,4
RETSUB
END
"""
    subdef7 = parse_program(src_q00_u00)
    interp7 = Interpreter()
    env7 = interp7.run(subdef7, {"P": [Point(5.0, 3.0, 0.0)]})
    q7 = env7["Q"]
    # origin (10,20,30) + 5*ex(1,0,0) + 3*ey(0,1,0) = (15, 23, 30)
    _assert_close(q7[0].x, 15.0, "Q00/U00 v GL3 zdroji - Q(1).x")
    _assert_close(q7[0].y, 23.0, "Q00/U00 v GL3 zdroji - Q(1).y")
    _assert_close(q7[0].z, 30.0, "Q00/U00 v GL3 zdroji - Q(1).z")
    print("Q00/U00 pouzite primo v GL3 zdroji (QC/UEX/UEY sestavene z cisel): OK - Q(1) = (%r, %r, %r)"
          % (q7[0].x, q7[0].y, q7[0].z))

    print()
    print("VSE OK - DCOOS3/TRA23 funguji na urovni skutecneho GL3 zdrojoveho textu.")


if __name__ == "__main__":
    main()
