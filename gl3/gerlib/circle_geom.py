# -*- coding: utf-8 -*-
"""
Sdilene pomocne funkce pro C33/C34 (kruznice tecna k primce+kruznici /
dvema kruznicim) - prusecik primky s kruznici a prusecik dvou kruznic.

Zadny primy Fortran ekvivalent - jde o standardni analytickou geometrii
(reseni kvadraticke rovnice), potreba jako stavebni kamen pro C33/C34.
"""

import math

from .types import Point
from .errors import NoSolution


def line_circle_intersection(line, center, radius):
    """Prusecik(y) primky (bod+smer) s kruznici (stred, polomer). Vraci
    seznam bodu SERAZENY vzestupne podle parametru t podel smeru primky
    (t=0 v line.origin, t roste ve smeru line.direction) - 0, 1 (tecna)
    nebo 2 body. Prazdny seznam, pokud se nedotykaji/neprotinaji."""
    dlen = math.hypot(line.direction.x, line.direction.y)
    if dlen < 1e-12:
        raise ValueError("line_circle_intersection: nulovy smerovy vektor primky")
    ux, uy = line.direction.x / dlen, line.direction.y / dlen

    # P(t) = origin + t*(ux,uy); |P(t)-center|^2 = radius^2
    dx = line.origin.x - center.x
    dy = line.origin.y - center.y
    b = 2.0 * (dx * ux + dy * uy)
    c = dx * dx + dy * dy - radius * radius
    disc = b * b - 4.0 * c  # a=1 (ux,uy jednotkovy)
    if disc < -1e-9:
        return []
    disc = max(disc, 0.0)
    sq = math.sqrt(disc)
    t1 = (-b - sq) / 2.0
    t2 = (-b + sq) / 2.0
    if abs(t1 - t2) < 1e-9:
        return [Point(line.origin.x + t1 * ux, line.origin.y + t1 * uy, 0.0)]
    return [
        Point(line.origin.x + t1 * ux, line.origin.y + t1 * uy, 0.0),
        Point(line.origin.x + t2 * ux, line.origin.y + t2 * uy, 0.0),
    ]


def circle_circle_intersection(center1, r1, center2, r2):
    """Prusecik(y) dvou kruznic. Vraci (left_point, right_point) - oba
    kandidaty prusecikove dvojice, kde 'left'/'right' jsou vzhledem k
    ORIENTOVANE spojnici center1->center2 (stejna konvence jako jinde -
    'left' = pri pohledu ve smeru center1->center2, otoceno o 90 CCW).
    Pro tecne se dotykajici kruznice jsou oba body totozne. NoSolution
    (kategorie "varovani" - viz errors.py), pokud se kruznice neprotinaji
    (prilis daleko, jedna uvnitr druhe bez dotyku, nebo stejny stred) -
    tohle je legitimni geometricky vysledek, ne bug."""
    dx = center2.x - center1.x
    dy = center2.y - center1.y
    d = math.hypot(dx, dy)
    if d < 1e-12:
        raise NoSolution("circle_circle_intersection: kruznice maji stejny stred")
    if d > r1 + r2 + 1e-9 or d < abs(r1 - r2) - 1e-9:
        raise NoSolution("circle_circle_intersection: kruznice se neprotinaji")

    a = (d * d + r1 * r1 - r2 * r2) / (2.0 * d)
    h_sq = max(r1 * r1 - a * a, 0.0)
    h = math.sqrt(h_sq)

    ux, uy = dx / d, dy / d
    mx = center1.x + a * ux
    my = center1.y + a * uy
    # kolmy (perpendicular) vektor, "left" = 90 CCW od smeru center1->center2
    px, py = -uy, ux

    left = Point(mx + h * px, my + h * py, 0.0)
    right = Point(mx - h * px, my - h * py, 0.0)
    return left, right
