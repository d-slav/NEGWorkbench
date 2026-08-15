# -*- coding: utf-8 -*-
"""
Procedura L300 (GL3 opcode L00)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Definice primky slozkami pruchozi bodu a vektoru smeru.

Uziti:   CALL L300(X1,Y1,A1,B1,X,Y,A,B,J)
         GL3:  LM=L00>>D1,D2,D3,D4

Parametry:  D1, D2  R*4  Souradnice pruchozi bodu (x, y)
            D3, D4  R*4  Slozky smeroveho vektoru (x, y)
            LM           Vysledna primka (pruchozi bod + jednotkovy,
                         smluvne orientovany smerovy vektor)
            J       I*2  J=0 spravne, J=3000 nulovy vektor (D3==D4==0)

Volane moduly:  GERLIBPC/LI:V221
"""

from .types import Point, Line, Vector
from .v221 import canonical_unit_vector


def line_from_coords(d1, d2, d3, d4):
    """L00: LM=L00>>D1,D2,D3,D4 — primka slozkami bodu (D1,D2) a vektoru
    smeru (D3,D4). Smer se normalizuje a kanonicky orientuje (V221).
    Chyba, pokud je smerovy vektor nulovy (puvodni J=3000)."""
    a, b = canonical_unit_vector(d3, d4)
    return Line(Point(d1, d2, 0.0), Vector(a, b, 0.0))
