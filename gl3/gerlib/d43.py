# -*- coding: utf-8 -*-
"""
Procedura D643 (GL3 opcode D43)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Plocha kruznice.

Uziti:   CALL D643(X1,Y1,A1,X)

Parametry: X1,Y1,A1  R*4  Parametry kruznice (stred X1,Y1 se u teto
                          operace nepouzije - presne jako v originale,
                          kde jsou to jen nevyuzite dummy parametry)
           X         R*4  Vysledny plosny obsah
"""

import math


def circle_area(circle):
    """Obsah kruhu (bere jen circle.radius)."""
    return math.pi * circle.radius ** 2
