# -*- coding: utf-8 -*-
"""
Procedura GTRIN     LET n.p. Uh.Hradiste     Ing.S.Trnka
Knihovna CURLIB32                      Listopad 1982

Ucel:    Reseni soustavy linearnich rovnic s tridiagonalni matici soustavy
         metodou upravene Gaussovy eliminace (Thomasuv algoritmus).

Uziti:   CALL GTRIN(W,I1,I2,N,K,US)

Parametry: W(N,3)   R*4  Matice soustavy: W(I,1) pod diagonalou,
                         W(I,2) hlavni diagonala, W(I,3) nad diagonalou
           US(N,K)  R*4  In: prave strany. Out: reseni.
"""


def solve_tridiagonal(w, rhs):
    """w[i] = [pod_diag, diag, nad_diag]; rhs[i] = [slozka1, slozka2, ...]
    (K sloupcu reseno soucasne). Vraci reseni (nemutuje vstupy)."""
    n = len(w)
    w = [row[:] for row in w]
    x = [row[:] for row in rhs]
    k = len(x[0])

    for i in range(1, n):
        a1 = w[i][0] / w[i - 1][1]
        w[i][1] -= w[i - 1][2] * a1
        for j in range(k):
            x[i][j] -= x[i - 1][j] * a1

    for j in range(k):
        x[n - 1][j] /= w[n - 1][1]

    for i in range(n - 2, -1, -1):
        for j in range(k):
            x[i][j] = (x[i][j] - w[i][2] * x[i + 1][j]) / w[i][1]

    return x
