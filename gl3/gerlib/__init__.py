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
from .l00 import line_from_coords
from .l02 import line_through_point
from .l04 import line_through_two_points
from .p49 import copy_point
from .c49 import copy_circle
from .p47 import circle_center
from .l343 import perpendicular_bisector
from .c02 import circle_from_3_points
from .v230 import perpendicular_vector
from .l20 import parallel_line
from .npo import point_count
from .p48 import chain_node, spline_node, curve_node
from .glkoe import segment_coefficients
from .glfun import evaluate as evaluate_segment
from .glply import polynomial_roots, real_roots_in_range
from .p40 import foot_point_on_line
from .p42 import foot_points, nearest_point
from .rkseg import curvature_radius_at
from .d50 import nearest_point_on_curve, radius_of_curvature
from .glpru import implicit_line, line_curve_intersections
from .p22 import intersection as line_curve_intersection
from .l45 import tangent_line_parallel
from .accur import set_accuracy, get_accuracy, reset_accuracy
from .e45 import discretize
from .nlsolve import solve as solve_nonlinear
from .sgpat import nearest_distance as sgpat_nearest_distance
from .s51 import offset_curve
from .errors import NoSolution
from .p00 import point_from_coords
from .c00 import circle_from_coords
from .c01 import circle_from_point
from .c32 import tangent_to_two_lines
from .c33 import tangent_to_line_and_circle
from .c34 import tangent_to_two_circles
from .circle_geom import line_circle_intersection, circle_circle_intersection

from .e01 import make_chain, tangent_point_on_chain
from .p85 import tangent_point
from .p86 import tangent_point_from_line
from .l46 import tangent_line
from .s03 import make_spline
from .s01 import make_spline as make_spline1

from .p51 import line_chain_intersection, line_chain_intersections
from .scale import scale

__all__ = [
    "Point", "Vector", "Line", "Circle", "Plane", "Curve", "Spline",
    "builtin_constants",
    "unit_vector", "canonical_unit_vector", "polar_angle_deg", "angle_between_deg",
    "is_zero_vector", "solve_tridiagonal", "tangent_vectors", "tangent_vectors_chordal",
    "sum_or_diff", "product_or_quotient",
    "point_point", "point_line", "vector_magnitude", "get_component", "index_parameter",
    "triangle_area", "triangle_area_signed", "triangle_area_from_lines", "circle_area",
    "offset_point", "interpolate_point", "line_intersection",
    "line_from_coords", "line_through_point", "line_through_two_points",
    "copy_point", "copy_circle", "circle_center",
    "perpendicular_bisector", "circle_from_3_points",
    "perpendicular_vector", "parallel_line",
    "point_count", "chain_node", "spline_node", "curve_node",
    "segment_coefficients", "evaluate_segment", "polynomial_roots",
    "real_roots_in_range", "foot_points", "nearest_point",
    "foot_point_on_line",
    "curvature_radius_at", "nearest_point_on_curve", "radius_of_curvature",
    "implicit_line", "line_curve_intersections", "line_curve_intersection",
    "line_chain_intersection", "line_chain_intersections",
    "tangent_line_parallel",
    "set_accuracy", "get_accuracy", "reset_accuracy", "discretize",
    "solve_nonlinear", "sgpat_nearest_distance", "offset_curve",
    "make_chain", "tangent_point_on_chain",
    "tangent_point", "tangent_point_from_line", "tangent_line",
    "make_spline", "make_spline1",
    "scale",
    "point_from_coords", "circle_from_coords", "circle_from_point",
    "tangent_to_two_lines", "tangent_to_line_and_circle", "tangent_to_two_circles",
    "line_circle_intersection", "circle_circle_intersection",
    "NoSolution",
]
