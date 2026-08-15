# -*- coding: utf-8 -*-
"""
geplib.plane - Trida pro rovinu v 3D prostoru a operace s rovinami.

Rovina je reprezentovana bodem v rovine (origin) a jednotkovym normalovym
vektorem (normal).

Implementovane operace:
  - R01 (make_plane_r01 / Plane.r01): RM=R01>>U,D
    Rovina normalou a vzdalenosti od pocatku.
"""
import math

from gerlib.types import Point, Vector, Line, Plane


def _extract_components(vec_or_obj):
    """Ziska trojici (x, y, z) z Vector, Point, Line (direction) nebo tuple/list."""
    if isinstance(vec_or_obj, (Vector, Point)):
        return (float(vec_or_obj.x), float(vec_or_obj.y), float(vec_or_obj.z))
    if isinstance(vec_or_obj, Line):
        d = vec_or_obj.direction
        return (float(d.x), float(d.y), float(d.z))
    if hasattr(vec_or_obj, "x") and hasattr(vec_or_obj, "y") and hasattr(vec_or_obj, "z"):
        return (float(vec_or_obj.x), float(vec_or_obj.y), float(vec_or_obj.z))
    if isinstance(vec_or_obj, (tuple, list)) and len(vec_or_obj) >= 3:
        return (float(vec_or_obj[0]), float(vec_or_obj[1]), float(vec_or_obj[2]))
    raise TypeError(
        "Ocekavan vektor (U), bod (Q), primka (M) nebo trojice (x,y,z), dostal: %r"
        % (vec_or_obj,)
    )


def canonical_unit_vector3(x, y, z, eps=1e-6):
    """Vrati jednotkovy, smluvne orientovany 3D vektor jako tuple (nx, ny, nz).

    Konvence (smluvni orientace podle GL3 / rozsireni V221 do 3D):
      - prvni nenulova slozka (v poradi x, y, z) urcuje orientaci:
        - je-li x > eps: kladna orientace (ponechat)
        - je-li x <= -eps: obratit (-x, -y, -z)
        - je-li |x| <= eps (x cca 0):
          - je-li y > eps: kladna orientace (ponechat)
          - je-li y <= -eps: obratit (-x, -y, -z)
          - je-li |y| <= eps (x i y cca 0):
            - je-li z < 0: obratit (-x, -y, -z)
            - jinak ponechat

    Vyvola ValueError, pokud je vektor nulovy (delka < 1e-9).
    """
    length = math.sqrt(x * x + y * y + z * z)
    if length < 1e-9:
        raise ValueError("R01: smerovy/normalovy vektor je nulovy (delka < 1e-9)")

    nx, ny, nz = x / length, y / length, z / length

    if nx > eps:
        return nx, ny, nz
    if nx <= -eps:
        return -nx, -ny, -nz

    if ny > eps:
        return nx, ny, nz
    if ny <= -eps:
        return -nx, -ny, -nz

    if nz < 0.0:
        return -nx, -ny, -nz
    return nx, ny, nz


def make_plane_r01(normal_ref, distance):
    """Operace R01 (NEG jazykova specifikace):
        RM=R01>>U,D

    Rovina ma normalovy vektor odvozen od obecneho vektoru U normalizaci
    a smluvni orientaci. Rovina lezi od pocatku ve smeru vektoru U (smluvni
    normaly) ve vzdalenosti D.

    Parametry:
        normal_ref (U): Vector (nebo Point/Line/trojice) zadavajici smer normaly.
        distance (D):   Skalarni hodnota - vzdalenost roviny od pocatku.

    Vrací:
        Plane: instance tridy Plane s nastavenym origin a normal.
    """
    ux, uy, uz = _extract_components(normal_ref)
    nx, ny, nz = canonical_unit_vector3(ux, uy, uz)
    d = float(distance)

    origin = Point(d * nx, d * ny, d * nz)
    normal = Vector(nx, ny, nz)
    return Plane(origin, normal)


__all__ = ["Plane", "make_plane_r01", "canonical_unit_vector3"]
