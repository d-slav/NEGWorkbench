# -*- coding: utf-8 -*-
"""
Procedura A510 - ZDROJAK NENI K DISPOZICI.

Odvozeno z pouziti v P85.FOR: CALL A510(XX,YY,XV1,YV1,ANGL,...) - vysledek
ANGL se porovnava s 0 a 180 stupni, oba vstupni vektory jsou uz predem
normalizovane (V220). Z toho jednoznacne plyne, ze jde o NEZNAMENKOVY uhel
mezi dvema vektory v rozsahu 0..180 stupnu - matematicky nedvojznacna
operace, nezavisla na tom, jak presne byla A510 uvnitr napsana.

Ucel (odvozeno): Uhel dvou vektoru (0..180 stupnu).
"""

import math


def angle_between_deg(x1, y1, x2, y2):
    """Neznamenkovy uhel mezi vektory (x1,y1) a (x2,y2), 0..180 stupnu."""
    n1 = math.hypot(x1, y1)
    n2 = math.hypot(x2, y2)
    if n1 < 1e-12 or n2 < 1e-12:
        return 0.0
    cos_a = (x1 * x2 + y1 * y2) / (n1 * n2)
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.degrees(math.acos(cos_a))
