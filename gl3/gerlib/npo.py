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

ROZSIRENI (nad ramec puvodniho GL3, domluveno v konverzaci): NPO teď
prijme i primo POLE bodu (napr. composite in:P(N) vstup ze skutecne
FreeCAD geometrie, viz gl3_program.py - '.Points' u Draft BSpline/Wire,
ktere muze mit libovolnou delku podle toho, co uzivatel v modelu
naklikal). Puvodni GL3 tohle nepotrebovalo, protoze velikost pole byla
vzdy staticka (znama uz z DIMEN) - u vstupu z FreeCADu uz ale predem
znama byt nemusi, takze NPO>P (bez indexu - cele pole, ne jeden prvek)
vraci jeho aktualni delku.
"""


def point_count(curve_or_chain_or_array):
    """Pocet uzlovych bodu 'curve_or_chain_or_array' - NPO. Prijima:
      - Curve, Spline (nebo cokoliv jineho s atributem .points)
      - obycejne Python pole (list) bodu - NASE rozsireni, viz hlavicka
        modulu."""
    if isinstance(curve_or_chain_or_array, list):
        return len(curve_or_chain_or_array)
    return len(curve_or_chain_or_array.points)

