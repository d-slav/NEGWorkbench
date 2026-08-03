# -*- coding: utf-8 -*-
"""
Procedura C402 (GL3 opcode C02)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Kruznice urcena tremi body.

Uziti:   CALL C402(X1,Y1,X2,Y2,X3,Y3,X,Y,A,J)
         GL3:  CM=C02>P1,P2,P3<

Parametry:  X1,Y1  R*4  Souradnice 1. bodu
            X2,Y2  R*4  Souradnice 2. bodu
            X3,Y3  R*4  Souradnice 3. bodu
            X,Y,A  R*4  Vysledna kruznice (stred, polomer)
            J      I*2  Chybove cislo:
                        J=4021  dva ze zadanych bodu totozne
                        J=4022  body lezi na primce (kolinearni)

Volane moduly:  GERLIBPC/LI:P120, L343

Algoritmus (1:1 podle C402.FOR): stred kruznice = prusecik os usecek
P1P2 a P2P3 (viz gerlib.l343.perpendicular_bisector + gerlib.p20.
line_intersection), polomer = vzdalenost stredu od P1.

POZNAMKA k chybe 4021 (totozne body): puvodni C402.FOR kontroluje jen
chybovy priznak J z DRUHEHO volani L343 (na P2,P3) - chyba z PRVNIHO
volani (P1,P2) by byla tichem prepsana, pokud druhe volani probehne v
poradku (typicka Fortran "zapomenuta kontrola mezivysledku"). Tady
misto 1:1 kopie teto mezery kontrolujeme oba pary bodu (P1,P2 i P2,P3)
explicitne - chovani pro spravna data je stejne, jen se navic
korektne odchyti pripad P1==P2 & P2!=P3, ktery by v originale prosel
bez chyby a spadl by pravdepodobne do neexistujiciho stavu.
"""

import math

from .types import Circle
from .p20 import line_intersection
from .l343 import perpendicular_bisector


def circle_from_3_points(p1, p2, p3):
    """Kruznice prochazejici body p1, p2, p3 (C402/C02).

    Chyby:
      - dva ze zadanych bodu totozne -> ValueError (puvodni J=4021)
      - vsechny tri body kolinearni (osy jsou rovnobezne, prusecik
        neexistuje) -> ValueError (puvodni J=4022)
    """
    try:
        bisector_12 = perpendicular_bisector(p1, p2)
    except ValueError:
        raise ValueError(
            "C402/C02: 1. a 2. bod jsou totozne (chyba 4021)"
        )
    try:
        bisector_23 = perpendicular_bisector(p2, p3)
    except ValueError:
        raise ValueError(
            "C402/C02: 2. a 3. bod jsou totozne (chyba 4021)"
        )

    try:
        center = line_intersection(bisector_12, bisector_23)
    except ValueError:
        raise ValueError(
            "C402/C02: zadane body lezi na primce (chyba 4022)"
        )

    radius = math.hypot(p1.x - center.x, p1.y - center.y)
    return Circle(center, radius)
