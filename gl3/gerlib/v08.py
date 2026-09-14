# -*- coding: utf-8 -*-
"""
Procedura V208          LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                       Listopad 1989

Ucel:    Vektor ziskany otocenim daneho vektoru o dany uhel. Pro
         zadany kladny uhel, smysl otaceni ccw, pro zaporny uhel,
         smysl otaceni cw.

Uziti:   CALL V208(X1,Y1,X2,X,Y,J)
         GL3:  VM=V08>V,A[,K]

Parametry:  X1,Y1  R*4  Slozky vstupniho vektoru V
            X2     R*4  Uhel A ve stupnich
            X,Y    R*4  Vysledny vektor VM (delka zachovana)
            J      I*2  Chybove cislo:
                         J=0     spravne provedeno
                         J=2080  nulovy vstupni vektor

V208.FOR samo o sobe K nema - je to primo K=0 (ccw pro kladne A)
pripad, presne jak popisuje jeho vlastni hlavicka ("pro kladnou
hodnotu uhlu, smysl otaceni ccw"). GL3 opcode V08 pridava volitelny
parametr K (0=ccw default, 1=cw) tak, ze pro K=1 se pouzity uhel
jednoduse obrati (viz G10.md 'V08 - Vektor otoceny o uhel').

Puvodni vypocet: B=ACOS(X1/A1) (uhel vektoru V v <0,PI>), s korekci
znamenka B=2*PI-B pro Y1<0 (doplneni do <0,2*PI) - coz je jen jina
cesta k polarnimu uhlu vektoru V, matematicky totozna s atan2(Y1,X1)
(lisi se jen tim, ze atan2 vraci vysledek v (-PI,PI> misto <0,2*PI) -
na vysledny COS/SIN po pricteni uhlu A to nema vliv, jde o stejny bod
na kruznici). Zde pouzit atan2 - vyhne se i domenove chybe ACOS, kdyz
X1/A1 kvuli zaokrouhlovani mirne prekroci <-1,1>.
"""
import math

from .types import Vector

_TOL = 1e-3  # stejna tolerance jako V208.FOR (1E-3)


def rotate_vector(vector, angle_deg, k=0):
    """V08: VM=V08>V,A[,K] - vektor V otoceny o uhel A (stupne), delka
    zachovana. K=0 (default) ccw pro kladne A, K=1 cw (viz hlavicka
    modulu). Nulovy vstupni vektor V je chyba (puvodni J=2080)."""
    length = math.hypot(vector.x, vector.y)
    if length <= _TOL:
        raise ValueError("V08: vstupni vektor V je nulovy (puvodni J=2080)")

    base_angle = math.atan2(vector.y, vector.x)
    delta = math.radians(angle_deg)
    if int(round(k)) != 0:
        delta = -delta

    new_angle = base_angle + delta
    return Vector(math.cos(new_angle) * length, math.sin(new_angle) * length, 0.0)
