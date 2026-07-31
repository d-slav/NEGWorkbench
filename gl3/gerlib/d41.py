# -*- coding: utf-8 -*-
"""
Procedura D641 (GL3 opcode D41)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Plocha trojuhelnika vymezeneho tremi primkami.

Uziti:   CALL D641(X1,Y1,A1,B1,X2,Y2,A2,B2,X3,Y3,A3,B3,X,J)

Volane moduly: GERLIBPC/LI:P120,D640 (viz p20.py, d40.py)

Pozn.: puvodni D641.FOR kontroluje chybu J jen po TRETIM volani P120,
takze pri rovnobeznosti prvni/druhe dvojice primek muze byt chyba
prepsana uspechem treti dvojice (bug v originale). Tady misto toho
kontrolujeme kazdy prusecik zvlast - spravnejsi chovani.
"""

from .p20 import line_intersection
from .d40 import triangle_area


def triangle_area_from_lines(line1, line2, line3):
    """Obsah trojuhelniku vymezeneho tremi primkami - najde prusecik kazde
    dvojice primek (P20) a spocita obsah trojuhelniku z techto tri
    vrcholu (D40)."""
    p_a = line_intersection(line1, line2)
    p_b = line_intersection(line1, line3)
    p_c = line_intersection(line2, line3)
    return triangle_area(p_a, p_b, p_c)
