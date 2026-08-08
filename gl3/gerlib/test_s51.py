# -*- coding: utf-8 -*-
"""Test nlsolve (nahrada DNSBM), sgpat (SGPAT), fs51 (FS51) a S51
(ekvidistantni krivka).

Zdroj: S51.FOR, FS51.FOR, SGPAT.FOR, DNSBM.FOR (dodano uzivatelem).
DNSBM nahrazeno Newton-Raphsonem (viz nlsolve.py hlavicka).

POZOR: D2 (presnost) je VLASTNI parametr S51, NE globalni prikaz ACCUR
(viz hlavicka s51.py - overeno a opraveno po hlaseni z realneho
FreeCADu) - testy proto D2 predavaji vzdy primo jako 'accuracy=',
nikdy pres gerlib.accur.set_accuracy()."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Spline
from gerlib.glkoe import segment_coefficients
from gerlib.glfun import evaluate
from gerlib.nlsolve import solve as nlsolve_solve
from gerlib.sgpat import nearest_distance
from gerlib.p42 import foot_points
from gerlib.fs51 import make_residual_fn
from gerlib.s01 import make_spline
from gerlib.s51 import offset_curve


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def parabola_spline():
    """Presna Hermitova reprezentace y=x^2 na <0,1> (viz test_d50.py)."""
    p0, p1 = Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)
    t0, t1 = Vector(1.0, 0.0, 0.0), Vector(1.0, 2.0, 0.0)
    return Spline([p0, p1], [t0, t1])


def true_offset_point(t, distance, side=0):
    """Nezavisly analyticky vzorec pro presnou ekvidistantu y=x^2 v
    parametru t=x (tecna (1,2t), normala (-2t,1) pro side=0 - stejna
    konvence jako _offset_xy v s51.py)."""
    length = math.hypot(1.0, 2.0 * t)
    sign = -1.0 if side else 1.0
    scale = sign * distance / length
    x = t - 2.0 * t * scale
    y = t * t + 1.0 * scale
    return x, y


def main():
    # --- nlsolve: jednoduchy znamy system (kruhove pruseciky) ---
    # x^2+y^2=4, (x-2)^2+y^2=4 -> reseni x=1, y=+-sqrt(3)
    def circles(x, n, k):
        if k == 1:
            return x[0] ** 2 + x[1] ** 2 - 4.0
        return (x[0] - 2.0) ** 2 + x[1] ** 2 - 4.0

    sol, converged = nlsolve_solve(circles, [0.5, 1.0], 2)
    check(converged, "nlsolve: konverguje na znamem systemu")
    check(math.isclose(sol[0], 1.0, abs_tol=1e-6), "nlsolve: x slozka reseni")
    check(math.isclose(abs(sol[1]), math.sqrt(3.0), abs_tol=1e-6), "nlsolve: y slozka reseni")

    # --- sgpat: musi souhlasit s P42/foot_points (stejna matematika) ---
    p0, p1 = Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)
    t0, t1 = Vector(1.0, 0.0, 0.0), Vector(1.0, 2.0, 0.0)
    coeffs = segment_coefficients(p0, p1, t0, t1, k=2)
    test_point = (0.5, 0.3)
    d_sgpat = nearest_distance(coeffs, test_point)

    spline = Spline([p0, p1], [t0, t1])
    feet = foot_points(spline, Point(test_point[0], test_point[1], 0.0))
    d_p42 = min(
        math.hypot(pt.x - test_point[0], pt.y - test_point[1]) for _seg, _t, pt in feet
    )
    check(math.isclose(d_sgpat, d_p42, rel_tol=1e-6),
          "SGPAT: stejny vysledek jako P42/foot_points (%.6f vs %.6f)" % (d_sgpat, d_p42))

    # --- fs51: rezidual je 0 pro presne spravne hodnoty (trivialni primka) ---
    # primka: P0=(0,0),P1=(10,0), tecny (10,0) na obou koncich, DD1=DD2=1
    residual_fn = make_residual_fn((0.0, 0.0), (10.0, 0.0), (10.0, 0.0), (10.0, 0.0),
                                    targets=(5.0, 0.0, 7.0, 0.0))
    x = [0.5, 0.7, 1.0, 1.0]
    r1 = residual_fn(x, 4, 1)
    r2 = residual_fn(x, 4, 2)
    check(math.isclose(r1, 0.0, abs_tol=1e-9) and math.isclose(r2, 0.0, abs_tol=1e-9),
          "FS51: nulovy rezidual pro spravne hodnoty na primce (t=0.5 -> bod (5,0))")

    # --- S51: primka - ekvidistanta je presne rovnobezna primka ---
    line_spline = Spline([Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)],
                          [Vector(10.0, 0.0, 0.0), Vector(10.0, 0.0, 0.0)])
    offset_line = offset_curve(line_spline, 2.0, side=0, accuracy=0.01)
    check(len(offset_line.points) == 2, "S51: primka -> ekvidistanta ma jen 2 body (zadne deleni)")
    check(math.isclose(offset_line.points[0].x, 0.0) and math.isclose(offset_line.points[0].y, 2.0),
          "S51: primka - prvni bod offsetu (0,2) pro side=0")
    check(math.isclose(offset_line.points[1].x, 10.0) and math.isclose(offset_line.points[1].y, 2.0),
          "S51: primka - posledni bod offsetu (10,2)")

    offset_line_r = offset_curve(line_spline, 2.0, side=1, accuracy=0.01)
    check(math.isclose(offset_line_r.points[0].y, -2.0), "S51: side=1 offsetuje na druhou stranu")

    # --- S51: parabola - overeni proti nezavislemu analytickemu vzorci ---
    parabola = parabola_spline()
    for accuracy in (0.05, 0.01):
        offset = offset_curve(parabola, 0.3, side=0, accuracy=accuracy)
        check(len(offset.points) >= 2, "S51: parabola - vysledek ma alespon 2 body (presnost %.3f)" % accuracy)

        max_err = 0.0
        for pt in offset.points:
            best = min(
                math.hypot(pt.x - tx, pt.y - ty)
                for tx, ty in (true_offset_point(t / 200.0, 0.3, side=0) for t in range(201))
            )
            max_err = max(max_err, best)
        check(max_err <= accuracy * 1.1,
              "S51: vsechny body vysledku jsou v ramci presnosti %.3f od analyticke ekvidistanty (chyba %.5f)"
              % (accuracy, max_err))

    # presnejsi pozadavek -> vic bodu (vic deleni) - 0.05 dava jeden usek
    # (fit je prekvapive dobry i bez deleni), 0.0001 uz musi delit
    coarse = offset_curve(parabola, 0.3, side=0, accuracy=0.05)
    fine = offset_curve(parabola, 0.3, side=0, accuracy=0.0001)
    check(len(coarse.points) == 2, "S51: presnost 0.05 - fit staci na jeden usek (zadne deleni)")
    check(len(fine.points) > len(coarse.points), "S51: presnost 0.0001 uz vyzaduje deleni (vic bodu)")

    max_err_fine = 0.0
    samples = [true_offset_point(t / 20000.0, 0.3, side=0) for t in range(20001)]
    for pt in fine.points:
        best = min(math.hypot(pt.x - tx, pt.y - ty) for tx, ty in samples)
        max_err_fine = max(max_err_fine, best)
    check(max_err_fine <= 0.0001 * 1.5,
          "S51: i po deleni segmentu (presnost 0.0001) vysledek sedi na analyticky vzorec (chyba %.6f)"
          % max_err_fine)

    # --- D2 vynechany pouziva globalni ACCUR (zamerny odklon od
    # originalu - viz hlavicka s51.py - podle prani v konverzaci) ---
    from gerlib.accur import set_accuracy, reset_accuracy
    set_accuracy(0.05)
    via_accur = offset_curve(parabola, 0.3, side=0)  # accuracy=None
    explicit = offset_curve(parabola, 0.3, side=0, accuracy=0.05)
    check(len(via_accur.points) == len(explicit.points),
          "S51: D2 vynechan pouzije aktualni globalni ACCUR (stejny vysledek jako explicitni D2=ACCUR)")
    reset_accuracy()

    # --- REGRESE: zaporny offset (puvodni bug - SGPAT vraci nezapornou
    # vzdalenost, srovnavalo se se znamenkovou distance misto ABS) ---
    hard_pts = [Point(-30.0, 20.0, 0.0), Point(-16.0, 23.0, 0.0), Point(-10.0, 10.0, 0.0),
                Point(0.0, 10.0, 0.0), Point(0.0, 20.0, 0.0), Point(15.0, 20.0, 0.0)]
    hard_spline = make_spline(hard_pts, len(hard_pts))
    for d in (0.10, -0.10, 1.0, -1.0, 2.0, -2.0):
        off = offset_curve(hard_spline, d, accuracy=0.01)
        check(len(off.points) >= len(hard_pts), "S51: zaporny/kladny offset %.2f funguje symetricky" % d)

    print("Vse OK.")


if __name__ == "__main__":
    main()
