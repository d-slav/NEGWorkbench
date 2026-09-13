# -*- coding: utf-8 -*-
"""Test S47 (spojeni dvou krivek) - viz S47.FOR (dodano uzivatelem) a
G10.md 'S47 - Spojeni dvou krivek'.

K neni v G10.md vubec zminen - vyznam vsech 4 hodnot (0..3) je
odvozen uzivatelem primo ze zdrojoveho kodu S47.FOR (viz
gerlib/s47.py modulovy docstring) - klicovy test tady je tedy presne
overeni chovani K=0/1/2/3 na krivkach se ZAMERNE ruznymi tecnami na
obou stranach spoje, plus nezavisla detekce 'closed' (uzavreny
smycky) na skutecne uzavíratelné dvojici (rozdelenem a znovu
spojenem S10 ctverci)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Spline
from gerlib.s01 import make_spline as make_s01
from gerlib.s10 import make_spline as make_s10
from gerlib.s47 import make_joined_spline


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


def vec_isclose(v, x, y, z, eps=1e-9):
    return abs(v.x - x) < eps and abs(v.y - y) < eps and abs(v.z - z) < eps


def main():
    # S1: (0,0,0)->(10,0,0), koncova tecna (1,1,0) [nenormovana - jen
    #     smer se pouzije, viz gerlib.s01 - vysledna delka = tetiva]
    # S2: (10,0,0)->(20,0,0), pocatecni tecna (1,-1,0)
    # -> ZAMERNE ruzne tecny na obou stranach spoje (45 stupnu nahoru
    #    vs. 45 stupnu dolu), aby K=0/1/2/3 davaly citelne odlisne
    #    vysledky.
    s1 = make_s01([Point(0, 0, 0), Point(10, 0, 0)], 2, v1=Vector(1, 0, 0), vk=Vector(1, 1, 0))
    s2 = make_s01([Point(10, 0, 0), Point(20, 0, 0)], 2, v1=Vector(1, -1, 0), vk=Vector(1, 0, 0))
    own_end_t1 = s1.segment_tangent_pair(0)[1]
    own_start_t2 = s2.segment_tangent_pair(0)[0]

    # --- zakladni tvar vysledku (body, opcode, provenience) ---
    joined = make_joined_spline(s1, s2, 0)
    check(joined.opcode == "S47", "provenience: opcode == 'S47'")
    check(len(joined.points) == 3, "spojena krivka ma 3 uzly (2+2-1)")
    check(
        [(p.x, p.y, p.z) for p in joined.points] == [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (20.0, 0.0, 0.0)],
        "body spojene krivky odpovidaji S1 nasledovane S2 (bez opakovani spolecneho bodu)",
    )

    # --- K=0 (vychozi): obe strany spoje si zachovaji SVE VLASTNI tecny ---
    j0 = make_joined_spline(s1, s2, 0)
    check(
        vec_isclose(j0.segment_tangent_pair(0)[1], own_end_t1.x, own_end_t1.y, own_end_t1.z),
        "K=0: konec S1 ve spoji ma SVOU vlastni tecnu (nezmenenou)",
    )
    check(
        vec_isclose(j0.segment_tangent_pair(1)[0], own_start_t2.x, own_start_t2.y, own_start_t2.z),
        "K=0: zacatek S2 ve spoji ma SVOU vlastni tecnu (nezmenenou)",
    )

    # --- K neuveden vubec (default) se chova stejne jako K=0 ---
    j_default = make_joined_spline(s1, s2)
    check(
        vec_isclose(j_default.segment_tangent_pair(0)[1], own_end_t1.x, own_end_t1.y, own_end_t1.z)
        and vec_isclose(j_default.segment_tangent_pair(1)[0], own_start_t2.x, own_start_t2.y, own_start_t2.z),
        "K neuveden -> stejne jako K=0",
    )

    # --- K=1: obe strany dostanou tecnu PRVNI krivky (S1) ---
    j1 = make_joined_spline(s1, s2, 1)
    t_end1, t_start2 = j1.segment_tangent_pair(0)[1], j1.segment_tangent_pair(1)[0]
    check(
        vec_isclose(t_end1, own_end_t1.x, own_end_t1.y, own_end_t1.z)
        and vec_isclose(t_start2, own_end_t1.x, own_end_t1.y, own_end_t1.z),
        "K=1: OBE strany spoje maji tecnu S1 (%s)" % (own_end_t1,),
    )

    # --- K=2: obe strany dostanou tecnu DRUHE krivky (S2) ---
    j2 = make_joined_spline(s1, s2, 2)
    t_end1, t_start2 = j2.segment_tangent_pair(0)[1], j2.segment_tangent_pair(1)[0]
    check(
        vec_isclose(t_end1, own_start_t2.x, own_start_t2.y, own_start_t2.z)
        and vec_isclose(t_start2, own_start_t2.x, own_start_t2.y, own_start_t2.z),
        "K=2: OBE strany spoje maji tecnu S2 (%s)" % (own_start_t2,),
    )

    # --- K=3: obe strany dostanou PRUMER obou puvodnich tecen ---
    j3 = make_joined_spline(s1, s2, 3)
    expected_avg_x = (own_end_t1.x + own_start_t2.x) / 2.0
    expected_avg_y = (own_end_t1.y + own_start_t2.y) / 2.0
    t_end1, t_start2 = j3.segment_tangent_pair(0)[1], j3.segment_tangent_pair(1)[0]
    check(
        vec_isclose(t_end1, expected_avg_x, expected_avg_y, 0.0)
        and vec_isclose(t_start2, expected_avg_x, expected_avg_y, 0.0),
        "K=3: OBE strany spoje maji prumer puvodnich tecen (%.4f, %.4f)" % (expected_avg_x, expected_avg_y),
    )

    # --- K mimo rozsah 0..3 -> chova se jako K=0 (S47.FOR: IF (K.LT.0.OR.K.GT.3) K=0) ---
    j_oor = make_joined_spline(s1, s2, 99)
    check(
        vec_isclose(j_oor.segment_tangent_pair(0)[1], own_end_t1.x, own_end_t1.y, own_end_t1.z),
        "K mimo rozsah (99) -> chova se jako K=0",
    )

    # --- 'closed' je NEZAVISLE na K - zustava False pro vsechny K, kdyz
    #     vstupni krivky netvori uzavíratelnou smycku (nase s1/s2 vyse
    #     netvori) ---
    for k in (0, 1, 2, 3):
        check(make_joined_spline(s1, s2, k).closed is False, "closed=False pro K=%d (krivky netvori smycku)" % k)

    # --- 'closed' detekce: rozdelim uzavreny ctverec (S10) na 2 poloviny
    #     a znovu spojim - MUSI vyjit closed=True, NEZAVISLE na K ---
    square = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0), Point(0, 10, 0), Point(0, 0, 0)]
    full = make_s10(square, 5)
    half1 = Spline(
        full.points[0:3], full.tangents[0:3], closed=False,
        opcode="S01", parametrization="chordal", segment_tangents=full.segment_tangents[0:2],
    )
    half2 = Spline(
        full.points[2:5], full.tangents[2:5], closed=False,
        opcode="S01", parametrization="chordal", segment_tangents=full.segment_tangents[2:4],
    )
    for k in (0, 1, 2, 3):
        rejoined = make_joined_spline(half1, half2, k)
        check(rejoined.closed is True, "rozdeleny+znovuspojeny uzavreny ctverec -> closed=True (K=%d)" % k)
    check(len(make_joined_spline(half1, half2, 0).points) == 5, "znovuspojeny ctverec ma zase 5 uzlu")

    # --- chyby: spatny typ / prilis kratka krivka ---
    try:
        make_joined_spline(s1, "not a spline")
        check(False, "S2 neni Spline - mel vyhodit TypeError")
    except TypeError as e:
        check("S47" in str(e), "spatny typ S2 -> jasna TypeError (%s)" % e)

    single_point_spline = Spline([Point(0, 0, 0)], [Vector(0, 0, 0)], closed=False)
    try:
        make_joined_spline(single_point_spline, s2)
        check(False, "S1 s 1 bodem (0 segmentu) mel vyhodit ValueError")
    except ValueError as e:
        check("S47" in str(e), "S1 s 1 bodem -> jasna ValueError (%s)" % e)

    print("\nVSE OK - S47 (spojeni dvou krivek, vc. K).")


if __name__ == "__main__":
    main()
