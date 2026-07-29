# -*- coding: utf-8 -*-
"""
Procedura DSPN      LET n.p. Uh.Hradiste     Ing.S.Trnka
Knihovna CURLIB32                      Unor 1982

Ucel:    Definice kubickeho splinu neperiodickeho - krivky otevrene
         rovinne nebo prostorove - CHORDALNI (chord-length) parametrizace.

Uziti:   CALL DSPN(QS,U1,U2,I1,I2,N,K,W,US,IERR)

Rozdil oproti dsn.py (DSN.FOR, pouzito v S03): DSN pouziva UNIFORMNI
parametrizaci (prava strana tridiagonalni soustavy ignoruje skutecne
vzdalenosti mezi uzlovymi body), DSPN pouziva CHORDALNI parametrizaci -
prava strana je vazeny prumer dvou "secnovych" smeru DELENYCH skutecnou
delkou tetivy sousedniho segmentu:

  vnitrni uzel i:  w1*U(i-1) + 2*U(i) + w3*U(i+1) =
                       3*w1*(Q(i)-Q(i-1))/h(i-1) + 3*w3*(Q(i+1)-Q(i))/h(i)
                   kde h(i) = |Q(i+1)-Q(i)|, w1 = h(i)/(h(i)+h(i-1)),
                   w3 = 1-w1 = h(i-1)/(h(i)+h(i-1))
  okrajovy uzel (tecna neni zadana):
      zacatek:  2*U(1) + U(2)   = 3*(Q(2)-Q(1))/h(1)
      konec:    U(N-1) + 2*U(N) = 3*(Q(N)-Q(N-1))/h(N-1)
  okrajovy uzel (tecna JE zadana): U = zadany vektor, znormovany na
      jednotkovou delku (VNORM) - viz gerlib.s01, kde se pak (stejne jako
      GLSPL.FOR) vysledne tecny vektory jeste prenasobi skutecnou delkou
      prislusneho segmentu.

Reseno pomoci gtrin.solve_tridiagonal (GTRIN) - stejny tridiagonalni
resic jako u DSN, jen jina prava strana/vahy.
"""

from .types import Vector
from .vnorm import is_zero_vector
from .gtrin import solve_tridiagonal


def _chord(a, b):
    dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _normalize(v):
    length = (v.x * v.x + v.y * v.y + v.z * v.z) ** 0.5
    if length <= 1e-10:
        length = 1.0
    return (v.x / length, v.y / length, v.z / length)


def tangent_vectors(nodes, v1=None, vk=None):
    """Tecne vektory (chordalni parametrizace) v uzlovych bodech
    otevreneho kubickeho splajnu.

    nodes - seznam bodu (Point), delka N>=3.
    v1/vk - volitelne okrajove tecne vektory (Vector); None nebo nulovy
            vektor = automaticky dopocitany (relaxovana okrajova
            podminka), jinak "clamped" (tecna = smer zadaneho vektoru,
            znormovany).
    """
    n = len(nodes)
    if n < 3:
        raise ValueError("DSPN: pocet bodu krivky musi byt >= 3 (dostal %d)" % (n,))

    h = []
    for i in range(n - 1):
        d = _chord(nodes[i], nodes[i + 1])
        if d <= 1e-3:
            raise ValueError("DSPN: body c. %d a %d jsou totozne" % (i + 1, i + 2))
        h.append(d)

    w = [[0.0, 0.0, 0.0] for _ in range(n)]
    us = [[0.0, 0.0, 0.0] for _ in range(n)]

    def comps(v):
        return (v.x, v.y, v.z)

    v1_zero = v1 is None or is_zero_vector(comps(v1))
    vk_zero = vk is None or is_zero_vector(comps(vk))

    # pocatecni uzel
    if not v1_zero:
        w[0][1], w[0][2] = 1.0, 0.0
        us[0] = list(_normalize(v1))
    else:
        w[0][1], w[0][2] = 2.0, 1.0
        h0 = h[0]
        us[0] = [
            3.0 * (nodes[1].x - nodes[0].x) / h0,
            3.0 * (nodes[1].y - nodes[0].y) / h0,
            3.0 * (nodes[1].z - nodes[0].z) / h0,
        ]

    # koncovy uzel
    if not vk_zero:
        w[n - 1][1], w[n - 1][0] = 1.0, 0.0
        us[n - 1] = list(_normalize(vk))
    else:
        w[n - 1][1], w[n - 1][0] = 2.0, 1.0
        hlast = h[n - 2]
        us[n - 1] = [
            3.0 * (nodes[n - 1].x - nodes[n - 2].x) / hlast,
            3.0 * (nodes[n - 1].y - nodes[n - 2].y) / hlast,
            3.0 * (nodes[n - 1].z - nodes[n - 2].z) / hlast,
        ]

    # vnitrni uzly - chordalni vazeny prumer dvou secnovych smeru
    for i in range(1, n - 1):
        h_back, h_fwd = h[i - 1], h[i]
        w1 = h_fwd / (h_fwd + h_back)
        w3 = 1.0 - w1
        w[i][0], w[i][1], w[i][2] = w1, 2.0, w3
        us[i] = [
            3.0 * w1 * (nodes[i].x - nodes[i - 1].x) / h_back
            + 3.0 * w3 * (nodes[i + 1].x - nodes[i].x) / h_fwd,
            3.0 * w1 * (nodes[i].y - nodes[i - 1].y) / h_back
            + 3.0 * w3 * (nodes[i + 1].y - nodes[i].y) / h_fwd,
            3.0 * w1 * (nodes[i].z - nodes[i - 1].z) / h_back
            + 3.0 * w3 * (nodes[i + 1].z - nodes[i].z) / h_fwd,
        ]

    solved = solve_tridiagonal(w, us)
    return [Vector(row[0], row[1], row[2]) for row in solved]
