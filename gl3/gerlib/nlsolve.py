# -*- coding: utf-8 -*-
"""
Procedura DNSBM        LET, k.p., Uh.Hradiste / Hitachi S-1511-1
Knihovna GL3E4                                     Cerven 1986

Ucel (puvodni): Reseni soustavy N nelinearnich rovnic Brentovou metodou
(kvazi-Newtonova metoda s ortogonalnimi transformacemi).

POZNAMKA - PROC NENI 1:1 PORT: puvodni DNSBM je rozsahla numericka
knihovni procedura (Hitachi, 1980) s vlastnim rizenim kroku, detekci
singularniho Jakobianu, "good progress" heuristikami atd. Misto
rekonstrukce tehle netrivialni 1980 implementace pouzivame klasickou
Newton-Raphsonovu metodu s numerickym (diferencnim) Jakobianem a
tlumenim kroku - kontrakt je stejny (dej rezidualni funkci FUNC(X,N,K)
a pocatecni odhad, dostanes X takove, ze FUNC(X,N,K)~0 pro vsechna K),
jina cesta k vysledku. Pro pouziti v S51 (4 rovnice, rozumny pocatecni
odhad blizko reseni) je to spolehlive a jednoduche.
"""


def solve(func, x0, n, tol=1e-9, max_iter=50, damping=1.0):
    """Newton-Raphsonova metoda pro soustavu 'func(x, n, k) = 0',
    k=1..n (1-based, jako puvodni FUNC(X,N,K)). 'x0' je pocatecni
    odhad (seznam n cisel). Vraci (x, converged) - x je vysledny
    seznam, converged True/False podle toho, jestli se dosahlo
    pozadovane presnosti do max_iter iteraci.

    Numericky Jakobian (dopredni diference), reseni linearniho
    systemu Gaussovou eliminaci s castecnou pivotaci (bez numpy -
    viz gerlib/glply.py pro stejny duvod bezzavislostniho pristupu)."""
    x = list(x0)

    for _iteration in range(max_iter):
        residuals = [func(x, n, k + 1) for k in range(n)]
        if max(abs(r) for r in residuals) < tol:
            return x, True

        jac = _numerical_jacobian(func, x, n, residuals)
        try:
            delta = _solve_linear(jac, [-r for r in residuals], n)
        except ZeroDivisionError:
            return x, False

        step = damping
        x = [x[i] + step * delta[i] for i in range(n)]

    residuals = [func(x, n, k + 1) for k in range(n)]
    converged = max(abs(r) for r in residuals) < tol
    return x, converged


def _numerical_jacobian(func, x, n, f0):
    """J[k][i] = d(residual_k)/d(x_i), dopredni diference."""
    jac = [[0.0] * n for _ in range(n)]
    for i in range(n):
        h = 1e-7 * max(1.0, abs(x[i]))
        x_perturbed = list(x)
        x_perturbed[i] += h
        for k in range(n):
            fk = func(x_perturbed, n, k + 1)
            jac[k][i] = (fk - f0[k]) / h
    return jac


def _solve_linear(a, b, n):
    """Gaussova eliminace s castecnou pivotaci pro Ax=b (male n, ctverec
    matice jako seznam seznamu). Vyhazuje ZeroDivisionError pri (temer)
    singularni matici."""
    a = [row[:] for row in a]
    b = list(b)

    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot_row][col]) < 1e-14:
            raise ZeroDivisionError("nlsolve: (temer) singularni Jakobian")
        if pivot_row != col:
            a[col], a[pivot_row] = a[pivot_row], a[col]
            b[col], b[pivot_row] = b[pivot_row], b[col]
        for row in range(col + 1, n):
            factor = a[row][col] / a[col][col]
            if factor == 0.0:
                continue
            for k in range(col, n):
                a[row][k] -= factor * a[col][k]
            b[row] -= factor * b[col]

    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        s = b[row] - sum(a[row][k] * x[k] for k in range(row + 1, n))
        x[row] = s / a[row][row]
    return x
