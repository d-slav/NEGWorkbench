# -*- coding: utf-8 -*-
"""
test_call_indexed_out.py - CALL s indexovanym cilem pro out: parametr
(napr. 'CALL/MakeCut/P,I,230,100,T(3)' - vysledek se zapise do T(3),
ne do cele nove promenne T) - zadani uzivatele.

Drive fungoval jako cil pro out: parametr jen holy identifikator
(napr. 'TT') - indexovany vyraz jako 'T(3)' se choval jako "literal na
miste vystupu", tedy se tise ZAHODIL (zadny zapis nikam). Ted se
'T(3)' (i s indexem jako vyrazem/promennou, napr. 'T(I)', ne jen
literalem) parsuje stejnym vyrazovym parserem jako kdekoliv jinde v
jazyce a zapise se do prislusneho prvku JIZ EXISTUJICIHO (DIMEN)
pole T v prostredi volajiciho.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter, GL3RuntimeError


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


MAKECUT = """
SUBRO/MakeCut/in:P(2),in:II,in:DposX,in:DoffY,out:T
T=Q00>DposX,DoffY,0
RETSUB
END
"""


def run(main_src):
    main_def = parse_program(main_src)
    sub_def = parse_program(MAKECUT)
    return Interpreter(registry={"MakeCut": sub_def}).run(main_def, {})


def main():
    # --- 1) T(3) - literal index ---
    src1 = """
SUBRO/MAIN1/out:D1
DIMEN,P(2)
DIMEN,I(2)
DIMEN,T(5)
P(1)=Q00>0,0,0
P(2)=Q00>1,1,1
I(1)=1
CALL/MakeCut/P,I,230,100,T(3)
D1=1.0
RETSUB
END
"""
    env = run(src1)
    t = env["T"]
    check(t[2].x == 230.0 and t[2].y == 100.0, "CALL s T(3): vysledek zapsan do T(3)")
    check(t[0] is None and t[1] is None and t[3] is None and t[4] is None,
          "CALL s T(3): ostatni prvky pole T zustavaji nedotcene (None)")

    # --- 2) T(J) - index jako promenna (ne jen literal) ---
    src2 = """
SUBRO/MAIN2/out:D1
DIMEN,P(2)
DIMEN,I(2)
DIMEN,T(5)
DIMEN,J(1)
P(1)=Q00>0,0,0
P(2)=Q00>1,1,1
I(1)=1
J=4
CALL/MakeCut/P,I,10,20,T(J)
D1=1.0
RETSUB
END
"""
    env2 = run(src2)
    t2 = env2["T"]
    check(t2[3].x == 10.0 and t2[3].y == 20.0, "CALL s T(J), J=4: vysledek zapsan do T(4)")

    # --- 3) chyba: cilove pole neni DIMEN'ovano pred volanim ---
    src3 = """
SUBRO/MAIN3/out:D1
DIMEN,P(2)
DIMEN,I(2)
P(1)=Q00>0,0,0
P(2)=Q00>1,1,1
I(1)=1
CALL/MakeCut/P,I,10,20,T(3)
D1=1.0
RETSUB
END
"""
    try:
        run(src3)
        check(False, "T nedeklarovane pred CALL s T(3) melo vyhodit GL3RuntimeError")
    except GL3RuntimeError as e:
        check("nebylo deklarovano" in str(e), "chybejici DIMEN T pred CALL/.../T(3): jasna chyba (%s)" % e)

    # --- 4) holy identifikator (bez indexu) porad funguje jako drive ---
    src4 = """
SUBRO/MAIN4/out:D1
DIMEN,P(2)
DIMEN,I(2)
P(1)=Q00>0,0,0
P(2)=Q00>1,1,1
I(1)=1
CALL/MakeCut/P,I,50,60,TT
D1=1.0
RETSUB
END
"""
    env4 = run(src4)
    check(env4["TT"].x == 50.0 and env4["TT"].y == 60.0, "CALL s holym identifikatorem (TT) funguje beze zmeny")

    print("\nVSE OK - CALL s indexovanym cilem pro out: parametr.")


if __name__ == "__main__":
    main()
