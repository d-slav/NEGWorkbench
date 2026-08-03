# -*- coding: utf-8 -*-
"""
Procedura P113 (GL3 opcode P13)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Bod deli usecku v danem delicim pomeru.

Uziti:   CALL P113(X1,Y1,X2,Y2,X3,X,Y)

Parametry: X1,Y1  R*4  Souradnice pocatecniho bodu
           X2,Y2  R*4  Souradnice koncoveho bodu usecky
           X3     R*4  Parametr - delici pomer <0,1>
                         (mimo tento interval extrapolace)
           X,Y    R*4  Souradnice vysledneho bodu
"""

from .types import Point


def interpolate_point(p1, p2, t):
    """Bod na usecce p1->p2 v pomeru t (0 = p1, 1 = p2). Mimo <0,1>
    extrapolace - stejne jako puvodni P113."""
    return Point(
        p1.x + t * (p2.x - p1.x),
        p1.y + t * (p2.y - p1.y),
        p1.z + t * (p2.z - p1.z),
    )
