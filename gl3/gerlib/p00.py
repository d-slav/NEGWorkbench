# -*- coding: utf-8 -*-
"""
GL3 opcode P00

Ucel:    Bod danymi souradnicemi.

Uziti:   PM=P00>D1,D2

Trivialni - zadny Fortran zdroj netreba (analogicky P49/C49/P47).
"""

from .types import Point


def point_from_coords(x, y):
    """P00: bod (x, y) - Z=0 (2D bod v rovine programu)."""
    return Point(x, y, 0.0)
