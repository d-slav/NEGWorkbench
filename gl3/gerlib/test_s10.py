# -*- coding: utf-8 -*-
"""Test S10 (GLSPL, uzavrena/periodicka chordalni parametrizace).

Klicovy test je symetrie na ctverci: 4 uzly stejne velkeho ctverce jsou
navzajem rovnocenne (rotace o 90 stupnu zobrazi konfiguraci samu na
sebe), takze SPRAVNE reseni MUSI davat tecne vektory stejne velikosti
ve vsech 4 rozich. Prvni pokus o implementaci (periodicke "phantom"
rozsireni o 1 bod pred zavolanim otevrene tangent_vectors(), viz
git historie s10.py) tohle NESPLNOVAL (davalo 2 ruzne velikosti
stridave) - byla to chyba, opravena skutecnym cyklickym
trojdiagonalnim resicem (gerlib.gtrin.solve_cyclic_tridiagonal).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from gerlib.s01 import make_spline as make_open_spline
from gerlib.s10 import make_spline as make_closed_spline


def _mag(v):
    return (v.x ** 2 + v.y ** 2 + v.z ** 2) ** 0.5


def main():
    # --- 1) symetrie na ctverci - viz modulovy docstring ---
    square = [
        Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0), Point(0, 10, 0),
        Point(0, 0, 0),  # uzaviraci bod = P(1)
    ]
    spline = make_closed_spline(square, 5)
    assert spline.closed is True
    assert spline.opcode == "S10" and spline.parametrization == "chordal"
    assert len(spline.points) == 5
    mags = [round(_mag(t), 9) for t in spline.tangents]
    print("Ctverec - velikosti tecnych vektoru ve vsech uzlech:", mags)
    assert len(set(mags)) == 1, "ctverec je plne symetricky - vsechny tecny musi vyjit stejne velike"
    # tecna v uzaviracim bode (index 4) musi byt STEJNA jako v P(1) (index 0)
    assert (round(spline.tangents[0].x, 9), round(spline.tangents[0].y, 9)) == (
        round(spline.tangents[4].x, 9), round(spline.tangents[4].y, 9)
    )
    print("Symetrie na ctverci (4 stejne velke tecny + sev = P(1)): OK")

    # --- 2) obdelnik (nesymetricky, ale porad periodicky) - sanity kontrola
    #     smeru: tecna v kazdem rohu by mela mirit "diagonalne" mezi obema
    #     prilehlymi stranami, ne rovnobezne s jednou z nich ---
    rect = [
        Point(0, 0, 0), Point(20, 0, 0), Point(20, 10, 0), Point(0, 10, 0),
        Point(0, 0, 0),
    ]
    spline_r = make_closed_spline(rect, 5)
    t0 = spline_r.tangents[0]
    assert t0.x > 0 and t0.y != 0, "tecna v rohu (0,0) obdelniku ma mirit sikmo, ne podel jedne strany"
    print("Obdelnik - tecna v rohu smeruje sikmo (%.3f, %.3f): OK" % (t0.x, t0.y))

    # --- 3) K musi byt >= 4 (viz G07.md) ---
    try:
        make_closed_spline([Point(0, 0, 0), Point(1, 0, 0), Point(0, 0, 0)], 3)
        assert False, "K=3 mel byt odmitnut (min pro uzavrenou krivku je 4)"
    except ValueError as e:
        assert "4" in str(e)
        print("K=3 odmitnuto (min. 4 pro uzavrenou krivku): OK (%s)" % e)

    # --- 4) K nad MAX_POINTS (300) odmitnuto ---
    try:
        make_closed_spline([Point(0, 0, 0)] * 301, 301)
        assert False, "K=301 mel byt odmitnut"
    except ValueError as e:
        assert "300" in str(e)
        print("K=301 odmitnuto (max. 300, sdileno s S01/T01): OK")

    # --- 5) prvni a posledni bod MUSI byt totozne ---
    open_ended = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0), Point(5, 5, 0)]
    try:
        make_closed_spline(open_ended, 4)
        assert False, "nezavreny vstup (P(1) != P(K)) mel byt odmitnut"
    except ValueError as e:
        assert "totozne" in str(e)
        print("Nezavreny vstup (P(1) != P(K)) odmitnut: OK (%s)" % e)

    # --- 6) S10 dava JINOU krivku nez S01 na stejnych (otevrenych) datech
    #     - jina matematika (cyklicka vs. volny okraj), i kdyz forma
    #     vstupu je podobna ---
    pentagon_open = [
        Point(0, 0, 0), Point(10, 2, 0), Point(8, 10, 0), Point(2, 9, 0), Point(-2, 3, 0),
    ]
    open_spline = make_open_spline(pentagon_open, 5)  # S01 - nezavreny, volne konce
    pentagon_closed = pentagon_open + [pentagon_open[0]]
    closed_spline = make_closed_spline(pentagon_closed, 6)  # S10 - stejny "tvar", ale uzavreny
    # tecna v P(1)/Q(1) se u otevrene (volny okraj) a uzavrene (cyklicka
    # vazba na posledni bod) verze musi ruzne - jinak by cyklicky resic
    # nedelal nic navic oproti volnemu okraji
    assert (round(open_spline.tangents[0].x, 6), round(open_spline.tangents[0].y, 6)) != (
        round(closed_spline.tangents[0].x, 6), round(closed_spline.tangents[0].y, 6)
    )
    print("S01 (volny okraj) vs S10 (cyklicka vazba) davaji ruznou tecnu v P(1): OK")

    print()
    print("VSE OK - S10 (uzavrena/periodicka krivka, sdili DSPN chordalni")
    print("vahovani se S01, ale resi skutecnou CYKLICKOU trojdiagonalni")
    print("soustavu) je matematicky spravne (symetricke na symetrickych datech).")


if __name__ == "__main__":
    main()
