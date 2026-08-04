# -*- coding: utf-8 -*-
"""
Procedura RKSEG        LET, k.p., Uh.Hradiste
Knihovna CURLIB32

Ucel:    Vypocet polomeru krivosti segmentu kubicke Hermitovy krivky
         pro zadany parametr.

Uziti:   CALL RKSEG(Q1,U1,Q2,U2,K,D,P,R,JF)

Parametry:  Q1,U1,Q2,U2  body a tecny segmentu (viz glkoe.py)
            K            rozmernost (2 nebo 3)
            D            delka secny nebo 1. (v puvodnim RKSEG se
                          nepouziva jinak nez jako predavany parametr
                          SPLSEG - u nas neni potreba, viz evaluate())
            P            parametr <0,1>
            R            IN/OUT - vypocteny (PODEPSANY) polomer
                          krivosti; vstupni hodnota 1E6 funguje jako
                          sentinel pro (temer) primy usek (staci, kdyz
                          determinant vyjde blizky nule)
            JF           chybove hlaseni

Vzorec (2D, K=2 - jediny pripad, ktery zatim v projektu potrebujeme):
    QP1 = C'(t)  (1. derivace)
    QP2 = C''(t) (2. derivace)
    DET = QP1.x*QP2.y - QP2.x*QP1.y
    R = (QP1.x^2 + QP1.y^2)^1.5 / DET     (POZOR: bez ABS - znamenko
                                            nese informaci o smeru
                                            zakriveni, presne jako v
                                            originale)
    (pokud |DET| <= 1e-6, segment je lokalne primy -> vraci se sentinel)
"""

from .glfun import evaluate


def curvature_radius_at(coeffs, t):
    """RKSEG (2D vetev) - podepsany polomer krivosti kubickeho segmentu
    s koeficienty 'coeffs' (viz glkoe.segment_coefficients) v parametru
    t. Vraci 1e6 (sentinel "prakticky primy usek") pokud je determinant
    (QP1 x QP2) blizky nule."""
    qp1 = evaluate(coeffs, t, order=1)
    qp2 = evaluate(coeffs, t, order=2)

    r = 1e6
    det = qp1[0] * qp2[1] - qp2[0] * qp1[1]
    if abs(det) > 1e-6:
        rm = (qp1[0] ** 2 + qp1[1] ** 2) ** 1.5 / det
        if abs(rm) < abs(r):
            r = rm
    return r
