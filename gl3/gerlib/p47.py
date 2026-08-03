# -*- coding: utf-8 -*-
"""
GL3 opcode P47

Ucel:    Vyjmuti stredu kruznice jako samostatneho bodu.

Uziti:   PM=P47>C

Parametry: C   Circle  vstupni kruznice
           PM  Point   vystup - stred kruznice C (hodnotova kopie, ne
                        primy odkaz na circle.center)

Zdroj:   puvodni Fortran nedodan - trivialni pomocna operace, zadana
         primo uzivatelem (bez A0xx.FOR).
"""

from .types import Point


def circle_center(circle):
    """Vraci stred kruznice 'circle' jako NOVOU instanci Point (hodnotova
    kopie - P47), aby pripadna dalsi mutace vysledku neovlivnila
    puvodni kruznici."""
    c = circle.center
    return Point(c.x, c.y, c.z)
