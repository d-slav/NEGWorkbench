# -*- coding: utf-8 -*-
"""
Procedura SCALEX (GL3 prikaz SCALE)
Knihovna GL3E2

Ucel:    Meritkova transformace geometrickeho objektu.

Uziti (GL3): SCALE,pg1,pg2,vr,vi<

Puvodni SCALEX.FOR je nizkourovnovy loop pres RTAB zaznamy (stejna
infrastruktura jako E01/L46 - viz jejich soubory), ale samotna
transformacni logika podle typu objektu (BTY) je citelna a prekladame
ji 1:1:

  P, V (2D bod/vektor)  - LL1=2: skaluji se OBE slozky (x, y).
  L (primka)            - LL1=2,LL2=2: skaluje se jen POCATEK (x, y),
                           SMER (slozky 3,4) zustava beze zmeny (jednotkovy
                           vektor smeru je pri jednotnem meritku invariantni).
  C (kruznice, 2D)      - LL1=3 (default): skaluji se vsechny 3 slozky
                           (stred.x, stred.y, POLOMER) - polomer je delka,
                           takze se skaluje spravne, i kdyz kod nema pro
                           kruznici zadnou specialni vetev.
  E (retezec/Curve)     - vsechny body i EPS (tolerance) se skaluji,
                           topologie (closed/indices/is_end) se nemeni.

3D typy (Q/U/R/M/G) a krivky S/T/H zatim nemame jako Python typy - pro ne
vyhazujeme jasnou chybu.
"""

from .types import Point, Vector, Line, Circle, Curve


def scale(obj, factor):
    """Objekt transformovany v meritku 'factor' (kolem pocatku souradnic -
    viz modulovy docstring pro presnou logiku podle typu)."""
    if isinstance(obj, Point):
        return Point(obj.x * factor, obj.y * factor, obj.z * factor)

    if isinstance(obj, Vector):
        return Vector(obj.x * factor, obj.y * factor, obj.z * factor)

    if isinstance(obj, Line):
        return Line(
            Point(obj.origin.x * factor, obj.origin.y * factor, obj.origin.z * factor),
            Vector(obj.direction.x, obj.direction.y, obj.direction.z),  # smer beze zmeny
        )

    if isinstance(obj, Circle):
        return Circle(
            Point(obj.center.x * factor, obj.center.y * factor, obj.center.z * factor),
            obj.radius * factor,
            Vector(obj.normal.x, obj.normal.y, obj.normal.z),  # normala beze zmeny
        )

    if isinstance(obj, Curve):
        new_points = [
            Point(p.x * factor, p.y * factor, p.z * factor) if p is not None else None
            for p in obj.points
        ]
        return Curve(
            new_points,
            closed=obj.closed,
            indices=list(obj.indices),
            is_end=list(obj.is_end),
            eps=obj.eps * factor,
        )

    raise TypeError(
        "SCALE: typ objektu %r zatim neni podporovan (3D typy a krivky "
        "S/T/H jeste nemame jako Python tridy)" % (obj,)
    )
