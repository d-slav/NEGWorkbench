# -*- coding: utf-8 -*-
"""
test_p66.py - Testy procedury P66 (bod na retezci souradnici, viz
G10.md 'P66 - Bod na retezci souradnici', Fortran P66.FOR).

Zamerene predevsim na SPRAVNE PORADI a SPRAVNY POCET pruseciku,
protoze puvodni Fortran ma netrivialni logiku pro deduplikaci krizeni
na sdilenych uzlech a pro "cely usek lezi na primce" pripady - viz
hlavicka gerlib/p66.py pro odvozeni.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Curve
from gerlib.p66 import point_on_chain_by_coord
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
    # --- vicenasobne krizeni v poradi (zigzag pres x=5, 3x) ---
    zigzag = Curve([
        Point(0.0, 0.0), Point(10.0, 0.0), Point(10.0, 10.0),
        Point(0.0, 10.0), Point(0.0, 20.0), Point(10.0, 20.0),
    ], closed=False)

    p1 = point_on_chain_by_coord(zigzag, 5.0, 10)  # K2=1, K1=0 (x)
    p2 = point_on_chain_by_coord(zigzag, 5.0, 20)
    p3 = point_on_chain_by_coord(zigzag, 5.0, 30)
    check(pt_isclose(p1, 5.0, 0.0), "zigzag: 1. prusecik x=5")
    check(pt_isclose(p2, 5.0, 10.0), "zigzag: 2. prusecik x=5")
    check(pt_isclose(p3, 5.0, 20.0), "zigzag: 3. prusecik x=5")
    try:
        point_on_chain_by_coord(zigzag, 5.0, 40)
        check(False, "4. prusecik nemel existovat")
    except ValueError:
        check(True, "zigzag: 4. prusecik neexistuje -> ValueError")

    # --- krizeni presne na sdilenem uzlu dvou useku - jen JEDNOU ---
    peak = Curve([Point(0.0, 0.0), Point(5.0, 5.0), Point(10.0, 0.0)], closed=False)
    pv = point_on_chain_by_coord(peak, 5.0, 10)
    check(pt_isclose(pv, 5.0, 5.0), "sdileny uzel: 1. prusecik je spicka (5,5)")
    try:
        point_on_chain_by_coord(peak, 5.0, 20)
        check(False, "sdileny uzel nesmi byt zapocitan dvakrat")
    except ValueError:
        check(True, "sdileny uzel: zapocitan jen jednou (2. neexistuje)")

    # --- cely usek lezi presne na souradnici D - chyba, ale zabira 1 poradi ---
    whole_seg = Curve([
        Point(0.0, 0.0), Point(5.0, 0.0), Point(5.0, 10.0), Point(10.0, 10.0),
    ], closed=False)
    try:
        point_on_chain_by_coord(whole_seg, 5.0, 10)
        check(False, "cely usek na primce mel vyhodit ValueError")
    except ValueError as e:
        check("cely usek" in str(e), "cely usek na primce -> ValueError (IER=568 stylem)")
    try:
        point_on_chain_by_coord(whole_seg, 5.0, 20)
        check(False, "2. prusecik nemel existovat (cely usek zabral jen 1 poradi)")
    except ValueError:
        check(True, "cely usek zabira presne jedno poradove cislo")

    # --- dva po sobe jdouci useky na primce (run) - porad jen JEDNO poradi ---
    run2 = Curve([
        Point(0.0, 0.0), Point(5.0, 0.0), Point(5.0, 5.0), Point(5.0, 10.0), Point(10.0, 10.0),
    ], closed=False)
    try:
        point_on_chain_by_coord(run2, 5.0, 10)
        check(False, "dvojity beh na primce mel vyhodit ValueError")
    except ValueError:
        check(True, "dvojity beh na primce (2 useky) -> ValueError pro K2=1")
    try:
        point_on_chain_by_coord(run2, 5.0, 20)
        check(False, "K2=2 nemel existovat (cely beh zabira jen 1 poradi)")
    except ValueError:
        check(True, "dvojity beh zabira porad jen jedno poradove cislo")

    # --- prvni bod retezce lezi presne na D ---
    starts_on_d = Curve([Point(5.0, 0.0), Point(10.0, 5.0), Point(15.0, 0.0)], closed=False)
    ps = point_on_chain_by_coord(starts_on_d, 5.0, 10)
    check(pt_isclose(ps, 5.0, 0.0), "prvni bod retezce presne na D se pocita")

    # --- posledni bod retezce lezi presne na D (konec posledniho useku) ---
    ends_on_d = Curve([Point(0.0, 0.0), Point(3.0, 3.0), Point(5.0, 0.0)], closed=False)
    pe = point_on_chain_by_coord(ends_on_d, 5.0, 10)
    check(pt_isclose(pe, 5.0, 0.0), "posledni usek konci presne na D - musi se zapocitat")

    # --- uzavreny retezec: zadny wraparound (jen jeden pruchod, presne jako original) ---
    closed_sq = Curve([
        Point(0.0, 0.0), Point(10.0, 0.0), Point(10.0, 10.0), Point(0.0, 10.0), Point(0.0, 0.0),
    ], closed=True)
    pc1 = point_on_chain_by_coord(closed_sq, 5.0, 10)
    pc2 = point_on_chain_by_coord(closed_sq, 5.0, 20)
    check(pt_isclose(pc1, 5.0, 0.0), "uzavreny retezec: 1. prusecik x=5")
    check(pt_isclose(pc2, 5.0, 10.0), "uzavreny retezec: 2. prusecik x=5 (uzaviraci usek)")
    try:
        point_on_chain_by_coord(closed_sq, 5.0, 30)
        check(False, "uzavreny retezec nema wraparound - 3. nemel existovat")
    except ValueError:
        check(True, "uzavreny retezec: zadny wraparound (K2=3 neexistuje)")

    # --- K1=1 (y-souradnice) ---
    diag = Curve([Point(0.0, 0.0), Point(10.0, 10.0)], closed=False)
    py = point_on_chain_by_coord(diag, 5.0, 11)  # K2=1, K1=1
    check(pt_isclose(py, 5.0, 5.0), "K1=1 (y-souradnice)")

    # --- neplatne KK ---
    try:
        point_on_chain_by_coord(diag, 5.0, 0)
        check(False, "K2=0 mel vyhodit ValueError")
    except ValueError:
        check(True, "K2=0 (neplatne) -> ValueError")
    try:
        point_on_chain_by_coord(diag, 5.0, 12)
        check(False, "K1=2 mel vyhodit ValueError")
    except ValueError:
        check(True, "K1=2 (neplatne) -> ValueError")

    # --- test pres realny GL3 zdrojovy text (vc. CRE/MOVE/ENDCRE) ---
    gl3_code = """
SUBRO/TESTP66/out:PM1,out:PM2
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
P4=P00>0.0,10.0
CRE,E1
MOVE/P1
MOVE*P2*P3*P4*P1
ENDCRE
PM1=P66>E1,5.0,10.0
PM2=P66>E1,5.0,20.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    check(pt_isclose(env["PM1"], 5.0, 0.0), "GL3: 1. prusecik x=5")
    check(pt_isclose(env["PM2"], 5.0, 10.0), "GL3: 2. prusecik x=5")

    print("\nVSE OK - P66 (gerlib.p66) je plne funkcni.")


if __name__ == "__main__":
    main()
