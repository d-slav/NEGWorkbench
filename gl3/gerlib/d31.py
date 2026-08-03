# -*- coding: utf-8 -*-
"""
Procedura D31 (GL3 opcode D31)      n.p. LET Kunovice
Knihovna GL3E2                                      Brezen 1984

Ucel:    Vyjmuty indexparametr bodu retezce nebo krivky.

Uziti:   DM=D31>E,P<     DM=D31>S,P<

Parametry: E/S  retezec (Curve) nebo krivka (Spline)
           P    bod lezici na krivce
           DM   indexparametr = celociselny index segmentu + zlomek <0,1>
                (odpovida P54.FOR pro retezec E, GLPAT pro krivku S)

Poznamka: telo P54/GLPAT neni k dispozici - pocita se primo z nase
          reprezentace Curve/Spline. Pro retezec pouziva curve.indices[i]
          jako celocast (konvence E01), pro splajn 1-based cislo segmentu.
          Chyba odpovida puvodnimu IER=369.
"""

import math

from .types import Point, Curve, Spline

_TOL = 1e-6


def _hermite_xy(p0, p1, t0, t1, t):
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    x = h00 * p0.x + h10 * t0.x + h01 * p1.x + h11 * t1.x
    y = h00 * p0.y + h10 * t0.y + h01 * p1.y + h11 * t1.y
    return x, y


def _hermite_dxy(p0, p1, t0, t1, t):
    dh00 = 6 * t ** 2 - 6 * t
    dh10 = 3 * t ** 2 - 4 * t + 1
    dh01 = -6 * t ** 2 + 6 * t
    dh11 = 3 * t ** 2 - 2 * t
    x = dh00 * p0.x + dh10 * t0.x + dh01 * p1.x + dh11 * t1.x
    y = dh00 * p0.y + dh10 * t0.y + dh01 * p1.y + dh11 * t1.y
    return x, y


def _find_hermite_t(p0, p1, t0, t1, target):
    """Najde t in <0,1>, kde Hermituv segment protina 'target' (Newton +
    fallback scan). Vraci None, pokud bod na segment nespadá."""
    t = 0.5
    for _ in range(40):
        x, y = _hermite_xy(p0, p1, t0, t1, t)
        dx = x - target.x
        dy = y - target.y
        if dx * dx + dy * dy < _TOL * _TOL:
            return max(0.0, min(1.0, t))
        ddx, ddy = _hermite_dxy(p0, p1, t0, t1, t)
        denom = ddx * ddx + ddy * ddy
        if denom < 1e-24:
            break
        dt = (dx * ddx + dy * ddy) / denom
        t = max(0.0, min(1.0, t - dt))

    best_t, best_d = 0.0, float("inf")
    for k in range(101):
        tt = k / 100.0
        x, y = _hermite_xy(p0, p1, t0, t1, tt)
        d = (x - target.x) ** 2 + (y - target.y) ** 2
        if d < best_d:
            best_d, best_t = d, tt
    if best_d < (_TOL * 10) ** 2:
        return best_t
    return None


def _segment_param(point, a, b):
    """Projekce bodu na usecku a->b: (t, kolma vzdalenost)."""
    dx = b.x - a.x
    dy = b.y - a.y
    len2 = dx * dx + dy * dy
    if len2 < 1e-24:
        return 0.0, math.hypot(point.x - a.x, point.y - a.y)
    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / len2
    px = a.x + t * dx
    py = a.y + t * dy
    return t, math.hypot(point.x - px, point.y - py)


def _index_on_chain(curve, point):
    pts = curve.points
    n = len(pts)
    if n < 2:
        raise ValueError("D31/IER=369: retezec ma mene nez 2 body")

    for i, p in enumerate(pts):
        if math.hypot(point.x - p.x, point.y - p.y) < _TOL:
            return float(curve.indices[i])

    best = None
    segments = n - 1
    if curve.closed:
        segments = n
    for i in range(segments):
        j = (i + 1) % n
        t, dist = _segment_param(point, pts[i], pts[j])
        if dist < _TOL and -_TOL <= t <= 1.0 + _TOL:
            t_clamped = max(0.0, min(1.0, t))
            value = float(curve.indices[i]) + t_clamped
            err = dist + abs(t - t_clamped)
            if best is None or err < best[0]:
                best = (err, value)

    if best is not None:
        return best[1]

    raise ValueError(
        "D31/IER=369: bod (%g, %g) nelezi na retezci" % (point.x, point.y)
    )


def _index_on_spline(spline, point):
    pts = spline.points
    n = len(pts)
    if n < 2:
        raise ValueError("D31/IER=369: krivka ma mene nez 2 uzly")

    for i, p in enumerate(pts):
        if math.hypot(point.x - p.x, point.y - p.y) < _TOL:
            if i == n - 1 and not spline.closed:
                return float(n - 1) + 1.0
            return float(i + 1)

    best = None
    segments = n - 1
    if spline.closed:
        segments = n
    for i in range(segments):
        j = (i + 1) % n
        if i < n - 1:
            t0, t1 = spline.segment_tangent_pair(i)
        else:
            t0 = spline.tangents[n - 1]
            t1 = spline.tangents[0]
        t = _find_hermite_t(pts[i], pts[j], t0, t1, point)
        if t is not None:
            x, y = _hermite_xy(pts[i], pts[j], t0, t1, t)
            err = math.hypot(x - point.x, y - point.y)
            value = float(i + 1) + t
            if best is None or err < best[0]:
                best = (err, value)

    if best is not None:
        return best[1]

    raise ValueError(
        "D31/IER=369: bod (%g, %g) nelezi na krivce" % (point.x, point.y)
    )


def index_parameter(curve_or_spline, point):
    """Indexparametr bodu na retezci (Curve/E) nebo krivce (Spline/S).

    Vraci skalar: celociselna cast = index segmentu (E01 indices pro
    retezec, 1..N-1 pro splajn), desetinna cast = parametr 0..1 na tom
    segmentu."""
    if not isinstance(point, Point):
        raise TypeError("D31: druhy argument musi byt bod (Point), dostal %r" % (point,))

    if isinstance(curve_or_spline, Curve):
        return _index_on_chain(curve_or_spline, point)
    if isinstance(curve_or_spline, Spline):
        return _index_on_spline(curve_or_spline, point)

    raise TypeError(
        "D31: prvni argument musi byt retezec (Curve) nebo krivka (Spline), dostal %r"
        % (curve_or_spline,)
    )
