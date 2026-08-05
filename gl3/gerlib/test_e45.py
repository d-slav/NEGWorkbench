# -*- coding: utf-8 -*-
"""Test ACCUR (globalni presnost) a E45 (nahrazeni krivky retezcem).

Testovaci krivka: znovu parabola y=x^2 (presna Hermitova reprezentace,
viz test_d50.py/test_p22.py) - umoznuje analyticky overit, ze vsechny
body vysledneho retezce lezi presne NA krivce a ze maximalni odchylka
tetivy od krivky nikde nepresahuje pozadovanou ACCUR."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Spline
from gerlib.accur import set_accuracy, get_accuracy, reset_accuracy
from gerlib.e45 import discretize, _segment_coeffs, _distance_to_chord
from gerlib.glfun import evaluate


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def max_chord_deviation(spline, chain):
    """Pro kazdou tetivu vysledneho retezce najde maximalni odchylku od
    skutecne krivky (hustym vzorkovanim) - nezavisla kontrola presnosti,
    nepouziva stejnou D(1..3)/POLY2 logiku jako _flatten_segment."""
    coeffs = _segment_coeffs(spline, 1)  # jednosegmentova testovaci krivka
    worst = 0.0
    for i in range(len(chain.points) - 1):
        p0, p1 = chain.points[i], chain.points[i + 1]
        # over 50 vzorky mezi odpovidajicimi parametry (lze, protoze pro
        # nasi testovaci parabolu je x(t)=t, takze parametr = x-souradnice)
        t0, t1 = p0.x, p1.x
        for s in range(1, 50):
            t = t0 + (t1 - t0) * s / 50.0
            xy = evaluate(coeffs, t, order=0)
            d = _distance_to_chord((p0.x, p0.y), (p1.x, p1.y), xy)
            worst = max(worst, d)
    return worst


def main():
    # --- ACCUR ---
    check(math.isclose(get_accuracy(), 0.01), "ACCUR: vychozi presnost je 0.01")
    set_accuracy(0.05)
    check(math.isclose(get_accuracy(), 0.05), "ACCUR: set_accuracy zmeni aktualni hodnotu")
    reset_accuracy()
    check(math.isclose(get_accuracy(), 0.01), "ACCUR: reset_accuracy vrati vychozich 0.01")

    # --- E45 na parabole y=x^2 (presna Hermitova reprezentace) ---
    p0, p1 = Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 0.0)
    t0, t1 = Vector(1.0, 0.0, 0.0), Vector(1.0, 2.0, 0.0)
    parabola = Spline([p0, p1], [t0, t1])

    for accuracy in (0.1, 0.02, 0.005):
        set_accuracy(accuracy)
        chain = discretize(parabola)
        check(chain.points[0].x == 0.0 and chain.points[0].y == 0.0, "E45: prvni bod retezce je zacatek krivky")
        check(math.isclose(chain.points[-1].x, 1.0) and math.isclose(chain.points[-1].y, 1.0),
              "E45: posledni bod retezce je konec krivky (presnost %.3f)" % accuracy)
        worst = max_chord_deviation(parabola, chain)
        check(worst <= accuracy * 1.05,
              "E45: max. odchylka tetivy (%.5f) je v ramci pozadovane presnosti %.3f" % (worst, accuracy))

    # presnejsi pozadavek musi dat aspon tolik bodu jako hrubsi
    set_accuracy(0.1)
    coarse = discretize(parabola)
    set_accuracy(0.005)
    fine = discretize(parabola)
    check(len(fine.points) >= len(coarse.points), "E45: presnejsi ACCUR -> aspon tolik bodu jako hrubsi")
    reset_accuracy()

    # --- E45 na primce (degenerovany segment - zadny extrem odchylky) ---
    line_spline = Spline([Point(0.0, 0.0, 0.0), Point(10.0, 0.0, 0.0)],
                          [Vector(10.0, 0.0, 0.0), Vector(10.0, 0.0, 0.0)])
    line_chain = discretize(line_spline)
    check(len(line_chain.points) == 2, "E45: dokonale rovny usek nepotrebuje zadne mezilehle body")
    check(line_chain.points[1].x == 10.0, "E45: primka - koncovy bod souhlasi")

    # --- E45 s explicitnimi P1/P2 (podinterval) ---
    set_accuracy(0.02)
    sub_start = Point(0.25, 0.0625, 0.0)  # bod na parabole v x=0.25
    sub_end = Point(0.75, 0.5625, 0.0)    # bod na parabole v x=0.75
    sub_chain = discretize(parabola, sub_start, sub_end)
    check(math.isclose(sub_chain.points[0].x, 0.25, abs_tol=1e-6),
          "E45: s P1/P2 zacina retezec v P1 (x=0.25)")
    check(math.isclose(sub_chain.points[-1].x, 0.75, abs_tol=1e-6),
          "E45: s P1/P2 konci retezec v P2 (x=0.75)")

    # --- E45 pozpatku (P1 "za" P2 na krivce) ---
    back_chain = discretize(parabola, sub_end, sub_start)
    check(math.isclose(back_chain.points[0].x, 0.75, abs_tol=1e-6),
          "E45: pozpatku - prvni bod je P1=sub_end (x=0.75)")
    check(math.isclose(back_chain.points[-1].x, 0.25, abs_tol=1e-6),
          "E45: pozpatku - posledni bod je P2=sub_start (x=0.25)")
    reset_accuracy()

    print("Vse OK.")


if __name__ == "__main__":
    main()
