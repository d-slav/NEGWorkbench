# -*- coding: utf-8 -*-
"""
Procedura P85 (GL3 opcode P85)      n.p. LET Kunovice
Knihovna GL3E2                                      Duben 1985

Ucel:    Dotykovy bod na retezci rovnobezne s primkou.

Uziti:   PM=P85>V,E,K<

Jadro algoritmu je v e01.tangent_point_on_chain (sdileno s P86 a L46).
"""

from .types import Point
from .e01 import tangent_point_on_chain


def tangent_point(direction, curve, k=1):
    """Dotykovy bod na retezci 'curve', tecny rovnobezne s vektorem
    'direction' (K-ty takovy bod)."""
    x, y, _idx = tangent_point_on_chain((direction.x, direction.y), curve, int(round(k)))
    return Point(x, y, 0.0)
