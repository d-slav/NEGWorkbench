# -*- coding: utf-8 -*-
"""
Procedura D610 (GL3 opcode D10)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Vzdalenost dvou bodu.

Uziti:   CALL D610(X1,Y1,X2,Y2,X)

Parametry: X1,Y1  R*4  Souradnice prvniho bodu
           X2,Y2  R*4  Souradnice druheho bodu
           X      R*4  Vysledna vzdalenost
"""

import math


def point_point(p1, p2):
    """Obycejna 2D euklidovska vzdalenost dvou bodu."""
    return math.hypot(p2.x - p1.x, p2.y - p1.y)
