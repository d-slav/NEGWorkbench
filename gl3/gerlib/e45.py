# -*- coding: utf-8 -*-
"""
Procedura E45        LET, k.p., Uh.Hradiste
Knihovna GL3E2                                     Brezen 1984

Ucel:    Nahrazeni krivky retezcem v intervalu s presnosti danou
         prikazem ACCUR.

Uziti:   EM=E45>S[,[P1][,P2]]<

Algoritmus (1:1 podle E45.FOR, s jednim zamernym zjednodusenim - viz
nize): pro usek krivky mezi (volitelnymi) body P1 a P2 (default cely
rozsah krivky, tj. P1=zacatek, P2=konec) se postupuje segment po
segmentu. V kazdem segmentu se rozsah parametru [p1_local,park] zkousi
pokryt JEDNOU useckou (tetivou); kvadraticky polynom (derivace odchylky
bodu krivky od tetivy) najde kandidaty na nejvetsi odchylku - pokud
nektery prekroci ACCUR, tetiva se zkrati az k tomuto bodu a zkousi se
znovu, dokud neni cely rozsah pokryt tetivami vyhovujicimi presnosti.

ZJEDNODUSENI oproti originalu: puvodni E45.FOR pro P1/P2 bez shodneho
"puvodu" (IIN(10,..)) s krivkou S vola GLPAT k dohledani odpovidajiciho
bodu - stejne jako u D50 (viz jeho hlavicka) misto GLPAT VZDY hledame
nejblizsi bod na krivce (gerlib.d50.nearest_point_on_curve). Navic
POCATECNI bod retezce vzdy dopocitavame primo z Hermitovych koeficientu
segmentu v nalezenem parametru, misto abychom (jako original) proste
prevzali souradnice vstupniho bodu P1 - tim se vyhneme puvodni
"DIST korekci" (kontrola nesouladu mezi P1 a spocitanym bodem, viz
IRR.GT.3 v originale), protoze u nas zadny nesoulad vzniknout nemuze.

Pripad IPPC=0 (original: STOP) - kdyz kvadraticky polynom nema v danem
rozsahu zadny koren, tj. odchylka od tetivy nikde uvnitr intervalu
nema lokalni extrem - u hladke kubiky to znamena, ze odchylka je
identicky nulova (tetiva == krivka, typicky primy usek) - misto pádu
programu se tetiva proste prijme (presnost je triviálně splnena).

Vysledny retezec ma stejnou konvenci indices/is_end jako E01 (viz
e01.make_chain) a eps nastavene na pouzitou hodnotu ACCUR.

Zavislosti: gerlib.glkoe (Hermitovy koeficienty), gerlib.glfun
(vyhodnoceni bodu na segmentu), gerlib.glply (hledani realnych korenu
- kvadraticky pripad, POLY2.FOR), gerlib.d50 (hledani nejblizsiho bodu
na krivce - nahrada za GLPAT), gerlib.e01 (sestaveni vysledneho
retezce - make_chain).
"""

import math

from .types import Point
from .glkoe import segment_coefficients
from .glfun import evaluate
from .glply import real_roots_in_range
from .d50 import nearest_point_on_curve
from .e01 import make_chain
from .accur import get_accuracy


def _segment_coeffs(spline, seg_idx):
    """Hermitovy koeficienty segmentu 'seg_idx' (1-based) krivky 'spline'."""
    p0 = spline.points[seg_idx - 1]
    p1 = spline.points[seg_idx]
    t0, t1 = spline.segment_tangent_pair(seg_idx - 1)
    return segment_coefficients(p0, p1, t0, t1, k=2)


def _chord_deviation_poly(coeffs, xy1, xy2):
    """D(1..3) (sestupne) - derivace odchylky bodu krivky od tetivy
    xy1->xy2, polozena rovna nule (viz hlavicka modulu)."""
    (a3x, a2x, a1x, _a0x), (a3y, a2y, a1y, _a0y) = coeffs
    dx = xy2[0] - xy1[0]
    dy = xy2[1] - xy1[1]
    d1 = 3.0 * (dy * a3x - dx * a3y)
    d2 = 2.0 * (dy * a2x - dx * a2y)
    d3 = dy * a1x - dx * a1y
    return [d1, d2, d3]


def _distance_to_chord(xy1, xy2, xm):
    """Kolma vzdalenost bodu 'xm' od tetivy xy1->xy2."""
    dx = xy2[0] - xy1[0]
    dy = xy2[1] - xy1[1]
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return 0.0
    num = abs(xy1[0] * (xy2[1] - xm[1]) + xy2[0] * (xm[1] - xy1[1]) + xm[0] * (xy1[1] - xy2[1]))
    return num / length


def _flatten_segment(coeffs, start_t, end_t, accuracy):
    """Rozdeli segment (koeficienty 'coeffs') od parametru start_t do
    end_t na tetivy tak, aby zadna neodchylovala krivku o vic nez
    'accuracy'. Vraci seznam (t, (x,y)) bodu (BEZ pocatecniho start_t,
    KONCI presne v end_t)."""
    results = []
    p1_local = start_t
    xy1 = evaluate(coeffs, p1_local, order=0)

    while True:
        p2_local = end_t
        xy2 = evaluate(coeffs, p2_local, order=0)

        while True:
            rmin, rmax = sorted((p1_local, p2_local))
            poly = _chord_deviation_poly(coeffs, xy1, xy2)
            roots = real_roots_in_range(poly, rmin - 1e-4, rmax + 1e-4)

            worst = None
            for z in roots:
                xm = evaluate(coeffs, z, order=0)
                if _distance_to_chord(xy1, xy2, xm) >= accuracy:
                    worst = (z, xm)
                    break

            if worst is None:
                break  # tetiva [p1_local,p2_local] uz vyhovuje presnosti
            p2_local, xy2 = worst  # zkrat tetivu a zkus znovu

        results.append((p2_local, xy2))
        xy1 = xy2
        p1_local = p2_local
        if abs(p1_local - end_t) < 1e-9:
            break

    return results


def discretize(spline, p1=None, p2=None):
    """E45: retezec (Curve) nahrazujici 'spline' mezi (volitelnymi)
    body p1,p2 s presnosti danou aktualnim ACCUR (gerlib.accur)."""
    accuracy = get_accuracy()
    n = len(spline.points)
    if n < 2:
        raise ValueError("E45: krivka musi mit alespon 2 body")

    if p1 is None:
        it1, par1 = 1, 0.0
    else:
        it1, par1 = nearest_point_on_curve(spline, p1)

    if p2 is None:
        it2, par2 = n - 1, 1.0
    else:
        it2, par2 = nearest_point_on_curve(spline, p2)

    forward = (it2 + par2) >= (it1 + par1)
    idd = 1 if forward else -1

    first_coeffs = _segment_coeffs(spline, it1)
    first_xy = evaluate(first_coeffs, par1, order=0)
    chain_points = [Point(first_xy[0], first_xy[1], 0.0)]

    parp = par1
    ic = it1
    while True:
        if ic == it2:
            park = par2
        else:
            park = 1.0 if idd == 1 else 0.0

        if abs(park - parp) > 1e-6:
            coeffs = _segment_coeffs(spline, ic)
            for _t, xy in _flatten_segment(coeffs, parp, park, accuracy):
                chain_points.append(Point(xy[0], xy[1], 0.0))

        if ic == it2:
            break
        ic += idd
        parp = 0.0 if idd == 1 else 1.0

    return make_chain(chain_points, eps=accuracy)
