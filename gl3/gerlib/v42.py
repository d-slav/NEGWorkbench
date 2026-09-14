# -*- coding: utf-8 -*-
"""
Operace V42 (NEG jazykova specifikace) - Vektor nasobeny skalarem.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'V42 - Vektor nasobeny
skalarem' a zadani uzivatele):

    VM=V42>V,D

    V = vektor (Vector)
    D = skalarni vyraz - vektor VM je D-nasobkem vektoru V (kazda
        slozka V vynasobena D).
"""
from .types import Vector


def scale_vector(v, d):
    """V42: VM=V42>V,D - vektor VM = D * V (kazda slozka vynasobena D)."""
    return Vector(v.x * d, v.y * d, v.z * d)
