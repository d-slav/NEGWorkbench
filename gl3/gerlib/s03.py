# -*- coding: utf-8 -*-
"""
Procedura SPLIN (GL3 opcode S03)    n.p. LET Kunovice
Knihovna GL3E3                                      17.3.1987

Ucel:    Krivka K body a okrajovymi tecnymi vektory s parametrizaci 0-1.

Uziti (GL3): SM=S03>P(I),K[,[V1],[VK][,N]]

    P(I) - pole uzlovych bodu krivky ("adresa prvniho bodu", Fortran
           konvence 'P(1),N' jako u E01/S01)
    K    - pocet bodu vysledne krivky <2,128>
    V1   - pocatecni tecny vektor (je-li nulovy/nezadany, dopocita se -
           viz dsn.py)
    VK   - koncovy tecny vektor (stejne)
    N    - rozdil indexu sousednich uzlovych bodu krivky v poli P
           (kazdy N-ty bod puvodniho pole se stane uzlem vysledne
           krivky); nezadano = 1 (kazdy bod)

Skutecny vypocet tecnych vektoru je v dsn.py (DSN.FOR) - SPLIN.FOR sam je
jen infrastrukturni wrapper (cteni/zapis zaznamu RTAB - stejna
infrastruktura jako E01/L46), pro nas uz neni potreba.
"""

from .types import Point, Vector, Spline
from .dsn import tangent_vectors


def make_spline(points_ref, k, v1=None, vk=None, n=None):
    k_int = int(round(k))
    if k_int < 2:
        raise ValueError("S03: K (pocet bodu krivky) musi byt >= 2 (dostal %r)" % (k,))
    step = int(round(n)) if n is not None else 1
    if step < 1:
        raise ValueError("S03: N (krok mezi uzly v poli) musi byt >= 1 (dostal %r)" % (n,))

    needed_span = (k_int - 1) * step + 1
    if len(points_ref) < needed_span:
        raise ValueError(
            "S03: pole bodu obsahuje jen %d prvku, ale je potreba %d (K=%d, N=%d)"
            % (len(points_ref), needed_span, k_int, step)
        )

    nodes = [points_ref[i * step] for i in range(k_int)]
    for i, p in enumerate(nodes):
        if p is None:
            raise ValueError("S03: uzlovy bod c. %d neni definovan" % (i + 1,))
        if not isinstance(p, Point):
            raise TypeError("S03: prvek c. %d neni bod (Point), ale %r" % (i + 1, p))

    if k_int == 2:
        # SPLIN.FOR: DSN vyzaduje aspon 3 body. Pro presne K=2 je to
        # (podle dokumentace) primy kubicky segment - tecna bez zadani
        # je sekanta mezi obema body.
        secant = Vector(nodes[1].x - nodes[0].x, nodes[1].y - nodes[0].y, nodes[1].z - nodes[0].z)

        def _pick(v):
            return v if (v is not None and (v.x, v.y, v.z) != (0.0, 0.0, 0.0)) else secant

        tangents = [_pick(v1), _pick(vk)]
    else:
        tangents = tangent_vectors(nodes, v1, vk)

    return Spline(nodes, tangents, closed=False)
