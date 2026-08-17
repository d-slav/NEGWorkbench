# -*- coding: utf-8 -*-
"""
Procedura P121 (GL3 opcode P21)     LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Prusecik primky s kruznici.

Uziti:   CALL P121(X1,Y1,A1,B1,X2,Y2,A2,X,Y,K,J)
         GL3:  PM=P21>L,C,K

Bod PM je prusecik primky L s kruznici C. Pro K=0 je pocitan prusecik
na zaporne strane primky, pro K=1 na kladne strane (viz G10.md 'P21 -
Prusecik primky s kruznici'). Je-li primka tecna, jsou oba body
totozne, na K nezalezi. Lezi-li primka mimo kruznici, prusecik
neexistuje - chyba (puvodni J=1210).

Puvodni P121.FOR pocita pres D611 (kolma vzdalenost stredu od primky)
a P117 (bod ve vzdalenosti rovnobezne s primkou od patniho bodu) -
matematicky presne to, co uz dela existujici gerlib.circle_geom.
line_circle_intersection (vraci prusecik(y) serazene vzestupne podle
parametru podel kladneho smeru primky) - K=0 tedy odpovida prvnimu
(zaporna/mensi t strana), K=1 druhemu (kladna/vetsi t strana) vracenemu
bodu, presne stejna konvence.
"""
from .types import Point
from .circle_geom import line_circle_intersection
from .errors import NoSolution


def line_circle_intersection_point(line, circle, k):
    """P21: PM=P21>L,C,K - prusecik primky L s kruznici C. K=0 zaporna
    strana primky, K=1 kladna strana. Chyba (NoSolution), lezi-li
    primka mimo kruznici (puvodni J=1210)."""
    points = line_circle_intersection(line, circle.center, circle.radius)
    if not points:
        raise NoSolution(
            "P21: primka lezi mimo kruznici - prusecik neexistuje (puvodni J=1210)"
        )
    if len(points) == 1:
        return Point(points[0].x, points[0].y, 0.0)
    k = int(round(k))
    chosen = points[0] if k == 0 else points[1]
    return Point(chosen.x, chosen.y, 0.0)
