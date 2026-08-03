# -*- coding: utf-8 -*-
"""Test V221 (kanonicky orientovany jednotkovy vektor) a L02/L302
(primka bodem ve smeru vektoru) - porovnani s vetvenim v puvodnim
Fortran zdroji (V220.FOR/V221.FOR/L302.FOR)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector
from gerlib.v221 import canonical_unit_vector
from gerlib.l02 import line_through_point


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # A jasne kladne (>1e-6) - vektor se necha tak, jak je
    a, b = canonical_unit_vector(3.0, 4.0)
    check(math.isclose(a, 0.6) and math.isclose(b, 0.8), "kladne A -> beze zmeny")

    # A jasne zaporne - vektor se otoci
    a2, b2 = canonical_unit_vector(-3.0, 4.0)
    check(math.isclose(a2, 0.6) and math.isclose(b2, -0.8), "zaporne A -> otoceni")

    # opacne zadany stejny smer musi dat STEJNY vysledek (smluvni orientace)
    check((a, b) == canonical_unit_vector(3.0, 4.0), "konzistence smeru (opakovane volani)")
    a3, b3 = canonical_unit_vector(3.0, -4.0)
    a4, b4 = canonical_unit_vector(-3.0, 4.0)
    check(math.isclose(a3, a4) and math.isclose(b3, b4),
          "(x,y) a (-x,-y) davaji stejnou kanonickou orientaci")

    # A priblizne nulove (svisly vektor), B kladne -> beze zmeny
    a5, b5 = canonical_unit_vector(0.0, 5.0)
    check(math.isclose(a5, 0.0, abs_tol=1e-9) and math.isclose(b5, 1.0), "svisly vektor, B>0 -> beze zmeny")

    # A priblizne nulove, B zaporne -> otoceni
    a6, b6 = canonical_unit_vector(0.0, -5.0)
    check(math.isclose(a6, 0.0, abs_tol=1e-9) and math.isclose(b6, 1.0), "svisly vektor, B<0 -> otoceni")

    # nulovy vektor -> chyba (puvodne J=2210)
    try:
        canonical_unit_vector(0.0, 0.0)
        check(False, "nulovy vektor mel vyhodit ValueError")
    except ValueError:
        check(True, "nulovy vektor -> ValueError (2210)")

    # L02: primka bodem P ve smeru V - Z se nemeni, smer je kanonicky
    p = Point(1.0, 2.0, 5.0)
    line = line_through_point(p, Vector(-3.0, 4.0, 0.0))
    check(line.origin.x == 1.0 and line.origin.y == 2.0 and line.origin.z == 5.0,
          "L02: pruchozi bod se prenasi beze zmeny (i Z)")
    check(math.isclose(line.direction.x, 0.6) and math.isclose(line.direction.y, -0.8),
          "L02: smer je kanonicky orientovana jednotkova V221")

    print("Vse OK.")


if __name__ == "__main__":
    main()
