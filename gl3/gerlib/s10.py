# -*- coding: utf-8 -*-
"""
Procedura GLSPL (GL3 opcode S10)    LET n.p. Uh.Hradiste
Zdroj: SPLINE.FOR (dispatch) + GLSPL.FOR/DSPN.FOR - STEJNA fortranovska
funkce jako S01 (viz gerlib.s01) - zadani uzivatele: "S01, T01, S10 a
T10 volaji stejnou fortran funkci." Uzavrenost krivky vyzaduje jinou
(CYKLICKOU) trojdiagonalni soustavu nez otevrena S01 - viz
gerlib.dspn.tangent_vectors_closed + gerlib.gtrin.solve_cyclic_tridiagonal
- ale vaha jednotlivych rovnic (chordalni prumer dvou secnovych smeru)
je STEJNA formule jako u DSPN pro S01, jen aplikovana na VSECHNY uzly
(zadny volny/okrajovy uzel neexistuje - kazdy ma sousedy na obou
stranach, indexovano cyklicky).

POZOR - prvni pokus (periodicke "phantom" rozsireni o 1 bod na kazde
strane pred zavolanim OTEVRENE tangent_vectors()) byl OVEREN JAKO
CHYBNY: na symetrickem ctverci (4 stejne dlouhe strany) dava ruzne
velke tecny vektory v jednotlivych rozich, coz je pro plne symetrickou
konfiguraci matematicky nemozne (spravne reseni MUSI byt symetricke).
"Phantom" rozsireni o pouhy 1 bod totiz do soustavy vnese chybu z
volneho/okrajoveho okrajoveho vzorce sousedniho (zahazovaneho) uzlu,
ktera se DO reseni sousednich SKUTECNYCH uzlu proscaka pres
Gaussovu eliminaci - neni to totez jako opravdu cyklicka soustava.
Overeno nezavisle numpy vypoctem (viz test_s10.py) pred timhle portem.

Ucel:    Uzavrena krivka K body se spojitou derivaci az do 2. radu
         vcetne (C2), sečnova (chord-length) parametrizace - viz G10.md
         'S10 - Uzavrena krivka prolozena K body'.

Uziti (GL3): SM=S10>P(I),K

    P(I) - pole uzlovych bodu krivky. Body P(I) (prvni) a P(I+K-1)
           (posledni) MUSI BYT TOTOZNE (viz G10.md - na rozdil od S01
           tu neni volny/otevreny konec, uzavreni je POVINNE, ne
           volitelne jako u E01 retezcu).
    K    - pocet bodu vysledne krivky VCETNE opakovaneho uzaviraciho
           bodu, K v <4,300> (viz G07.md: "minimalni pocet uzlovych
           bodu pro uzavrene krivky (S10, T10, S05, T04) je omezen na
           4"; horni mez 300 sdilena s S01/T01, sečnova parametrizace).
"""

from .types import Point, Vector, Spline
from .dspn import tangent_vectors_closed, _chord
from .s01 import MAX_POINTS

MIN_POINTS = 4


def make_spline(points_ref, k, opcode="S10"):
    k_int = int(round(k))
    if k_int < MIN_POINTS:
        raise ValueError(
            "%s: K (pocet bodu vc. uzaviraciho) musi byt >= %d pro uzavrenou "
            "krivku (dostal %r)" % (opcode, MIN_POINTS, k)
        )
    if k_int > MAX_POINTS:
        raise ValueError(
            "%s: K (pocet bodu krivky) nesmi prekrocit %d (dostal %d)"
            % (opcode, MAX_POINTS, k_int)
        )

    if len(points_ref) < k_int:
        raise ValueError(
            "%s: pole bodu obsahuje jen %d prvku, ale je potreba %d (K=%d)"
            % (opcode, len(points_ref), k_int, k_int)
        )

    nodes = list(points_ref[:k_int])
    for i, p in enumerate(nodes):
        if p is None:
            raise ValueError("%s: uzlovy bod c. %d neni definovan" % (opcode, i + 1))
        if not isinstance(p, Point):
            raise TypeError("%s: prvek c. %d neni bod (Point), ale %r" % (opcode, i + 1, p))

    first, last = nodes[0], nodes[-1]
    if _chord(first, last) > 1e-3:
        raise ValueError(
            "%s: pocatecni bod P(I) a koncovy bod P(I+K-1) musi byt totozne "
            "(uzavreni krivky) - vzdalenost %.6g" % (opcode, _chord(first, last))
        )

    # Prstenec unikatnich bodu (posledni prvek 'nodes' je jen opakovani
    # prvniho, viz kontrola vyse) - K bodu ma presne K-1 unikatnich.
    ring = nodes[:-1]

    directions = tangent_vectors_closed(ring)  # M smeru (chordalni vaha), cyklicka soustava
    directions = directions + [directions[0]]  # tecna v uzaviracim bode (=ring[0]) je stejna

    segment_tangents = []
    for i in range(k_int - 1):
        chord_len = _chord(nodes[i], nodes[i + 1])
        d_start, d_end = directions[i], directions[i + 1]
        t_start = Vector(d_start.x * chord_len, d_start.y * chord_len, d_start.z * chord_len)
        t_end = Vector(d_end.x * chord_len, d_end.y * chord_len, d_end.z * chord_len)
        segment_tangents.append((t_start, t_end))

    # 'tangents' (jedna na uzel) drzime jen informativne/pro zpetnou
    # kompatibilitu - autoritativni jsou segment_tangents (viz s01.py,
    # stejna konvence). Pro vnitrni uzel i pouzijeme tecnu z KONCE
    # predchoziho segmentu (i-1), stejne jako S01.
    node_tangents = [segment_tangents[0][0]]
    for i in range(k_int - 1):
        node_tangents.append(segment_tangents[i][1])

    return Spline(
        nodes, node_tangents, closed=True,
        opcode=opcode, parametrization="chordal",
        segment_tangents=segment_tangents,
    )
