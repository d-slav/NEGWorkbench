# -*- coding: utf-8 -*-
"""
Prikaz TRA23 (NEG jazykova specifikace) - Transformace z roviny do
prostoru.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz zadani uzivatele):

    TRA23,pg1,pg2,vi1,vi2

    pg1 = vystupni (prostorova) promenna/pole - vysledek transformace.
    pg2 = vstupni (rovinna) promenna/pole - co se ma transformovat.
    vi1 = pocet transformovanych objektu - PLATI JEN PRO POLE (viz
          _exec_tra23 v gl3_interpreter.py: rozliseni pole/jednotlivy
          objekt se dela za behu podle skutecne hodnoty pg2, ne staticky).
    vi2 = cislo souradnicove soustavy definovane driv prikazem DCOOS3
          (viz geplib.dcoos3).

Podporovane typove dvojice (viz tabulka v zadani uzivatele) - ZATIM jen
to, co je momentalne potreba, dalsi pribudou stejnym zpusobem, az budou
potreba:
    P -> Q   (bod)
    S -> T   (krivka)

Rovinny bod/krivka (P/S) nese souradnice (x, y[, z=0 - Point/Vector v
gerlib nesou z vzdy, pro 2D objekty nepouzite]) jako MISTNI souradnice
V RAMCI souradnicove soustavy definovane DCOOS3 - transformace bodu je
proto proste: bod_zakladni = origin + x*ex + y*ey + z*ez. Smerove
veliciny (tecny vektory krivky) se transformuji BEZ pocatku (jen
rotace): vektor_zakladni = x*ex + y*ey + z*ez.
"""
from gerlib.types import Point, Vector, Spline


def transform_point3(point, coord_system):
    """Bod (jeho x,y,z se berou jako MISTNI souradnice v coord_system)
    -> bod v zakladni souradnicove soustave."""
    cs = coord_system
    x, y, z = point.x, point.y, point.z
    return Point(
        cs.origin.x + x * cs.ex.x + y * cs.ey.x + z * cs.ez.x,
        cs.origin.y + x * cs.ex.y + y * cs.ey.y + z * cs.ez.y,
        cs.origin.z + x * cs.ex.z + y * cs.ey.z + z * cs.ez.z,
    )


def transform_vector3(vector, coord_system):
    """Smerovy vektor (napr. tecna krivky) -> zakladni s.s., BEZ pocatku
    (jen rotace, zadny posun)."""
    cs = coord_system
    x, y, z = vector.x, vector.y, vector.z
    return Vector(
        x * cs.ex.x + y * cs.ey.x + z * cs.ez.x,
        x * cs.ex.y + y * cs.ey.y + z * cs.ez.y,
        x * cs.ex.z + y * cs.ey.z + z * cs.ez.z,
    )


def transform_spline3(spline, coord_system):
    """Cela krivka (Spline) - transformuje vsechny uzlove body i tecny
    (a segment_tangents, pokud jsou - viz S01/'chordalni' parametrizace).
    opcode/parametrization/closed se prenasi beze zmeny (popisuji TVAR
    krivky, ne souradnou soustavu, ve ktere lezi)."""
    points = [transform_point3(p, coord_system) for p in spline.points]
    tangents = [transform_vector3(t, coord_system) for t in spline.tangents]
    segment_tangents = None
    if spline.segment_tangents is not None:
        segment_tangents = [
            (transform_vector3(t0, coord_system), transform_vector3(t1, coord_system))
            for (t0, t1) in spline.segment_tangents
        ]
    return Spline(
        points, tangents,
        closed=spline.closed,
        opcode=spline.opcode,
        parametrization=spline.parametrization,
        segment_tangents=segment_tangents,
    )


def transform3(value, coord_system):
    """Dispatch podle skutecneho gerlib typu hodnoty (GL3 prefix - P vs.
    Q, S vs. T - uz interpret vyresil pri cteni/zapisu promenne; tady
    rozhoduje jen skutecny Python typ). Rozsirit, az pribudou dalsi
    dvojice z tabulky (V->U, L->M, C->G, E->H)."""
    if isinstance(value, Point):
        return transform_point3(value, coord_system)
    if isinstance(value, Spline):
        return transform_spline3(value, coord_system)
    raise TypeError(
        "TRA23: transformace typu '%s' zatim neni podporovana (jen bod "
        "P->Q a krivka S->T)" % (type(value).__name__,)
    )
