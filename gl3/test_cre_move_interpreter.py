# -*- coding: utf-8 -*-
"""
test_cre_move_interpreter.py - overuje CRE/MOVE/ENDCRE (vytvareni
retezce, viz G10.md 'VYTVARENI RETEZCU POMOCI KRESLICICH PRIKAZU' a
G17.md/G18.md pro fraze prikazu MOVE) na urovni skutecneho GL3
zdrojoveho textu (parse_program + Interpreter.run()), stejny styl jako
test_dcoos3_tra23_interpreter.py.
"""
import math

from gl3_lang import parse_program
from gl3_interpreter import Interpreter, GL3RuntimeError
from gl3_ops import NotYetImplemented
from gerlib.types import Curve


def _assert_close(a, b, msg, eps=1e-6):
    assert abs(a - b) < eps, "%s: %r != %r" % (msg, a, b)


def main():
    # --- 1) obdelnik pomoci bodovych frazi (*P), retezec neni uzavreny ---
    src_rect = """
SUBRO/TRECT/out:E1
P1=P00>0,0
P2=P00>10,0
P3=P00>10,10
P4=P00>0,10
CRE,E1
MOVE/P1
MOVE*P2*P3*P4
ENDCRE
RETSUB
END
"""
    subdef = parse_program(src_rect)
    interp = Interpreter()
    env = interp.run(subdef, {})
    e1 = env["E1"]
    assert isinstance(e1, Curve)
    pts = [(round(p.x, 6), round(p.y, 6)) for p in e1.points]
    assert pts == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)], pts
    assert e1.closed is False
    print("CRE/MOVE/ENDCRE (obdelnik, otevreny retezec): OK - %r" % (pts,))

    # --- 2) ctverec s poslednim bodem = prvni bod -> retezec se uzavre ---
    src_closed = """
SUBRO/TCLOSED/out:E1
P1=P00>0,0
P2=P00>5,0
P3=P00>5,5
P4=P00>0,5
CRE,E1
MOVE/P1
MOVE*P2*P3*P4*P1
ENDCRE
RETSUB
END
"""
    subdef2 = parse_program(src_closed)
    interp2 = Interpreter()
    env2 = interp2.run(subdef2, {})
    e2 = env2["E1"]
    assert e2.closed is True, "retezec vracejici se do vychoziho bodu musi byt closed"
    print("CRE/MOVE/ENDCRE (ctverec, uzavreny retezec): OK - closed=%r" % (e2.closed,))

    # --- 3) obloukova fraze *C (cela kruznice) uvnitr CRE bloku ---
    src_circle = """
SUBRO/TCIRCLE/out:E1
Q1=P00>5,0
CC=C00>0,0,5
ACCUR,0.02
CRE,E1
MOVE/Q1
MOVE*CC
ENDCRE
RETSUB
END
"""
    subdef3 = parse_program(src_circle)
    interp3 = Interpreter()
    env3 = interp3.run(subdef3, {})
    e3 = env3["E1"]
    assert len(e3.points) > 8, "aproximace kruznice by mela mit vic nez 8 bodu"
    assert e3.closed is True
    for p in e3.points:
        r = math.hypot(p.x, p.y)
        _assert_close(r, 5.0, "bod aproximace lezi na kruznici o polomeru 5", eps=0.05)
    print("CRE/MOVE/ENDCRE (fraze *C - cela kruznice): OK - %d bodu, closed=%r"
          % (len(e3.points), e3.closed))

    # --- 4) D#A (polarni) + INCRE rezim ---
    src_polar = """
SUBRO/TPOLAR/out:E1
Z=P00>0,0
CRE,E1
MOVE/Z
MOVE*(10)#(0)
INCRE
MOVE*(5)#(90)
ABSOL
ENDCRE
RETSUB
END
"""
    subdef4 = parse_program(src_polar)
    interp4 = Interpreter()
    env4 = interp4.run(subdef4, {})
    e4 = env4["E1"]
    pts4 = [(round(p.x, 6), round(p.y, 6)) for p in e4.points]
    assert pts4 == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)], pts4
    print("CRE/MOVE/ENDCRE (D#A, ABSOL/INCRE): OK - %r" % (pts4,))

    # --- 5) MOVE mimo CRE...ENDCRE musi selhat srozumitelnou chybou ---
    src_bad = """
SUBRO/TBAD/out:E1
Z=P00>0,0
MOVE/Z
RETSUB
END
"""
    subdef5 = parse_program(src_bad)
    interp5 = Interpreter()
    try:
        interp5.run(subdef5, {})
        assert False, "MOVE mimo CRE...ENDCRE musi vyhodit chybu"
    except GL3RuntimeError:
        print("MOVE mimo CRE...ENDCRE: OK - spravne vyhozena GL3RuntimeError")

    # --- 6) prechodova fraze uvnitr MOVE -> NotYetImplemented ---
    from gerlib import Point as _Point, Vector as _Vector, Line as _Line

    src_transition = """
SUBRO/TTRANS/in:L1,in:L2,out:E1
Z=P00>0,0
CRE,E1
MOVE/Z
MOVE*L1,L2,(1),(0)
ENDCRE
RETSUB
END
"""
    subdef6 = parse_program(src_transition)
    interp6 = Interpreter()
    l1 = _Line(_Point(0.0, 0.0, 0.0), _Vector(1.0, 0.0, 0.0))
    l2 = _Line(_Point(5.0, -5.0, 0.0), _Vector(0.0, 1.0, 0.0))
    try:
        interp6.run(subdef6, {"L1": l1, "L2": l2})
        assert False, "prechodova fraze musi (zatim) vyhodit NotYetImplemented"
    except NotYetImplemented:
        print("MOVE s prechodovou frazi: OK - spravne vyhozena NotYetImplemented")

    print("Vsechny testy CRE/MOVE/ENDCRE (interpreter) OK.")


if __name__ == "__main__":
    main()
