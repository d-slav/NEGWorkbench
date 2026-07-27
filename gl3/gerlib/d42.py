# -*- coding: utf-8 -*-
"""
Procedura D642 (GL3 opcode D42)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Plocha trojuhelnika danymi tremi body, se znamenkem podle
         poradi vrcholu (CW kladne, CCW zaporne).

Uziti:   CALL D642(X1,Y1,X2,Y2,X3,Y3,X)
"""

from .d40 import _cross_z


def triangle_area_signed(p1, p2, p3):
    """Obsah trojuhelniku danymi tremi body, znamenko podle poradi vrcholu."""
    a1, b1 = p1.x - p2.x, p1.y - p2.y
    a2, b2 = p3.x - p2.x, p3.y - p2.y
    return _cross_z(a1, b1, a2, b2) / 2.0
