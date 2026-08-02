# -*- coding: utf-8 -*-
"""
Operace U00 (NEG jazykova specifikace) - Vektor tremi slozkami.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz zadani uzivatele):

    UM=U00>D1,D2,D3

    D1,D2,D3 = skalarni vyrazy - slozky x, y, z noveho vektoru (v
               souradnicich zakladni/base souradnicove soustavy).
"""
from gerlib.types import Vector


def make_vector3(d1, d2, d3):
    """U00: UM=U00>D1,D2,D3 - vektor danymi slozkami x, y, z."""
    return Vector(d1, d2, d3)
