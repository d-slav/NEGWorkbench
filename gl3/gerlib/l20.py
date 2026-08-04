# -*- coding: utf-8 -*-
"""
Procedura L320 (GL3 opcode L20)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Primka rovnobezna s danou primkou v dane vzdalenosti.

Uziti:   CALL L320(X1,Y1,A1,B1,X2,X,Y,A,B,K)
         GL3:  LM=L20>L,D[,K]

Parametry:  X1,Y1,A1,B1  R*4  Parametry vstupni primky
            X2           R*4  Vzdalenost
            X,Y,A,B      R*4  Vysledna primka (smer stejny jako u
                              vstupni primky - kopie A1,B1 beze zmeny)
            K            I*2  Vyberove cislo (K=0 vlevo, K=1 vpravo,
                              viz V230). V GL3 volani nepovinny parametr
                              - pri vynechani K=0.

Volane moduly:  GERLIBPC/LI:V230
"""

from .types import Point, Line, Vector
from .v230 import perpendicular_vector


def parallel_line(line, distance, k=0):
    """Primka rovnobezna s 'line' ve vzdalenosti 'distance', na strane
    urcene 'k' (0 = vlevo, 1 = vpravo pri pohledu v kladnem smeru
    vstupni primky - viz V230/perpendicular_vector). Smer vysledne
    primky je stejny jako u vstupni primky (L320: A=A1, B=B1 beze
    zmeny)."""
    perp = perpendicular_vector(line.direction, k)
    x = line.origin.x + distance * perp.x
    y = line.origin.y + distance * perp.y
    direction = Vector(line.direction.x, line.direction.y, line.direction.z)
    return Line(Point(x, y, line.origin.z), direction)
