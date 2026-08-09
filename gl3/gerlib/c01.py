# -*- coding: utf-8 -*-
"""
GL3 opcode C01

Ucel:    Kruznice stredem (bodem) a polomerem.

Uziti:   CM=C01>P,D

Trivialni - zadny Fortran zdroj netreba.
"""

from .types import Circle


def circle_from_point(center, radius):
    """C01: kruznice se stredem 'center' (Point) a polomerem 'radius'."""
    return Circle(center, radius)
