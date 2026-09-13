# -*- coding: utf-8 -*-
"""
Operace V20 (NEG jazykova specifikace) - Jednotkovy vektor k obecnemu
vektoru.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'V20 - Jednotkovy vektor k
obecnemu vektoru'):

    VM=V20>V

    V = vektor (Vector) - VM je jednotkovy vektor se smerem souhlasnym
        s V. Je-li V nulovy vektor, je hlasena chyba (G10.md - puvodni
        IER neznamy, zdrojovy kod nedodan).
"""
from .types import Vector


def make_unit_vector(v):
    """V20: VM=V20>V - jednotkovy vektor ve smeru V; V nesmi byt
    nulovy vektor."""
    length = (v.x * v.x + v.y * v.y + v.z * v.z) ** 0.5
    if length <= 1e-10:
        raise ValueError("V20: vektor V nesmi byt nulovy")
    return Vector(v.x / length, v.y / length, v.z / length)
