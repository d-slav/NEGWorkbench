# -*- coding: utf-8 -*-
"""Test Q02 (Bod zmenou K-te souradnice bodu) - viz G10.md."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from geplib.q02 import make_point_by_component
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


def main():
    q = Point(1.0, 2.0, 3.0)

    r1 = make_point_by_component(q, 99.0, 1)
    check((r1.x, r1.y, r1.z) == (99.0, 2.0, 3.0), "K=1 meni jen x")

    r2 = make_point_by_component(q, 99.0, 2)
    check((r2.x, r2.y, r2.z) == (1.0, 99.0, 3.0), "K=2 meni jen y")

    r3 = make_point_by_component(q, 99.0, 3)
    check((r3.x, r3.y, r3.z) == (1.0, 2.0, 99.0), "K=3 meni jen z")

    try:
        make_point_by_component(q, 99.0, 4)
        check(False, "K=4 melo vyhodit ValueError")
    except ValueError as e:
        check("Q02" in str(e), "K=4 odmitnuto (%s)" % e)

    # --- pres realny GL3 zdroj ---
    src = """
SUBRO/TESTQ02/out:Q2
Q1=Q00>1.0,2.0,3.0
Q2=Q02>Q1,50.0,2
RETSUB
END
"""
    env = Interpreter().run(parse_program(src), {})
    qm = env["Q2"]
    check((qm.x, qm.y, qm.z) == (1.0, 50.0, 3.0), "GL3: Q02>Q1,50.0,2 opravi jen y")

    print("\nVSE OK - Q02.")


if __name__ == "__main__":
    main()
