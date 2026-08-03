# -*- coding: utf-8 -*-
"""
GL3 opcode P49

Ucel:    Prekopirovani bodu - hodnotova kopie (ekvivalent prirazeni
         PM=P, kde primy Fortran zapis nebyl k dispozici, protoze P je
         slozeny/vicerozmerny typ, ne skalar).

Uziti:   PM=P49>>P<

Parametry: P   Point  vstupni bod
           PM  Point  vystup - nova instance se stejnymi souradnicemi
                       jako P (ne stejna reference)

Zdroj:   puvodni Fortran nedodan - trivialni pomocna operace, zadana
         primo uzivatelem (bez A0xx.FOR).
"""

from .types import Point


def copy_point(point):
    """Vraci NOVOU instanci Point se stejnymi souradnicemi jako 'point'
    (hodnotova kopie - P49). Dulezite hlavne tam, kde by dalsi operace
    mohla vysledek mutovat na miste a nesmi tim ovlivnit puvodni bod."""
    return Point(point.x, point.y, point.z)
