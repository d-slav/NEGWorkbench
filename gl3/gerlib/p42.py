# -*- coding: utf-8 -*-
"""
Procedura P42        LET, n.p., Uh.Hradiste (P.Franc)
Knihovna GL3E2                                     Unor 1983

Ucel:    Patni bod na krivce (2D).

Uziti:   PM=P42>P,S,K<
         P - vnejsi bod, S - krivka (Spline), K - poradove cislo
             (1-based) hledaneho patniho bodu, pokud jich krivka ma
             vic (viz nize)

Chyby:   K<1                          -> puvodni IER=228
         mene nez K patnich bodu      -> puvodni IER=230

Algoritmus (1:1 podle P42.FOR): pro kazdy segment krivky (kubicky
Hermituv kus mezi sousednimi uzly) se hleda parametr t, ve kterem je
spojnice bodu P a bodu na segmentu C(t) kolma na tecnu segmentu -
tedy koreny rovnice
    d/dt [ (C(t)-P) . (C(t)-P) ] = 0
coz je (protoze C(t) je kubika) polynom 5. stupne v t. Jeho koeficienty
D(1..6) jsou v puvodnim zdroji sestaveny primo z Hermitovych koeficientu
segmentu (viz _distance_derivative_poly nize - odvozeno rozepsanim
konvoluce C'(t)*(C(t)-P), overeno clen po clenu proti puvodnimu kodu).

Krivka muze mit vic nez jeden patni bod (kazdy segment muze prispet 0
az nekolik korenu v <0,1>) - K vybira, ktery z nich (v poradi, jak je
prochazi segment po segmentu) se ma vratit. Na hranici dvou segmentu
(koren t=1 na segmentu I, ktery neni posledni) se zahodi duplicitni
koren - stejny bod bude nalezen znovu jako t=0 na segmentu I+1.

Zavislosti: gerlib.glkoe (Hermitovy koeficienty), gerlib.glfun
(vyhodnoceni bodu na segmentu), gerlib.glply (hledani realnych
korenu - viz jeho hlavicka, proc neni 1:1 port puvodniho GLPLY).
"""

from .types import Point
from .glkoe import segment_coefficients
from .glfun import evaluate
from .glply import real_roots_in_range

_RMN = -1e-4
_RMX = 1.0 + 1e-4


def _distance_derivative_poly(coeffs, wx, wy):
    """Koeficienty D(1..6) polynomu d/dt|C(t)-P|^2 (sestupne, pro
    real_roots_in_range: [D6,D5,D4,D3,D2,D1]) - viz hlavicka modulu."""
    (a3x, a2x, a1x, _a0x), (a3y, a2y, a1y, _a0y) = coeffs

    d6 = 3.0 * (a3x * a3x + a3y * a3y)
    d5 = 5.0 * (a3x * a2x + a3y * a2y)
    d4 = 4.0 * (a3x * a1x + a3y * a1y) + 2.0 * (a2x * a2x + a2y * a2y)
    d3 = 3.0 * (a3x * wx + a3y * wy + a2x * a1x + a2y * a1y)
    d2 = 2.0 * (a2x * wx + a2y * wy) + a1x * a1x + a1y * a1y
    d1 = a1x * wx + a1y * wy

    return [d6, d5, d4, d3, d2, d1]


def foot_points(spline, point):
    """Vsechny paty kolmic z 'point' na 'spline', v poradi segment po
    segmentu (jak je hleda P42.FOR) - seznam (segment_index, t, Point),
    segment_index je 1-based (1..N-1)."""
    pts = spline.points
    n = len(pts)
    results = []
    for i in range(1, n):  # i = 1-based cislo segmentu (mezi body i, i+1)
        p0, p1 = pts[i - 1], pts[i]
        t0, t1 = spline.segment_tangent_pair(i - 1)
        coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
        wx = coeffs[0][3] - point.x  # a0x - Px
        wy = coeffs[1][3] - point.y  # a0y - Py
        poly = _distance_derivative_poly(coeffs, wx, wy)
        roots = real_roots_in_range(poly, _RMN, _RMX)

        if roots and abs(roots[-1] - 1.0) < 1e-5 and (i + 1) != n:
            # koren na konci segmentu, ktery neni posledni - stejny bod
            # se najde znovu jako t=0 na nasledujicim segmentu
            roots = roots[:-1]

        for t in roots:
            t_clamped = min(1.0, max(0.0, t))
            xy = evaluate(coeffs, t_clamped, order=0)
            results.append((i, t, Point(xy[0], xy[1], 0.0)))

    return results


def nearest_point(spline, point, k):
    """P42: K-ty (1-based) patni bod kolmice z 'point' na 'spline'."""
    k_int = int(round(k))
    if k_int < 1:
        raise ValueError("P42: K musi byt >= 1 (puvodni chyba 228), dostal %r" % (k,))

    feet = foot_points(spline, point)
    if k_int > len(feet):
        raise ValueError(
            "P42: krivka ma jen %d patni(ch) bod(u), pozadovano K=%d "
            "(puvodni chyba 230)" % (len(feet), k_int)
        )
    return feet[k_int - 1][2]
