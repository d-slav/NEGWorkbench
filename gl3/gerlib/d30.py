# -*- coding: utf-8 -*-
"""
GL3 opcode D30 - ZDROJAK NENI K DISPOZICI, popsano jen v dokumentaci:

    DM=D30>pg,K     Vyjmuta slozka geometrickeho objektu
                    pg: D, A, P, V, C, L, Q, U, R, M, G.
                    Vyber K: 1 - x, 2 - y, 3 - z, ...

Cislovani slozek nize odpovida internimu zaznamu, jak ho pouziva SCALEX.FOR
(viz scale.py):
    D, A (skalar)     - jen K=1 (hodnota sama)
    P, Q (bod)        - K=1:x, 2:y, 3:z
    V, U (vektor)     - K=1:x, 2:y, 3:z
    C (kruznice 2D)   - K=1:stred.x, 2:stred.y, 3:polomer
    L (primka 2D)     - K=1:pocatek.x, 2:pocatek.y, 3:smer.x, 4:smer.y

Pozor: primka (M) a kruznice (G) v prostoru maji podle SCALEX.FOR JINE
cislovani slozek nez jejich 2D protejsky (M: 1-3 pocatek xyz, 4-6 smer xyz;
G: 1-3 stred xyz, 4-6 normala xyz, 7 polomer) - protoze nase Line/Circle
tridy nerozlisuji "je to 2D nebo 3D pouziti", tahle implementace pouziva
vzdy 2D (L/C) konvenci. Pro M/G by bylo potreba vedet, ktery GL3 typovy
prefix se skutecne pouzil - zatim nepodporovano.
"""

from .types import Point, Vector, Line, Circle


def get_component(obj, k):
    k = int(round(k))

    if isinstance(obj, (int, float)):
        if k != 1:
            raise ValueError("D30: skalar (D/A) ma jen slozku K=1 (dostal K=%d)" % (k,))
        return obj

    if isinstance(obj, (Point, Vector)):
        if k == 1:
            return obj.x
        if k == 2:
            return obj.y
        if k == 3:
            return obj.z
        raise ValueError("D30: bod/vektor (P/V/Q/U) ma jen slozky K=1..3 (dostal K=%d)" % (k,))

    if isinstance(obj, Line):
        if k == 1:
            return obj.origin.x
        if k == 2:
            return obj.origin.y
        if k == 3:
            return obj.direction.x
        if k == 4:
            return obj.direction.y
        raise ValueError(
            "D30: primka (L, 2D konvence) ma jen slozky K=1..4 (dostal K=%d)" % (k,)
        )

    if isinstance(obj, Circle):
        if k == 1:
            return obj.center.x
        if k == 2:
            return obj.center.y
        if k == 3:
            return obj.radius
        raise ValueError(
            "D30: kruznice (C, 2D konvence) ma jen slozky K=1..3 (dostal K=%d)" % (k,)
        )

    raise TypeError("D30: typ objektu %r zatim neni podporovan" % (obj,))
