# -*- coding: utf-8 -*-
"""
Procedura V230        LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                       Listopad 1989

Ucel:    Jednotkovy vektor kolmy k primce.

Uziti:   CALL V230(X1,Y1,A1,B1,A,B,K)

Parametry:  X1,Y1,A1,B1  R*4  Parametry primky (viz poznamka - X1,Y1
                              se v tele procedury nepouzivaji)
            A,B          R*4  Slozky vysledneho vektoru
            K            I*2  Vyberove cislo:
                               K=0  vektor smeruje do leve poloroviny
                                    (pri pohledu v kladnem smeru primky)
                               K=1  vektor smeruje do prave poloroviny

Poznamka: puvodni Fortran ma ve vstupni signature i bod primky (X1,Y1),
ale v tele procedury se pouziva jen na "PREKL=X1"/"PREKL=Y1" (nepouzita
prekladacova "vyplnova" promenna - nejspis kvuli shode signatury s
volajicim L320, nebo starsi ladici zbytek) - fakticky potrebuje jen
smerovy vektor primky (A1,B1). Vysledny vektor NENI v teto procedure
explicitne normalizovan - je to jen rotace vstupniho smeroveho vektoru
o 90 stupnu, takze zustane jednotkovy prave tehdy, kdyz uz jednotkovy
byl vstupni smer primky (v tomto projektu vzdy je - primky vznikaji
pres V221/kanonickou orientaci, viz l02.py).
"""

from .types import Vector


def perpendicular_vector(direction, k):
    """Jednotkovy vektor kolmy na smer primky 'direction', pootoceny o
    90 stupnu doleva (k<=0) nebo doprava (k>0) vzhledem ke kladnemu
    smeru primky (V230 - vetveni IF(K) 1,1,2 je 1:1 prevzato).
    Predpoklada, ze 'direction' uz je jednotkovy vektor."""
    a1, b1 = direction.x, direction.y
    if k <= 0:
        return Vector(-b1, a1, 0.0)
    return Vector(b1, -a1, 0.0)
