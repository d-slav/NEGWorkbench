# -*- coding: utf-8 -*-
"""Test: DIMEN nesmi tise prepsat jiz svazany 'in:' vstupni parametr
(typicky composite in:P(N)) na prazdne pole - objeveno pri lazeni
NPO>P na poli bodu primo z FreeCAD geometrie (viz gl3_program.py).

Overuje se i spravne SCOPOVANI (per-env, ne globalne na Interpreter) -
vnorene CALL musi mit moznost pouzit vlastni lokalni promennou se
stejnym jmenem jako vnejsi in: parametr, s vlastnim legitimnim DIMEN,
aniz by to spadlo do stejne chyby."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gerlib import Point


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # 1) NPO na poli bodu (in: composite vstup, bez DIMEN) - zakladni pripad
    src_ok = """
SUBRO/TESTNPO/in:P(1),out:K
K=NPO>P
RETSUB
END
"""
    pts = [Point(0, 0, 0), Point(1, 1, 0), Point(2, 2, 0)]
    interp = Interpreter()
    result = interp.run(parse_program(src_ok), inputs={"P": pts})
    check(result.get("K") == 3, "NPO>P na in: poli bodu vrati jeho skutecnou delku")

    # 2) DIMEN na uz svazany in: vstup - MUSI jasne selhat, ne tise prepsat
    src_bad = """
SUBRO/TESTDIMEN/in:P(1),out:K
DIMEN,P(5)
K=NPO>P
RETSUB
END
"""
    try:
        Interpreter().run(parse_program(src_bad), inputs={"P": pts})
        check(False, "DIMEN na in: vstup mel vyhodit ValueError")
    except ValueError as e:
        check("uz je vstupni parametr" in str(e), "DIMEN na in: vstup -> jasna ValueError (%s)" % e)

    # 3) scoping pres vnorene CALL - vnitrni subrutina ma VLASTNI lokalni P
    # s legitimnim DIMEN,P(3), nezavisle na vnejsim in:P
    inner_src = """
SUBRO/INNER/out:M
DIMEN,P(3)
P(1)=10
P(2)=20
P(3)=30
M=NPO>P
RETSUB
END
"""
    outer_src = """
SUBRO/OUTER/in:P(1),out:K,out:M
CALL/INNER/M
K=NPO>P
RETSUB
END
"""
    inner = parse_program(inner_src)
    outer = parse_program(outer_src)
    interp2 = Interpreter(registry={"INNER": inner, "OUTER": outer})
    pts5 = [Point(float(i), float(i), 0.0) for i in range(5)]
    r = interp2.run(outer, inputs={"P": pts5})
    check(r.get("K") == 5, "vnejsi in:P zustava nedotcene (delka 5)")
    check(r.get("M") == 3, "vnitrni CALL ma vlastni lokalni P s legitimnim DIMEN,P(3) - funguje beze zmeny")

    print("Vse OK.")


if __name__ == "__main__":
    main()
