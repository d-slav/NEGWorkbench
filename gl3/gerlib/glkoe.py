# -*- coding: utf-8 -*-
"""
Procedura GLKOE        LET, k.p., Uh.Hradiste
Knihovna CURLIB32                       Unor 1983

Ucel:    Vypocet koeficientu (DBLE) kubickeho segmentu.

Uziti:   CALL GLKOE(QR,K,RK)

Parametry:  QR(12)  R*4  Q1,Q2,U1,U2 - 4 body po 3 slozkach (X,Y,Z):
                         P0 (QR(1:3)), P1 (QR(4:6)), tecna T0 (QR(7:9)),
                         tecna T1 (QR(10:12)). 2D krivka pouzije jen
                         slozky X,Y (K=2), Z zustava nevyuzita.
            K       I*2  Rozmernost (2 nebo 3)
            RK(4,K) R*8  Vysledne koeficienty kubiky (DBLE), sestupne:
                         RK(1,j)=a3, RK(2,j)=a2, RK(3,j)=a1, RK(4,j)=a0
                         pro osu j, tedy C_j(t) = a3*t^3+a2*t^2+a1*t+a0

Matice E je standardni kubicka Hermitova bazova matice:
    E = [ 2 -2  1  1]
        [-3  3 -2 -1]
        [ 0  0  1  0]
        [ 1  0  0  0]
a RK = E * V, kde V = [P0;P1;T0;T1] (po radcich, pro kazdou osu
zvlast) - viz DATA E v puvodnim zdroji (rozepsano a overeno sloupec
po sloupci).

V nasem projektu vstup neni QR(12) (fortranovske pole), ale primo
body/tecny z nasi Spline reprezentace (Point, Vector) - viz
segment_coefficients() nize, ktera je s GLKOE matematicky totozna.
"""


def segment_coefficients(p0, p1, t0, t1, k=2):
    """GLKOE - kubicke Hermitovy koeficienty segmentu <p0,p1> s tecnami
    t0 (na zacatku), t1 (na konci) - jiz naskalovanymi pro tento segment
    (viz Spline.segment_tangent_pair, ktera resi rozdil mezi uniformni
    S03 a chordalni S01 parametrizaci).

    Vraci seznam k n-tic (a3,a2,a1,a0) - jedna n-tice na kazdou
    souradnicovou osu (poradi X,Y[,Z]), tak, ze
        C_osa(t) = a3*t**3 + a2*t**2 + a1*t + a0
    """
    p0v = (p0.x, p0.y, p0.z)
    p1v = (p1.x, p1.y, p1.z)
    t0v = (t0.x, t0.y, t0.z)
    t1v = (t1.x, t1.y, t1.z)

    coeffs = []
    for j in range(k):
        P0, P1, T0, T1 = p0v[j], p1v[j], t0v[j], t1v[j]
        a3 = 2.0 * P0 - 2.0 * P1 + T0 + T1
        a2 = -3.0 * P0 + 3.0 * P1 - 2.0 * T0 - T1
        a1 = T0
        a0 = P0
        coeffs.append((a3, a2, a1, a0))
    return coeffs
