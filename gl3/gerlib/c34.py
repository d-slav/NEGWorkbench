# -*- coding: utf-8 -*-
"""
GL3 opcode C34

Ucel:    Kruznice daneho polomeru tecna ke dvema kruznicim.

Uziti:   CM=C34>C1,C2,D,KKK

Kruznice CM o polomeru D se tecne dotyka kruznic C1 a C2.
    K3=0 dotyk vnitrni s C1, K3=1 dotyk vnejsi s C1
    K2=0 dotyk vnitrni s C2, K2=1 dotyk vnejsi s C2
    K1=0 stred CM vlevo od orientovane spojnice stredu C1->C2,
    K1=1 stred CM vpravo
Nelze-li kruznici sestrojit, je hlasena chyba.

POZNAMKA k baleni KKK: zadny Fortran zdroj nedodan - stejny predpoklad
dekadickeho baleni jako C32/C33 - KKK = 100*K3 + 10*K2 + K1 (poradi
K3,K2,K1 v popisu odpovida poradi cifer stovky/desitky/jednotky).

Algoritmus: "dotyk vnitrni" = stred CM ve vzdalenosti |R-D| od stredu
dane kruznice (funguje pro oba pripady, kdyz CM je uvnitr i kdyz dana
kruznice je uvnitr CM), "dotyk vnejsi" = vzdalenost R+D. Stred CM je
pak prusecik dvou takto urcenych ("redukovanych") kruznic kolem stredu
C1 a C2 - klasicka Apolloniova konstrukce zjednodusena o jeden stupen
diky znamemu polomeru D. K1 vybira mezi dvema kandidaty (circle_geom.
circle_circle_intersection).
"""

from .types import Circle
from .circle_geom import circle_circle_intersection


def tangent_to_two_circles(circle1, circle2, radius, kkk):
    """C34: kruznice polomeru 'radius' tecna k 'circle1' a 'circle2'.
    'kkk' je baleny vyber dotyku/strany - viz hlavicka modulu."""
    kkk_int = int(round(kkk))
    k1 = kkk_int % 10
    k2 = (kkk_int // 10) % 10
    k3 = (kkk_int // 100) % 10

    d1 = circle1.radius + radius if k3 else abs(circle1.radius - radius)
    d2 = circle2.radius + radius if k2 else abs(circle2.radius - radius)

    left, right = circle_circle_intersection(circle1.center, d1, circle2.center, d2)
    center = right if k1 else left
    return Circle(center, radius)
