# -*- coding: utf-8 -*-
"""Test nlsolve (nahrada DNSBM), sgpat (SGPAT), fs51 (FS51) a S51
(ekvidistantni krivka).

Zdroj: S51.FOR, FS51.FOR, SGPAT.FOR, DNSBM.FOR (dodano uzivatelem).
DNSBM nahrazeno Newton-Raphsonem (viz nlsolve.py hlavicka)."""
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
from gerlib.accur import set_accuracy, reset_accuracy
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
    # pri t=0.5 na teto primce: bod = (5,0) presne (h00*0+h10*10*1+...) - over rezidual K=1,2
    r1 = residual_fn(x, 4, 1)
    r2 = residual_fn(x, 4, 2)
    check(math.isclose(r1, 0.0, abs_tol=1e-9) and math.isclose(r2, 0.0, abs_tol=1e-9),
          "FS51: nulovy rezidual pro spravne hodnoty na primce (t=0.5 -> bod (5,0))")

    # --- S51: primka - ekvidistanta je presne rovnobezna primka ---
    line_spline = Spline([Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)],
                          [Vector(10.0, 0.0, 0.0), Vector(10.0, 0.0, 0.0)])
    set_accuracy(0.01)
    offset_line = offset_curve(line_spline, 2.0, side=0)
    check(len(offset_line.points) == 2, "S51: primka -> ekvidistanta ma jen 2 body (zadne deleni)")
    check(math.isclose(offset_line.points[0].x, 0.0) and math.isclose(offset_line.points[0].y, 2.0),
          "S51: primka - prvni bod offsetu (0,2) pro side=0")
    check(math.isclose(offset_line.points[1].x, 10.0) and math.isclose(offset_line.points[1].y, 2.0),
          "S51: primka - posledni bod offsetu (10,2)")

    # strana side=1 musi dat opacny smer offsetu
    offset_line_r = offset_curve(line_spline, 2.0, side=1)
    check(math.isclose(offset_line_r.points[0].y, -2.0), "S51: side=1 offsetuje na druhou stranu")
    reset_accuracy()

    # --- S51: parabola - overeni proti nezavislemu analytickemu vzorci ---
    parabola = parabola_spline()
    for accuracy in (0.05, 0.01):
        set_accuracy(accuracy)
        offset = offset_curve(parabola, 0.3, side=0)
        check(len(offset.points) >= 2, "S51: parabola - vysledek ma alespon 2 body (presnost %.3f)" % accuracy)

        # over kazdy bod vysledne ekvidistanty proti analytickemu vzorci -
        # potrebujeme najit odpovidajici parametr t (x-souradnice puvodni
        # paraboly = t, ale offset bod uz ma jinou x-souradnici, takze
        # hledame t numericky - staci hruby sken, staci pro kontrolu ACCUR)
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
    reset_accuracy()

    # presnejsi pozadavek -> vic bodu (vic deleni) - 0.05 dava jeden usek
    # (fit je prekvapive dobry i bez deleni), 0.0001 uz musi delit
    set_accuracy(0.05)
    coarse = offset_curve(parabola, 0.3, side=0)
    set_accuracy(0.0001)
    fine = offset_curve(parabola, 0.3, side=0)
    check(len(coarse.points) == 2, "S51: presnost 0.05 - fit staci na jeden usek (zadne deleni)")
    check(len(fine.points) > len(coarse.points), "S51: presnost 0.0001 uz vyzaduje deleni (vic bodu)")

    # a i po deleni musi vysledek pri 0.0001 sedet na analyticky vzorec
    # (hustsi vzorkovaci mrizka, aby sama chyba vzorkovani nebyla vetsi
    # nez overovana tolerance)
    max_err_fine = 0.0
    samples = [true_offset_point(t / 20000.0, 0.3, side=0) for t in range(20001)]
    for pt in fine.points:
        best = min(math.hypot(pt.x - tx, pt.y - ty) for tx, ty in samples)
        max_err_fine = max(max_err_fine, best)
    check(max_err_fine <= 0.0001 * 1.5,
          "S51: i po deleni segmentu (presnost 0.0001) vysledek sedi na analyticky vzorec (chyba %.6f)"
          % max_err_fine)
    reset_accuracy()

    print("Vse OK.")


if __name__ == "__main__":
    main()
