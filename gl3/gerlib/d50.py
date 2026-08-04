# -*- coding: utf-8 -*-
"""
Procedura D50        LET, k.p., Uh.Hradiste
Knihovna GL3E2                                     Prosinec 1987

Ucel:    Polomer krivosti rovinne Hermitovy krivky v danem bodu.

Uziti:   DM=D50>S,P<     (rovinna krivka, K=2; D90 by byla prostorova
                          obdoba pro K=3, zatim nepotreba)

POZNAMKA k puvodnimu Fortranu - proc bez GLPAT: D50.FOR normalne
predpoklada, ze bod P uz "patri" ke krivce S (byl na ni odvozen napr.
pres P48/P42) a pozna to podle interniho priznaku IIN(10,..) - pak
staci precist ulozeny segment primo ze zaznamu (IIN(7,..)). Pokud P
ma jiny puvod (IIN(10,2).NE.IIN(10,3)), zavola se GLPAT, ktera bod P
na krivku S dohleda hledanim globalniho minima vzdalenosti pres vsechny
segmenty (viz jeji vetev 3 pro obecnou Hermitovu krivku - branch pro
ITP.NE.0,1, tedy presne nas pripad Spline).

V nasi in-memory reprezentaci nemame (a nechceme zavadet) skryty
priznak puvodu bodu - misto rozliseni dvou vetvi proto VZDY hledame
bod na krivce nejblizsi zadanemu P stejnym zpusobem, jakym by to delala
GLPAT vetev 3 (viz nearest_point_on_curve nize). Pro typicke pouziti
(P je vysledek P42/P48 na teze S, tedy uz lezi presne na krivce) to
da naprosto stejny vysledek jako puvodni "rychla cesta" pres ulozeny
index - jen bez cachovani. Zjednodusuje to implementaci a sjednocuje
oba puvodni pripady do jednoho (odsouhlaseno v konverzaci).

Zavislosti: gerlib.p42 (paty kolmic - vnitrek segmentu), gerlib.p48
(uzlove body a jejich segmentova prislusnost), gerlib.rkseg (samotny
vzorec polomeru krivosti).
"""

import math

from .p42 import foot_points
from .p48 import spline_node
from .glkoe import segment_coefficients
from .rkseg import curvature_radius_at


def nearest_point_on_curve(spline, point):
    """Najde bod na 'spline' nejblizsi vnejsimu bodu 'point' - kombinuje
    paty kolmic uvnitr segmentu (P42) a uzlove body (P48, pro pripad,
    ze P je presne v uzlu/rohu krivky, kde kolma pata nemusi existovat)
    a vybere globalni minimum vzdalenosti (jako GLPAT vetev 3).

    Vraci (segment_index_1based, t)."""
    pts = spline.points
    n = len(pts)
    if n < 2:
        raise ValueError("D50: krivka musi mit alespon 2 body")

    candidates = []  # (vzdalenost, segment_index, t)

    for seg_idx, t, foot_pt in foot_points(spline, point):
        d = math.hypot(foot_pt.x - point.x, foot_pt.y - point.y)
        candidates.append((d, seg_idx, t))

    for k in range(1, n + 1):
        node_pt, seg_idx, is_end = spline_node(spline, k)
        d = math.hypot(node_pt.x - point.x, node_pt.y - point.y)
        t = 1.0 if is_end else 0.0
        candidates.append((d, seg_idx, t))

    candidates.sort(key=lambda c: c[0])
    _, seg_idx, t = candidates[0]
    return seg_idx, t


def radius_of_curvature(spline, point):
    """D50: podepsany polomer krivosti 'spline' v bode na krivce
    nejblizsim 'point' (viz nearest_point_on_curve pro vysvetleni, proc
    bez GLPAT)."""
    seg_idx, t = nearest_point_on_curve(spline, point)
    p0 = spline.points[seg_idx - 1]
    p1 = spline.points[seg_idx]
    t0, t1 = spline.segment_tangent_pair(seg_idx - 1)
    coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
    return curvature_radius_at(coeffs, t)
