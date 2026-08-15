# -*- coding: utf-8 -*-
"""
test_p51.py - Testy procedury P51 (prusecik primky s retezcem Curve).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib import Point, Vector, Line, make_chain, line_chain_intersection, line_chain_intersections
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def _assert_close(a, b, msg, eps=1e-6):
    assert abs(a - b) < eps, "%s: %r != %r (rozdil %r)" % (msg, a, b, abs(a - b))


def _assert_pt_close(p, x, y, msg, eps=1e-6):
    _assert_close(p.x, x, msg + " (x)", eps)
    _assert_close(p.y, y, msg + " (y)", eps)


def test_basic_intersections():
    # Retezec ve tvaru obdelniku (0,0) -> (4,0) -> (4,4) -> (0,4) -> (0,0)
    pts = [Point(0, 0), Point(4, 0), Point(4, 4), Point(0, 4), Point(0, 0)]
    chain = make_chain(pts)

    # Svisla primka x = 2
    ln = Line(Point(2, 0), Vector(0, 1))

    hits = line_chain_intersections(ln, chain)
    assert len(hits) == 2, "Obdelnik protnuty svislou primkou musi mit 2 pruseciky, nalezeno: %d" % len(hits)
    _assert_pt_close(hits[0], 2.0, 0.0, "Prvni prusecik na spodni hrane")
    _assert_pt_close(hits[1], 2.0, 4.0, "Druhy prusecik na horni hrane")

    # Volani line_chain_intersection s K=1 a K=2
    p1 = line_chain_intersection(ln, chain, 1)
    p2 = line_chain_intersection(ln, chain, 2)
    _assert_pt_close(p1, 2.0, 0.0, "P51 K=1")
    _assert_pt_close(p2, 2.0, 4.0, "P51 K=2")

    print("test_basic_intersections(): OK")


def test_vertex_crossing():
    # Retezec ve tvaru V: (0, 0) -> (2, 2) -> (4, 0)
    chain = make_chain([Point(0, 0), Point(2, 2), Point(4, 0)])

    # Primka x = 2 prochazi presne vrcholem (2, 2)
    ln = Line(Point(2, 0), Vector(0, 1))
    hits = line_chain_intersections(ln, chain)
    assert len(hits) == 1, "Pruchod spolecnym vrcholem nesmi zpusobit duplicitu, nalezeno: %d" % len(hits)
    _assert_pt_close(hits[0], 2.0, 2.0, "Prusecik ve vrcholu")

    p = line_chain_intersection(ln, chain, 1)
    _assert_pt_close(p, 2.0, 2.0, "P51 K=1 ve vrcholu")

    print("test_vertex_crossing(): OK")


def test_multi_segment_order():
    # Retezec tvaru pilky: (0,0) -> (1,2) -> (2,0) -> (3,2) -> (4,0)
    chain = make_chain([Point(0, 0), Point(1, 2), Point(2, 0), Point(3, 2), Point(4, 0)])

    # Vodorovna primka y = 1 protina 4 segmenty
    ln = Line(Point(0, 1), Vector(1, 0))
    hits = line_chain_intersections(ln, chain)
    assert len(hits) == 4, "Pilka protnuta primkou y=1 musi mit 4 pruseciky, nalezeno: %d" % len(hits)
    _assert_pt_close(hits[0], 0.5, 1.0, "1. prusecik pilky")
    _assert_pt_close(hits[1], 1.5, 1.0, "2. prusecik pilky")
    _assert_pt_close(hits[2], 2.5, 1.0, "3. prusecik pilky")
    _assert_pt_close(hits[3], 3.5, 1.0, "4. prusecik pilky")

    for k in range(1, 5):
        pk = line_chain_intersection(ln, chain, k)
        _assert_pt_close(pk, k - 0.5, 1.0, "P51 K=%d" % k)

    print("test_multi_segment_order(): OK")


def test_error_handling():
    chain = make_chain([Point(0, 0), Point(2, 0), Point(2, 2)])
    ln = Line(Point(0, 5), Vector(1, 0))  # Primka y=5 mimo retezec

    # Zadne pruseciky
    hits = line_chain_intersections(ln, chain)
    assert len(hits) == 0, "Mimo retezec musi byt 0 pruseciku"

    try:
        line_chain_intersection(ln, chain, 1)
        assert False, "Melo vyhodit ValueError pro neexistujici prusecik"
    except ValueError as e:
        assert "prusecik" in str(e).lower()

    # K < 1
    try:
        line_chain_intersection(ln, chain, 0)
        assert False, "Melo vyhodit ValueError pro K=0"
    except ValueError as e:
        assert "k musi byt >= 1" in str(e).lower()

    # Nulovy smer primky
    try:
        ln_zero = Line(Point(0, 0), Vector(0, 0))
        line_chain_intersections(ln_zero, chain)
        assert False, "Melo vyhodit ValueError pro nulovy smer primky"
    except ValueError as e:
        assert "nulovy" in str(e).lower()

    print("test_error_handling(): OK")


def test_interpreter_p51():
    gl3_code = """
SUBRO/TESTP51/out:PT1,out:PT2
DIMEN,P(3)
DATA,P,0.0,0.0, 2.0,2.0, 4.0,0.0
E1=E01>P(1),3
L1=L02>P0,VY
PT1=P51>L1,E1,1
RETSUB
END
"""
    # L1 je osa Y posunuta pres x=2 pomoci L02:
    # L02>bod, smer -> vytvori primku
    gl3_code2 = """
SUBRO/TESTP51/out:PT1,out:PT2
DIMEN,P(4)
DATA,P,4
0.0,0.0
4.0,0.0
4.0,4.0
0.0,4.0
E1=E01>P(1),4
P_LN=P00>2.0,0.0
L1=L02>P_LN,VY
PT1=P51>L1,E1,1
PT2=P51>L1,E1,2
RETSUB
END
"""
    program = parse_program(gl3_code2)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    assert "PT1" in env and "PT2" in env
    pt1 = env["PT1"]
    pt2 = env["PT2"]
    _assert_pt_close(pt1, 2.0, 0.0, "GL3 PT1")
    _assert_pt_close(pt2, 2.0, 4.0, "GL3 PT2")

    print("test_interpreter_p51(): OK")


def main():
    test_basic_intersections()
    test_vertex_crossing()
    test_multi_segment_order()
    test_error_handling()
    test_interpreter_p51()
    print("\nVSE OK - P51 (gerlib.p51) je plne funkcni.")


if __name__ == "__main__":
    main()
