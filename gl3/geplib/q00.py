# -*- coding: utf-8 -*-
"""
Operace Q00 (NEG jazykova specifikace) - Bod tremi souradnicemi.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz zadani uzivatele):

    QM=Q00>D1,D2,D3

    D1,D2,D3 = skalarni vyrazy - souradnice x, y, z noveho bodu (v
               souradnicich zakladni/base souradnicove soustavy).
"""
from gerlib.types import Point


def make_point3(d1, d2, d3):
    """Q00: QM=Q00>D1,D2,D3 - bod danymi souradnicemi x, y, z."""
    return Point(d1, d2, d3)
