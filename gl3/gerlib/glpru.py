# -*- coding: utf-8 -*-
"""
Procedura GLPRU        LET, k.p., Uh.Hradiste
Knihovna GL3E2                                     Unor 1983

Ucel:    Vypocet pruseciku 2D splinu s primkou NEBO 3D splinu s
         rovinou (K=2 nebo K=3 - viz zdrojovy GLPRU.FOR, ktery je
         SPOLECNY pro oba pripady, jen parametrizovany K; volaji ho
         P22.FOR - primka/2D krivka, K=2 - a Q38.FOR - rovina/3D
         krivka, K=3).

Uziti:   CALL GLPRU(N,K,R,M,L,I,P,Q,JF)
    N   pocet bodu splinu
    K   pocet rozmeru (2 nebo 3)
    R(K+1)  koeficienty implicitni rovnice primky/roviny (viz
            implicit_line / implicit_plane)
    M   poradi hledaneho pruseciku
    I,P,Q,JF  vystup: interval, parametr, souradnice, chyba

Algoritmus (1:1 podle GLPRU.FOR, jen bez GLDPL3 - viz nize), overeno
proti dodanemu zdroji (K=2 vetev jiz drive, K=3 vetev nove pri portu
Q38 - viz geplib/q38.py, ktery uz GLPRU jen POUZIVA):

Pro kazdy segment se implicitni rovnice primky/roviny dosadi za
x,y[,z] do kubickych Hermitovych koeficientu segmentu (GLKOE) -
vysledkem je kubicky polynom v t (koeficienty R1, sestupne). Jeho
realne koreny v <-1e-5, 1.00001> jsou kandidati na pruseciky.

Dve vrstvy deduplikace (obe "ponechej drivejsi vyskyt, zahod pozdejsi
duplicitu"), OBE zalozene na skutecne (K-rozmerne) vzdalenosti bodu na
krivce (< 0.001), NE na blizkosti parametru t:
  1) koren na konci segmentu (t priblizne 1.0), ktery neni posledni
     segment, se zahodi - stejny bod se najde znovu jako t=0 na
     nasledujicim segmentu (stejny trik jako v p42.py)
  2) sousedni koreny (v poradi t) v RAMCI JEDNOHO SEGMENTU, jejichz
     body na krivce jsou blize nez 0.001, se povazuji za tentyz bod -
     ponecha se drivejsi, pozdejsi se zahodi (puvodni Fortran to resi
     explicitne pro az 3 koreny kubiky dvema porovnanimi - DIST(Q2,Q3)
     a nasledne DIST(Q1,Q2); obecny "drz posledni prijaty, porovnej
     kazdy dalsi jen s nim" scan dava matematicky STEJNY vysledek pro
     libovolnou kombinaci az 3 blizkych/vzdalenych korenu, overeno
     rozborem vsech pripadu).
  3) TAHLE druha vrstva navic funguje i PRES hranici segmentu (puvodni
     "Q4" - posledni prijaty bod predchoziho segmentu se porovnava s
     prvnim prezivsim kandidatem noveho segmentu).

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
_POINT_TOL = 0.001  # DIST(Qi,Qj)<0.001 - jak uvnitr segmentu, tak pres Q4


def implicit_line(line):
    """Implicitni rovnice primky f(x,y) = rr[0]*x + rr[1]*y + rr[2] = 0
    sestavena z parametricke primky (bod (X,Y), smer (A,B)) - viz
    RR pole v P22.FOR."""
    X, Y = line.origin.x, line.origin.y
    A, B = line.direction.x, line.direction.y
    return (-B, A, X * B - Y * A)


def implicit_plane(plane):
    """Implicitni rovnice roviny f(x,y,z) = rr[0]*x+rr[1]*y+rr[2]*z+
    rr[3] = 0 sestavena z bodu+normaly (viz R(K,JC3), K=1..4, v
    Q38.FOR - nase Plane uklada origin+normal misto primo implicitnich
    koeficientu, prevod je: rr = (normal, -dot(normal, origin))."""
    nx, ny, nz = plane.normal.x, plane.normal.y, plane.normal.z
    ox, oy, oz = plane.origin.x, plane.origin.y, plane.origin.z
    return (nx, ny, nz, -(nx * ox + ny * oy + nz * oz))


def _segment_poly(coeffs, rr, k):
    """Koeficienty (sestupne, [c3,c2,c1,c0]) kubickeho polynomu
    f(C(t)) = rr . (C(t), 1) pro segment s Hermitovymi koeficienty
    'coeffs' (k os) a implicitni primku/rovinu 'rr' (k+1 koeficientu)."""
    c3 = c2 = c1 = 0.0
    c0 = rr[k]
    for j in range(k):
        a3, a2, a1, a0 = coeffs[j]
        c3 += rr[j] * a3
        c2 += rr[j] * a2
        c1 += rr[j] * a1
        c0 += rr[j] * a0
    return [c3, c2, c1, c0]


def _dist(p, q, k):
    return math.sqrt(sum((p[i] - q[i]) ** 2 for i in range(k)))


def _hyperplane_curve_intersections(spline, rr, k):
    """Spolecne jadro GLPRU pro K=2 (primka x 2D krivka) i K=3 (rovina
    x 3D krivka) - viz hlavicka modulu. Vraci seznam (segment_index_
    1based, t, Point), v poradi segment po segmentu / rostouciho t."""
    pts = spline.points
    n = len(pts)
    results = []
    last_accepted = None  # Q4 - posledni prijaty bod predchoziho segmentu

    for i in range(1, n):
        p0, p1 = pts[i - 1], pts[i]
        t0, t1 = spline.segment_tangent_pair(i - 1)
        coeffs = segment_coefficients(p0, p1, t0, t1, k=k)
        poly = _segment_poly(coeffs, rr, k)
        roots = real_roots_in_range(poly, _DMEZ, _HMEZ)

        if roots and (i + 1) != n and abs(1.0 - roots[-1]) < 1e-5:
            roots = roots[:-1]
        if not roots:
            continue

        candidates = [(t, tuple(evaluate(coeffs, t, order=0))) for t in roots]

        # deduplikace sousednich korenu uvnitr segmentu (ponech drivejsi)
        merged = [candidates[0]]
        for t, xyz in candidates[1:]:
            if _dist(xyz, merged[-1][1], k) < _POINT_TOL:
                continue
            merged.append((t, xyz))

        # deduplikace pres hranici segmentu (Q4)
        if last_accepted is not None and _dist(merged[0][1], last_accepted, k) < _POINT_TOL:
            merged = merged[1:]
        if not merged:
            continue

        for t, xyz in merged:
            coords = xyz if k == 3 else (xyz[0], xyz[1], 0.0)
            results.append((i, t, Point(*coords)))
        last_accepted = merged[-1][1]

    return results


def line_curve_intersections(spline, line):
    """GLPRU (K=2): vsechny pruseciky 'line' s 2D krivkou 'spline', v
    poradi segment po segmentu / rostouciho parametru - seznam
    (segment_index_1based, t, Point). Viz hlavicka modulu."""
    rr = implicit_line(line)
    return _hyperplane_curve_intersections(spline, rr, k=2)


def plane_curve_intersections(spline, plane):
    """GLPRU (K=3): vsechny pruseciky 'plane' s 3D krivkou 'spline', v
    poradi segment po segmentu / rostouciho parametru - seznam
    (segment_index_1based, t, Point). Viz hlavicka modulu."""
    rr = implicit_plane(plane)
    return _hyperplane_curve_intersections(spline, rr, k=3)
