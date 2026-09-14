# -*- coding: utf-8 -*-
"""
Operace V41 (NEG jazykova specifikace) - Vektor dane delky rovnobezny
s vektorem.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'V41 - Vektor dane delky
rovnobezny s vektorem'):

    VM=V41>V,D

    V = vektor (Vector)
    D = skalarni vyraz - vysledna velikost vektoru VM

Vektor VM ma stejny smer jako V, velikost upravena na hodnotu D -
VM = (V / |V|) * D. Zaporne D tedy dava vektor OPACNEHO smeru nez V
(stejna konvence jako u V42 - znamenko D se projevi primo), velikost
|VM| = |D|.

D=0 vraci nulovy vektor bez ohledu na V (zadna chyba, ani kdyby V byl
nulovy - vysledek 0*cokoliv je jednoznacne nulovy vektor). Je-li V
nulovy vektor A D nenulove, je hlasena chyba (G10.md - smer neni
definovany, puvodni IER neznamy, zdrojovy kod nedodan).
"""
from .types import Vector


def scale_to_length(v, d):
    """V41: VM=V41>V,D - vektor rovnobezny s V, velikost upravena na D
    (VM = (V/|V|) * D). D=0 vraci nulovy vektor bez ohledu na V; V
    nulovy s nenulovym D je chyba."""
    if d == 0:
        return Vector(0.0, 0.0, 0.0)
    length = (v.x * v.x + v.y * v.y + v.z * v.z) ** 0.5
    if length <= 1e-10:
        raise ValueError("V41: vektor V nesmi byt nulovy, kdyz D neni 0")
    factor = d / length
    return Vector(v.x * factor, v.y * factor, v.z * factor)
