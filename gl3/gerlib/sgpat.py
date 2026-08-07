# -*- coding: utf-8 -*-
"""
Procedura SGPAT        LET, k.p., Uh.Hradiste
Knihovna GL3E2                                     Kveten 1985

Ucel:    Vypocet vzdalenosti bodu od segmentu kubickeho spline.

Uziti:   CALL SGPAT(DL,Q,RRK,JF)

Parametry:  Q    - vstupni bod
            RRK  - koeficienty segmentu (viz glkoe.segment_coefficients)
            DL   - vysledna (minimalni) vzdalenost
            JF   - chybove cislo (JF>0 - nenalezen zadny koren)

Algoritmus je matematicky TOTOZNY s P42 (paty kolmic - viz p42.py):
najde vsechny koreny kvintickeho polynomu (derivace kvadratu
vzdalenosti bodu od krivky, polozena rovna nule) v <0,1> a vrati
NEJMENSI z prislusnych vzdalenosti. Na rozdil od P42 SGPAT hleda jen
v presnem <0,1> (zadne presahy +-1e-4 pres kraje segmentu - u P42 to
bylo potreba kvuli detekci duplicitnich korenu na hranici sousednich
segmentu, tady operujeme na JEDINEM izolovanem segmentu, takze to
neni potreba - a puvodni zdroj presne takhle, bez presahu, vola
GLPLY1).

Pouziva se v S51 jako "orakulum" pro adaptivni deleni ekvidistanty -
merí, jak daleko je bod na aproximovane ekvidistantni krivce od
PUVODNI krivky, a porovnava se zjistenou hodnotou s ocekavanou
konstantni odchylkou.
"""

from .glfun import evaluate
from .glply import real_roots_in_range
from .p42 import _distance_derivative_poly


def nearest_distance(coeffs, point):
    """SGPAT: nejmensi vzdalenost bodu 'point' (x,y) od segmentu s
    koeficienty 'coeffs' (viz glkoe.segment_coefficients), hledano po
    celem <0,1>. Vraci None, pokud kvinticka derivace nema v <0,1>
    zadny koren (puvodni JF>0 - nenalezeno)."""
    wx = coeffs[0][3] - point[0]  # a0x - Px
    wy = coeffs[1][3] - point[1]  # a0y - Py
    poly = _distance_derivative_poly(coeffs, wx, wy)
    roots = real_roots_in_range(poly, 0.0, 1.0)
    if not roots:
        return None

    best = None
    for t in roots:
        xy = evaluate(coeffs, t, order=0)
        d = ((xy[0] - point[0]) ** 2 + (xy[1] - point[1]) ** 2) ** 0.5
        if best is None or d < best:
            best = d
    return best
