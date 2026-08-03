# -*- coding: utf-8 -*-
"""
Procedura L302 (GL3 opcode L02)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Definice primky pruchozim bodem a obecnym vektorem smeru.

Uziti:   CALL L302(X1,Y1,X2,Y2,X,Y,A,B,J)
         GL3:  LM=L02>P,V

Parametry:  X1,Y1    R*4  Souradnice vstupniho bodu
            X2,Y2    R*4  Slozky obecneho vektoru smeru
            X,Y,A,B  R*4  Parametry primky (pruchozi bod a jednotkovy,
                          smluvne orientovany smerovy vektor)
            J        I*2  Chybove cislo: J=0 primka definovana,
                          J=3020 zadan nulovy vektor

Volane moduly:  GERLIBPC/LI:V221
"""

from .types import Point, Line, Vector
from .v221 import canonical_unit_vector


def line_through_point(point, direction):
    """Primka bodem 'point' ve smeru obecneho vektoru 'direction' (L302
    / GL3 opcode L02). Smer se normalizuje a kanonicky orientuje (V221)
    - vysledna primka tedy zavisi jen na ose vektoru 'direction', ne na
    tom, kterym smerem po teto ose byl zadan. Z-slozka pruchoziho bodu
    se prenasi beze zmeny (2D operace, smer lezi v rovine z=0)."""
    a, b = canonical_unit_vector(direction.x, direction.y)
    return Line(Point(point.x, point.y, point.z), Vector(a, b, 0.0))
