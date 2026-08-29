# -*- coding: utf-8 -*-
"""Test prikazu TYPE (G13.md 'PRIKAZY VYSTUPU TYPU TYPE') a s tim
souvisejici opravu PRINT/WRITE - obecny formatovac libovolneho GL3
objektu (gl3_ops.format_components), predtim jen Point/skalar (Circle,
Line, Vector, 3D typy, i B-string by drive spadly na float(value))."""
import contextlib
import io
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


def run_capture(src, inputs=None):
    subdef = parse_program(src)
    interp = Interpreter()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        env = interp.run(subdef, inputs or {})
    return buf.getvalue(), env


def main():
    # --- 1) presny priklad z G13.md: TYPE,BO,QA,'  LEZI NA KRIVCE T' ---
    out, _ = run_capture("""
SUBRO/T1/out:D1
BO='BOD Q'
QA=Q00>50.0,23.5,0.0
TYPE,BO,QA,'  LEZI NA KRIVCE T'
D1=1.0
RETSUB
END
""")
    check(out.strip() == "BOD Q 50.000 23.500 0.000   LEZI NA KRIVCE T",
          "presny priklad z G13.md pro TYPE: %r" % out)

    # --- 2) TYPE spoji cislo (I) a literaly do JEDNOHO radku ---
    out, _ = run_capture("""
SUBRO/T2/out:D1
IK=5
TYPE,'K=',IK
D1=1.0
RETSUB
END
""")
    check(out.strip() == "K= 5", "TYPE s celym cislem: %r" % out)

    # --- 3) TYPE jen s literaly (zadna promenna) ---
    out, _ = run_capture("""
SUBRO/T3/out:D1
TYPE,'hello',' ','world'
D1=1.0
RETSUB
END
""")
    check(out.strip() == "hello   world", "TYPE jen s literaly: %r" % out)

    # --- 4) PRINT retezcove (B) promenne - drive spadlo na float(value) ---
    out, _ = run_capture("""
SUBRO/T4/out:D1
BX='hello world'
PRINT,BX
D1=1.0
RETSUB
END
""")
    check("hello world" in out, "PRINT B (retezec) uz nespada, vypise text: %r" % out)

    # --- 5) PRINT Circle (2D) -> 3 cisla (stred x,y + polomer) ---
    out, _ = run_capture("""
SUBRO/T5/out:D1
C1=C00>5.0,5.0,10.0
PRINT,C1
D1=1.0
RETSUB
END
""")
    check("5.000" in out and "10.000" in out, "PRINT Circle (2D) -> 3 cisla: %r" % out)

    # --- 6) PRINT Line (2D) -> 4 cisla (bod x,y + smer x,y) ---
    out, _ = run_capture("""
SUBRO/T6/out:D1
P1=P00>0.0,0.0
P2=P00>1.0,1.0
LN=L04>P1,P2
PRINT,LN
D1=1.0
RETSUB
END
""")
    check(out.count("0.000") >= 2, "PRINT Line (2D) -> 4 cisla: %r" % out)

    # --- 7) retezec (E, promenlivy pocet uzlovych bodu) v PRINT -> jasna
    #     chyba, ne spatny/napolo vypocteny vysledek ---
    src7 = """
SUBRO/T7/out:D1
P1=P00>0.0,0.0
P2=P00>1.0,0.0
CRE,EE
MOVE/P1*P2
ENDCRE
PRINT,EE
D1=1.0
RETSUB
END
"""
    try:
        run_capture(src7)
        check(False, "PRINT retezce (E) mel vyhodit NotYetImplemented")
    except NotYetImplemented as e:
        check("retezec" in str(e) or "E" in str(e), "PRINT retezce (E) -> jasna chyba: %s" % e)

    print()
    print("Vsechny testy TYPE + PRINT/WRITE formatovani OK.")


if __name__ == "__main__":
    main()
