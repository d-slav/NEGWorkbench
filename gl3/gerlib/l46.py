# -*- coding: utf-8 -*-
"""
Procedura L46 (GL3 opcode L46)      n.p. LET Kunovice
Knihovna GL3E2                                      Duben 1985

Ucel:    Primka tecne se dotykajici retezce rovnobezne s primkou.

Uziti:   LM=L46>L,E,K<

L46.FOR je tenky wrapper nad P86 (viz p86.py): najde dotykovy bod a
postavi novou primku se stejnym SMEREM jako vstupni L (1:1 podle
L46.FOR: DO 10 I=3,4 R(I,JC1)=R(I,JC2)), jen jiny pocatek - novy
dotykovy bod.
"""

from .types import Point, Line, Vector
from .e01 import tangent_point_on_chain


def tangent_line(line, curve, k=1):
    """Primka tecne se dotykajici retezce 'curve', rovnobezna s primkou
    'line' (K-ty takovy dotykovy bod). Vysledna primka ma stejny SMER
    jako 'line', jen jiny pocatek - novy dotykovy bod."""
    x, y, _idx = tangent_point_on_chain(
        (line.direction.x, line.direction.y), curve, int(round(k))
    )
    return Line(Point(x, y, 0.0), Vector(line.direction.x, line.direction.y, 0.0))
