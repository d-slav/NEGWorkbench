# -*- coding: utf-8 -*-
"""
Procedura P86 (GL3 opcode P86)      n.p. LET Kunovice     RNDr. Krusina
Knihovna GL3E2                                      Duben 1985

Ucel:    Dotykovy bod na retezci rovnobezne s primkou.

Uziti:   PM=P86>L,E,K<

P86.FOR je jen tenky wrapper: vytahne smer primky L a preda ho do P85
(viz p85.py). Pouziva se jen smer L, ne jeji poloha.
"""

from .types import Point
from .e01 import tangent_point_on_chain


def tangent_point_from_line(line, curve, k=1):
    """Dotykovy bod na retezci 'curve' rovnobezne s primkou 'line'
    (pouziva se jen smer primky, ne jeji poloha)."""
    x, y, _idx = tangent_point_on_chain(
        (line.direction.x, line.direction.y), curve, int(round(k))
    )
    return Point(x, y, 0.0)
