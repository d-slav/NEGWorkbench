# -*- coding: utf-8 -*-
"""
GL3 opcode NPO

Ucel:    Pocet uzlovych bodu retezce nebo krivky.

Uziti:   pi=NPO>vg(S,E,T,H)   (vg = libovolny typ krivky/retezce: 2D
                                krivka S, 2D retezec E, 3D krivka T,
                                3D retezec H)

Zdroj: neni potreba specialni Fortran zdroj (dle zadani "odvodit z
objektu") - hodnota je primo dostupna z nasi Python reprezentace,
Curve i Spline uz drzi svuj seznam uzlovych bodu v pameti (.points).
Az pribudou 3D obdoby T/H, staci aby take mely atribut .points -
funkce potom zafunguje beze zmeny.
"""


def point_count(curve_or_chain):
    """Pocet uzlovych bodu 'curve_or_chain' (Curve, Spline, nebo
    cokoliv jineho s atributem .points) - NPO."""
    return len(curve_or_chain.points)
