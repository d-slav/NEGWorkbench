# -*- coding: utf-8 -*-
"""
Procedura GLPLY        LET, k.p., Uh.Hradiste
Knihovna CURLIB32                       Unor 1983

Ucel (puvodni): Vypocet realnych korenu polynomicke funkce M-teho
                stupne v intervalu <X1,X2>.

Uziti (puvodni): CALL GLPLY(R,M,X1,X2,REA,IPOC,IER)
    R(M+1)  koeficienty polynomu (DBLE), IPOC pocet nalezenych korenu,
    REA(IPOC) koreny vzestupne serazene.

POZNAMKA - PROC TOHLE NENI 1:1 PORT: puvodni GLPLY je jen "obalka",
skutecnou praci dela GLDES (odhad/rozdeleni intervalu podle Descartova
pravidla znamenek) + GLPOL/GLPOL1 (iterativni hledani korenu, patrne
nejaka varianta Bairstowovy/Newtonovy metody z tehdejsi numericke
knihovny) + GLVYB (vyber korenu spadajicich do <X1,X2>) - zadna z
techto tri procedur nebyla dodana.

Namisto rekonstrukce neznameho iterativniho algoritmu z roku 1983
pouzivame numericky rovnocenny, ale jinak implementovany pristup:
Durand-Kernerovu (Weierstrassovu) metodu pro soucasne hledani vsech
korenu polynomu (cisty Python, zadna zavislost na numpy/scipy - viz
gerlib/types.py "zadna zavislost..."). Kontrakt (najdi vsechny realne
koreny polynomu v danem intervalu) je stejny, jen numericka cesta k
nemu jina - pro nase pouziti (P42: kubicky segment -> derivace
vzdalenosti je nejvyse 5. stupne) je to spolehlive a rychle.
"""


def polynomial_roots(coeffs_desc, max_iter=300, tol=1e-12):
    """Vsechny (komplexni) koreny polynomu se SESTUPNYMI koeficienty
    'coeffs_desc' (coeffs_desc[0] = koeficient nejvyssiho stupne, musi
    byt nenulovy) - Durand-Kernerova metoda."""
    n = len(coeffs_desc) - 1
    if n < 1:
        return []
    c0 = coeffs_desc[0]
    norm = [c / c0 for c in coeffs_desc]  # monicky polynom (nejvyssi koef. = 1)

    roots = [(0.4 + 0.9j) ** k for k in range(n)]
    for _ in range(max_iter):
        new_roots = list(roots)
        max_delta = 0.0
        for i in range(n):
            xi = roots[i]
            val = 0.0 + 0.0j
            for c in norm:
                val = val * xi + c
            denom = 1.0 + 0.0j
            for j in range(n):
                if j != i:
                    denom *= (xi - roots[j])
            if abs(denom) < 1e-14:
                denom = 1e-14 + 0.0j
            delta = val / denom
            new_roots[i] = xi - delta
            if abs(delta) > max_delta:
                max_delta = abs(delta)
        roots = new_roots
        if max_delta < tol:
            break
    return roots


def real_roots_in_range(coeffs_desc, x1, x2, imag_tol=1e-6, edge_tol=1e-9):
    """GLPLY (funkcni nahrada) - realne koreny polynomu se sestupnymi
    koeficienty 'coeffs_desc' v intervalu [x1,x2], vzestupne serazene.
    Vedouci (temer) nulove koeficienty se odstrani (jako puvodni smycka
    "M1=M1-1"). Komplexni koren se povazuje za "realny", kdyz je jeho
    imaginarni slozka mensi nez 'imag_tol'."""
    c = list(coeffs_desc)
    while len(c) > 1 and abs(c[0]) < 1e-10:
        c = c[1:]
    if len(c) <= 1:
        return []
    roots = polynomial_roots(c)
    result = sorted(
        r.real for r in roots
        if abs(r.imag) < imag_tol and (x1 - edge_tol) <= r.real <= (x2 + edge_tol)
    )
    return result
