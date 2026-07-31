# -*- coding: utf-8 -*-
"""
Procedura D640 (GL3 opcode D40)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Plocha trojuhelnika danymi tremi body (vysledek vzdy kladny).

Uziti:   CALL D640(X1,Y1,X2,Y2,X3,Y3,X)

Volane moduly: GERLIBPC/LI:V201 (krizovy soucin - viz _cross_z nize)
"""


def _cross_z(ax, ay, bx, by):
    """Z-slozka vektoroveho soucinu dvou 2D vektoru (V201)."""
    return ax * by - ay * bx


def triangle_area(p1, p2, p3):
    """Obsah trojuhelniku danymi tremi body (vysledek vzdy kladny)."""
    a1, b1 = p1.x - p2.x, p1.y - p2.y
    a2, b2 = p3.x - p2.x, p3.y - p2.y
    return abs(_cross_z(a1, b1, a2, b2)) / 2.0
