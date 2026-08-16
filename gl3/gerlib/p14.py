# -*- coding: utf-8 -*-
"""
GL3 opcode P14

Ucel:    Bod na primce souradnici x (y).

Uziti:   PM=P14>>D,L,K
         PM = bod lezici na primce L, jehoz jedna souradnice ma
              hodnotu D. Pro K=0 je x-ova souradnice rovna D, pro K=1
              je y-ova souradnice rovna D (viz G10.md 'P14 - Bod na
              primce souradnici x (y)').

Je-li primka L kolma k souradnicove ose, pro kterou bylo zvoleno K
(tj. jeji smerovy vektor ma nulovou slozku ve smeru teto osy), nemuze
byt bod jednoznacne urcen - hlasena chyba (i v degenerovanem pripade,
kdy primka na dane souradnici D lezi cela - nekonecne mnoho reseni).

Parametry:
    D (float): Pozadovana souradnice (x pro K=0, y pro K=1)
    L (line):  Primka (Line)
    K (int):   0 = x-ova souradnice, 1 = y-ova souradnice

Zdroj:   puvodni Fortran nedodan - implementace 1:1 podle textove
         specifikace v prirucce (analogicky L04/P43).
"""
from .types import Point

_TOL = 1e-9


def point_on_line_by_coord(d, line, k):
    """P14: bod na primce 'line' se souradnici x=d (k=0) nebo y=d (k=1)."""
    x0, y0 = line.origin.x, line.origin.y
    z0 = getattr(line.origin, "z", 0.0)
    vx, vy = line.direction.x, line.direction.y

    k = int(round(k))
    if k == 0:
        if abs(vx) < _TOL:
            raise ValueError(
                "P14: primka je kolma k ose x (K=0) - x-ovou souradnici "
                "nelze pouzit k jednoznacnemu urceni bodu"
            )
        t = (d - x0) / vx
        return Point(d, y0 + t * vy, z0)

    if k == 1:
        if abs(vy) < _TOL:
            raise ValueError(
                "P14: primka je kolma k ose y (K=1) - y-ovou souradnici "
                "nelze pouzit k jednoznacnemu urceni bodu"
            )
        t = (d - y0) / vy
        return Point(x0 + t * vx, d, z0)

    raise ValueError("P14: vyberove cislo K musi byt 0 nebo 1 (je %r)" % (k,))
