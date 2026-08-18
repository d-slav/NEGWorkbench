# -*- coding: utf-8 -*-
"""
Operace Q38 (GL3 opcode Q38) - Prusecik krivky s rovinou.

Uziti (GL3): QM=Q38>T,R,K

    T - krivka (Spline, kubicky Hermitovsky splajn, viz gerlib.types.
        Spline - typicky vznikla operaci T01/T03/... )
    R - rovina (Plane)
    K - vyberove cislo: K-ty prusecik pocitany OD POCATKU KRIVKY, je-li
        pruseciku vice (viz G10.md 'Q38 - Prusecik krivky s rovinou').

Prime podle dodaneho Q38.FOR: Q38 jen priprava vstupu (implicitni
rovnice roviny z R(1..4)) a volani GLPRU s K=3 (viz gerlib.glpru -
STEJNA procedura, kterou uz pouziva P22 pro K=2/primku - viz tamni
hlavicka pro presny popis algoritmu a obou vrstev deduplikace).
Chyba (JF<>0 v GLPRU) -> puvodni IER=298.
"""
from gerlib.glpru import plane_curve_intersections
from gerlib.errors import NoSolution


def curve_plane_intersection(spline, plane, k):
    """Q38: QM=Q38>T,R,K - K-ty prusecik krivky T s rovinou R, pocitano
    od pocatku krivky (viz gerlib.glpru.plane_curve_intersections)."""
    k_int = int(round(k))
    if k_int < 1:
        raise ValueError("Q38: vyberove cislo K musi byt >= 1 (dostal %r)" % (k,))

    hits = plane_curve_intersections(spline, plane)
    if k_int > len(hits):
        raise NoSolution(
            "Q38: krivka a rovina maji jen %d prusecik(u), pozadovano "
            "K=%d (puvodni IER=298)" % (len(hits), k_int)
        )
    return hits[k_int - 1][2]
