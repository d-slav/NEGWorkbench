# -*- coding: utf-8 -*-
"""
Procedura D620 (GL3 opcode D20)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Velikost vektoru.

Uziti:   CALL D620(X1,Y1,X)

Parametry: X1,Y1  R*4  Slozky vektoru
           X      R*4  Vysledna delka vektoru
"""

import math


def vector_magnitude(vec):
    """Velikost vektoru."""
    return math.hypot(vec.x, vec.y)
