# -*- coding: utf-8 -*-
"""
Operace Q15 (NEG jazykova specifikace) - Bod parametrem ke dvema
bodum.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'Q15 - Bod parametrem ke
dvema bodum' a zadani uzivatele):

    QM=Q15>Q1,Q2,D

    Q1, Q2 = body (Point)
    D      = skalarni vyraz - parametr na primce Q1-Q2:
             QM = Q1 + (Q2-Q1)*D
             D=0 -> QM totozny s Q1, D=1 -> QM totozny s Q2, D=-1 -> QM
             symetricky k Q2 se stredem symetrie Q1, atd. (extrapolace
             mimo usecku Q1-Q2 je platna, zadne omezeni na D).
"""
from gerlib.types import Point


def make_point_by_parameter(q1, q2, d):
    """Q15: QM=Q15>Q1,Q2,D - bod na primce Q1-Q2 dany parametrem D
    (QM = Q1 + (Q2-Q1)*D)."""
    return Point(
        q1.x + (q2.x - q1.x) * d,
        q1.y + (q2.y - q1.y) * d,
        q1.z + (q2.z - q1.z) * d,
    )
