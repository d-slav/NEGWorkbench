# -*- coding: utf-8 -*-
"""
Procedura E01 (GL3 opcode E01)      n.p. LET Kunovice
Puvodni komentar: definovani 2D retezce mnozinou bodu.

Uziti (GL3): EM=E01>P,N - P je "adresa prvniho bodu" pole (Fortran
konvence 'P(1),N' - precti N prvku pole P pocinaje P(1)), N pocet bodu.

Podle E01.FOR:
  - precte prvnich N bodu pocinaje danym zacatkem
  - zjisti, jestli je krivka uzavrena: vzdalenost prvniho a posledniho
    bodu < 1e-3 (puvodni CALL D610 + IF(DV.LT.1E-3) ITP=3)
  - kazdemu bodu prirad index 1..N-1, pricemz POSLEDNI bod dostane
    stejny index jako predposledni a priznak is_end=True (v originale
    PARAM=1D0 misto 0D0) - presny vyznam pro pozdejsi operace (hledani
    N-teho bodu, pocet bodu, ...) zatim neznáme, jen se 1:1 replikuje.

Tento soubor take obsahuje tangent_point_on_chain() - jadro puvodni
P85.FOR (hledani tecneho bodu na retezci), ktere sdileji operace P85,
P86 a L46 (viz jejich soubory) - dava smysl drzet ho spolu s Curve/E01,
protoze je na jeho vnitrni reprezentaci (points/closed/indices) uzce
navazany.
"""

from .types import Point, Curve
from .v220 import unit_vector
from .a521 import polar_angle_deg
from .a510 import angle_between_deg


def make_chain(points, n=None):
    """E01: 2D retezec (Curve) z pole bodu.

    points - posloupnost bodu (Point); pokud je delsi nez N, pouziji se
             jen prvnich N.
    n      - pocet bodu k pouziti; None = pouzij vsechny 'points'.
    """
    n_int = int(round(n)) if n is not None else len(points)
    if n_int < 2:
        raise ValueError("E01: pocet bodu N musi byt aspon 2 (dostal %r)" % (n,))
    if len(points) < n_int:
        raise ValueError(
            "E01: pole bodu obsahuje jen %d prvku, ale N=%d" % (len(points), n_int)
        )
    pts = points[:n_int]
    for i, p in enumerate(pts):
        if p is None:
            raise ValueError("E01: bod na pozici %d neni definovan" % (i + 1,))
        if not isinstance(p, Point):
            raise TypeError("E01: prvek na pozici %d neni bod (Point), ale %r" % (i + 1, p))

    first, last = pts[0], pts[-1]
    import math
    closed = math.hypot(last.x - first.x, last.y - first.y) < 1e-3

    indices = []
    is_end = []
    for i in range(n_int):
        if i == n_int - 1:
            indices.append(n_int - 1)
            is_end.append(True)
        else:
            indices.append(i + 1)
            is_end.append(False)

    return Curve(list(pts), closed=closed, indices=indices, is_end=is_end, eps=0.0)


def tangent_point_on_chain(dir_xy, curve, k):
    """Jadro P85.FOR (a tedy i P86/L46, ktere na nem stoji): najde K-ty bod
    na retezci 'curve', kde je retezec "tecny" (rovnobezny) se smerovym
    vektorem dir_xy.

    Dva zpusoby, jak se bod pocita:
      - HRANA retezce je (temer) rovnobezna se smerem -> tecny bod je prvni
        vrchol takove (mozna vicehranove) rovnobezne useky.
      - VRCHOL, kde sousedni hrany "prehodi stranu" vuci primce danou timto
        smerem (klasicky "otocny" bod, jako u hledani opornych primek
        konvexniho obalu).

    Vraci (x, y, index) - souradnice bodu a jeho 1-based poradi v poli bodu
    krivky (odpovida IIN(7,JC1)=IR-2 v puvodnim P85.FOR).
    """
    import math

    xx, yy = unit_vector(*dir_xy)
    pts = curve.points
    n = len(pts)
    if n < 3:
        raise ValueError(
            "retezec ma jen %d bod(y) - pro hledani tecneho bodu jsou "
            "potreba aspon 3" % (n,)
        )

    xx1, yy1 = pts[0].x, pts[0].y
    l1 = True
    ipoc = 0

    for i in range(2, n + 1):  # i = 1-based index bodu XX2,YY2
        p2 = pts[i - 1]
        xx2, yy2 = p2.x, p2.y

        d1 = math.hypot(xx2 - xx1, yy2 - yy1)
        if d1 < 1e-3:
            continue  # degenerovana (nulova) hrana - preskoc, XX1 se neposouva
        xv1, yv1 = (xx2 - xx1) / d1, (yy2 - yy1) / d1

        angl = angle_between_deg(xx, yy, xv1, yv1)
        if angl < 1e-2 or abs(180.0 - angl) < 1e-2:
            # hrana je rovnobezna se smerem - "plocha" tecna
            if l1:
                ipoc += 1
                l1 = False
                if ipoc == k:
                    return xx2, yy2, i
            xx1, yy1 = xx2, yy2
            continue

        if i == n:
            xx1, yy1 = xx2, yy2
            continue  # posledni bod - neni dalsi hrana pro "rohovy" test

        p3 = pts[i]
        xx3, yy3 = p3.x, p3.y
        d2 = math.hypot(xx3 - xx2, yy3 - yy2)
        if d2 < 1e-3:
            continue  # degenerovana nasledujici hrana - preskoc (XX1 se neposouva)
        xv2, yv2 = (xx3 - xx2) / d2, (yy3 - yy2) / d2

        aa1 = polar_angle_deg(xv1, yv1)
        aa2 = polar_angle_deg(xv2, yv2)
        dm, hm = min(aa1, aa2), max(aa1, aa2)
        if hm - dm > 180.0:
            dm, hm = hm, dm + 360.0
        dm += 1e-5
        hm -= 1e-5
        angl0 = polar_angle_deg(xx, yy)

        hit = False
        for step in (-1, 0, 1, 2):
            aa = angl0 + step * 180.0
            if dm < aa < hm:
                hit = True
                break

        if hit:
            ipoc += 1
            l1 = True
            if ipoc == k:
                return xx2, yy2, i

        xx1, yy1 = xx2, yy2

    raise ValueError(
        "na retezci nebyl nalezen %d. tecny bod rovnobezny se zadanym smerem" % (k,)
    )
