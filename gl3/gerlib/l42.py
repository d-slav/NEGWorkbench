# -*- coding: utf-8 -*-
"""
Procedura L42 (GL3 opcode L42)      LET, n.p., Uh.Hradiste
Knihovna GL3E2                                      Unor 1983

Ucel:    Primka kolma z bodu ke krivce (2D).

Uziti:   LM=L42>P,S,K<
    P - vnejsi bod
    S - krivka (Spline)
    K - poradove cislo (1-based) - K-ty prusecik s orientovanou
        krivkou (=K-ty patni bod, viz P42), pocitany od jejiho
        pocatku. Mimo <1,M> (M = skutecny pocet patnich bodu) ->
        chyba (puvodni IER=290).

Primka LM prochazi PUVODNIM bodem P (ne patnim bodem!) a je normalou
krivky S v K-tem patnim bode (viz G10.md 'L42 - Primka kolma ke
krivce bodem').

Primy prepis L42.FOR - jen skladani uz existujicich casti:
  1) P42 (gerlib.p42.nearest_point) - najde K-ty patni bod na S.
  2) V34 (gerlib.v34.curve_normal_at_point, K=0 pevne - viz puvodni
     "IIN(1,13)=0" - smer normaly tu nezalezi, pouzije se jen jako
     smerovy vektor primky) - normala krivky v tomto patnim bode.
  3) L02/L302 (gerlib.l02.line_through_point) - primka PUVODNIM bodem
     P a timto smerem.
"""
from .p42 import nearest_point
from .v34 import curve_normal_at_point
from .l02 import line_through_point


def perpendicular_to_curve(point, spline, k):
    """L42: LM=L42>P,S,K - primka bodem P, kolma ke krivce S v jejim
    K-tem patnim bode (viz hlavicka modulu)."""
    try:
        foot = nearest_point(spline, point, k)
    except ValueError as exc:
        raise ValueError("L42: %s (puvodni IER=290)" % exc)
    normal = curve_normal_at_point(foot, spline, 0)
    return line_through_point(point, normal)
