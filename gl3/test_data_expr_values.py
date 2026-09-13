# -*- coding: utf-8 -*-
"""
test_data_expr_values.py - DATA prikaz s VYRAZY jako hodnotami (ne jen
holymi konstantami) - zadani uzivatele:

    DATA,Q1,2
    DX(1), 0, 65
    DX(2), 0, 19

Kdyz je 'count' (2 v priklade vyse) doslovny literal primo v kodu (ne
promenna/vyraz) A cil ma znamy pevny pocet slozek na objekt (viz
DATA_CONSTANTS_PER_OBJECT v gl3_lang.py), parser uz PRI PARSOVANI zna
presny pocet ocekavanych hodnot (count * pocet-na-objekt) a hodnoty
smi byt libovolne VYRAZY (ne uz jen cisla/retezcove literaly), sbirane
pres libovolny pocet radku, oddelene jen carkou.

Vyraz na miste POCTU (count) prikazu DATA zamerne NENI podporovan
(zadani uzivatele - "Vyraz na miste poctu... delat ted nebudeme") -
pro tenhle pripad zustava puvodni chovani (jen holé konstanty).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter, GL3RuntimeError


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


def run(src):
    return Interpreter().run(parse_program(src), {})


def main():
    # --- 1) presne zadani uzivatele: Q(3D bod, 3 slozky na objekt),
    #     hodnoty jsou vyrazy (DX(1)/DX(2)) i cisla, po radcich ---
    src1 = """
SUBRO/TEST1/out:D1
DIMEN,DX(2)
DIMEN,Q1(2)
DX(1)=100.0
DX(2)=200.0
DATA,Q1,2
DX(1), 0, 65
DX(2), 0, 19
D1=1.0
RETSUB
END
"""
    env1 = run(src1)
    q1 = env1["Q1"]
    check(q1[0].x == 100.0 and q1[0].y == 0.0 and q1[0].z == 65.0, "1. objekt: DX(1),0,65")
    check(q1[1].x == 200.0 and q1[1].y == 0.0 and q1[1].z == 19.0, "2. objekt: DX(2),0,19")

    # --- 2) vyraz smi byt i aritmeticky (ne jen odkaz na promennou) ---
    src2 = """
SUBRO/TEST2/out:D1
DIMEN,K(1)
DIMEN,Q1(1)
K=10
DATA,Q1,1
K+5, K*2, 0
D1=1.0
RETSUB
END
"""
    env2 = run(src2)
    q2 = env2["Q1"][0]
    check(q2.x == 15.0 and q2.y == 20.0 and q2.z == 0.0, "aritmeticky vyraz jako hodnota (K+5, K*2)")

    # --- 3) vsechny hodnoty na jednom radku (jeden objekt) - beze zmeny ---
    src3 = """
SUBRO/TEST3/out:D1
DIMEN,DX(1)
DIMEN,Q1(1)
DX(1)=7.0
DATA,Q1,1
DX(1), 1.0, 2.0
D1=1.0
RETSUB
END
"""
    env3 = run(src3)
    q3 = env3["Q1"][0]
    check(q3.x == 7.0 and q3.y == 1.0 and q3.z == 2.0, "vsechny hodnoty jednoho objektu na jednom radku")

    # --- 4) puvodni styl (jen holé konstanty) funguje beze zmeny ---
    src4 = """
SUBRO/TEST4/out:D1
DIMEN,Q1(2)
DATA,Q1,2
1, 2, 3
4, 5, 6
D1=1.0
RETSUB
END
"""
    env4 = run(src4)
    q4 = env4["Q1"]
    check((q4[0].x, q4[0].y, q4[0].z) == (1.0, 2.0, 3.0), "puvodni styl (holé konstanty) - 1. objekt")
    check((q4[1].x, q4[1].y, q4[1].z) == (4.0, 5.0, 6.0), "puvodni styl (holé konstanty) - 2. objekt")

    # --- 5) count je PROMENNA (ne literal) - zustava puvodni chovani,
    #     jen holé konstanty (vyraz jako hodnota v tomhle pripade NENI
    #     podporovan - zadani uzivatele) ---
    src5 = """
SUBRO/TEST5/out:D1
DIMEN,K(1)
DIMEN,Q1(1)
K=1
DATA,Q1,K
1, 2, 3
D1=1.0
RETSUB
END
"""
    env5 = run(src5)
    q5 = env5["Q1"][0]
    check((q5.x, q5.y, q5.z) == (1.0, 2.0, 3.0), "count jako promenna - stary rezim (holé konstanty) funguje")

    # --- 6) spatny pocet hodnot (skutecny autoruv omyl) porad hlasi
    #     spravnou runtime chybu (GL3RuntimeError), NE syntax chybu -
    #     parser se nesmi 'natahnout' do NASLEDUJICIHO prikazu ---
    src6 = """
SUBRO/TEST6/out:K
DIMEN,P(2)
DATA,P,2
1.0,2.0,3.0
K=1
RETSUB
END
"""
    try:
        run(src6)
        check(False, "spatny pocet hodnot mel vyhodit GL3RuntimeError")
    except GL3RuntimeError as e:
        check("ocekavano" in str(e), "spatny pocet hodnot -> GL3RuntimeError, ne syntax chyba (%s)" % e)

    print("\nVSE OK - DATA s vyrazy jako hodnotami.")


if __name__ == "__main__":
    main()
