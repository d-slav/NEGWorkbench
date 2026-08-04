# -*- coding: utf-8 -*-
"""Test V230 (kolmy vektor k primce, K=0/1) a L20/L320 (rovnobezna
primka ve vzdalenosti)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line
from gerlib.v230 import perpendicular_vector
from gerlib.l20 import parallel_line


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # primka vodorovna, smer (1,0) - kladny smer doprava
    horiz = Vector(1.0, 0.0, 0.0)

    # K=0 (<=0) -> vlevo pri pohledu ve smeru primky = (0,1) (nahoru)
    v = perpendicular_vector(horiz, 0)
    a, b = v.x, v.y
    check(math.isclose(a, 0.0, abs_tol=1e-9) and math.isclose(b, 1.0), "V230: K=0 -> vlevo (nahoru) pro vodorovnou primku")

    # K=1 -> vpravo = (0,-1) (dolu)
    v2 = perpendicular_vector(horiz, 1)
    a2, b2 = v2.x, v2.y
    check(math.isclose(a2, 0.0, abs_tol=1e-9) and math.isclose(b2, -1.0), "V230: K=1 -> vpravo (dolu) pro vodorovnou primku")

    # zaporne K se chova jako K=0 (vetveni IF(K) 1,1,2)
    v3 = perpendicular_vector(horiz, -5)
    a3, b3 = v3.x, v3.y
    check((a3, b3) == (a, b), "V230: zaporne K se chova jako K=0")

    # L20 na vodorovne primce bodem (2,3), vzdalenost 5, K=0 (nahoru)
    line = Line(Point(2.0, 3.0, 1.0), Vector(1.0, 0.0, 0.0))
    par0 = parallel_line(line, 5.0, 0)
    check(math.isclose(par0.origin.x, 2.0) and math.isclose(par0.origin.y, 8.0),
          "L20: K=0, posun o vzdalenost 5 nahoru")
    check(par0.origin.z == 1.0, "L20: Z souradnice bodu primky se prenasi beze zmeny")
    check(math.isclose(par0.direction.x, 1.0) and math.isclose(par0.direction.y, 0.0),
          "L20: smer vysledne primky je stejny jako u vstupni")

    # K=1 (dolu)
    par1 = parallel_line(line, 5.0, 1)
    check(math.isclose(par1.origin.x, 2.0) and math.isclose(par1.origin.y, -2.0),
          "L20: K=1, posun o vzdalenost 5 dolu")

    # vychozi K (nezadano) = 0
    par_default = parallel_line(line, 5.0)
    check(math.isclose(par_default.origin.x, par0.origin.x) and math.isclose(par_default.origin.y, par0.origin.y),
          "L20: vynechany K se chova jako K=0")

    # sikma primka - overeni, ze kolmy vektor je opravdu kolmy (skalarni soucin 0)
    diag = Vector(0.6, 0.8, 0.0)
    pv = perpendicular_vector(diag, 0)
    pa, pb = pv.x, pv.y
    check(math.isclose(diag.x * pa + diag.y * pb, 0.0, abs_tol=1e-9),
          "V230: vysledny vektor je kolmy na vstupni smer (skalarni soucin 0)")
    check(math.isclose(math.hypot(pa, pb), 1.0), "V230: vysledny vektor zustava jednotkovy (vstup uz byl jednotkovy)")

    print("Vse OK.")


if __name__ == "__main__":
    main()
