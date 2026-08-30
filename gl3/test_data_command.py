# -*- coding: utf-8 -*-
"""Test prikazu DATA (viz manual dodany v konverzaci) - typove
sestaveni objektu (D,I,B,P,V,C,L), indexovany cil, vicero objektu na
radku, viceradkove konstanty, chybove stavy."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gl3_ops import NotYetImplemented


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def run(src, inputs=None):
    return Interpreter().run(parse_program(src), inputs=inputs or {})


def main():
    # --- P (bod, 2 konstanty), viceradkove, bez indexu (od 1) ---
    src = """
SUBRO/T1/out:S1
DIMEN,P(6)
DATA,P,6
-30.0,20.0
-16.0,23.0
-10.0,10.0
0.0,10.0
0.0,20.0
15.0,20.0
J=NPO>P
S1=S01>P,J
RETSUB
END
"""
    r = run(src)
    s1 = r.get("S1")
    check(len(s1.points) == 6, "DATA P: sestrojena krivka se 6 body")
    check(s1.points[0].x == -30.0 and s1.points[0].y == 20.0, "DATA P: prvni bod souhlasi")
    check(s1.points[5].x == 15.0 and s1.points[5].y == 20.0, "DATA P: posledni bod souhlasi")

    # --- indexovany cil DATA,P(2),1 ---
    src2 = """
SUBRO/T2/out:X,out:Y
DIMEN,P(6)
DATA,P(2),1
99.0,88.0
X=P(2)
RETSUB
END
"""
    r2 = run(src2)
    p2 = r2.get("X")
    check(p2.x == 99.0 and p2.y == 88.0, "DATA P(2),1: zapis presne na index 2")

    # --- vice objektu na jednom radku (C - 3 konstanty) ---
    src3 = """
SUBRO/T3/out:R1,out:R2
DIMEN,C(2)
DATA,C,2
1.0,2.0,5.0,3.0,4.0,6.0
R1=C(1)
R2=C(2)
RETSUB
END
"""
    r3 = run(src3)
    c1, c2 = r3.get("R1"), r3.get("R2")
    check(c1.center.x == 1.0 and c1.center.y == 2.0 and c1.radius == 5.0, "DATA C: prvni kruznice")
    check(c2.center.x == 3.0 and c2.center.y == 4.0 and c2.radius == 6.0, "DATA C: druha kruznice (na stejnem radku)")

    # --- L (primka, 4 konstanty) ---
    src4 = """
SUBRO/T4/out:R1
DIMEN,L(1)
DATA,L,1
1.0,2.0,10.0,0.0
R1=L(1)
RETSUB
END
"""
    r4 = run(src4)
    line = r4.get("R1")
    check(line.origin.x == 1.0 and line.origin.y == 2.0, "DATA L: pocatecni bod")
    check(line.direction.x == 10.0 and line.direction.y == 0.0, "DATA L: smerovy vektor")

    # --- V (vektor), D (skalar), I (cele cislo) ---
    src5 = """
SUBRO/T5/out:R1,out:R2,out:R3
DIMEN,V(1),D(1),I(1)
DATA,V,1
3.0,4.0
DATA,D,1
2.5
DATA,I,1
7
R1=V(1)
R2=D(1)
R3=I(1)
RETSUB
END
"""
    r5 = run(src5)
    check(r5.get("R1").x == 3.0 and r5.get("R1").y == 4.0, "DATA V: vektor")
    check(r5.get("R2") == 2.5, "DATA D: skalar")
    check(r5.get("R3") == 7, "DATA I: cele cislo")

    # --- chybovy stav: spatny pocet konstant ---
    bad1 = """
SUBRO/BAD1/out:K
DIMEN,P(2)
DATA,P,2
1.0,2.0,3.0
K=1
RETSUB
END
"""
    try:
        run(bad1)
        check(False, "DATA: spatny pocet konstant mel vyhodit ValueError")
    except ValueError:
        check(True, "DATA: spatny pocet konstant -> ValueError")

    # --- chybovy stav: chybejici DIMEN ---
    bad2 = """
SUBRO/BAD2/out:K
DATA,P,1
1.0,2.0
K=1
RETSUB
END
"""
    try:
        run(bad2)
        check(False, "DATA: chybejici DIMEN mel vyhodit NameError")
    except NameError:
        check(True, "DATA: chybejici DIMEN -> NameError")

    # --- chybovy stav: nepodporovany 3D typ ---
    bad3 = """
SUBRO/BAD3/out:K
DIMEN,Q(1)
DATA,Q,1
1.0,2.0,3.0
K=1
RETSUB
END
"""
    try:
        run(bad3)
        check(False, "DATA: 3D typ Q mel vyhodit NotYetImplemented")
    except NotImplementedError:
        check(False, "DATA: 3D typ Q vyhodilo vestaveny NotImplementedError - "
                      "FreeCAD ho tise polyka jako 'not implemented', musi to "
                      "byt gl3_ops.NotYetImplemented (viz jeho docstring)")
    except NotYetImplemented:
        check(True, "DATA: 3D typ Q (zatim nepodporovano) -> NotYetImplemented "
                     "(NE vestaveny NotImplementedError - viz duvod v gl3_ops.py)")

    print("Vse OK.")


if __name__ == "__main__":
    main()
