# -*- coding: utf-8 -*-
"""Test L45 (tecna primka k retezci, rovnobezna s vektorem) a oprava
P85 (min. pocet bodu 2 mist 3 - overeno proti skutecnemu P85.FOR).

Zdroj: L45.FOR + P85.FOR (dodano uzivatelem). Jadro P85 (e01.
tangent_point_on_chain) uz existovalo z drivejska - overeno tady
rucne radek po radku proti dodanemu zdroji, jen upraven prah min.
poctu bodu."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Curve
from gerlib.e01 import tangent_point_on_chain
from gerlib.l45 import tangent_line_parallel


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- P85 oprava: retezec o 2 bodech, hrana presne rovnobezna s V ---
    two_pt = Curve([Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)], indices=[1, 1], is_end=[False, True])
    x, y, idx = tangent_point_on_chain((1.0, 0.0), two_pt, 1)
    check(math.isclose(x, 10.0) and math.isclose(y, 0.0), "P85: 2-bodovy retezec, rovnobezna hrana -> nalezen bod")

    # --- P85 na "hvezdickovem" retezci (jasny "rohovy" tecny bod) ---
    # ctverec (0,0)-(4,0)-(4,4)-(0,4)-(0,0)(uzavreny), hledame dotykovy
    # bod ve smeru (1,0) - ma to byt vrchol/hrana kolmá na smer... pro
    # smer (1,0) (vodorovny) je "tecny" bod tam, kde se ctverec "otaci"
    # kolem svisle primky - coz jsou LEVA i PRAVA hrana (obe svisle,
    # tedy KOLME na V, ne rovnobezne - takze rohovy test)
    square = Curve(
        [Point(0.0, 0.0, 0.0), Point(4.0, 0.0, 0.0), Point(4.0, 4.0, 0.0),
         Point(0.0, 4.0, 0.0), Point(0.0, 0.0, 0.0)],
        indices=[1, 2, 3, 4, 4], is_end=[False, False, False, False, True],
    )
    xs, ys, idxs = tangent_point_on_chain((1.0, 0.0), square, 1)
    check((xs, ys) in [(4.0, 0.0), (4.0, 4.0)], "P85: ctverec, smer (1,0) -> tecny bod na prave strane")

    # --- L45: primka tecna k retezci, smer KANONICKY orientovany (ne mistni) ---
    line1 = tangent_line_parallel(Vector(-1.0, 0.0, 0.0), two_pt, 1)
    check(math.isclose(line1.origin.x, 10.0) and math.isclose(line1.origin.y, 0.0),
          "L45: pocatek vysledne primky je dotykovy bod")
    # smer musi byt KANONICKA orientace vstupniho vektoru (-1,0) -> V221 flip -> (1,0)
    check(math.isclose(line1.direction.x, 1.0) and math.isclose(line1.direction.y, 0.0),
          "L45: smer vysledne primky je kanonicky orientovany vstupni vektor (V221), ne mistni smer retezce")

    # --- L45 na ctverci ---
    line2 = tangent_line_parallel(Vector(1.0, 0.0, 0.0), square, 1)
    check(line2.origin.x == 4.0, "L45: dotykovy bod na ctverci ma x=4 (prava strana)")
    check(math.isclose(line2.direction.x, 1.0) and math.isclose(line2.direction.y, 0.0),
          "L45: smer primky na ctverci odpovida kanonicke orientaci V")

    # --- chybovy stav: K prilis velke ---
    try:
        tangent_line_parallel(Vector(1.0, 0.0, 0.0), two_pt, 5)
        check(False, "L45: K prilis velke melo vyhodit ValueError")
    except ValueError:
        check(True, "L45: K prilis velke -> ValueError")

    print("Vse OK.")


if __name__ == "__main__":
    main()
