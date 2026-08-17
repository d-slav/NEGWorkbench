# -*- coding: utf-8 -*-
"""
Procedura P58
Unor 1985

Ucel:    Bod od bodu po retezci E do vzdalenosti.

Uziti:   PM=P58>>P,E,D[,K]

Bod PM lezi na retezci E ve vzdalenosti abs(D) od bodu P (merene po
retezci). Pro nezaporne D je PM vynasen od P ve smeru orientace
retezce pro K=1 (default), proti smeru orientace pro K=0 (viz G10.md
'P58 - Bod od bodu po retezci do vzdalenosti', Fortran P58.FOR).

Nelezi-li P primo na retezci E, hleda se nejblizsi bod na E (stejna
logika jako P54/gerlib.d31.index_parameter - puvodni P58.FOR ji vola,
neni-li bod P jiz indexovanym bodem retezce E). Presahne-li pozadovana
vzdalenost konec OTEVRENEHO retezce (v pozadovanem smeru), je hlasena
chyba (IER=534); UZAVRENY retezec misto toho pokracuje pres uzaver
(wraparound), pripadne i vicekrat dokola.

Parametry:
    P (Point): Vychozi bod (nemusi byt uzel retezce)
    E (Curve): Retezec
    D (float): Pozadovana vzdalenost (bere se abs(D))
    K (int, volitelne): 1 = ve smeru orientace retezce (default),
                         0 = proti smeru orientace retezce
                         (viz hlavicka modulu - zaporne D smer obraci,
                         stejne jako v puvodnim Fortranu)
"""
import math

from .types import Point, Curve
from .p13 import interpolate_point

_TOL = 1e-6


def _segment_param(point, a, b):
    """Projekce bodu na usecku a->b: (t, kolma vzdalenost)."""
    dx, dy = b.x - a.x, b.y - a.y
    len2 = dx * dx + dy * dy
    if len2 < 1e-24:
        return 0.0, math.hypot(point.x - a.x, point.y - a.y)
    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / len2
    px, py = a.x + t * dx, a.y + t * dy
    return t, math.hypot(point.x - px, point.y - py)


def _locate_on_chain(curve, point):
    """Vrati (j, t): bod 'point' lezi na usecce curve.points[j]->[j+1]
    v parametru t (0<=t<=1), j je 0-based index do curve.points."""
    pts = curve.points
    n = len(pts)

    for i, p in enumerate(pts):
        if math.hypot(point.x - p.x, point.y - p.y) < _TOL:
            if i == n - 1:
                return n - 2, 1.0
            return i, 0.0

    best = None
    for i in range(n - 1):
        t, dist = _segment_param(point, pts[i], pts[i + 1])
        if dist < _TOL and -_TOL <= t <= 1.0 + _TOL:
            t_clamped = max(0.0, min(1.0, t))
            err = dist + abs(t - t_clamped)
            if best is None or err < best[0]:
                best = (err, (i, t_clamped))

    if best is not None:
        return best[1]

    raise ValueError(
        "P58: bod P (%g, %g) nelezi na retezci E (puvodni IER=533)"
        % (point.x, point.y)
    )


def _seg_len(pts, i):
    return math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y)


def point_at_distance_along_chain(point, curve, distance, k=1):
    """P58: PM=P58>P,E,D,K - bod na retezci E ve vzdalenosti abs(D) od
    bodu P (viz hlavicka modulu)."""
    if not isinstance(curve, Curve):
        raise TypeError("P58: druhy argument musi byt retezec (Curve), dostal %r" % (curve,))
    pts = curve.points
    n = len(pts)
    if n < 2:
        raise ValueError("P58: retezec ma min nez 2 body")

    k = int(round(k))
    j, t = _locate_on_chain(curve, point)

    signed = -distance if k == 0 else distance
    forward = signed >= 0.0
    remaining_dist = abs(signed)

    max_laps = 10000 * n  # ochrana proti nekonecne smycce na degenerovanem (nulove dlouhem) uzavrenem retezci

    if forward:
        seg_len = _seg_len(pts, j)
        remaining_on_seg = (1.0 - t) * seg_len
        if remaining_on_seg >= remaining_dist:
            new_t = t + (remaining_dist / seg_len if seg_len > _TOL else 0.0)
            return interpolate_point(pts[j], pts[j + 1], new_t)
        remaining_dist -= remaining_on_seg

        idx = j + 1
        for _ in range(max_laps):
            if idx >= n - 1:
                if not curve.closed:
                    raise ValueError(
                        "P58: pozadovana vzdalenost presahuje konec "
                        "otevreneho retezce E (puvodni IER=534)"
                    )
                idx = 0
            seg_len = _seg_len(pts, idx)
            if seg_len >= remaining_dist:
                new_t = remaining_dist / seg_len if seg_len > _TOL else 0.0
                return interpolate_point(pts[idx], pts[idx + 1], new_t)
            remaining_dist -= seg_len
            idx += 1
        raise ValueError("P58: prekrocen maximalni pocet obehnuti uzavreneho retezce")

    # proti smeru orientace retezce (K=0, nebo zaporne D pri K=1)
    seg_len = _seg_len(pts, j)
    remaining_on_seg = t * seg_len
    if remaining_on_seg >= remaining_dist:
        new_t = t - (remaining_dist / seg_len if seg_len > _TOL else 0.0)
        return interpolate_point(pts[j], pts[j + 1], new_t)
    remaining_dist -= remaining_on_seg

    idx = j - 1
    for _ in range(max_laps):
        if idx < 0:
            if not curve.closed:
                raise ValueError(
                    "P58: pozadovana vzdalenost presahuje pocatek "
                    "otevreneho retezce E (puvodni IER=534)"
                )
            idx = n - 2
        seg_len = _seg_len(pts, idx)
        if seg_len >= remaining_dist:
            new_t = 1.0 - (remaining_dist / seg_len if seg_len > _TOL else 0.0)
            return interpolate_point(pts[idx], pts[idx + 1], new_t)
        remaining_dist -= seg_len
        idx -= 1
    raise ValueError("P58: prekrocen maximalni pocet obehnuti uzavreneho retezce")
