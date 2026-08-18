# -*- coding: utf-8 -*-
"""
Procedura V37 (interni pomocna procedura, NENI GL3 opcode)
Knihovna GL3E2                                      Unor 1983

Ucel:    Jednotkovy tecny vektor 2D krivky v obecnem bode.

Zdrojovy V37.FOR nebyl dodan, ale jeho ucel je jednoznacne odvoditelny
z V34.FOR, ktere ho vola jako prvni krok pred rotaci vysledku o 90
stupnu (V231/gerlib.v230.perpendicular_vector) - musi tedy vracet
JEDNOTKOVY TECNY vektor krivky v danem bode (aby po pootoceni o 90
stupnu vysla jednotkova normala, presne jak V34 dokumentuje).

Implementace: bod P se nejdriv lokalizuje na krivce S (segment + t,
stejna logika jako D31/index_parameter - viz gerlib.d31), pak se v tomto
miste vyhodnoti 1. derivace segmentu (GLFUN/gerlib.glfun.evaluate,
order=1) a vysledek se normalizuje (V220/gerlib.v220.unit_vector).
Chyba, nelezi-li P na S (puvodni V34 IER=272).
"""
import math

from .types import Vector
from .d31 import index_parameter
from .glkoe import segment_coefficients
from .glfun import evaluate
from .v220 import unit_vector


def _segment_and_t(spline, idx):
    """Prevede indexparametr (viz D31) na (segment_1based, t) - segment
    N (= pocet uzlu) je uzaverovy segment uzavrene krivky (posledni
    uzel -> prvni uzel), existuje jen je-li spline.closed."""
    n = len(spline.points)
    max_segment = n if spline.closed else n - 1

    seg = int(math.floor(idx))
    t = idx - seg
    if seg >= max_segment:
        seg = max_segment
        t = 1.0
    if seg < 1:
        seg = 1
        t = 0.0
    return seg, t


def _segment_endpoints_and_tangents(spline, seg):
    """(p0, p1, t0, t1) pro 1-based segment 'seg' - vc. uzaveroveho
    segmentu uzavrene krivky (seg == pocet uzlu)."""
    n = len(spline.points)
    if seg < n:
        p0, p1 = spline.points[seg - 1], spline.points[seg]
        t0, t1 = spline.segment_tangent_pair(seg - 1)
    else:
        p0, p1 = spline.points[n - 1], spline.points[0]
        t0, t1 = spline.tangents[n - 1], spline.tangents[0]
    return p0, p1, t0, t1


def curve_tangent_at_point(spline, point):
    """V37: jednotkovy tecny vektor krivky 'spline' v bode 'point'
    (bod musi lezet na krivce - viz index_parameter, jinak ValueError,
    puvodni IER=272 z V34)."""
    idx = index_parameter(spline, point)
    seg, t = _segment_and_t(spline, idx)
    p0, p1, t0, t1 = _segment_endpoints_and_tangents(spline, seg)
    coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
    dx, dy = evaluate(coeffs, t, order=1)
    ux, uy = unit_vector(dx, dy)
    return Vector(ux, uy, 0.0)
