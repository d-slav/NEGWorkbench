# -*- coding: utf-8 -*-
"""
Procedura D28            LET, k.p., Uh.Hradiste
Knihovna GL3E2                                      Brezen 1984

Ucel:    Delka retezce E; delka retezce v intervalu.

Uziti:   DM=D28>>E[,[P1][,P2]]

DM je delka retezce E, nejsou-li uvedeny body P1 a P2. Je-li zadan jen
bod P1, pocita se delka od P1 do konce retezce. Je-li zadan jen bod P2,
pocita se delka od pocatku retezce do P2. Jsou-li zadany oba body,
pocita se delka od P1 do P2 podle nasledujiciho pravidla (viz G10.md
'D28 - Delka retezce; delka retezce v intervalu'):
  - pro OTEVRENY retezec nezavisi na poradi bodu P1, P2 (pocita se
    delka mezi P1 a P2 po retezci E)
  - pro UZAVRENY retezec zavisi na poradi: je-li P1 PRED P2 (podle
    postupu parametru po retezci), pocita se delka z P1 do P2 po
    retezci E; je-li P1 ZA P2, pocita se delka z P1 do konce retezce E
    a z konce (identicky rovnemu pocatku) retezce E do P2.

Puvodni Fortran (C430... resp. D28.FOR) pracuje primo se zaznamy
souboru CL2 (indexy INDX1/INDX2 + zlomkovy parametr RR(4,..), pomocna
procedura P54 - najde index bodu na retezci, coz odpovida jiz
existujicimu D31/gerlib.d31.index_parameter). Tento port pocita delku
primo z nasi reprezentace Curve (points/closed), beze zmeny vysledku:
misto indexoveho parametru pouziva kumulativni delku od pocatku
retezce k danemu bodu (viz _position_on_chain nize) - matematicky
totozne, jen bez zavislosti na CL2 zaznamovem formatu.

Chyba, nelezi-li P1/P2 na retezci E (odpovida puvodnimu IER=377/378).
"""
import math

from .types import Point, Curve

_TOL = 1e-6


def _cumulative_lengths(points):
    cum = [0.0] * len(points)
    for i in range(1, len(points)):
        cum[i] = cum[i - 1] + math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
    return cum


def _segment_param(point, a, b):
    """Projekce bodu na usecku a->b: (t, kolma vzdalenost) - stejne jako
    v gerlib.d31."""
    dx, dy = b.x - a.x, b.y - a.y
    len2 = dx * dx + dy * dy
    if len2 < 1e-24:
        return 0.0, math.hypot(point.x - a.x, point.y - a.y)
    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / len2
    px, py = a.x + t * dx, a.y + t * dy
    return t, math.hypot(point.x - px, point.y - py)


def _position_on_chain(curve, point, cum, which):
    """Kumulativni delka od pocatku retezce 'curve' k bodu 'point'
    (0 = pocatek, cum[-1] = konec). 'which' (\"P1\"/\"P2\") jen pro
    chybovou hlasku."""
    pts = curve.points
    n = len(pts)

    for i, p in enumerate(pts):
        if math.hypot(point.x - p.x, point.y - p.y) < _TOL:
            return cum[i]

    best = None
    for i in range(n - 1):
        t, dist = _segment_param(point, pts[i], pts[i + 1])
        if dist < _TOL and -_TOL <= t <= 1.0 + _TOL:
            t_clamped = max(0.0, min(1.0, t))
            pos = cum[i] + t_clamped * (cum[i + 1] - cum[i])
            err = dist + abs(t - t_clamped)
            if best is None or err < best[0]:
                best = (err, pos)

    if best is not None:
        return best[1]

    raise ValueError(
        "D28: bod %s (%g, %g) nelezi na retezci E (puvodni IER=%s)"
        % (which, point.x, point.y, "377" if which == "P1" else "378")
    )


def length_of_chain(curve, p1=None, p2=None):
    """D28: DM=D28>E[,[P1][,P2]] - delka retezce 'curve', pripadne jen
    v useku od 'p1' (nebo pocatku) do 'p2' (nebo konce) - viz hlavicka
    modulu pro presna pravidla poradi u uzavreneho retezce."""
    if not isinstance(curve, Curve):
        raise TypeError("D28: prvni argument musi byt retezec (Curve), dostal %r" % (curve,))
    if len(curve.points) < 2:
        raise ValueError("D28: retezec ma min nez 2 body")

    cum = _cumulative_lengths(curve.points)
    total = cum[-1]

    pos_a = _position_on_chain(curve, p1, cum, "P1") if p1 is not None else 0.0
    pos_b = _position_on_chain(curve, p2, cum, "P2") if p2 is not None else total

    if pos_b >= pos_a:
        return pos_b - pos_a
    if p1 is not None and p2 is not None and curve.closed:
        # P1 je "za" P2 (podle postupu parametru) - z P1 do konce
        # retezce + z pocatku (=konce) retezce do P2.
        return (total - pos_a) + pos_b
    # Otevreny retezec (nebo jen jeden bod zadan): na poradi nezalezi.
    return pos_a - pos_b
