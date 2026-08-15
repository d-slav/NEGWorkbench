# -*- coding: utf-8 -*-
"""
Procedura P140 (GL3 opcode P40)

Ucel:    Patni bod na primce (kolmice spustena z bodu P na primku L).

Uziti:   PM=P40>>P,L
         PM = patni bod kolmice spustene z bodu P na primku L.
              Lezi-li bod P na primce, jsou oba body totozne.

Parametry:
    P (point): Bod (Point)
    L (line):  Primka (Line)
"""
from .types import Point, Line


def foot_point_on_line(point, line):
    """P40: Patni bod kolmice spustene z bodu 'point' na primku 'line'."""
    if isinstance(point, Line) and isinstance(line, Point):
        point, line = line, point

    x0, y0 = line.origin.x, line.origin.y
    z0 = getattr(line.origin, "z", 0.0)

    vx, vy = line.direction.x, line.direction.y
    vz = getattr(line.direction, "z", 0.0)

    denom = vx * vx + vy * vy + vz * vz
    if denom < 1e-12:
        raise ValueError("P40: smerovy vektor primky je nulovy")

    xp, yp = point.x, point.y
    zp = getattr(point, "z", 0.0)

    dx = xp - x0
    dy = yp - y0
    dz = zp - z0

    t = (dx * vx + dy * vy + dz * vz) / denom
    return Point(x0 + t * vx, y0 + t * vy, z0 + t * vz)
