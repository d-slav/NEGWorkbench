# -*- coding: utf-8 -*-
"""
Procedura L343        LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                       Listopad 1989 (predpokladano)

Ucel:    Osa usecky - primka kolma na spojnici dvou bodu, prochazejici
         jejim stredem.

Uziti:   CALL L343(X1,Y1,X2,Y2,X,Y,A,B,J)

POZNAMKA: puvodni zdrojak L343.FOR nebyl k dispozici (dodano jen
C402.FOR a P120.FOR, ktere L343 jako podmodul pouze VOLAJI). Chovani
odvozeno vyhradne z kontextu pouziti v C402.FOR (kruznice tremi body):
prusecik os usecek P1P2 a P2P3 musi byt bod stejne vzdaleny od vsech
tri vrcholu, tedy stred opsane kruznice - a jedina primka s touto
vlastnosti je osa usecky (kolmice stredem). Znamenko/velikost smeroveho
vektoru (A,B) nema vliv na vysledek P120/P20 (viz jeho docstring), takze
tahle nejednoznacnost puvodniho zdroje neovlivnuje spravnost C402/C02.

Parametry:  X1,Y1  R*4  Souradnice 1. bodu usecky
            X2,Y2  R*4  Souradnice 2. bodu usecky
            X,Y    R*4  Bod na ose (stred usecky)
            A,B    R*4  Smer osy (kolmy na usecku P1P2)
            J      I*2  Chybove cislo: J>0 pri totoznych bodech (usecka
                        nulove delky - osa neni definovana)
"""

from .types import Point, Line, Vector


def perpendicular_bisector(p1, p2):
    """Osa usecky p1-p2: primka stredem usecky, kolma na jeji smer
    (L343). Smer vysledne primky neni normalizovan ani kanonicky
    orientovan podle V221 - staci k tomu, aby dala spravny prusecik
    pres P20/line_intersection (viz poznamka v hlavicce modulu)."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        raise ValueError(
            "L343: zadane body jsou totozne - osa usecky neni definovana"
        )
    mid = Point((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0, 0.0)
    direction = Vector(-dy, dx, 0.0)
    return Line(mid, direction)
