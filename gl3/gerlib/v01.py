# -*- coding: utf-8 -*-
"""
Operace V01 (NEG jazykova specifikace) - Vektor dvema body.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'V01 - Vektor dvema body'):

    VM=V01>P1,P2

    P1,P2 = body (Point) - vektor VM je orientovan z P1 do P2, jeho
            velikost je dana vzdalenosti bodu. Jsou-li P1 a P2
            totozne, ulozi se nulovy vektor (zadna zvlastni vyjimka
            netreba - odecteni dvou stejnych bodu uz samo o sobe
            nulovy vektor da).
"""
from .types import Vector


def make_vector_between(p1, p2):
    """V01: VM=V01>P1,P2 - vektor orientovany z P1 do P2."""
    return Vector(p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
