# -*- coding: utf-8 -*-
"""
Procedura P51 (GL3 opcode P51)

Ucel:    Prusecik primky s retezcem (Curve).

Uziti:   PM=P51>>L,E,K
         PM = prusecik primky L s retezcem E.
         K  = poradi pruseciku pocitaneho od pocatku retezce (1-based, K >= 1).

Chyba:   K < 1 nebo nalezeno mene nez K pruseciku -> ValueError (puvodni chyba 237).
"""
import math

from .types import Point, Line, Curve


def line_chain_intersections(line, curve, tol=1e-5):
    """Najde vsechny pruseciky primky 'line' s retezcem 'curve' v poradi
    od zacatku retezce ke konci.

    Vraci seznam bodu Point(x, y, 0.0).
    """
    if isinstance(line, Curve) and isinstance(curve, Line):
        line, curve = curve, line

    x0, y0 = line.origin.x, line.origin.y
    vx, vy = line.direction.x, line.direction.y

    line_len = math.hypot(vx, vy)
    if line_len < 1e-9:
        raise ValueError("P51: smerovy vektor primky je nulovy")

    # Implicitni primka: cx * x + cy * y + c0 = 0
    cx = -vy
    cy = vx
    c0 = -(cx * x0 + cy * y0)

    pts = curve.points
    n = len(pts)
    if n < 2:
        return []

    hits = []

    for i in range(n - 1):
        p0, p1 = pts[i], pts[i + 1]
        x1, y1 = p0.x, p0.y
        x2, y2 = p1.x, p1.y

        dx = x2 - x1
        dy = y2 - y1

        f0 = cx * x1 + cy * y1 + c0
        f1 = cx * x2 + cy * y2 + c0

        denom = f0 - f1  # -(cx * dx + cy * dy)

        if abs(denom) < 1e-9:
            # Usecka je rovnobezna s primkou
            if abs(f0) < tol:
                # Usecka lezi na primce: pridame jeji pocatecni bod
                hits.append(Point(x1, y1, 0.0))
                # Pokud jde o posledni segment, pridame i koncovy bod
                if i == n - 2:
                    hits.append(Point(x2, y2, 0.0))
            continue

        t = f0 / denom

        # Koren lezi na usecce v mezich [-tol, 1 + tol]
        if -tol <= t <= 1.0 + tol:
            # Pokud koren lezi na konci segmentu (t ~ 1.0) a neni to posledni
            # segment, preskocime ho - nasledujici segment ho prida jako t ~ 0.0.
            if i < n - 2 and abs(1.0 - t) < tol:
                continue

            t_clamped = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            qx = x1 + t_clamped * dx
            qy = y1 + t_clamped * dy
            hits.append(Point(qx, qy, 0.0))

    return hits


def line_chain_intersection(line, curve, k=1):
    """P51: K-ty (1-based) prusecik primky 'line' s retezcem 'curve'."""
    k_int = int(round(k))
    if k_int < 1:
        raise ValueError("P51: K musi byt >= 1 (puvodni chyba 237), dostal %r" % (k,))

    hits = line_chain_intersections(line, curve)
    if k_int > len(hits):
        raise ValueError(
            "P51: primka a retezec maji jen %d prusecik(u), pozadovano K=%d "
            "(puvodni chyba 237)" % (len(hits), k_int)
        )
    return hits[k_int - 1]
