# -*- coding: utf-8 -*-
"""
Procedura GLFUN (a GLFUND - DBLE varianta, matematicky totozna)
LET, k.p., Uh.Hradiste
Knihovna CURLIB32                       Unor 1983

Ucel:    Vypocet funkcni hodnoty / 1. derivace / 2. derivace na
         kubickem segmentu zadanem koeficienty (viz GLKOE/
         segment_coefficients).

Uziti:   CALL GLFUN(Q,P,RK,K,L)

Parametry:  P       DBLE  Parametr bodu
            RK(4,K) DBLE  Koeficienty segmentu (viz glkoe.py)
            K       I*2   Rozmernost krivky (2 nebo 3)
            L       I*2   0=hodnota, 1=1.derivace, 2=2.derivace
            Q(K)          Vysledek

Puvodni GLFUN pocita vahovy vektor PAR pres pomocnou GLPAR (nedodana,
ale trivialni - standardni derivace mocninne baze):
    L=0: PAR=[t^3, t^2, t, 1]
    L=1: PAR=[3t^2, 2t, 1, 0]
    L=2: PAR=[6t, 2, 0, 0]
a Q = PAR . RK (skalarni soucin s kazdym sloupcem RK) - presne to,
co dela evaluate() nize primo z (a3,a2,a1,a0).
"""


def evaluate(coeffs, t, order=0):
    """GLFUN/GLFUND - hodnota (order=0), 1. derivace (order=1) nebo 2.
    derivace (order=2) kubickeho segmentu s koeficienty 'coeffs'
    (vystup segment_coefficients: seznam n-tic (a3,a2,a1,a0)) v
    parametru t. Vraci seznam hodnot, jednu na kazdou osu."""
    result = []
    for (a3, a2, a1, a0) in coeffs:
        if order == 0:
            v = a3 * t ** 3 + a2 * t ** 2 + a1 * t + a0
        elif order == 1:
            v = 3.0 * a3 * t ** 2 + 2.0 * a2 * t + a1
        elif order == 2:
            v = 6.0 * a3 * t + 2.0 * a2
        else:
            raise ValueError("GLFUN: neplatny parametr L (0/1/2), dostal %r" % (order,))
        result.append(v)
    return result
