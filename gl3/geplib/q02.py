# -*- coding: utf-8 -*-
"""
Operace Q02 (NEG jazykova specifikace) - Bod zmenou K-te souradnice bodu
(pravouhle posunuti).

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'Q02 - Bod zmenou slozky
(pravouhle posunuti)' a zadani uzivatele):

    QM=Q02>Q,D,K

    Q = bod (Point)
    D = skalarni vyraz - nova hodnota K-te souradnice
    K = vyberove cislo: 1 = x-ova slozka, 2 = y-ova, 3 = z-ova.
        Zbyvajici dve slozky zustavaji puvodni (z bodu Q).
"""
from gerlib.types import Point


def make_point_by_component(q, d, k):
    """Q02: QM=Q02>Q,D,K - bod vznikly opravou K-te souradnice bodu Q na
    hodnotu D; K musi byt 1 (x), 2 (y) nebo 3 (z)."""
    k_int = int(round(k))
    if k_int == 1:
        return Point(d, q.y, q.z)
    if k_int == 2:
        return Point(q.x, d, q.z)
    if k_int == 3:
        return Point(q.x, q.y, d)
    raise ValueError("Q02: vyberove cislo K musi byt 1 (x), 2 (y) nebo 3 (z), dostal %r" % (k,))
