# -*- coding: utf-8 -*-
"""
Procedura P117 (GL3 opcode P17)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Bod v dane vzdalenosti od daneho bodu rovnobezne s danou
         primkou.

Uziti:   CALL P117(X1,Y1,A2,B2,X3,X,Y,K)
         GL3:  PM=P17>P,L,D[,K]

Bod PM lezi ve vzdalenosti D od bodu P ve smeru danem primkou L (jen
SMER primky L se pouziva, jeji vlastni poloha - origin - je
nepodstatna). Pro K=0 je vzdalenost vynasena v zapornem smeru primky,
pro K=1 (default) v kladnem smeru (viz G10.md 'P17 - Bod od bodu ve
vzdalenosti rovnobezne s primkou').

Parametry:
    P (Point): Vychozi bod
    L (Line):  Primka (pouzit se jen jeji smerovy vektor - predpoklada
               se, ze uz je jednotkovy, viz konvence L00/L02/L04 a
               napr. gerlib.v230.perpendicular_vector)
    D (float): Pozadovana vzdalenost
    K (int, volitelne): 0 = zaporny smer primky, 1 = kladny smer
                         (default)
"""
from .types import Point


def point_parallel_to_line(point, line, distance, k=1):
    """P17: PM=P17>P,L,D,K - bod ve vzdalenosti D od bodu P ve smeru
    (K=1, default) nebo proti smeru (K=0) primky L."""
    d = -distance if int(round(k)) == 0 else distance
    ux, uy = line.direction.x, line.direction.y
    return Point(point.x + d * ux, point.y + d * uy, 0.0)
