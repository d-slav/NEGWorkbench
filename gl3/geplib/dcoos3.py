# -*- coding: utf-8 -*-
"""
Prikaz DCOOS3 (NEG jazykova specifikace) - Definice prostorove
souradnicove soustavy.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz zadani uzivatele):

    DCOOS3,vi,vg1,vg2,vg3

    vi  = cislo souradnicove soustavy, 1..10.
    vg1 = Q (bod) - pocatek nove soustavy (v souradnicich zakladni s.s.).
    vg2 = Q/U/M - urcuje kladny smer osy x':
            Q: kladna osa x' prochazi bodem vg2 (smer = vg2 - vg1)
            U: kladny smer osy x' je totozny se smerem vektoru vg2
            M: kladny smer osy x' je totozny s kladnym smerem primky vg2
    vg3 = Q/U/M - urcuje smer a orientaci osy y'. Osa y' lezi v rovine
          urcene osou x' a timhle smerem (Gram-Schmidt: slozka kolma na
          x'), kladny smer smeruje do polupoloviny, kam vg3 ukazuje:
            Q: rovina/polorovina dana bodem vg3 (smer = vg3 - vg1)
            U: rovina/polorovina dana vektorem vg3
            M: rovina/polorovina dana kladnym smerem primky vg3

Osa z' se dopocita jako ex' x ey' (krizovy soucin) - vznikla soustava je
tim padem VZDY pravotociva (a ex', ey', ez' jsou vzdy ortonormalni,
nezavisle na tom, jestli vg2/vg3 byly uz normalizovane).
"""
import math

from gerlib.types import Point, Vector, Line


class CoordSystem3(object):
    """Prostorova souradnicova soustava - pocatek + 3 ortonormalni osy,
    vsechny ve slozkach ZAKLADNI (base) souradnicove soustavy."""
    __slots__ = ("origin", "ex", "ey", "ez")

    def __init__(self, origin, ex, ey, ez):
        self.origin, self.ex, self.ey, self.ez = origin, ex, ey, ez

    def __repr__(self):
        return "CoordSystem3(origin=%r, ex=%r, ey=%r, ez=%r)" % (
            self.origin, self.ex, self.ey, self.ez
        )


def _sub(a, b):
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(v):
    d = math.sqrt(_dot(v, v))
    if d < 1e-9:
        raise ValueError("DCOOS3: smerovy vektor je nulovy/degenerovany")
    return (v[0] / d, v[1] / d, v[2] / d)


def _direction_from(ref, origin):
    """Prevede vg2/vg3 (Q/U/M) na smerovy vektor (tuple x,y,z), jeste
    NEnormalizovany - viz modulovy docstring pro vyznam jednotlivych typu."""
    if isinstance(ref, Point):
        return _sub(ref, origin)
    if isinstance(ref, Vector):
        return (ref.x, ref.y, ref.z)
    if isinstance(ref, Line):
        d = ref.direction
        return (d.x, d.y, d.z)
    raise TypeError(
        "DCOOS3: ocekavan bod (Q), vektor (U) nebo primka (M), dostal %r"
        % (ref,)
    )


def define_coord_system3(origin, x_ref, y_ref):
    """Hlavni vypocet DCOOS3 - viz modulovy docstring. origin musi byt
    Point (vg1); x_ref/y_ref (vg2/vg3) libovolna kombinace Point/Vector/
    Line (Q/U/M)."""
    if not isinstance(origin, Point):
        raise TypeError("DCOOS3: pocatek (vg1) musi byt bod (Q)")

    ex = _norm(_direction_from(x_ref, origin))

    h = _direction_from(y_ref, origin)
    # Gram-Schmidt: cast h kolma na ex (lezici v rovine {ex, h}).
    h_dot_ex = _dot(h, ex)
    ey_raw = (
        h[0] - h_dot_ex * ex[0],
        h[1] - h_dot_ex * ex[1],
        h[2] - h_dot_ex * ex[2],
    )
    try:
        ey = _norm(ey_raw)
    except ValueError:
        raise ValueError(
            "DCOOS3: vg3 je rovnobezny s osou x' - nelze jednoznacne "
            "urcit rovinu x'y'"
        )

    ez = _cross(ex, ey)  # uz jednotkovy (ex, ey jsou ortonormalni)

    return CoordSystem3(origin, Vector(*ex), Vector(*ey), Vector(*ez))
