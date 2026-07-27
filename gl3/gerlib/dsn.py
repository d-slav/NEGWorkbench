# -*- coding: utf-8 -*-
"""
Procedura DSN       LET n.p. Uh.Hradiste     Ing.S.Trnka
Knihovna CURLIB32                      Brezen 1987

Ucel:    Definice kubickeho splinu neperiodickeho - krivky otevrene
         rovinne nebo prostorove - parametrizovane 0-1.

Uziti:   CALL DSN(QS,U1,U2,I1,I2,N,K,W,US,IERR)

Algoritmus: klasicky parametricky kubicky splajn (uniformni
parametrizace, kazdy segment 0-1) - tridiagonalni soustava:
  vnitrni uzel i:  U(i-1) + 4*U(i) + U(i+1) = 3*(Q(i+1)-Q(i-1))
  okrajovy uzel (tecna NEni zadana - relaxovana podminka):
      zacatek:  2*U(1) + U(2)     = 3*(Q(2)-Q(1))
      konec:    U(N-1) + 2*U(N)   = 3*(Q(N)-Q(N-1))
  okrajovy uzel (tecna JE zadana - "clamped"): U = zadany vektor primo.

Reseno pomoci gtrin.solve_tridiagonal (GTRIN), zda je tecna "zadana" pozna
vnorm.is_zero_vector (VNORM - nulovy vektor = "nezadano").
"""

from .types import Vector
from .vnorm import is_zero_vector
from .gtrin import solve_tridiagonal


def tangent_vectors(nodes, v1=None, vk=None):
    """Tecne vektory v uzlovych bodech otevreneho kubickeho splajnu.

    nodes - seznam bodu (Point), delka N>=3.
    v1/vk - volitelne okrajove tecne vektory (Vector); None nebo nulovy
            vektor = automaticky dopocitany (relaxovana okrajova
            podminka), jinak "clamped" (tecna primo rovna zadanemu
            vektoru).
    """
    n = len(nodes)
    if n < 3:
        raise ValueError("DSN: pocet bodu krivky musi byt >= 3 (dostal %d)" % (n,))

    w = [[0.0, 0.0, 0.0] for _ in range(n)]
    us = [[0.0, 0.0, 0.0] for _ in range(n)]

    def comps(v):
        return (v.x, v.y, v.z)

    v1_zero = v1 is None or is_zero_vector(comps(v1))
    vk_zero = vk is None or is_zero_vector(comps(vk))

    # pocatecni uzel
    if not v1_zero:
        w[0][1], w[0][2] = 1.0, 0.0
        us[0] = [v1.x, v1.y, v1.z]
    else:
        w[0][1], w[0][2] = 2.0, 1.0
        us[0] = [
            3.0 * (nodes[1].x - nodes[0].x),
            3.0 * (nodes[1].y - nodes[0].y),
            3.0 * (nodes[1].z - nodes[0].z),
        ]

    # koncovy uzel
    if not vk_zero:
        w[n - 1][1], w[n - 1][0] = 1.0, 0.0
        us[n - 1] = [vk.x, vk.y, vk.z]
    else:
        w[n - 1][1], w[n - 1][0] = 2.0, 1.0
        us[n - 1] = [
            3.0 * (nodes[n - 1].x - nodes[n - 2].x),
            3.0 * (nodes[n - 1].y - nodes[n - 2].y),
            3.0 * (nodes[n - 1].z - nodes[n - 2].z),
        ]

    # vnitrni uzly
    for i in range(1, n - 1):
        w[i][0], w[i][1], w[i][2] = 1.0, 4.0, 1.0
        us[i] = [
            3.0 * (nodes[i + 1].x - nodes[i - 1].x),
            3.0 * (nodes[i + 1].y - nodes[i - 1].y),
            3.0 * (nodes[i + 1].z - nodes[i - 1].z),
        ]

    solved = solve_tridiagonal(w, us)
    return [Vector(row[0], row[1], row[2]) for row in solved]
