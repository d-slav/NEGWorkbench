# -*- coding: utf-8 -*-
"""
Procedura D611 (GL3 opcode D11)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Vzdalenost bodu od primky.

Uziti:   CALL D611(X1,Y1,X2,Y2,A2,B2,X)

Parametry: X1,Y1        R*4  Souradnice bodu
           X2,Y2,A2,B2  R*4  Parametry primky (bod + smer)
           X            R*4  Vysledna vzdalenost

Puvodni vzorec X=ABS(B2*(X2-X1)-A2*(Y2-Y1)) POCITA BEZ deleni velikosti
smeroveho vektoru - predpoklada, ze (A2,B2) uz je jednotkovy vektor
(u nas Line.direction vzdy je). Pro jistotu ho tu pro-forma znovu
normalizujeme (viz v220.unit_vector), aby funkce fungovala spravne i pro
pripadnou nenormalizovanou primku.
"""

from .v220 import unit_vector


def point_line(point, line):
    """Vzdalenost bodu od primky."""
    ax, ay = unit_vector(line.direction.x, line.direction.y)
    x1, y1 = point.x, point.y
    x2, y2 = line.origin.x, line.origin.y
    return abs(ay * (x2 - x1) - ax * (y2 - y1))
