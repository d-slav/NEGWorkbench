# -*- coding: utf-8 -*-
"""
Procedura GLPRU        LET, k.p., Uh.Hradiste
Knihovna GL3E2                                     Unor 1983

Ucel:    Vypocet pruseciku 2D splinu s primkou (nebo 3D splinu s
         rovinou - K=3, zatim nepotreba).

Uziti:   CALL GLPRU(N,K,R,M,L,I,P,Q,JF)
    N   pocet bodu splinu
    K   pocet rozmeru (2)
    R(K+1)  koeficienty implicitni rovnice primky (viz implicit_line)
    M   poradi hledaneho pruseciku
    I,P,Q,JF  vystup: interval, parametr, souradnice, chyba

Algoritmus (1:1 podle GLPRU.FOR, jen bez GLDPL3 - viz nize):

Pro kazdy segment se implicitni rovnice primky dosadi za x,y do
kubickych Hermitovych koeficientu segmentu (GLKOE) - vysledkem je
kubicky polynom v t (koeficienty R1, sestupne). Jeho realne koreny v
<-1e-5, 1.00001> jsou kandidati na pruseciky.

Dve vrstvy deduplikace (obe "ponechej drivejsi vyskyt, zahod pozdejsi
duplicitu"):
  1) koren na konci segmentu (t priblizne 1.0), ktery neni posledni
     segment, se zahodi - stejny bod se najde znovu jako t=0 na
     nasledujicim segmentu (stejny trik jako v p42.py)
  2) sousedni koreny (v poradi t), jejichz body na krivce jsou blize
     nez 0.001, se povazuji za tentyz bod - ponecha se drivejsi,
     pozdejsi se zahodi. Tahle druha vrstva funguje i PRES hranici
     segmentu (puvodni "Q4" - posledni prijaty bod predchoziho
     segmentu se porovnava s prvnim kandidatem noveho segmentu).

POZNAMKA - proc bez GLDPL3: puvodni GLPRU pouziva specializovany
resic KUBICKE rovnice (GLDPL3, nedodan). Misto nej pouzivame nasi uz
existujici obecnou funkci real_roots_in_range (postavenou pro P42 na
kvintiku, funguje ale pro libovolny stupen vc. kubiky) - stejny
kontrakt (vsechny realne koreny v intervalu, vzestupne), jina cesta k
vysledku.
"""

import math

from .types import Point
from .glkoe import segment_coefficients
from .glfun import evaluate
from .glply import real_roots_in_range

_DMEZ = -1e-5
_HMEZ = 1.00001


def implicit_line(line):
    """Implicitni rovnice primky f(x,y) = rr[0]*x + rr[1]*y + rr[2] = 0
    sestavena z parametricke primky (bod (X,Y), smer (A,B)) - viz
    RR pole v P22.FOR."""
    X, Y = line.origin.x, line.origin.y
    A, B = line.direction.x, line.direction.y
    return (-B, A, X * B - Y * A)


def _segment_line_poly(coeffs, rr):
    """Koeficienty (sestupne, [c3,c2,c1,c0]) kubickeho polynomu
    f(C(t)) = rr . (Cx(t), Cy(t), 1) pro segment s Hermitovymi
    koeficienty 'coeffs' a implicitni primku 'rr'."""
    (a3x, a2x, a1x, a0x), (a3y, a2y, a1y, a0y) = coeffs
    rr0, rr1, rr2 = rr
    c3 = rr0 * a3x + rr1 * a3y
    c2 = rr0 * a2x + rr1 * a2y
    c1 = rr0 * a1x + rr1 * a1y
    c0 = rr0 * a0x + rr1 * a0y + rr2
    return [c3, c2, c1, c0]


def _dist2d(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def line_curve_intersections(spline, line):
    """Vsechny pruseciky 'line' s 'spline', v poradi segment po
    segmentu / rostouciho parametru - seznam (segment_index_1based, t,
    Point). Viz hlavicka modulu pro deduplikaci."""
    rr = implicit_line(line)
    pts = spline.points
    n = len(pts)
    results = []
    last_accepted_xy = None  # Q4 - posledni prijaty bod predchoziho segmentu

    for i in range(1, n):
        p0, p1 = pts[i - 1], pts[i]
        t0, t1 = spline.segment_tangent_pair(i - 1)
        coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
        poly = _segment_line_poly(coeffs, rr)
        roots = real_roots_in_range(poly, _DMEZ, _HMEZ)

        if roots and (i + 1) != n and abs(1.0 - roots[-1]) < 1e-5:
            roots = roots[:-1]
        if not roots:
            continue

        candidates = [(t, evaluate(coeffs, t, order=0)) for t in roots]

        # deduplikace sousednich korenu uvnitr segmentu (ponech drivejsi)
        merged = [candidates[0]]
        for t, xy in candidates[1:]:
            if _dist2d(xy, merged[-1][1]) < 0.001:
                continue
            merged.append((t, xy))

        # deduplikace pres hranici segmentu (Q4)
        if last_accepted_xy is not None and _dist2d(merged[0][1], last_accepted_xy) < 0.001:
            merged = merged[1:]
        if not merged:
            continue

        for t, xy in merged:
            results.append((i, t, Point(xy[0], xy[1], 0.0)))
        last_accepted_xy = merged[-1][1]

    return results
