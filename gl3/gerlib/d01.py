# -*- coding: utf-8 -*-
"""
Procedura D601 (GL3 opcode D01)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Soucet a rozdil skalaru.

Uziti:   CALL D601(X1,X2,X,K)

Parametry: X1,X2  R*4  Realne hodnoty
           X      R*4  Vysledna hodnota
           K      I*2  Vyberove cislo: 0 - soucet, 1 - rozdil
"""


def sum_or_diff(x1, x2, k=0):
    """Soucet (k=0) nebo rozdil (k!=0) dvou skalaru."""
    if k == 0:
        return x1 + x2
    return x1 - x2
