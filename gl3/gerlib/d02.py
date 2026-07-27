# -*- coding: utf-8 -*-
"""
Procedura D602 (GL3 opcode D02)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Soucin a podil skalaru.

Uziti:   CALL D602(X1,X2,X,K,J)

Parametry: X1,X2  R*4  Realne hodnoty
           X      R*4  Vysledna hodnota
           K      I*2  Vyberove cislo: 0 - soucin, 1 - podil
           J      I*2  Chybove cislo (J=6020 pri deleni (temer) nulou)
"""


def product_or_quotient(x1, x2, k=0):
    """Soucin (k=0) nebo podil (k!=0) dvou skalaru. Chyba (puvodne J=6020),
    kdyz je pri deleni x2 (temer) nulove."""
    if k == 0:
        return x1 * x2
    if abs(x2) < 1e-10:
        raise ValueError("D602: deleni (temer) nulou (x2=%r)" % (x2,))
    return x1 / x2
