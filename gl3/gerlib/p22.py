# -*- coding: utf-8 -*-
"""
Procedura P22        LET, k.p., Uh.Hradiste
Knihovna GL3E2                                     Unor 1983

Ucel:    Prusecik primky s krivkou 2D spline.

Uziti:   PM=P22>L,S,K<     K - poradi pruseciku <1,...>

Chyba:   K < 1 nebo mene nez K pruseciku nalezeno -> puvodni IER=237

Zavislosti: gerlib.glpru (samotne hledani pruseciku po segmentech).
"""

from .glpru import line_curve_intersections


def intersection(spline, line, k):
    """P22: K-ty (1-based) prusecik 'line' s 'spline'."""
    k_int = int(round(k))
    if k_int < 1:
        raise ValueError("P22: K musi byt >= 1 (puvodni chyba 237), dostal %r" % (k,))

    hits = line_curve_intersections(spline, line)
    if k_int > len(hits):
        raise ValueError(
            "P22: primka a krivka maji jen %d prusecik(u), pozadovano K=%d "
            "(puvodni chyba 237)" % (len(hits), k_int)
        )
    return hits[k_int - 1][2]
