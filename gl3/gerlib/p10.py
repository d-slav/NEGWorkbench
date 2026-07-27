# -*- coding: utf-8 -*-
"""
Procedura P110 (GL3 opcode P10)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Bod od bodu prirustky.

Uziti:   CALL P110(X1,Y1,X2,X3,X,Y)

Parametry: X1,Y1  R*4  Souradnice bodu
           X2     R*4  Prirustek x-ove souradnice
           X3     R*4  Prirustek y-ove souradnice
           X,Y    R*4  Souradnice bodu (vystup)
"""

from .types import Point


def offset_point(point, dx, dy):
    """Bod posunuty o prirustky (dx, dy). Z-slozka beze zmeny (2D operace)."""
    return Point(point.x + dx, point.y + dy, point.z)
