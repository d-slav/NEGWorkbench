# -*- coding: utf-8 -*-
"""
Procedura L45 (GL3 opcode L45)      n.p. LET Kunovice
Knihovna GL3E2                                      Brezen 1985

Ucel:    Primka "tecna" k retezci, rovnobezna se zadanym vektorem -
         prochazi dotykovym bodem (viz P85/e01.tangent_point_on_chain),
         smer vysledne primky je KANONICKY ORIENTOVANA kopie puvodniho
         vektoru V (V221 - viz l02.py), NE mistni smer retezce v danem
         bode (na rozdil od L46, ktere kopiruje smer vstupni primky
         beze zmeny - viz l46.py).

Uziti:   LM=L45>V,E,K<

Algoritmus (1:1 podle L45.FOR): zavola P85 pro nalezeni dotykoveho
bodu (chyba IER=544 z P85 - "nalezeno pres celou rovnobeznou hranu" -
se tu povazuje za uspech, ne chybu), pak sestavi vyslednou primku s
timto bodem jako pocatkem a V221(V) jako smerem.

Zavislosti: gerlib.e01.tangent_point_on_chain (P85), gerlib.v221.
canonical_unit_vector (V221).
"""

from .types import Point, Line, Vector
from .e01 import tangent_point_on_chain
from .v221 import canonical_unit_vector


def tangent_line_parallel(direction, curve, k=1):
    """L45: primka dotykajici se retezce 'curve' (K-ty dotykovy bod,
    P85), ve smeru 'direction' - smer vysledne primky je kanonicky
    orientovana jednotkova kopie 'direction' (V221), ne mistni smer
    retezce v nalezenem bode."""
    x, y, _idx = tangent_point_on_chain((direction.x, direction.y), curve, int(round(k)))
    a, b = canonical_unit_vector(direction.x, direction.y)
    return Line(Point(x, y, 0.0), Vector(a, b, 0.0))
