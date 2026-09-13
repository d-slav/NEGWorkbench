# -*- coding: utf-8 -*-
"""
Procedura ANGL70 - ZDROJAK NENI K DISPOZICI.

Odvozeno z pouziti v S47.FOR: CALL ANGL70(Q2,QK(10),A,HFIX(0),NOJF) -
vysledek A se porovnava s 1E-3 (stupne) coby prah "tecny jsou prakticky
rovnobezne". Q2 a QK(10) jsou oba 3-slozkove vektory (tecny krivky, ne
predem normalizovane jako u A510/V220) - jde tedy o 3D obdobu A510
(viz gerlib/a510.py), stejny nezname­nkovy uhel 0..180 stupnu, jen pro
plne 3D vektory a bez predpokladu, ze uz jsou normalizovane (proto tu
normalizace ZDE probiha, na rozdil od A510).

HFIX(0) a NOJF (pravdepodobne priznak/pocitadlo chyb - stejna
konvence jako u jinych GL3 procedur s vystupnim IER/NOJF parametrem)
pro vypocet samotneho uhlu nejsou potreba a v tomto portu se
nepouzivaji - volajici (S47) je nikdy nekontroluje.

Ucel (odvozeno): Uhel dvou (obecne nenormalizovanych) 3D vektoru,
0..180 stupnu.
"""

import math


def angle_between_deg(v1, v2):
    """Neznamenkovy uhel mezi 3D vektory v1 a v2 (Vector, nebo cokoliv
    s atributy x,y,z), 0..180 stupnu. Nulovy vektor (na kteroukoliv
    stranu) dava uhel 0.0 (stejna konvence jako a510.angle_between_deg)."""
    n1 = math.sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z)
    n2 = math.sqrt(v2.x * v2.x + v2.y * v2.y + v2.z * v2.z)
    if n1 < 1e-12 or n2 < 1e-12:
        return 0.0
    cos_a = (v1.x * v2.x + v1.y * v2.y + v1.z * v2.z) / (n1 * n2)
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.degrees(math.acos(cos_a))
