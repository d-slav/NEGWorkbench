# -*- coding: utf-8 -*-
"""gerlib.constants - vzdy dostupne preddefinovane geometricke konstanty
(pocatek soustavy, jednotkove vektory os, osy, souradnicove roviny)."""

from .types import Point, Vector, Line, Plane


def builtin_constants():
    """Vraci CERSTVOU kopii vsech konstant (ne sdilenou instanci) - aby
    pripadna budouci operace, ktera by (chybne) mutovala bod/vektor na
    miste misto vraceni nove hodnoty, nemohla "poskodit" konstantu pro
    dalsi pouziti."""
    return {
        "DPI": 3.1415927,

        # rovinne (2D)
        "P0": Point(0.0, 0.0, 0.0),
        "V0": Vector(0.0, 0.0, 0.0),
        "VX": Vector(1.0, 0.0, 0.0),
        "VY": Vector(0.0, 1.0, 0.0),
        "VXN": Vector(-1.0, 0.0, 0.0),
        "VYN": Vector(0.0, -1.0, 0.0),
        "LX": Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0)),
        "LY": Line(Point(0.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)),

        # prostorove (3D)
        "Q0": Point(0.0, 0.0, 0.0),
        "U0": Vector(0.0, 0.0, 0.0),
        "UX": Vector(1.0, 0.0, 0.0),
        "UY": Vector(0.0, 1.0, 0.0),
        "UZ": Vector(0.0, 0.0, 1.0),
        "UXN": Vector(-1.0, 0.0, 0.0),
        "UYN": Vector(0.0, -1.0, 0.0),
        "UZN": Vector(0.0, 0.0, -1.0),
        "MX": Line(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0)),
        "MY": Line(Point(0.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)),
        "MZ": Line(Point(0.0, 0.0, 0.0), Vector(0.0, 0.0, 1.0)),
        "RXY": Plane(Point(0.0, 0.0, 0.0), Vector(0.0, 0.0, 1.0)),
        "RXZ": Plane(Point(0.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)),
        "RYZ": Plane(Point(0.0, 0.0, 0.0), Vector(1.0, 0.0, 0.0)),
    }
