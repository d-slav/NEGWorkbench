# -*- coding: utf-8 -*-
"""test_move_geom.py - primy test gerlib.move_geom (bez GL3 interpretru),
stejny styl jako ostatni test_*.py v gerlib/."""

import math

from .types import Point, Vector, Line, Circle
from .e01 import make_chain
from .accur import set_accuracy
from .move_geom import evaluate_move_phrase, MovePhraseError, MovePhraseNotYetImplemented


def check(cond, msg):
    assert cond, "FAIL: %s" % msg
    print("OK: %s" % msg)


def close(a, b, eps=1e-6):
    return abs(a - b) < eps


def main():
    set_accuracy(0.01)

    origin = Point(0.0, 0.0, 0.0)

    # --- *D - smer predchoziho pohybu ---
    pts, d = evaluate_move_phrase(origin, (1.0, 0.0), "ABSOL", None, [5.0])
    check(close(pts[0].x, 5.0) and close(pts[0].y, 0.0), "D: pohyb ve smeru predchoziho pohybu")

    try:
        evaluate_move_phrase(origin, None, "ABSOL", None, [5.0])
        check(False, "D bez znameho smeru musi vyhodit chybu")
    except MovePhraseError:
        print("OK: D bez znameho smeru vyhazuje MovePhraseError")

    # --- *P - absolutni bod ---
    pts, d = evaluate_move_phrase(origin, None, "ABSOL", None, [Point(3.0, 4.0, 0.0)])
    check(close(pts[0].x, 3.0) and close(pts[0].y, 4.0), "P: absolutni bod")

    # --- *V - vektor ---
    pts, d = evaluate_move_phrase(origin, None, "ABSOL", None, [Vector(2.0, -1.0, 0.0)])
    check(close(pts[0].x, 2.0) and close(pts[0].y, -1.0), "V: pohyb o vektor")

    # --- *D#A - polarni souradnice ---
    pts, d = evaluate_move_phrase(origin, None, "ABSOL", "#", [10.0, 90.0])
    check(close(pts[0].x, 0.0) and close(pts[0].y, 10.0), "D#A: absolutni polarni bod (90 stupnu)")

    pts, d = evaluate_move_phrase(Point(1.0, 1.0, 0.0), None, "INCRE", "#", [10.0, 90.0])
    check(close(pts[0].x, 1.0) and close(pts[0].y, 11.0), "D#A: prirustkovy polarni bod")

    # --- *D1:D2 ---
    pts, d = evaluate_move_phrase(Point(1.0, 1.0, 0.0), None, "ABSOL", ":", [3.0, 4.0])
    check(close(pts[0].x, 3.0) and close(pts[0].y, 4.0), "D1:D2: absolutni kartezsky bod")

    pts, d = evaluate_move_phrase(Point(1.0, 1.0, 0.0), None, "INCRE", ":", [3.0, 4.0])
    check(close(pts[0].x, 4.0) and close(pts[0].y, 5.0), "D1:D2: prirustkovy kartezsky bod")

    # --- *D:V ---
    pts, d = evaluate_move_phrase(origin, None, "ABSOL", ":", [5.0, Vector(0.0, 1.0, 0.0)])
    check(close(pts[0].x, 0.0) and close(pts[0].y, 5.0), "D:V: pohyb dane vzdalenosti ve smeru vektoru")

    # --- *L1:L2 ---
    l1 = Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0))
    l2 = Line(Point(5.0, -5.0, 0.0), Vector(0.0, 1.0, 0.0))
    pts, d = evaluate_move_phrase(origin, None, "ABSOL", ":", [l1, l2])
    check(close(pts[0].x, 5.0) and close(pts[0].y, 0.0), "L1:L2: prusecik dvou primek")

    # --- *L:0 ---
    pts, d = evaluate_move_phrase(Point(2.0, 3.0, 0.0), None, "ABSOL", ":", [l1, 0.0])
    check(close(pts[0].x, 2.0) and close(pts[0].y, 0.0), "L:0: patni bod na primce")

    # --- *C:0 ---
    c = Circle(Point(0.0, 0.0, 0.0), 5.0)
    pts, d = evaluate_move_phrase(Point(10.0, 0.0, 0.0), None, "ABSOL", ":", [c, 0.0])
    check(close(pts[0].x, 5.0) and close(pts[0].y, 0.0), "C:0: nejblizsi bod na kruznici")

    # --- *C - cela kruznice ---
    start = Point(5.0, 0.0, 0.0)
    pts, d = evaluate_move_phrase(start, None, "ABSOL", None, [c])
    check(len(pts) > 4, "C: cela kruznice ma vic nez 4 aproximacni body")
    check(close(pts[-1].x, 5.0, 0.02) and close(pts[-1].y, 0.0, 0.02), "C: cela kruznice se vraci do vychoziho bodu")

    # --- *P1,P2,K - arc kolem stredu ---
    pts, d = evaluate_move_phrase(start, None, "ABSOL", ",", [Point(0.0, 5.0, 0.0), Point(0.0, 0.0, 0.0), 0.0])
    check(close(pts[-1].x, 0.0, 0.02) and close(pts[-1].y, 5.0, 0.02), "P1,P2,K=0: ctvrtkruh ccw do (0,5)")

    # --- *P,C,K - arc podel dane kruznice ---
    pts, d = evaluate_move_phrase(start, None, "ABSOL", ",", [Point(0.0, 5.0, 0.0), c, 0.0])
    check(close(pts[-1].x, 0.0, 0.02) and close(pts[-1].y, 5.0, 0.02), "P,C,K=0: ctvrtkruh ccw podel C do (0,5)")

    # --- *E a P1,P2,E - retezcove fraze ---
    chain = make_chain([Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)])
    pts, d = evaluate_move_phrase(Point(0.0, 0.0, 0.0), None, "ABSOL", None, [chain])
    check([(p.x, p.y) for p in pts] == [(1.0, 0.0), (1.0, 1.0)], "E: cely retezec od zacatku")

    pts, d = evaluate_move_phrase(Point(1.0, 1.0, 0.0), None, "ABSOL", None, [chain])
    check([(p.x, p.y) for p in pts] == [(1.0, 0.0), (0.0, 0.0)], "E: cely retezec pozpatku od konce")

    pts, d = evaluate_move_phrase(
        Point(0.0, 0.0, 0.0), None, "ABSOL", ",",
        [Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0), chain],
    )
    check([(p.x, p.y) for p in pts] == [(1.0, 1.0)], "P1,P2,E: usek retezce (zde jen koncovy bod)")

    # --- prechodova fraze - zatim NotYetImplemented ---
    try:
        evaluate_move_phrase(origin, None, "ABSOL", ",", [l1, l2, 5.0, 0.0])
        check(False, "prechodova fraze L1,L2,D,K musi (zatim) vyhodit MovePhraseNotYetImplemented")
    except MovePhraseNotYetImplemented:
        print("OK: prechodova fraze primka-primka spravne hlasi NotYetImplemented")

    print("Vsechny testy gerlib.move_geom OK.")


if __name__ == "__main__":
    main()
