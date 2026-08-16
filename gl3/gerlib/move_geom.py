# -*- coding: utf-8 -*-
"""
gerlib/move_geom.py - geometricke vyhodnoceni pohybovych frazi prikazu
MOVE (viz prirucka G18.md odst. "ROZDELENI ROVINNYCH POHYBOVYCH FRAZI
(MOVE)"), pouzivane predevsim pri vytvareni retezcu prikazy CRE/ENDCRE
(viz G10.md "VYTVARENI RETEZCU POMOCI KRESLICICH PRIKAZU").

Zadna zavislost na GL3 interpretru - cisty Python/gerlib, stejne jako
zbytek balicku. Interpret (gl3_interpreter.py) jen:
  - vyhodnoti argumenty jedne fraze na Python hodnoty (float/Point/
    Vector/Line/Circle/Curve/Spline),
  - zavola evaluate_move_phrase() s temito hodnotami a separatorem
    pouzitym v syntaxi fraze (None/'#'/':'/','),
  - vysledne body prida do budovaneho retezce.

Rozliseni KONKRETNI fraze (D, P, V, D#A, D1:D2, ...) se dela az TADY,
za behu, podle (poctu hodnot, separatoru, RUNTIME TYPU hodnot) - presne
stejnym zpusobem, jakym uz GL3 rozlisuje typy jinde (napr. D30/
get_component podle typu vstupniho objektu). Zadna staticka analyza
jmen promennych neni potreba, protoze v prirucce pouzita pismena
(D, P, V, L, C, E, S, K, ...) jsou jen OZNACENI OCEKAVANEHO TYPU
vyrazu, ne doslovne nazvy promennych.
"""

import math

from .types import Point, Vector, Line, Circle, Curve, Spline
from .v220 import unit_vector
from .a521 import polar_angle_deg
from .accur import get_accuracy
from .d31 import index_parameter
from .errors import NoSolution

_TOL = 1e-6


class MovePhraseError(ValueError):
    """Fraze prikazu MOVE se nepodarilo vyhodnotit (spatne typy/pocet
    parametru, nebo geometricky nesmyslny vstup - napr. bod nelezici
    na pozadovane primce/kruznici)."""
    pass


class MovePhraseNotYetImplemented(NotImplementedError):
    """Fraze je rozpoznana (odpovida znamemu tvaru z prirucky), ale jeji
    zpracovani jeste neni naportovano (typicky prechodove fraze -
    primka-primka, primka-kruznice, kruznice-primka, kruznice-kruznice,
    viz G18.md 'Rovinne prechodove fraze')."""
    pass


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _unit_dir(p_from, p_to):
    """Normalizovany smer p_from->p_to, nebo None pro nulovou (degenerovanou)
    usecku."""
    dx, dy = p_to.x - p_from.x, p_to.y - p_from.y
    if math.hypot(dx, dy) < _TOL:
        return None
    return unit_vector(dx, dy)


# ---------------------------------------------------------------------------
# Useckove fraze (jeden vysledny bod) - viz G18.md "Rovinne useckove fraze"
# ---------------------------------------------------------------------------

def nearest_point_on_circle(point, circle):
    """Nejblizsi bod na kruznici 'circle' k bodu 'point' - fraze *C:0."""
    dx = point.x - circle.center.x
    dy = point.y - circle.center.y
    d = math.hypot(dx, dy)
    if d < _TOL:
        raise MovePhraseError(
            "C:0 - bod lezi ve stredu kruznice, nejblizsi bod na kruznici "
            "neni jednoznacny"
        )
    ux, uy = dx / d, dy / d
    return Point(circle.center.x + circle.radius * ux, circle.center.y + circle.radius * uy, 0.0)


def _resolve_line_phrase(current_point, last_direction, mode, sep, values):
    """Useckove fraze (vraci PRAVE JEDEN novy bod). Viz G18.md 18.4.1."""

    # --- fraze bez separatoru (jedna hodnota) ---
    if sep is None and len(values) == 1:
        (v,) = values

        if _is_number(v):
            # *D - pohyb ve smeru predchoziho pohybu o vzdalenost D
            if last_direction is None:
                raise MovePhraseError(
                    "D - smer predchoziho pohybu neni znamy (prvni fraze "
                    "retezce/kresby musi urcit bod nebo vektor, ne holou "
                    "vzdalenost)"
                )
            ux, uy = last_direction
            return Point(current_point.x + v * ux, current_point.y + v * uy, 0.0)

        if isinstance(v, Point):
            # *P - pohyb do bodu P (vzdy absolutni, bez ohledu na ABSOL/INCRE)
            return Point(v.x, v.y, 0.0)

        if isinstance(v, Vector):
            # *V - pohyb ve smeru vektoru V o vzdalenost = velikost V
            return Point(current_point.x + v.x, current_point.y + v.y, 0.0)

    # --- *D#A - polarni souradnice ---
    if sep == "#" and len(values) == 2 and _is_number(values[0]) and _is_number(values[1]):
        d, a = values
        origin = Point(0.0, 0.0, 0.0) if mode == "ABSOL" else current_point
        rad = math.radians(a)
        return Point(origin.x + d * math.cos(rad), origin.y + d * math.sin(rad), 0.0)

    if sep == ":" and len(values) == 2:
        a, b = values

        if _is_number(a) and _is_number(b):
            # *D1:D2 - kartezske souradnice, rezim ABSOL/INCRE
            if mode == "ABSOL":
                return Point(float(a), float(b), 0.0)
            return Point(current_point.x + a, current_point.y + b, 0.0)

        if _is_number(a) and isinstance(b, Vector):
            # *D:V - pohyb ve smeru vektoru V o vzdalenost D (rezim ABSOL/
            # INCRE fazi neovlivnuje - neni to "promenlivy rezim")
            ux, uy = unit_vector(b.x, b.y)
            return Point(current_point.x + a * ux, current_point.y + a * uy, 0.0)

        if isinstance(a, Line) and isinstance(b, Line):
            # *L1:L2 - prusecik dvou primek
            from .p20 import line_intersection
            return line_intersection(a, b)

        if isinstance(a, Line) and _is_number(b):
            # *L:0 - patni bod kolmice z aktualniho bodu na primku L
            from .p40 import foot_point_on_line
            return foot_point_on_line(current_point, a)

        if isinstance(a, Circle) and _is_number(b):
            # *C:0 - nejblizsi bod na kruznici C
            return nearest_point_on_circle(current_point, a)

        if isinstance(a, Curve) and _is_number(b):
            # *E:K - pocatecni (K=0) / koncovy (K=1) bod retezce
            k = int(round(b))
            return Point(a.points[0].x, a.points[0].y, 0.0) if k == 0 \
                else Point(a.points[-1].x, a.points[-1].y, 0.0)

        if isinstance(a, Spline) and _is_number(b):
            # *S:K - pocatecni (K=0) / koncovy (K=1) bod krivky
            k = int(round(b))
            return Point(a.points[0].x, a.points[0].y, 0.0) if k == 0 \
                else Point(a.points[-1].x, a.points[-1].y, 0.0)

    return None  # neni to useckova fraze - zkusi se dal jako obloukova/retezcova/...


# ---------------------------------------------------------------------------
# Obloukove fraze (aproximovane useckami s presnosti ACCUR)
# ---------------------------------------------------------------------------

def _max_step_angle_rad(radius, accuracy):
    """Maximalni uhlovy krok (radiany) mezi dvema body aproximujici
    tetivy tak, aby se od kruznice o danem polomeru neodchylovaly vic
    nez o 'accuracy' (viz ACCUR, prirucka odst. 17.6.2)."""
    if radius <= 0:
        raise MovePhraseError("polomer obloukove fraze musi byt kladny (je %r)" % (radius,))
    ratio = 1.0 - (accuracy / radius)
    ratio = max(min(ratio, 1.0), -1.0)
    step = 2.0 * math.acos(ratio)
    if step <= 1e-9:
        step = 1e-3
    return step


def flatten_arc(center, radius, start_angle_deg, end_angle_deg, ccw, accuracy=None, full_circle=False):
    """Aproximuje oblouk kruznice useckami s presnosti danou ACCUR.
    Vraci seznam bodu BEZ pocatecniho bodu, VCETNE koncoveho bodu.

    ccw=True - proti smeru hodinovych rucicek, ccw=False - po smeru.
    full_circle=True - vzdy cely obvod (fraze *C), i kdyz start==end.
    """
    if accuracy is None:
        accuracy = get_accuracy()

    start = math.radians(start_angle_deg)
    end = math.radians(end_angle_deg)
    full = 2.0 * math.pi

    if ccw:
        span = (end - start) % full
    else:
        span = -((start - end) % full)

    if full_circle or abs(span) < 1e-9:
        span = full if ccw else -full

    step = _max_step_angle_rad(radius, accuracy)
    n_steps = max(1, int(math.ceil(abs(span) / step)))

    points = []
    for i in range(1, n_steps + 1):
        a = start + span * (float(i) / n_steps)
        points.append(Point(center.x + radius * math.cos(a), center.y + radius * math.sin(a), 0.0))
    return points


def _resolve_arc_phrase(current_point, sep, values, accuracy=None):
    """Obloukove fraze - viz G18.md 'Rovinne obloukove fraze'. Vraci
    seznam bodu (aproximace oblouku useckami), nebo None, pokud tvar
    fraze neodpovida zadne znamem obloukove frazi."""

    if sep is None and len(values) == 1 and isinstance(values[0], Circle):
        # *C - cela kruznice z aktualniho bodu (musi na ni lezet), ccw
        circle = values[0]
        start_angle = polar_angle_deg(current_point.x - circle.center.x,
                                       current_point.y - circle.center.y)
        return flatten_arc(circle.center, circle.radius, start_angle, start_angle,
                            ccw=True, accuracy=accuracy, full_circle=True)

    if sep == "," and len(values) == 3:
        a, b, c = values

        if isinstance(a, Point) and isinstance(b, Point) and _is_number(c):
            # *P1,P2,K - po kruznici (stred P2, polomer=|current-P2|) do
            # bodu P1; K=0 ccw, K=1 cw
            p1, center, k = a, b, int(round(c))
            radius = math.hypot(current_point.x - center.x, current_point.y - center.y)
            start_angle = polar_angle_deg(current_point.x - center.x, current_point.y - center.y)
            end_angle = polar_angle_deg(p1.x - center.x, p1.y - center.y)
            return flatten_arc(center, radius, start_angle, end_angle, ccw=(k == 0), accuracy=accuracy)

        if isinstance(a, Point) and isinstance(b, Circle) and _is_number(c):
            # *P,C,K - po kruznici C do bodu P; K=0 ccw, K=1 cw
            p, circle, k = a, b, int(round(c))
            start_angle = polar_angle_deg(current_point.x - circle.center.x,
                                           current_point.y - circle.center.y)
            end_angle = polar_angle_deg(p.x - circle.center.x, p.y - circle.center.y)
            return flatten_arc(circle.center, circle.radius, start_angle, end_angle,
                                ccw=(k == 0), accuracy=accuracy)

    return None


# ---------------------------------------------------------------------------
# Retezcove/krivkove fraze - cely retezec/krivka, nebo jeho usek P1,P2
# ---------------------------------------------------------------------------

def _chain_points_oriented(curve, current_point):
    """Body retezce 'curve' orientovane tak, aby navazovaly na
    'current_point' (ktery musi lezet na jednom z jeho krajnich uzlu) -
    fraze *E."""
    first, last = curve.points[0], curve.points[-1]
    if math.hypot(current_point.x - first.x, current_point.y - first.y) < _TOL:
        return list(curve.points[1:])
    if math.hypot(current_point.x - last.x, current_point.y - last.y) < _TOL:
        return list(reversed(curve.points[:-1]))
    raise MovePhraseError(
        "E - aktualni bod nelezi na zadnem krajnim uzlu retezce "
        "(fraze *E navazuje na cely retezec od jeho kraje)"
    )


def _spline_points_oriented(spline, current_point, accuracy=None):
    """Body krivky 'spline' (aproximovane useckami s presnosti ACCUR)
    orientovane tak, aby navazovaly na 'current_point' - fraze *S."""
    from .e45 import discretize
    curve = discretize(spline)
    return _chain_points_oriented(curve, current_point)


def _chain_segment_points(curve, p1, p2):
    """Vnitrni uzly retezce 'curve' MEZI body p1 a p2 (bez p1, VCETNE p2)
    v poradi p1->p2 - fraze *P1,P2,E. Pouziva D31/index_parameter k
    nalezeni pozice p1/p2 na retezci."""
    idx1 = index_parameter(curve, p1)
    idx2 = index_parameter(curve, p2)

    pts, idxs = curve.points, curve.indices
    if idx2 >= idx1:
        interior = [pts[i] for i in range(len(pts)) if idx1 < idxs[i] < idx2]
    else:
        interior = [pts[i] for i in range(len(pts) - 1, -1, -1) if idx2 < idxs[i] < idx1]
    return interior + [Point(p2.x, p2.y, 0.0)]


def _spline_segment_points(spline, p1, p2, accuracy=None):
    """Totez jako _chain_segment_points, ale pro krivku (Spline) - nejdriv
    se krivka aproximuje retezcem s presnosti ACCUR (viz discretize),
    pak se pouzije stejna logika jako pro retezec - fraze *P1,P2,S."""
    from .e45 import discretize
    curve = discretize(spline)
    return _chain_segment_points(curve, p1, p2)


def _resolve_chain_phrase(current_point, sep, values, accuracy=None):
    """Retezcove/krivkove fraze - viz G18.md 'Rovinne retezcove fraze' a
    'Rovinne krivkove fraze'. Vraci seznam bodu, nebo None, pokud tvar
    fraze neodpovida."""

    if sep is None and len(values) == 1:
        (v,) = values
        if isinstance(v, Curve):
            return _chain_points_oriented(v, current_point)
        if isinstance(v, Spline):
            return _spline_points_oriented(v, current_point, accuracy)

    if sep == "," and len(values) == 3:
        a, b, c = values
        if isinstance(a, Point) and isinstance(b, Point) and isinstance(c, Curve):
            return _chain_segment_points(c, a, b)
        if isinstance(a, Point) and isinstance(b, Point) and isinstance(c, Spline):
            return _spline_segment_points(c, a, b, accuracy)

    return None


# ---------------------------------------------------------------------------
# Prechodove fraze (primka-primka, primka-kruznice, kruznice-primka,
# kruznice-kruznice) - zatim NEIMPLEMENTOVANO, viz G18.md "Rovinne
# prechodove fraze". Staveni kamen (vypocet prechodove kruznice) uz
# existuje (C32/C33/C34), chybi vypocet tecnych bodu P1/P2 a smeru
# navazujiciho oblouku - az bude potreba, dodelat podle stejneho vzoru
# jako C32/C33/C34.
# ---------------------------------------------------------------------------

def _classify_transition_phrase(sep, values):
    if sep != "," or len(values) != 4:
        return None
    a, b = values[0], values[1]
    if isinstance(a, Line) and isinstance(b, Line):
        return "primka-primka (MOVE*L1,L2,D,K)"
    if isinstance(a, Line) and isinstance(b, Circle):
        return "primka-kruznice (MOVE*L1,C1,D,KK)"
    if isinstance(a, Circle) and isinstance(b, Line):
        return "kruznice-primka (MOVE*C1,L1,D,KKK)"
    if isinstance(a, Circle) and isinstance(b, Circle):
        return "kruznice-kruznice (MOVE*C1,C2,D,KKK)"
    return None


# ---------------------------------------------------------------------------
# Verejne API
# ---------------------------------------------------------------------------

def evaluate_move_phrase(current_point, last_direction, mode, sep, values, accuracy=None):
    """Vyhodnoti jednu pohybovou frazi prikazu MOVE (jiz vyhodnocene
    argumenty 'values' + separator 'sep' pouzity v jeji syntaxi - None
    pro holou hodnotu, '#'/':'/',' podle toho, jaky oddelovac fraze v
    GL3 zdroji pouzila).

    Vraci (novy_seznam_bodu, novy_smer):
      novy_seznam_bodu - neprazdny seznam bodu (Point) k pripojeni do
        retezce/kresby (useckova fraze = 1 bod, obloukova/retezcova =
        vic bodu).
      novy_smer - (dx, dy) normalizovany smer POSLEDNIHO vznikleho
        useku (pro nasledujici frazi *D), nebo None pro degenerovany
        (nulovy) usek.

    Vyhazuje MovePhraseError pro geometricky/typove nesmyslny vstup,
    MovePhraseNotYetImplemented pro rozpoznane, ale jeste
    neportovane prechodove fraze.
    """
    point = _resolve_line_phrase(current_point, last_direction, mode, sep, values)
    if point is not None:
        return [point], _unit_dir(current_point, point)

    arc_points = _resolve_arc_phrase(current_point, sep, values, accuracy)
    if arc_points is not None:
        last_seg_start = current_point if len(arc_points) == 1 else arc_points[-2]
        return arc_points, _unit_dir(last_seg_start, arc_points[-1])

    chain_points = _resolve_chain_phrase(current_point, sep, values, accuracy)
    if chain_points is not None:
        if not chain_points:
            raise MovePhraseError("retezcova/krivkova fraze vyprodukovala prazdny usek (P1 a P2 jsou stejny bod?)")
        last_seg_start = current_point if len(chain_points) == 1 else chain_points[-2]
        return chain_points, _unit_dir(last_seg_start, chain_points[-1])

    transition_kind = _classify_transition_phrase(sep, values)
    if transition_kind is not None:
        raise MovePhraseNotYetImplemented(
            "prechodova fraze typu %s jeste neni implementovana - staveni "
            "kamen (vypocet prechodove kruznice) uz existuje (C32/C33/"
            "C34), chybi dopocet tecnych bodu a smeru navazujiciho "
            "oblouku" % transition_kind
        )

    raise MovePhraseError(
        "nerozpoznana fraze prikazu MOVE (separator=%r, %d hodnot typu %r)"
        % (sep, len(values), [type(v).__name__ for v in values])
    )
