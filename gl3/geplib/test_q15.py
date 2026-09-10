# -*- coding: utf-8 -*-
"""Test Q15 (Bod parametrem ke dvema bodum) - viz G10.md."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from geplib.q15 import make_point_by_parameter
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


def isclose(a, b, eps=1e-9):
    return abs(a - b) < eps


def main():
    q1 = Point(0.0, 0.0, 0.0)
    q2 = Point(10.0, 20.0, 30.0)

    r0 = make_point_by_parameter(q1, q2, 0.0)
    check((r0.x, r0.y, r0.z) == (0.0, 0.0, 0.0), "D=0 -> totozny s Q1")

    r1 = make_point_by_parameter(q1, q2, 1.0)
    check((r1.x, r1.y, r1.z) == (10.0, 20.0, 30.0), "D=1 -> totozny s Q2")

    r_mid = make_point_by_parameter(q1, q2, 0.5)
    check((r_mid.x, r_mid.y, r_mid.z) == (5.0, 10.0, 15.0), "D=0.5 -> stred usecky")

    r_sym = make_point_by_parameter(q1, q2, -1.0)
    check((r_sym.x, r_sym.y, r_sym.z) == (-10.0, -20.0, -30.0), "D=-1 -> bod symetricky k Q2 podle Q1")

    r_ext = make_point_by_parameter(q1, q2, 2.0)
    check((r_ext.x, r_ext.y, r_ext.z) == (20.0, 40.0, 60.0), "D=2 -> extrapolace za Q2 povolena")

    # --- pres realny GL3 zdroj ---
    src = """
SUBRO/TESTQ15/out:Q3
Q1=Q00>0.0,0.0,0.0
Q2=Q00>10.0,20.0,30.0
Q3=Q15>Q1,Q2,0.5
RETSUB
END
"""
    env = Interpreter().run(parse_program(src), {})
    qm = env["Q3"]
    check((qm.x, qm.y, qm.z) == (5.0, 10.0, 15.0), "GL3: Q15>Q1,Q2,0.5 dava stred usecky")

    print("\nVSE OK - Q15.")


if __name__ == "__main__":
    main()
