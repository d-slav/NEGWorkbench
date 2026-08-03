# -*- coding: utf-8 -*-
"""
GL3 opcode C49

Ucel:    Prekopirovani kruznice - hodnotova kopie (ekvivalent P49, jen
         pro typ C/Circle).

Uziti:   CM=C49>>C<

Parametry: C   Circle  vstupni kruznice
           CM  Circle  vystup - nova instance (novy stred, polomer,
                        normala) se stejnymi hodnotami jako C

Zdroj:   puvodni Fortran nedodan - trivialni pomocna operace, zadana
         primo uzivatelem (bez A0xx.FOR), analogicka P49.
"""

from .types import Point, Vector, Circle


def copy_circle(circle):
    """Vraci NOVOU instanci Circle se stejnymi hodnotami jako 'circle'
    (hodnotova kopie vc. stredu a normaly, ne sdilene reference - C49)."""
    center = Point(circle.center.x, circle.center.y, circle.center.z)
    normal = Vector(circle.normal.x, circle.normal.y, circle.normal.z)
    return Circle(center, circle.radius, normal)
