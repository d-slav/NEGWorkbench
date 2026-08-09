# -*- coding: utf-8 -*-
"""
GL3 opcode C33

Ucel:    Kruznice daneho polomeru tecna k primce a kruznici.

Uziti:   CM=C33>L,C,D,KKK

Kruznice CM o polomeru D se tecne dotyka primky L a kruznice C.
    K3=0 vlevo od L, K3=1 vpravo od L (konvence L20/V230)
    K2=0 dotyk vnitrni s C, K2=1 dotyk vnejsi s C
    K1 - viz POZNAMKA nize (nejista interpretace)
V pripadech, kdy kruznice nemuze byt vypoctena, je hlasena chyba.

POZNAMKA k baleni KKK: stejny predpoklad jako C32/C34 - KKK = 100*K3 +
10*K2 + K1.

POZOR - K1 NENI jednoznacne odvoditelne jen z popisu: zadani rika
"kruznici lezici na zaporne strane primky ziskame K1=0, na kladne
K1=1", ale STRANA primky uz je urcena K3 (leva/prava) - oba body,
mezi kterymi K1 rozhoduje, lezi na TEZE (K3 vybrane) rovnobezne
primce, takze nemohou lezet na ruznych stranach L samotne. Nejlogictejsi
vysvetleni: po posunuti L o D (K3) a "redukci" kruznice C na polomer
|R-D| nebo R+D (K2) muze mit posunuta primka s touto redukovanou
kruznici AZ DVA pruseciky - K1 mezi nimi rozhoduje. Tady se K1
interpretuje jako vyber mezi temito dvema kandidaty podle znamenka
parametru podel smeru primky L (K1=0 mensi/"zapornejsi" parametr,
K1=1 vetsi/"kladnejsi") - odpovida to terminologii "zaporna/kladna
strana", i kdyz doslova nejde o stranu primky, ale o polohu podel ni.

TOHLE JE NEJISTE bez zdrojoveho kodu C33.FOR - pokud bude k dispozici,
overit/opravit. Do te doby otestovano jen na tom, ze VYSLEDEK je
geometricky spravny (tecna k L i C, spravny polomer) - K1 vyber sam
neni nezavisle overitelny bez originalu.

Algoritmus: primka rovnobezna s L posunuta o D na stranu K3 (L20),
polomer "redukovane" kruznice kolem stredu C je |R-D| (K2=0) nebo R+D
(K2=1), prusecik posunute primky s touto redukovanou kruznici dava
kandidaty na stred CM (circle_geom.line_circle_intersection).
"""

from .types import Circle
from .l20 import parallel_line
from .circle_geom import line_circle_intersection


def tangent_to_line_and_circle(line, circle, radius, kkk):
    """C33: kruznice polomeru 'radius' tecna k 'line' a 'circle'.
    'kkk' je baleny vyber strany/dotyku/kandidata - viz hlavicka
    modulu (K1 je nejista interpretace bez zdrojoveho kodu)."""
    kkk_int = int(round(kkk))
    k1 = kkk_int % 10
    k2 = (kkk_int // 10) % 10
    k3 = (kkk_int // 100) % 10

    offset_line = parallel_line(line, radius, k3)
    target_radius = circle.radius + radius if k2 else abs(circle.radius - radius)

    candidates = line_circle_intersection(offset_line, circle.center, target_radius)
    if not candidates:
        raise ValueError(
            "C33: kruznici nelze sestrojit - posunuta primka a redukovana "
            "kruznice se neprotinaji"
        )
    if len(candidates) == 1:
        center = candidates[0]
    else:
        # candidates jsou serazene vzestupne podle parametru t podel primky
        center = candidates[1] if k1 else candidates[0]

    return Circle(center, radius)
