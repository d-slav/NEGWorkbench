# -*- coding: utf-8 -*-
"""
Procedura Q48 (GL3 opcode Q48, prostorova obdoba P48) - Vyjmuty
uzlovy bod retezce nebo krivky.

Uziti (GL3): QM=Q48>pg,K       K - index <1,N>
             (pg = prostorovy retezec typu H / Curve, nebo prostorova
             krivka typu T / Spline)

Bod QM je K-tym uzlovym bodem retezce (pg=H) nebo krivky (pg=T) - viz
G10.md 'Q48 - Vyjmuty uzlovy bod retezce nebo krivky'. K mimo <1,N> ->
chyba (stejna konvence jako P48, puvodni IER=256).

Stejna logika jako uz existujici P48 (viz gerlib/p48.py - sdilena
pres _node_index_and_flag: "posledni bod" konvence indices/is_end,
K mimo <1,N> chyba) - JEDINY rozdil je, ze Q48 NEZTRACI Z-slozku. P48
ji na vystupu tvrde nuluje (Point(p.x, p.y, 0.0)), coz je pro rovinny
retezec/krivku (E/S) neskodne (Z uz tam je 0 tak jako tak), ale pro
prostorovy pg (H/T) by to byla skutecna ztrata dat.
"""
from gerlib.types import Point, Curve, Spline
from gerlib.p48 import _node_index_and_flag


def chain_node3(curve, k):
    """Q48 pro prostorovy retezec (H/Curve). Vraci (Point, index,
    is_end) - viz hlavicka modulu."""
    n = len(curve.points)
    k_int, idx, is_end = _node_index_and_flag(k, n)
    p = curve.points[k_int - 1]
    return Point(p.x, p.y, p.z), idx, is_end


def spline_node3(spline, k):
    """Q48 pro prostorovou krivku (T/Spline). Vraci (Point, index,
    is_end) - viz hlavicka modulu."""
    n = len(spline.points)
    k_int, idx, is_end = _node_index_and_flag(k, n)
    p = spline.points[k_int - 1]
    return Point(p.x, p.y, p.z), idx, is_end


def curve_node3(curve_or_spline, k):
    """Q48: dispatch podle typu (retezec H = Curve, krivka T = Spline),
    viz gerlib.p48.curve_node (stejny princip, jen bez ztraty Z)."""
    if isinstance(curve_or_spline, Curve):
        point, _, _ = chain_node3(curve_or_spline, k)
    elif isinstance(curve_or_spline, Spline):
        point, _, _ = spline_node3(curve_or_spline, k)
    else:
        raise TypeError(
            "Q48: ocekaval retezec (Curve/H) nebo krivku (Spline/T), "
            "dostal %r" % (type(curve_or_spline),)
        )
    return point
