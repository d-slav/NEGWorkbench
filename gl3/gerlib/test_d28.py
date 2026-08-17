# -*- coding: utf-8 -*-
"""
test_d28.py - Testy procedury D28 (delka retezce; delka retezce v
intervalu, viz G10.md 'D28 - Delka retezce; delka retezce v
intervalu', Fortran D28.FOR).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Curve
from gerlib.d28 import length_of_chain
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def main():
    # --- otevreny retezec: "L" tvar (0,0)->(4,0)->(4,4)->(0,4), delka 12 ---
    open_pts = [Point(0.0, 0.0), Point(4.0, 0.0), Point(4.0, 4.0), Point(0.0, 4.0)]
    open_chain = Curve(open_pts, closed=False)

    check(isclose(length_of_chain(open_chain), 12.0), "otevreny retezec: cela delka")

    p1 = Point(2.0, 0.0)  # stred prvniho useku
    p2 = Point(4.0, 2.0)  # stred druheho useku
    check(isclose(length_of_chain(open_chain, p1=p1), 10.0), "otevreny: jen P1 -> od P1 do konce")
    check(isclose(length_of_chain(open_chain, p2=p2), 6.0), "otevreny: jen P2 -> od zacatku do P2")
    check(isclose(length_of_chain(open_chain, p1=p1, p2=p2), 4.0), "otevreny: P1->P2 (spravne poradi)")
    check(isclose(length_of_chain(open_chain, p1=p2, p2=p1), 4.0),
          "otevreny: P2->P1 (obracene poradi) - na poradi NEZALEZI")

    # --- uzavreny retezec: ctverec 4x4, obvod 16 ---
    closed_pts = open_pts + [Point(0.0, 0.0)]  # posledni bod = prvni
    closed_chain = Curve(closed_pts, closed=True)

    check(isclose(length_of_chain(closed_chain), 16.0), "uzavreny retezec: cela delka (obvod)")

    q1 = Point(2.0, 0.0)  # pozice 2
    q2 = Point(4.0, 2.0)  # pozice 6
    check(isclose(length_of_chain(closed_chain, p1=q1, p2=q2), 4.0),
          "uzavreny: P1 PRED P2 -> primo po retezci")
    check(isclose(length_of_chain(closed_chain, p1=q2, p2=q1), 12.0),
          "uzavreny: P1 ZA P2 -> pres konec/pocatek (wraparound), 16-4=12")

    # --- chybejici bod na retezci -> chyba ---
    try:
        length_of_chain(open_chain, p1=Point(99.0, 99.0))
        check(False, "bod mimo retezec mel vyhodit ValueError")
    except ValueError:
        check(True, "bod mimo retezec -> ValueError")

    # --- test pres realny GL3 zdrojovy text (vc. CRE/MOVE/ENDCRE) ---
    gl3_code = """
SUBRO/TESTD28/out:DM1,out:DM2,out:DM3
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
P4=P00>0.0,10.0
CRE,E1
MOVE/P1
MOVE*P2*P3*P4*P1
ENDCRE
DM1=D28>E1
PM=P00>5.0,0.0
DM2=D28>E1,PM
DM3=D28>E1,PM,P3
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(isclose(env["DM1"], 40.0), "GL3: cely obvod ctverce 10x10 = 40")
    check(isclose(env["DM2"], 35.0), "GL3: od (5,0) do konce = 35")
    check(isclose(env["DM3"], 15.0), "GL3: od (5,0) do (10,10) = 15")

    # --- nove: vynechany P1 uprostred seznamu argumentu (D28>E1,,PM) ---
    gl3_code_omit = """
SUBRO/TESTD28OMIT/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
P4=P00>0.0,10.0
CRE,E1
MOVE/P1
MOVE*P2*P3*P4*P1
ENDCRE
PM=P00>5.0,0.0
DM=D28>E1,,PM
RETSUB
END
"""
    program_omit = parse_program(gl3_code_omit)
    interpreter_omit = Interpreter()
    env_omit = interpreter_omit.run(program_omit, {})
    check(isclose(env_omit["DM"], 5.0),
          "GL3: D28>E1,,PM (P1 vynechan uprostred) - od zacatku do (5,0) = 5")

    print("\nVSE OK - D28 (gerlib.d28) je plne funkcni.")


if __name__ == "__main__":
    main()
