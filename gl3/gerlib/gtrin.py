# -*- coding: utf-8 -*-
"""
Procedura GTRIN     LET n.p. Uh.Hradiste
Knihovna CURLIB32                      Listopad 1982

Ucel:    Reseni soustavy linearnich rovnic s tridiagonalni matici soustavy
         metodou upravene Gaussovy eliminace (Thomasuv algoritmus).

Uziti:   CALL GTRIN(W,I1,I2,N,K,US)

Parametry: W(N,3)   R*4  Matice soustavy: W(I,1) pod diagonalou,
                         W(I,2) hlavni diagonala, W(I,3) nad diagonalou
           US(N,K)  R*4  In: prave strany. Out: reseni.

Navic (bez primeho fortranoveho predobrazu - puvodni GTRIN resi jen
beznou/necyklickou soustavu) solve_cyclic_tridiagonal() nize - CYKLicka
varianta pro uzavrene/periodicke krivky (S10/T10, viz gerlib.s10),
Shermanovou-Morrisonovou metodou prevedena na dve volani teto same
solve_tridiagonal().
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


def solve_cyclic_tridiagonal(w, rhs, alpha, beta):
    """Reseni CYKLICKE trojdiagonalni soustavy (periodicka/uzavrena
    krivka - viz gerlib.s10) Shermanovou-Morrisonovou metodou (klasicky
    postup, viz napr. Numerical Recipes, kapitola o trojdiagonalnich
    soustavach - "cyclic"): cyklickou soustavu s rohovymi prvky alpha
    (A[0][n-1]) a beta (A[n-1][0]) prevede na DVE bezne (necyklicke)
    trojdiagonalni soustavy se stejnou (mirne upravenou) matici W,
    resene stavajicim solve_tridiagonal() vyse - zadny samostatny
    cykllicky solver navic netreba.

    w[i] = [pod_diag, diag, nad_diag] BEZ rohovych prvku (w[0][0] a
           w[n-1][2] se ignoruji, presne jako u solve_tridiagonal - tam
           kde by v cyklicke soustave byly rohove prvky, tady je misto
           nich 0/cokoliv, protoze se predavaji zvlast jako alpha/beta).
    rhs[i] = prava strana (K sloupcu najednou, stejne jako
           solve_tridiagonal).
    alpha  = A[0][n-1]   (koeficient posledni nezname v 1. rovnici)
    beta   = A[n-1][0]   (koeficient prvni nezname v posledni rovnici)

    Postup: zvol gamma = -diag[0] (aby uprava diagonaly nezpusobila
    deleni nulou v beznem pripade), uprav diag[0] -= gamma a
    diag[n-1] -= alpha*beta/gamma, vyres W*x=rhs A ZAROVEN W*z=u (kde u
    je nulovy vektor az na u[0]=gamma, u[n-1]=alpha) - obe naraz jako
    dalsi 'sloupce' jednoho spolecneho solve_tridiagonal() volani - a
    slozene reseni pak dej dohromady vzorcem
    x_final = x - ((x[0]+beta*x[n-1]/gamma)/(1+z[0]+beta*z[n-1]/gamma))*z.
    """
    n = len(w)
    if n < 3:
        raise ValueError(
            "cyklicka trojdiagonalni soustava potrebuje aspon 3 rovnice (ma %d)" % n
        )

    gamma = -w[0][1] if w[0][1] != 0 else -1.0
    w_mod = [row[:] for row in w]
    w_mod[0][1] -= gamma
    w_mod[n - 1][1] -= alpha * beta / gamma

    k = len(rhs[0])
    # 'u' sloupec (viz docstring) se resi NAJEDNOU s puvodnimi K sloupci
    # prave strany - je to porad jedna a ta sama matice W, takze staci
    # jeden pruchod solve_tridiagonal() s K+1 sloupci misto dvou volani.
    u_col = [0.0] * n
    u_col[0] = gamma
    u_col[n - 1] = alpha
    augmented = [list(rhs[i]) + [u_col[i]] for i in range(n)]
    solved = solve_tridiagonal(w_mod, augmented)

    x = [row[:k] for row in solved]
    z = [row[k] for row in solved]

    result = [[0.0] * k for _ in range(n)]
    for j in range(k):
        fact = (x[0][j] + beta * x[n - 1][j] / gamma) / (1.0 + z[0] + beta * z[n - 1] / gamma)
        for i in range(n):
            result[i][j] = x[i][j] - fact * z[i]
    return result
