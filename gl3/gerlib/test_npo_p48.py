# -*- coding: utf-8 -*-
"""Test NPO (pocet uzlovych bodu) a P48 (K-ty uzlovy bod retezce/krivky).

Zdroj: P48.FOR + P48E.FOR + P48S.FOR (dodano uzivatelem) - viz p48.py
pro vysvetleni, proc se puvodni zaznamova/souborova logika nahrazuje
funkcnim ekvivalentem nad Curve.points/Spline.points."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Curve, Spline
from gerlib.npo import point_count
from gerlib.p48 import chain_node, spline_node, curve_node


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def make_test_chain(n=5):
    pts = [Point(float(i), float(i) * 2, 0.0) for i in range(n)]
    # E01 konvence: posledni bod dostane index N-1 a is_end=True
    indices = [i + 1 for i in range(n - 1)] + [n - 1]
    is_end = [False] * (n - 1) + [True]
    return Curve(pts, closed=False, indices=indices, is_end=is_end)


def make_test_spline(n=4):
    pts = [Point(float(i), float(i) * i, 0.0) for i in range(n)]
    tangents = [Point(1.0, 0.0, 0.0) for _ in range(n)]
    return Spline(pts, tangents)


def main():
    chain = make_test_chain(5)
    spline = make_test_spline(4)

    # NPO
    check(point_count(chain) == 5, "NPO: pocet bodu retezce")
    check(point_count(spline) == 4, "NPO: pocet bodu krivky")

    # NPO - rozsireni: obycejne pole bodu (napr. composite in:P(N) vstup
    # primo z FreeCAD geometrie - viz gl3_program.py)
    check(point_count([Point(0, 0, 0), Point(1, 1, 0), Point(2, 4, 0)]) == 3,
          "NPO: pocet prvku obycejneho pole bodu (nase rozsireni)")
    check(point_count([]) == 0, "NPO: prazdne pole -> 0")

    # P48 - chain, normalni bod (K < N)
    p, idx, is_end = chain_node(chain, 2)
    check(p.x == chain.points[1].x and p.y == chain.points[1].y, "P48E: souradnice K=2 souhlasi")
    check(idx == 2 and is_end is False, "P48E: K=2 (< N) -> index=K, is_end=False")

    # P48 - chain, posledni bod (K == N != 1)
    p_last, idx_last, is_end_last = chain_node(chain, 5)
    check(p_last.x == chain.points[4].x and p_last.y == chain.points[4].y,
          "P48E: souradnice posledniho bodu souhlasi")
    check(idx_last == 4 and is_end_last is True,
          "P48E: K=N -> index=N-1, is_end=True (jako E01/Curve.indices)")

    # P48 - spline, analogicky
    ps, idxs, ends = spline_node(spline, 4)
    check(ps.x == spline.points[3].x and idxs == 3 and ends is True,
          "P48S: K=N -> index=N-1, is_end=True")
    ps2, idxs2, ends2 = spline_node(spline, 1)
    check(ps2.x == spline.points[0].x and idxs2 == 1 and ends2 is False,
          "P48S: K=1 (< N) -> index=1, is_end=False")

    # curve_node - vraci jen Point, dispatch podle typu (Curve vs Spline)
    only_point = curve_node(chain, 3)
    check(isinstance(only_point, Point) and only_point.x == chain.points[2].x,
          "P48: curve_node na Curve vrati spravny Point")
    only_point_s = curve_node(spline, 2)
    check(isinstance(only_point_s, Point) and only_point_s.x == spline.points[1].x,
          "P48: curve_node na Spline vrati spravny Point")

    # chybove stavy - K mimo rozsah
    try:
        chain_node(chain, 0)
        check(False, "P48E: K=0 melo vyhodit ValueError (256)")
    except ValueError:
        check(True, "P48E: K=0 -> ValueError (256)")

    try:
        chain_node(chain, 6)
        check(False, "P48E: K=N+1 melo vyhodit ValueError (256)")
    except ValueError:
        check(True, "P48E: K=N+1 -> ValueError (256)")

    # okrajovy pripad N=1 (podle originalu K==N ale N==1 se NEPOVAZUJE
    # za "posledni bod v jinem segmentu", protoze zadny segment neni)
    single = make_test_chain(1) if False else Curve([Point(1.0, 1.0, 0.0)], indices=[1], is_end=[False])
    p_single, idx_single, end_single = chain_node(single, 1)
    check(idx_single == 1 and end_single is False, "P48E: N=1 -> K==N se NEobrati na N-1 (zadny predchozi segment)")

    # curve_node na necem jinem nez Curve/Spline -> TypeError
    try:
        curve_node("not a curve", 1)
        check(False, "P48: spatny typ mel vyhodit TypeError")
    except TypeError:
        check(True, "P48: spatny typ objektu -> TypeError")

    # K jako FLOAT (realny GL3 interpret vzdy predava cisla jako float,
    # i kdyz "cele" - napr. 2.0 - byl to skutecny latentni bug: primy list
    # index list[k-1] s float k spadl na "list indices must be integers")
    p_float, idx_float, end_float = chain_node(chain, 2.0)
    check(p_float.x == chain.points[1].x and p_float.y == chain.points[1].y,
          "P48E: K jako float (2.0) funguje stejne jako int 2")
    p_float_last, idx_float_last, end_float_last = chain_node(chain, 5.0)
    check(end_float_last is True, "P48E: K jako float na poslednim bode take funguje")

    print("Vse OK.")


if __name__ == "__main__":
    main()
