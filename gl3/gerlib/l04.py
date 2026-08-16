# -*- coding: utf-8 -*-
"""
GL3 opcode L04                                      LET, k.p., Uh.Hradiste

Ucel:    Definice primky dvema body.

Uziti:   LM=L04>>P1,P2

Parametry:  P1, P2  Pruchozi body primky
            LM      Vysledna primka (pruchozi bod P1 a jednotkovy,
                    smluvne orientovany smerovy vektor P1->P2)

Primka je smluvne orientovana nezavisle na poradi bodu P1, P2 (viz
V221/canonical_unit_vector). Neni definovana, jsou-li body P1 a P2
totozne, t.j. jejich vzdalenost je mensi nez 0.001 jednotky - chyba
(viz G10.md, odst. "L04 - Primka dvema body").

Zadny Fortran zdroj neni k dispozici (analogicky L00/L02) - implementace
1:1 podle textove specifikace v prirucce.
"""

import math

from .types import Point, Line, Vector
from .v221 import canonical_unit_vector

_MIN_DISTANCE = 0.001


def line_through_two_points(p1, p2):
    """L04: LM=L04>>P1,P2 - primka body P1 a P2. Chyba, jsou-li body P1
    a P2 totozne (vzdalenost < 0.001 jednotky)."""
    dx, dy = p2.x - p1.x, p2.y - p1.y
    if math.hypot(dx, dy) < _MIN_DISTANCE:
        raise ValueError(
            "L04: body P1 a P2 jsou totozne (vzdalenost mensi nez %s "
            "jednotky) - primka neni definovana" % _MIN_DISTANCE
        )
    a, b = canonical_unit_vector(dx, dy)
    return Line(Point(p1.x, p1.y, p1.z), Vector(a, b, 0.0))
