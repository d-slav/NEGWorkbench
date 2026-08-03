# -*- coding: utf-8 -*-
"""
gerlib - GEometrie Rovinna LIBrary.

Samostatna, na GL3/FreeCADu nezavisla knihovna 2D (a casti 3D) geometrie,
vznikla jako vedlejsi produkt reimplementace NEG/GL3 geometrickych operaci
(puvodni Fortran knihovna GL3E/GERLIBPC z LET Kunovice, 1985-1989).

Kazda operace ma svuj vlastni soubor pojmenovany podle GL3 opcode (d10.py,
d11.py, e01.py, l46.py, p85.py, p86.py, scale.py, ...) s puvodni Fortran
hlavickou (Ucel/Uziti/Parametry) jako dokumentaci. Nizkourovnove pomocne
operace bez vlastniho GL3 opcode (V220, A521, A510) si drzi puvodni
Fortran jmena.

types.py a constants.py nejsou operace, ale sdilena infrastruktura
(zakladni geometricke typy a preddefinovane konstanty).

Pouziti:
    from gerlib import Point, Curve, make_chain, tangent_line
"""

from .types import Point, Vector, Line, Circle, Plane, Curve, Spline
from .constants import builtin_constants

from .v220 import unit_vector
from .v221 import canonical_unit_vector
from .a521 import polar_angle_deg
from .a510 import angle_between_deg
from .vnorm import is_zero_vector
from .gtrin import solve_tridiagonal
from .dsn import tangent_vectors
from .dspn import tangent_vectors as tangent_vectors_chordal

from .d01 import sum_or_diff
from .d02 import product_or_quotient
from .d10 import point_point
from .d11 import point_line
from .d20 import vector_magnitude
from .d30 import get_component
from .d31 import index_parameter
from .d40 import triangle_area
from .d41 import triangle_area_from_lines
from .d42 import triangle_area_signed
from .d43 import circle_area

from .p10 import offset_point
from .p13 import interpolate_point
from .p20 import line_intersection
from .l02 import line_through_point
from .p49 import copy_point
from .c49 import copy_circle
from .p47 import circle_center

from .e01 import make_chain, tangent_point_on_chain
from .p85 import tangent_point
from .p86 import tangent_point_from_line
from .l46 import tangent_line
from .s03 import make_spline
from .s01 import make_spline as make_spline1

from .scale import scale

__all__ = [
    "Point", "Vector", "Line", "Circle", "Plane", "Curve", "Spline",
    "builtin_constants",
    "unit_vector", "canonical_unit_vector", "polar_angle_deg", "angle_between_deg",
    "is_zero_vector", "solve_tridiagonal", "tangent_vectors", "tangent_vectors_chordal",
    "sum_or_diff", "product_or_quotient",
    "point_point", "point_line", "vector_magnitude", "get_component", "index_parameter",
    "triangle_area", "triangle_area_signed", "triangle_area_from_lines", "circle_area",
    "offset_point", "interpolate_point", "line_intersection", "line_through_point",
    "copy_point", "copy_circle", "circle_center",
    "make_chain", "tangent_point_on_chain",
    "tangent_point", "tangent_point_from_line", "tangent_line",
    "make_spline", "make_spline1",
    "scale",
]
