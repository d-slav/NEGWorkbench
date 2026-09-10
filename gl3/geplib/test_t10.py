# -*- coding: utf-8 -*-
"""
test_t10.py - Testy operace T10 (uzavrena prostorova krivka mnozinou
K bodu, sečnova parametrizace - viz G10.md 'T10 - Uzavrena krivka
prolozena mnozinou K bodu'; prostorova obdoba S10).

T10 je tenky wrapper nad gerlib.s10.make_spline (viz geplib/t10.py),
takze testy hlavne overuji: (1) spravnou provenience (opcode='T10'),
(2) ze funguje i s NENULOVOU Z-slozkou (3D, na rozdil od S10, kde je Z
v testovych datech typicky 0), (3) sdilene chovani se S10 (min. K=4,
max. K<=300, P(1)==P(K) povinne), (4) test pres realny GL3 zdrojovy
text vc. DIMEN pole Q.
"""
import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from geplib.t10 import make_spatial_spline
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-9):
    return abs(a - b) < eps


def _tilted_square(side=10.0, angle_deg=30.0):
    """Rovinny ctverec (0,0)-(side,0)-(side,side)-(0,side), naklonen
    OTOCENIM (ne zkosenim!) kolem osy X o 'angle_deg' - delky stran i
    pravé uhly zustavaji presne zachovany, takze si ctverec podrzi
    plnou 4-fold rotacni symetrii i v 3D (na rozdil od naivniho
    'kazdy roh jina Z', ktere by z nej udelalo kosoctverec s jen
    2-fold symetrii - viz git historie tohoto testu, prvni pokus na
    tohle nedopatrenim narazil)."""
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))

    def tilt(x, y):
        return Point(x, y * c, y * s)

    return [tilt(0, 0), tilt(side, 0), tilt(side, side), tilt(0, side), tilt(0, 0)]


def main():
    # --- zakladni uzavrena 3D krivka (nenulova Z), skutecne rotacne
    #     symetricky ctverec nakloneny v prostoru - viz _tilted_square() ---
    pts = _tilted_square()
    sp = make_spatial_spline(pts, 5)
    check(sp.opcode == "T10", "provenience: opcode == 'T10'")
    check(sp.parametrization == "chordal", "provenience: parametrizace 'chordal' (stejna jako S10/T01/S01)")
    check(sp.closed is True, "T10 vytvari uzavrenou krivku (closed=True)")
    check(len(sp.points) == 5, "krivka ma 5 uzlovych bodu (4 unikatni + uzaviraci)")
    check(isclose(sp.points[2].z, 5.0), "Z-slozka uzlu se prenasi beze zmeny (skutecne 3D)")
    mags = [round((t.x ** 2 + t.y ** 2 + t.z ** 2) ** 0.5, 6) for t in sp.tangents[:-1]]
    check(len(set(mags)) == 1, "prostorovy 'ctverec' (vsechny 4 strany stejne dlouhe) - tecny stejne velike")

    # --- min. K=4 (sdileno s S10) ---
    try:
        make_spatial_spline([Point(0, 0, 0), Point(1, 0, 0), Point(0, 0, 0)], 3)
        check(False, "K=3 melo vyhodit ValueError (min. 4 pro uzavrenou krivku)")
    except ValueError as e:
        check("T10" in str(e) and "4" in str(e), "K=3 -> ValueError se spravnym oznacenim opcode (T10)")

    # --- max. K<=300 (sdileno s S10/S01/T01) ---
    try:
        make_spatial_spline([Point(float(i), 0.0, 0.0) for i in range(301)] + [Point(0.0, 0.0, 0.0)], 301)
        check(False, "K=301 melo vyhodit ValueError (K<=300)")
    except ValueError as e:
        check("T10" in str(e) and "300" in str(e), "K>300 -> ValueError se spravnym oznacenim opcode (T10)")

    # --- P(1) musi byt totozny s P(K) ---
    try:
        make_spatial_spline([Point(0, 0, 0), Point(1, 0, 0), Point(1, 1, 0), Point(0, 1, 0)], 4)
        check(False, "nezavreny vstup mel vyhodit ValueError")
    except ValueError as e:
        check("totozne" in str(e), "nezavreny vstup (Q(1) != Q(K)) odmitnut")

    # --- test pres realny GL3 zdrojovy text (vc. DIMEN pole Q) ---
    c = round(math.cos(math.radians(30)), 10)
    s = round(math.sin(math.radians(30)), 10)
    gl3_code = """
SUBRO/TESTT10/out:TM1
DIMEN,Q(5)
Q(1)=Q00>0.0,0.0,0.0
Q(2)=Q00>10.0,0.0,0.0
Q(3)=Q00>10.0,{yc},{ys}
Q(4)=Q00>0.0,{yc},{ys}
Q(5)=Q00>0.0,0.0,0.0
TM1=T10>Q(1),5.0
RETSUB
END
""".format(yc=10 * c, ys=10 * s)
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})

    tm1 = env["TM1"]
    check(tm1.opcode == "T10", "GL3: TM1 opcode == 'T10'")
    check(tm1.closed is True, "GL3: TM1 je uzavrena (closed=True)")
    check(
        [(round(p.x, 6), round(p.y, 6), round(p.z, 6)) for p in tm1.points]
        == [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, round(10 * c, 6), round(10 * s, 6)),
            (0.0, round(10 * c, 6), round(10 * s, 6)), (0.0, 0.0, 0.0)],
        "GL3: TM1 uzlove body odpovidaji poli Q",
    )

    print("\nVSE OK - T10 (geplib.t10) je plne funkcni.")


if __name__ == "__main__":
    main()
