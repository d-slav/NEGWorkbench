# -*- coding: utf-8 -*-
"""
Operace T10 (GL3 opcode T10, prostorova obdoba S10) - Uzavrena krivka
prolozena K body (vc. opakovaneho uzaviraciho bodu), sečnova (chord-
length) parametrizace, C2 spojitost pres sev.

Uziti (GL3): TM=T10>Q(I),K

    Q(I) - pole uzlovych bodu krivky (3D). Body Q(I) (prvni) a Q(I+K-1)
           (posledni) MUSI BYT TOTOZNE (uzavreni krivky).
    K    - pocet bodu VCETNE opakovaneho uzaviraciho bodu, K v <4,300>
           (viz G07.md - sdileno s S01/T01/S10).

Zadani uzivatele: "S01, T01, S10 a T10 volaji stejnou fortran funkci."
Presne jako T01 je tenky wrapper nad gerlib.s01.make_spline (viz jeho
docstring), T10 je tenky wrapper nad gerlib.s10.make_spline - Point/
Vector v tomto portu uz VZDY nesou x,y,z (viz geplib/__init__.py
docstring: rozdil P/Q a V/U je jen jazykova konvence GL3 prefixu, ne
odlisny Python typ), takze zadna dalsi prostorova logika navic
netreba.
"""
from gerlib.s10 import make_spline as _make_spline


def make_spatial_spline(points_ref, k):
    """T10: TM=T10>Q(I),K - uzavrena prostorova krivka K body (vc.
    opakovaneho uzaviraciho bodu), sečnova parametrizace (viz
    gerlib.s10.make_spline - shodna matematika, jen jina provenience
    oznaceni vysledne krivky)."""
    return _make_spline(points_ref, k, opcode="T10")
