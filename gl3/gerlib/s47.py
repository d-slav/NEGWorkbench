# -*- coding: utf-8 -*-
"""
Procedury S47,T47    Knihovna GL3E2
Zdroj: S47.FOR (Brezen 1984) - dodano uzivatelem.

Ucel:    Spojeni dvou krivek 2D i 3D.
         SM=S47>S1,S2[,K]
         TM=T47>T1,T2[,K]

Krivka SM/TM vznika spojenim S1(T1) a S2(T2) - ke koncovemu bodu prvni
krivky se pripoji druha krivka svym pocatecnim bodem (nejsou-li tyto
body totozne, vznika NESOUVISLA krivka - viz G10.md, zadny zavazny
pozadavek na shodu tu neni). Vysledna krivka je orientovana souhlasne
s orientaci S1(T1).

K (v G10.md vubec nezminen - odvozeno uzivatelem primo ze zdrojoveho
kodu, viz nize) rika, jak se ve SPOJI (uzel, kde S1 konci a S2 zacina)
naloz1 s tecnymi vektory obou krivek, ktere tam obecne NEJSOU stejne
(kazda krivka ma svou vlastni koncovou/pocatecni tecnu):

    K=0 (vychozi, i pro cokoliv mimo 0..3 - IF (K.LT.0.OR.K.GT.3) K=0
        ve S47.FOR)  - obe krivky si v miste spoje ZACHOVAJI SVE VLASTNI
        tecny - vysledna krivka muze mit ve spoji zlom (tecna
        nespojita, jen poloha spojita).
    K=1 - ve spoji se pouzije tecny vektor PRVNI krivky (S1/T1) - jeho
        hodnota se prevezme i pro zacatek druhe krivky.
    K=2 - ve spoji se pouzije tecny vektor DRUHE krivky (S2/T2).
    K=3 - tecne vektory obou krivek se ve spoji ZPRUMERUJI (aritmeticky
        prumer po slozkach), aby vznikla vizualne hladsi (ale uz ani
        jedne puvodni krivce presne neodpovidajici) navaznost.

'closed' vysledne krivky (viz Spline.closed) se urcuje NEZAVISLE na K,
z PUVODNICH (nijak K neupravenych) tecen a poloh obou vstupnich krivek
- presne podle S47.FOR: kontroluje se, jestli by spojenim S2-pak-S1 (v
tomhle poradi, tedy "obchozi"/vnejsi sev) vznikla poloha- i tecne-
spojita (uhel < 1e-3 stupne, vzdalenost < 1e-3) navaznost SOUCASNE se
skutecnym (vnitrnim) spojem S1-pak-S2 - jinymi slovy: jsou-li S1 a S2
navzajem tak dobre slozitelne, ze spolecne tvori jednu hladce uzavrenou
smycku, at uz ji obejdes od S1 k S2, nebo (opacnym smerem pres vnejsi
konce) od S2 zpet k S1. Kdyz ano, vysledna krivka SM/TM se oznaci jako
uzavrena (closed=True); jinak jako otevrena (closed=False), bez ohledu
na to, jak moc "hladce" spolu S1/S2 na SKUTECNEM spoji navazuji (to uz
resi jen K, ne closed-priznak).
"""
from .types import Point, Vector, Spline
from .dspn import _chord
from .angl70 import angle_between_deg

_ANGLE_EPS_DEG = 1e-3
_DIST_EPS = 1e-3


def _own_segment_tangents(spline):
    """Seznam (tecna_na_zacatku, tecna_na_konci) pro kazdy segment
    'spline', PUVODNI (nijak neupravene) - viz Spline.segment_tangent_pair
    (funguje jednotne pro spolecnou tecnu na uzel - S03 - i rozdilne
    tecny po stranach uzlu - S01/S10)."""
    return [spline.segment_tangent_pair(i) for i in range(len(spline.points) - 1)]


def _avg_vector(v1, v2):
    return Vector((v1.x + v2.x) / 2.0, (v1.y + v2.y) / 2.0, (v1.z + v2.z) / 2.0)


def make_joined_spline(spline1, spline2, k=None, opcode="S47"):
    if not isinstance(spline1, Spline):
        raise TypeError("%s: prvni krivka (S1) neni Spline, ale %r" % (opcode, type(spline1)))
    if not isinstance(spline2, Spline):
        raise TypeError("%s: druha krivka (S2) neni Spline, ale %r" % (opcode, type(spline2)))
    if len(spline1.points) < 2:
        raise ValueError("%s: prvni krivka (S1) musi mit aspon 1 segment (2 body)" % (opcode,))
    if len(spline2.points) < 2:
        raise ValueError("%s: druha krivka (S2) musi mit aspon 1 segment (2 body)" % (opcode,))

    k_int = int(round(k)) if k is not None else 0
    if k_int < 0 or k_int > 3:
        k_int = 0  # S47.FOR: IF (K.LT.0.OR.K.GT.3) K=0

    seg1 = _own_segment_tangents(spline1)
    seg2 = _own_segment_tangents(spline2)

    # 'closed' - viz modulovy docstring - z PUVODNICH (K se netyka)
    # tecen a poloh obou vstupnich krivek.
    own_start_t1 = seg1[0][0]
    own_end_t1 = seg1[-1][1]
    own_start_t2 = seg2[0][0]
    own_end_t2 = seg2[-1][1]
    closed = (
        _chord(spline1.points[0], spline2.points[-1]) <= _DIST_EPS
        and angle_between_deg(own_start_t1, own_end_t2) <= _ANGLE_EPS_DEG
        and _chord(spline1.points[-1], spline2.points[0]) <= _DIST_EPS
        and angle_between_deg(own_end_t1, own_start_t2) <= _ANGLE_EPS_DEG
    )

    # Tecna(y) VE SPOJI (mezi koncem S1 a zacatkem S2) podle K - viz
    # modulovy docstring. Zbytek tecen obou krivek zustava beze zmeny.
    if k_int == 0:
        joint_t1, joint_t2 = own_end_t1, own_start_t2
    elif k_int == 1:
        joint_t1, joint_t2 = own_end_t1, own_end_t1
    elif k_int == 2:
        joint_t1, joint_t2 = own_start_t2, own_start_t2
    else:  # k_int == 3
        avg = _avg_vector(own_end_t1, own_start_t2)
        joint_t1, joint_t2 = avg, avg

    seg1 = seg1[:-1] + [(seg1[-1][0], joint_t1)]
    seg2 = [(joint_t2, seg2[0][1])] + seg2[1:]

    points = list(spline1.points) + list(spline2.points[1:])
    segment_tangents = seg1 + seg2
    node_tangents = [segment_tangents[0][0]] + [pair[1] for pair in segment_tangents]

    return Spline(
        points, node_tangents, closed=closed,
        opcode=opcode, parametrization="chordal",
        segment_tangents=segment_tangents,
    )
