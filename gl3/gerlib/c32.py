# -*- coding: utf-8 -*-
"""
GL3 opcode C32

Ucel:    Kruznice daneho polomeru tecna ke dvema primkam.

Uziti:   CM=C32>L1,L2,D,KK

Kruznice CM o polomeru D se tecne dotyka primek L1 a L2. Vyber strany:
    K2=0 vlevo od L1, K2=1 vpravo od L1  (stejna konvence jako L20/V230:
    "vlevo" = pri pohledu v kladnem smeru primky)
    K1=0 vlevo od L2, K1=1 vpravo od L2
Jsou-li L1 a L2 rovnobezne, je hlasena chyba.

POZNAMKA k baleni KK: zadny Fortran zdroj nedodan - odvozeno z popisu.
Predpoklada se dekadicke baleni "cislo K spolu urcuje svou pozici
cifry" - KK = 10*K2 + K1 (K2 je vyssi/tucty, K1 nizsi/jednotky,
odpovida poradi K2,K1 v popisu i tomu, ze K2 patri "vetsimu" indexu).
Pokud bude zdroj k dispozici, tenhle predpoklad snadno overit/opravit.

Algoritmus: primka rovnobezna s L1 posunuta o D na stranu K2 (L20),
primka rovnobezna s L2 posunuta o D na stranu K1, jejich prusecik je
stred CM (P20/line_intersection - uz hlasi chybu pro rovnobezne
primky, presne jak pozadovano).
"""

from .types import Circle
from .l20 import parallel_line
from .p20 import line_intersection


def tangent_to_two_lines(line1, line2, radius, kk):
    """C32: kruznice polomeru 'radius' tecna k 'line1' a 'line2'.
    'kk' je baleny vyber stran - viz hlavicka modulu."""
    kk_int = int(round(kk))
    k1 = kk_int % 10
    k2 = (kk_int // 10) % 10

    offset1 = parallel_line(line1, radius, k2)
    offset2 = parallel_line(line2, radius, k1)
    center = line_intersection(offset1, offset2)
    return Circle(center, radius)
