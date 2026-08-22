# -*- coding: utf-8 -*-
"""
Operace H02 (GL3 opcode H02, prostorova obdoba E01/E02) - Retezec
mnozinou vyjmenovanych bodu.

Uziti (GL3): HM=H02>Q1,Q2[,Q3]...[,Q7]

Souvisly retezec HM je dan zadanymi body (2 az 7). Je-li prvni a
posledni bod totozny, vznika uzavreny retezec (viz G10.md 'H02 -
Retezec mnozinou vyjmenovanych bodu').

Zadny samostatny Fortran zdroj pro H02 neni k dispozici, ale princip
je zrejmy z E01.FOR (viz gerlib/e01.py - "definovani retezce mnozinou
bodu", tam 2D pole s poctem N; H02 je jeho prostorova obdoba s primo
vyjmenovanymi body misto pole) - stejna konstrukce Curve (points/
closed/indices/is_end), jen s UZAVRENOSTI overovanou VE 3D (vc.
Z-slozky, na rozdil od E01, ktere pracuje jen v rovine).
"""
import math

from gerlib.types import Point, Curve

_TOL = 1e-3  # stejna tolerance jako E01.FOR (1E-3)
_MAX_POINTS = 7


def make_chain3(*points):
    """H02: HM=H02>Q1,Q2[,Q3]...[,Q7] - souvisly prostorovy retezec
    (Curve) danymi body (2 az 7). Je-li prvni a posledni bod totozny
    (vc. Z), vznika uzavreny retezec."""
    n = len(points)
    if n < 2:
        raise ValueError("H02: potreba aspon 2 body (dostal %d)" % n)
    if n > _MAX_POINTS:
        raise ValueError("H02: nejvyse %d bodu (dostal %d)" % (_MAX_POINTS, n))

    for i, p in enumerate(points):
        if p is None:
            raise ValueError("H02: bod Q%d neni definovan" % (i + 1))
        if not isinstance(p, Point):
            raise TypeError("H02: Q%d neni bod (Point), ale %r" % (i + 1, p))

    first, last = points[0], points[-1]
    closed = math.sqrt(
        (last.x - first.x) ** 2 + (last.y - first.y) ** 2 + (last.z - first.z) ** 2
    ) < _TOL

    indices = []
    is_end = []
    for i in range(n):
        if i == n - 1:
            indices.append(n - 1)
            is_end.append(True)
        else:
            indices.append(i + 1)
            is_end.append(False)

    return Curve(list(points), closed=closed, indices=indices, is_end=is_end, eps=0.0)
