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

# Stejne jako MAKECUT, ale out: parametr je deklarovan S DIM=1 (napr.
# "out:T(1)") - Fortranova konvence, kdy i jedina hodnota jde v poli -
# tenhle tvar hlavicky drive zpusoboval, ze se hodnota pri zapisu zpet
# (bare identifikator I indexovany cil) OBALILA do jednoprvkoveho listu
# misto same hodnoty (nahlaseno uzivatelem, viz test_dim1_*).
MAKECUT_DIM1 = """
SUBRO/MakeCutD1/in:P(2),in:II,in:DposX,in:DoffY,out:T(1)
T(1)=Q00>DposX,DoffY,0
RETSUB
END
"""

# Skutecny multi-element out: pole (dim=2) - pro kontrolu, ze se
# unwrap-na-1-prvek NEUPLATNI a cely pole zustane bez zmeny (bare
# identifikator na CALL cili ma dostat cele pole, jako drive).
MAKETWO = """
SUBRO/MakeTwo/out:PO(2)
PO(1)=Q00>1,1,1
PO(2)=Q00>2,2,2
RETSUB
END
"""


def run(main_src, registry=None):
    main_def = parse_program(main_src)
    if registry is None:
        registry = {"MakeCut": parse_program(MAKECUT)}
    return Interpreter(registry=registry).run(main_def, {})


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

    # --- 5) out: parametr deklarovany S DIM=1 (napr. "out:T(1)") -
    #     zapis do indexovaneho cile NESMI hodnotu obalit do
    #     jednoprvkoveho listu (drivejsi bug, nahlaseno uzivatelem) ---
    dim1_registry = {"MakeCutD1": parse_program(MAKECUT_DIM1)}
    src5 = """
SUBRO/MAIN5/out:D1
DIMEN,P(2)
DIMEN,I(2)
DIMEN,T(5)
P(1)=Q00>0,0,0
P(2)=Q00>1,1,1
I(1)=1
CALL/MakeCutD1/P,I,230,100,T(3)
D1=1.0
RETSUB
END
"""
    env5 = run(src5, dim1_registry)
    t5 = env5["T"][2]
    check(t5.x == 230.0 and t5.y == 100.0, "out:T(1) + indexovany cil T(3): hodnota NENI obalena v listu")

    # --- 6) totez, ale s holym identifikatorem (out:T(1) je preexistujici
    #     bug, netykal se jen indexovaneho cile - overit i tuhle cestu) ---
    src6 = """
SUBRO/MAIN6/out:D1
DIMEN,P(2)
DIMEN,I(2)
P(1)=Q00>0,0,0
P(2)=Q00>1,1,1
I(1)=1
CALL/MakeCutD1/P,I,230,100,TT
D1=1.0
RETSUB
END
"""
    env6 = run(src6, dim1_registry)
    check(env6["TT"].x == 230.0 and env6["TT"].y == 100.0, "out:T(1) + holy identifikator TT: hodnota NENI obalena v listu")

    # --- 7) skutecny multi-element out: pole (dim=2) - unwrap se NESMI
    #     uplatnit, bare identifikator ma dostat CELE pole ---
    two_registry = {"MakeTwo": parse_program(MAKETWO)}
    src7 = """
SUBRO/MAIN7/out:D1
CALL/MakeTwo/PP
D1=1.0
RETSUB
END
"""
    env7 = run(src7, two_registry)
    pp = env7["PP"]
    check(isinstance(pp, list) and len(pp) == 2, "out: pole s dim=2 zustava cele pole (zadny unwrap)")
    check(pp[0].x == 1.0 and pp[1].x == 2.0, "out: pole s dim=2 ma spravne prvky")

    print("\nVSE OK - CALL s indexovanym cilem pro out: parametr.")


if __name__ == "__main__":
    main()
