# -*- coding: utf-8 -*-
"""
Procedura V220        LET, k.p., Uh.Hradiste          P.Franc
Knihovna GERLIBPC                       Listopad 1989

Ucel:    Jednotkovy vektor, jehoz smer je urcen danym obecnym vektorem.

Uziti:   CALL V220(A1,B1,A,B,J)

Parametry:  A1,B1  R*4  Slozky obecneho vektoru
            A,B    R*4  Slozky vysl. jednot. vektoru
            J      I*2  Chybove cislo: J=0 spravne, J=2200 vektor je nulovy
"""

import math


def unit_vector(x, y):
    """Jednotkovy vektor ve smeru (x, y); chyba, kdyz je vektor (temer)
    nulovy (original: J=2200)."""
    d = math.hypot(x, y)
    if d < 1e-3:
        raise ValueError("smerovy vektor je nulovy (V220: chyba 2200)")
    return x / d, y / d
