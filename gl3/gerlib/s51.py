# -*- coding: utf-8 -*-
"""
Procedura S51        LET, k.p., Uh.Hradiste
Knihovna GL3E4                                     Listopad 1987

Ucel:    Ekvidistantni (rovnobezna) krivka ke krivce ve vzdalenosti D1,
         volitelne jen na useku <P1,P2>, s presnosti danou ACCUR (D2).

Uziti:   SM=S51>S,D1[,[P1][,P2]][,K][,D2]<
         K - strana (0=vlevo,1=vpravo, jako V230/L20), D2 - presnost
             ekvidistanty

ZAMERNY ODKLON OD ORIGINALU: puvodni S51.FOR cte D2 jako svuj vlastni
argument a pri jeho vynechani nastavuje ACCUR=0 (zadna kontrola
odchylky) - viz "ACCUR=R(1,7); IF(ITY(7).EQ.32767) ACCUR=0." Podle
domluvy v konverzaci se u nas D2 vynechane MISTO toho chova stejne
jako u E45 - pouzije se aktualni hodnota globalniho prikazu ACCUR
(gerlib/accur.py, vychozi 0.01). Kdo chce vysloveny "bez kontroly
odchylky" rezim (rychly, ale vysledek nemusi byt skutecna
ekvidistanta u vice zakrivenych useku), musi D2 predat explicitne
jako 0 (nebo zapornou hodnotu).

Algoritmus (1:1 podle S51.FOR): presna ekvidistanta kubiky obecne
NENI kubika (normala zavisi na |C'(t)|, tedy odmocnina) - kazdy puvodni
segment se proto NAHRAZUJE novou Hermitovou kubikou:
  - krajni body nove kubiky = presny offset (bod + D1*normala)
  - smer tecen nove kubiky = STEJNY jako puvodni (jen skalovana
    velikost DD1,DD2)
  - DD1,DD2 a dva vnitrni parametry S,T (kde se nova kubika ma presne
    setkat se skutecnou ekvidistantou) se dopocitaji resenim soustavy
    4 nelinearnich rovnic (FS51 + nlsolve, nahrada za DNSBM - viz jeho
    hlavicka proc to neni 1:1 port)
  - pokud odchylka fitovane krivky od puvodni (mereno pres SGPAT ve 3
    bodech) prekroci ACCUR, usek segmentu se zmensi a fituje se znovu

POZNAMKA - bez GLPAT: stejne jako D50/E45 (viz jejich hlavicky) misto
GLPAT vzdy pouzivame nearest_point_on_curve pro rozreseni volitelnych
P1/P2.

Zavislosti: gerlib.glkoe, gerlib.glfun, gerlib.d50 (nearest_point_on_
curve), gerlib.fs51, gerlib.nlsolve, gerlib.sgpat, gerlib.accur.
"""

import math

from .types import Point, Vector, Spline
from .glkoe import segment_coefficients
from .glfun import evaluate
from .d50 import nearest_point_on_curve
from .fs51 import make_residual_fn
from .nlsolve import solve as nlsolve_solve
from .sgpat import nearest_distance
from .accur import get_accuracy

_MAX_SUBDIVIDE_RETRIES = 6


def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def _offset_xy(px, py, tx, ty, distance, side):
    """Offset bodu (px,py) s tecnou (tx,ty) o 'distance' po normale;
    side=0 vlevo, side=1 vpravo (stejna konvence jako V230/L20:
    normala = (-ty,tx) pro side=0)."""
    length = math.hypot(tx, ty)
    if length < 1e-12:
        raise ValueError("S51: nulovy tecny vektor segmentu - nelze spocitat normalu")
    sign = -1.0 if side else 1.0
    scale = sign * distance / length
    return px - ty * scale, py + tx * scale


def _flip_segment(seg):
    """Obrati jeden Hermituv segment (p0,p1,t0,t1) - pro pripad, ze
    P1 lezelo 'za' P2 na krivce (viz S51.FOR label 210-220): body se
    prohodi, tecny se prohodi A ZNEGUJI (smer pohybu se obraci)."""
    p0, p1, t0, t1 = seg
    return p1, p0, (-t1[0], -t1[1]), (-t0[0], -t0[1])


def offset_curve(spline, distance, p1=None, p2=None, side=0, accuracy=None):
    """S51: ekvidistantni krivka ke 'spline' ve vzdalenosti 'distance'
    (na useku <p1,p2>, pokud jsou zadane). side: 0=vlevo, 1=vpravo.
    accuracy=None (D2 vynechany) pouzije aktualni globalni ACCUR (viz
    hlavicka modulu - ZAMERNY odklon od originalu, kde by D2 vynechany
    znamenal 0/bez kontroly)."""
    n = len(spline.points)
    if n < 2:
        raise ValueError("S51: krivka musi mit alespon 2 body")

    if p1 is None:
        i1, par1 = 1, 0.0
    else:
        i1, par1 = nearest_point_on_curve(spline, p1)
    if p2 is None:
        i2, par2 = n - 1, 1.0
    else:
        i2, par2 = nearest_point_on_curve(spline, p2)

    reverse_output = False
    if (i1 + par1) > (i2 + par2):
        reverse_output = True
        i1, i2 = i2, i1
        par1, par2 = par2, par1

    acc = get_accuracy() if accuracy is None else accuracy

    segments = []  # kazdy prvek: (p0_xy, p1_xy, t0_xy, t1_xy)

    for ir in range(i1, i2 + 1):
        p0_node = spline.points[ir - 1]
        p1_node = spline.points[ir]
        t0_node, t1_node = spline.segment_tangent_pair(ir - 1)
        coeffs = segment_coefficients(p0_node, p1_node, t0_node, t1_node, k=2)
        chord = _dist((p0_node.x, p0_node.y), (p1_node.x, p1_node.y))

        pard = par1 if ir == i1 else 0.0
        pp2 = par2 if ir == i2 else 1.0

        if ir == i1 and par1 > 1e-5:
            cur_start_xy = evaluate(coeffs, par1, order=0)
            cur_start_tan_xy = evaluate(coeffs, par1, order=1)
        else:
            cur_start_xy = (p0_node.x, p0_node.y)
            cur_start_tan_xy = (t0_node.x, t0_node.y)

        if ir == i2:
            kon_xy = evaluate(coeffs, par2, order=0)
            kon_tan_xy = evaluate(coeffs, par2, order=1)
        else:
            kon_xy = (p1_node.x, p1_node.y)
            kon_tan_xy = (t1_node.x, t1_node.y)

        p2 = pp2
        roztec = p2 - pard
        if roztec < 1e-15:
            continue  # cely usek tohoto segmentu je jiz "za" P1 - preskoc

        cur_end_xy, cur_end_tan_xy = kon_xy, kon_tan_xy
        iss = 0

        while True:
            # --- labely 80/90: offset koncovych bodu aktualniho useku ---
            xx1, yy1 = _offset_xy(
                cur_start_xy[0], cur_start_xy[1],
                cur_start_tan_xy[0], cur_start_tan_xy[1], distance, side,
            )
            xx2, yy2 = _offset_xy(
                cur_end_xy[0], cur_end_xy[1],
                cur_end_tan_xy[0], cur_end_tan_xy[1], distance, side,
            )

            last_par = last_qz = last_qp = None

            if acc <= 0:
                dd1 = dd2 = _dist((xx1, yy1), (xx2, yy2)) / chord
                fit_ok = True
            else:
                dd_guess = _dist(cur_start_xy, cur_end_xy) / chord
                xx = [1.0 / 3.0, 2.0 / 3.0, dd_guess, dd_guess]
                targets = [0.0, 0.0, 0.0, 0.0]
                ss = 1.0
                for i in (2, 1):
                    ss -= 1.0 / 3.0
                    par = pard + roztec * ss
                    qz = evaluate(coeffs, par, order=0)
                    qp = evaluate(coeffs, par, order=1)
                    tlen = math.hypot(qp[0], qp[1])
                    if tlen < 1e-12:
                        raise ValueError("S51: nulova tecna uvnitr segmentu - nelze pokracovat")
                    local_scale = (-1.0 if side else 1.0) * distance / tlen
                    ex = qz[0] - qp[1] * local_scale
                    ey = qz[1] + qp[0] * local_scale
                    targets[2 * (i - 1)] = ex
                    targets[2 * (i - 1) + 1] = ey
                    last_par, last_qz, last_qp = par, qz, qp

                residual_fn = make_residual_fn(
                    (xx1, yy1), (xx2, yy2),
                    cur_start_tan_xy, cur_end_tan_xy,
                    targets,
                )
                solved, converged = nlsolve_solve(residual_fn, xx, 4)
                dd1, dd2 = solved[2], solved[3]
                fit_ok = converged and dd1 > 0 and dd2 > 0

            if fit_ok:
                iss = 0  # 1:1 podle originalu (label 120: ISS=0) - resetuje se
                         # hned po uspesne konvergenci DNSBM, bez ohledu na to,
                         # jestli pozdeji projde i kontrola presnosti
                new_seg = (
                    (xx1, yy1), (xx2, yy2),
                    (cur_start_tan_xy[0] * dd1, cur_start_tan_xy[1] * dd1),
                    (cur_end_tan_xy[0] * dd2, cur_end_tan_xy[1] * dd2),
                )

                accept = True
                if acc > 0:
                    fit_coeffs = segment_coefficients(
                        Point(new_seg[0][0], new_seg[0][1], 0.0),
                        Point(new_seg[1][0], new_seg[1][1], 0.0),
                        Vector(new_seg[2][0], new_seg[2][1], 0.0),
                        Vector(new_seg[3][0], new_seg[3][1], 0.0),
                        k=2,
                    )
                    aa1 = 0.0
                    for i in (1, 2, 3):
                        aa1 += solved[i - 1] if i <= 2 else 0.0
                        if i == 3:
                            aa1 = 1.0 + solved[1]
                        ss_mid = 0.5 * aa1
                        qpp = evaluate(fit_coeffs, ss_mid, order=0)
                        measured = nearest_distance(coeffs, qpp)
                        if measured is None:
                            raise ValueError(
                                "S51: SGPAT nenasla zadny bod na puvodni krivce "
                                "(neocekavana geometrie segmentu)"
                            )
                        if abs(abs(distance) - measured) > acc:
                            accept = False
                            break

                if accept:
                    segments.append(new_seg)
                    if abs(p2 - pp2) < 1e-9:
                        break
                    # zbyva cast puvodniho segmentu [p2,pp2] - pokracuj
                    p2 = pp2
                    cur_start_xy, cur_start_tan_xy = cur_end_xy, cur_end_tan_xy
                    cur_end_xy, cur_end_tan_xy = kon_xy, kon_tan_xy
                    pard = pard + roztec
                    roztec = p2 - pard
                    continue
                # jinak: propadni do "rozdel" (label 140) - POZOR, tohle
                # se (1:1 podle originalu) NEPOCITA do limitu ISS - jen
                # DNSBM-nekonvergence (vetev 'else' nize) ma limit 6
                # pokusu; selhani kontroly presnosti je omezeno jen
                # minimalni velikosti useku (ROZTEC.LT.1D-5 nize)

            else:
                iss += 1
                if iss >= _MAX_SUBDIVIDE_RETRIES:
                    raise ValueError(
                        "S51: fitovani segmentu ekvidistanty se nepodarilo ani "
                        "po %d pokusech o zmenseni useku (puvodni chyba 800)"
                        % (_MAX_SUBDIVIDE_RETRIES,)
                    )

            # --- label 140: rozdel usek na mensi a zkus znovu ---
            if last_par is None:
                # acc<=0 vetev sem nikdy nedojde (fit_ok vzdy True), ale
                # pro jistotu osetreno
                raise ValueError("S51: neocekavany stav pri deleni useku")
            cur_end_xy, cur_end_tan_xy = last_qz, last_qp
            p2 = last_par
            roztec = p2 - pard
            if roztec < 1e-5:
                raise ValueError(
                    "S51: usek segmentu je po opakovanem deleni prilis maly "
                    "(puvodni chyba 800)"
                )

    if reverse_output:
        segments = [_flip_segment(s) for s in reversed(segments)]

    points = [Point(segments[0][0][0], segments[0][0][1], 0.0)]
    tangents = [Vector(segments[0][2][0], segments[0][2][1], 0.0)]
    segment_tangents = []
    for seg in segments:
        p0_xy, p1_xy, t0_xy, t1_xy = seg
        points.append(Point(p1_xy[0], p1_xy[1], 0.0))
        tangents.append(Vector(t1_xy[0], t1_xy[1], 0.0))
        segment_tangents.append((
            Vector(t0_xy[0], t0_xy[1], 0.0),
            Vector(t1_xy[0], t1_xy[1], 0.0),
        ))

    return Spline(points, tangents, closed=False, opcode="S51", segment_tangents=segment_tangents)
