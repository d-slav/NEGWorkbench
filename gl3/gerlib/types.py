# -*- coding: utf-8 -*-
"""
gerlib.types - zakladni geometricke typy.

Zadna zavislost na GL3 interpretru ani FreeCADu - cisty Python, pouzitelny
kdekoliv. Point/Vector nesou i Z, aby stejne tridy sly pouzit pro 2D i 3D
objekty (2D pouziva jen Z=0.0).
"""


class Point:
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __repr__(self):
        return "Point(%.3f, %.3f, %.3f)" % (self.x, self.y, self.z)


class Vector:
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __repr__(self):
        return "Vector(%.3f, %.3f, %.3f)" % (self.x, self.y, self.z)


class Line:
    """Primka: bod + smer."""
    __slots__ = ("origin", "direction")

    def __init__(self, origin, direction):
        self.origin, self.direction = origin, direction

    def __repr__(self):
        return "Line(origin=%r, direction=%r)" % (self.origin, self.direction)


class Circle:
    """Kruznice: stred, polomer, normala roviny."""
    __slots__ = ("center", "radius", "normal")

    def __init__(self, center, radius, normal=None):
        self.center, self.radius = center, radius
        self.normal = normal or Vector(0, 0, 1)

    def __repr__(self):
        return "Circle(center=%r, r=%.3f)" % (self.center, self.radius)


class Plane:
    """Rovina: bod + normala."""
    __slots__ = ("origin", "normal")

    def __init__(self, origin, normal):
        self.origin, self.normal = origin, normal

    def __repr__(self):
        return "Plane(origin=%r, normal=%r)" % (self.origin, self.normal)


class Spline:
    """Krivka typu S - kubicky Hermitovsky splajn danymi uzlovymi body a
    tecnymi vektory v kazdem uzlu (odpovida zaznamum QA,QB,UA,UB z
    SPLIN.FOR - kazdy segment je kubicky Hermitovsky kus parametrizovany
    0-1 mezi sousednimi uzly)."""
    __slots__ = ("points", "tangents", "closed")

    def __init__(self, points, tangents, closed=False):
        self.points = list(points)
        self.tangents = list(tangents)  # stejna delka jako points
        self.closed = closed

    def __repr__(self):
        kind = "uzavrena" if self.closed else "otevrena"
        return "Spline(%d uzlu, %s)" % (len(self.points), kind)


class Curve:
    """Krivka/retezec bodu (diskretizovana krivka - polygonovy tah).

    closed  - jestli prvni a posledni bod splyvaji (vzdalenost < 1e-3).
    indices - 1-based index kazdeho bodu podle puvodniho GL3 algoritmu
              (E01.FOR): 1,2,...,N-1,N-1 - POSLEDNI bod sdili index
              s predposlednim.
    is_end  - priznak "toto je posledni bod" (v originale PARAM=1D0 misto
              0D0) - jen posledni bod ma True.
    eps     - tolerance ulozena spolu s krivkou (u E01.FOR vzdy 0.0).

    Presny vyznam indices/is_end pro dalsi operace (napr. hledani N-teho
    bodu) zatim neznáme, ale zachovavame je 1:1 podle originalu, at se na
    ne pripadne muzou spolehnout."""
    __slots__ = ("points", "closed", "indices", "is_end", "eps")

    def __init__(self, points, closed=False, indices=None, is_end=None, eps=0.0):
        self.points = list(points)
        self.closed = closed
        self.indices = list(indices) if indices is not None else list(range(1, len(self.points) + 1))
        self.is_end = list(is_end) if is_end is not None else [False] * len(self.points)
        self.eps = eps

    def __repr__(self):
        kind = "uzavrena" if self.closed else "otevrena"
        return "Curve(%d bodu, %s)" % (len(self.points), kind)
