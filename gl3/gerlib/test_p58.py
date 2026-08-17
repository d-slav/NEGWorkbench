# -*- coding: utf-8 -*-
"""
test_p58.py - Testy procedury P58 (bod od bodu po retezci do
vzdalenosti, viz G10.md 'P58 - Bod od bodu po retezci do vzdalenosti',
Fortran P58.FOR).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Curve
from gerlib.p58 import point_at_distance_along_chain
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def pt_isclose(p, x, y, eps=1e-6):
    return isclose(p.x, x, eps) and isclose(p.y, y, eps)


def main():
    # --- otevreny retezec: "L" tvar (0,0)->(4,0)->(4,4)->(0,4) ---
    open_pts = [Point(0.0, 0.0), Point(4.0, 0.0), Point(4.0, 4.0), Point(0.0, 4.0)]
    open_chain = Curve(open_pts, closed=False)
    p = Point(2.0, 0.0)  # lezi na prvnim useku

    r = point_at_distance_along_chain(p, open_chain, 3.0)  # default K=1
    check(pt_isclose(r, 4.0, 1.0), "otevreny: dopredu (default K=1), presahuje uzel")

    r2 = point_at_distance_along_chain(p, open_chain, 1.0, 0)
    check(pt_isclose(r2, 1.0, 0.0), "otevreny: pozpatku (K=0), v ramci prvniho useku")

    try:
        point_at_distance_along_chain(p, open_chain, 5.0, 0)
        check(False, "otevreny: presah pocatku mel vyhodit chybu")
    except ValueError:
        check(True, "otevreny: presah pocatku (K=0) -> ValueError")

    try:
        point_at_distance_along_chain(p, open_chain, 11.0, 1)
        check(False, "otevreny: presah konce mel vyhodit chybu")
    except ValueError:
        check(True, "otevreny: presah konce (K=1) -> ValueError")

    # --- bod primo v uzlu retezce ---
    r3 = point_at_distance_along_chain(open_pts[1], open_chain, 2.0, 1)
    check(pt_isclose(r3, 4.0, 2.0), "otevreny: vychozi bod je primo uzel retezce")

    # --- uzaverny retezec: ctverec 4x4, obvod 16 ---
    closed_pts = open_pts + [Point(0.0, 0.0)]
    closed_chain = Curve(closed_pts, closed=True)

    r4 = point_at_distance_along_chain(p, closed_chain, 17.0)  # cely obvod (16) + 1
    check(pt_isclose(r4, 3.0, 0.0), "uzavreny: presah pres uzaver (wraparound), 1 lap + 1")

    r5 = point_at_distance_along_chain(p, closed_chain, 16.0 * 3 + 1.0)  # 3 laps + 1
    check(pt_isclose(r5, 3.0, 0.0), "uzavreny: vicenasobny wraparound (3 laps + 1)")

    r6 = point_at_distance_along_chain(p, closed_chain, 17.0, 0)  # pozpatku pres uzaver
    check(pt_isclose(r6, 1.0, 0.0), "uzavreny: wraparound pozpatku (K=0)")

    # --- vzdalenost 0 vraci vychozi bod ---
    r7 = point_at_distance_along_chain(p, open_chain, 0.0)
    check(pt_isclose(r7, p.x, p.y), "D=0 vraci vychozi bod")

    # --- bod mimo retezec -> chyba ---
    try:
        point_at_distance_along_chain(Point(99.0, 99.0), open_chain, 1.0)
        check(False, "bod mimo retezec mel vyhodit chybu")
    except ValueError:
        check(True, "bod mimo retezec -> ValueError")

    # --- test pres realny GL3 zdrojovy text (vc. CRE/MOVE/ENDCRE) ---
    gl3_code = """
SUBRO/TESTP58/out:PM1,out:PM2
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
P4=P00>0.0,10.0
CRE,E1
MOVE/P1
MOVE*P2*P3*P4*P1
ENDCRE
PP=P00>5.0,0.0
PM1=P58>PP,E1,3.0
PM2=P58>PP,E1,3.0,0.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(pt_isclose(env["PM1"], 8.0, 0.0), "GL3: default K=1 (ve smeru)")
    check(pt_isclose(env["PM2"], 2.0, 0.0), "GL3: K=0 (proti smeru)")

    print("\nVSE OK - P58 (gerlib.p58) je plne funkcni.")


if __name__ == "__main__":
    main()
