# -*- coding: utf-8 -*-
"""
GL3 opcode C00

Ucel:    Kruznice souradnicemi stredu a polomerem.

Uziti:   CM=C00>D1,D2,D3

Trivialni - zadny Fortran zdroj netreba.
"""

from .types import Point, Circle


def circle_from_coords(x, y, radius):
    """C00: kruznice se stredem (x, y) (Z=0) a polomerem 'radius'."""
    return Circle(Point(x, y, 0.0), radius)
