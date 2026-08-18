# -*- coding: utf-8 -*-
"""
Procedura V34 (GL3 opcode V34)      LET,n.p.,Uh.Hradiste (P.Franc)
Knihovna GL3E2                                      Unor 1983

Ucel:    Jednotkova normala 2D krivky v obecnem bode.

Uziti:   VM=V34>P,S,K<
    P - bod lezici na krivce S (jinak chyba, puvodni IER=272)
    S - krivka (Spline)
    K - 0 = vlevo (pri pohledu ve smeru krivky), 1 = vpravo

Primy prepis V34.FOR: najde jednotkovy tecny vektor krivky v bode P
(V37/gerlib.v37.curve_tangent_at_point - interni pomocna procedura;
zdroj V37.FOR nedodan, ucel odvozen z kontextu volani, viz tamni
hlavicka), pak ho pootoci o 90 stupnu (V231/gerlib.v230.
perpendicular_vector - stejna K=0 vlevo/K=1 vpravo konvence jako
puvodni V231).
"""
from .v37 import curve_tangent_at_point
from .v230 import perpendicular_vector


def curve_normal_at_point(point, spline, k):
    """V34: VM=V34>P,S,K - jednotkova normala krivky S v bode P (K=0
    vlevo, K=1 vpravo ve smeru krivky)."""
    try:
        tangent = curve_tangent_at_point(spline, point)
    except ValueError as exc:
        raise ValueError("V34: %s (puvodni IER=272)" % exc)
    return perpendicular_vector(tangent, int(round(k)))
