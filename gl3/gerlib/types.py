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

    @classmethod
    def r01(cls, normal_ref, distance):
        """RM=R01>>U,D - Rovina normalou a vzdalenosti od pocatku."""
        from geplib.plane import make_plane_r01
        return make_plane_r01(normal_ref, distance)

    def equation_coefficients(self):
        """Vrati koeficienty obecne rovnice roviny (a, b, c, d), kde:
            a*x + b*y + c*z + d = 0.
        """
        a, b, c = self.normal.x, self.normal.y, self.normal.z
        d = -(a * self.origin.x + b * self.origin.y + c * self.origin.z)
        return (a, b, c, d)

    def distance_to_point(self, point):
        """Orientovana (se znamenkem) vzdalenost bodu od roviny."""
        px = getattr(point, "x", point[0] if isinstance(point, (tuple, list)) else 0.0)
        py = getattr(point, "y", point[1] if isinstance(point, (tuple, list)) else 0.0)
        pz = getattr(point, "z", point[2] if isinstance(point, (tuple, list)) else 0.0)
        a, b, c, d = self.equation_coefficients()
        return a * px + b * py + c * pz + d

    def project_point(self, point):
        """Kolmy prumet bodu do roviny."""
        px = getattr(point, "x", point[0] if isinstance(point, (tuple, list)) else 0.0)
        py = getattr(point, "y", point[1] if isinstance(point, (tuple, list)) else 0.0)
        pz = getattr(point, "z", point[2] if isinstance(point, (tuple, list)) else 0.0)
        dist = self.distance_to_point(point)
        return Point(
            px - dist * self.normal.x,
            py - dist * self.normal.y,
            pz - dist * self.normal.z,
        )


class Spline:
    """Krivka typu S - kubicky Hermitovsky splajn danymi uzlovymi body a
    tecnymi vektory (odpovida zaznamum QA,QB,UA,UB ze SPLIN.FOR - kazdy
    segment je kubicky Hermitovsky kus parametrizovany 0-1 mezi sousednimi
    uzly).

    opcode/parametrization - "vlajka jak krivka vznikla": ktery GL3 opcode
    ji vyrobil (napr. "S03", "S01") a jakou parametrizaci pouziva
    ("uniform" - ignoruje skutecne vzdalenosti mezi body, vs "chordal" -
    tecny prepocitane skutecnou delkou tetivy segmentu). Dulezite nejen
    pro Export, ale i do budoucna pro pravidla, ktere krivky lze pouzit
    pro generovani ploch.

    tangents       - JEDNA tecna na uzel (delka jako points). Autoritativni
                     jen pokud segment_tangents is None (typicky "uniform"
                     parametrizace jako S03, kde je tecna na uzlu skutecne
                     sdilena obema sousednimi segmenty). Pro "chordal"
                     pripady (S01) je tu jen informativne (viz
                     segment_tangent_pair()).
    segment_tangents - None (staci tangents), NEBO seznam N-1 dvojic
                     (tecna_na_zacatku_segmentu, tecna_na_konci_segmentu) -
                     jedna dvojice na kazdy segment. Pouzivano u
                     chordalni parametrizace (S01/GLSPL.FOR), kde tecna
                     "na tomtez" uzlu ma jinou velikost podle toho, pro
                     ktery ze dvou sousednich segmentu se pouzije (kazdy
                     segment se skaluje svou vlastni delkou tetivy).
    """
    __slots__ = ("points", "tangents", "closed", "opcode", "parametrization", "segment_tangents")

    def __init__(self, points, tangents, closed=False, opcode="S03",
                 parametrization="uniform", segment_tangents=None):
        self.points = list(points)
        self.tangents = list(tangents)  # stejna delka jako points
        self.closed = closed
        self.opcode = opcode
        self.parametrization = parametrization
        self.segment_tangents = (
            [(t0, t1) for (t0, t1) in segment_tangents] if segment_tangents is not None else None
        )

    def segment_tangent_pair(self, i):
        """Tecny pouzitelne pro segment i (mezi body i a i+1) - funguje
        stejne bez ohledu na to, jestli krivka ma spolecnou tecnu na uzel
        (S03) nebo rozdilne tecny po segmentech (S01)."""
        if self.segment_tangents is not None:
            return self.segment_tangents[i]
        return (self.tangents[i], self.tangents[i + 1])

    def __repr__(self):
        kind = "uzavrena" if self.closed else "otevrena"
        return "Spline(%d uzlu, %s, %s/%s)" % (
            len(self.points), kind, self.opcode, self.parametrization
        )


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
