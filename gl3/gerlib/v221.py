# -*- coding: utf-8 -*-
"""
Procedura V221        LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                       Listopad 1989

Ucel:    Jednotkovy smluvne orientovany vektor, jehoz smer je urcen
         danym obecnym vektorem.

Uziti:   CALL V221(A1,B1,A,B,J)

Parametry:  A1,B1  R*4  Slozky obecneho vektoru (vstup.)
            A,B    R*4  Slozky jednotkoveho, smluvne orientovaneho
                        vektoru
            J      I*2  Chybove cislo: J=0 spravne provedeno,
                        J=2210 zadan nulovy vektor

Volane moduly:  GERLIBPC/LI:V220
"""

from .v220 import unit_vector


def canonical_unit_vector(x, y):
    """Jednotkovy vektor ve smeru (x, y), navic "smluvne orientovany"
    (V221): vysledek nezavisi na tom, kterym koncem byl vstupni vektor
    zadan (x,y) vs (-x,-y) davaji stejny vysledek.

    Konvence (1:1 podle V221.FOR - viz vetveni IF(A-1E-6).../IF(B)...):
      - je-li A (x-slozka po normalizaci) > 1e-6, vektor se necha tak,
        jak je (kladna x-ova slozka),
      - je-li A <= -1e-6, vektor se otoci (-A, -B),
      - je-li A priblizne nulove (|A| <= 1e-6, tj. vektor temer svisly),
        rozhoduje znamenko B: B < 0 => otocit, jinak necha tak, jak je.

    Chyba (nulovy vektor) - viz unit_vector - propaguje se jako
    ValueError; puvodni Fortran kod J=2200 z V220 se zde meni na
    J=2210 (V221 ma svuj vlastni kod pro tutez situaci).
    """
    try:
        a, b = unit_vector(x, y)
    except ValueError:
        raise ValueError("smerovy vektor je nulovy (V221: chyba 2210)")

    if a > 1e-6:
        return a, b
    if a <= -1e-6:
        return -a, -b
    # a je prakticky nulove (vektor temer svisly) - rozhoduje znamenko B
    if b < 0:
        return -a, -b
    return a, b
