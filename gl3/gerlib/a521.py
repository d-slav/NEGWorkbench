# -*- coding: utf-8 -*-
"""
Procedura A521 (rekonstrukce z pouziti v P85.FOR)

Ucel:    Uhel vektoru od kladneho smeru osy X, ve stupnich, v rozsahu
         [0, 360).
"""

import math


def polar_angle_deg(x, y):
    """Uhel vektoru (x, y) od kladneho smeru osy X, ve stupnich, [0, 360)."""
    return math.degrees(math.atan2(y, x)) % 360.0
