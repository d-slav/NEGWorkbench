# -*- coding: utf-8 -*-
"""
Procedura GLSPL (GL3 opcode S01)    LET n.p. Uh.Hradiste
Zdroj: SPLINE.FOR (dispatch dle dimenze) + GLSPL.FOR (vlastni telo)

Ucel:    Krivka K body se dvema okrajovymi tecnymi vektory - CHORDALNI
         (chord-length) parametrizace. Na rozdil od S03 (dsn.py,
         uniformni parametrizace - vzdalenosti mezi body se ignoruji)
         GLSPL pocita tecne smery pomoci DSPN (viz dspn.py), ktere
         vahuje prispevky sousednich bodu skutecnou delkou tetivy
         segmentu - blizsi tomu, jak casto parametrizuji krivky i bezne
         CAD/OCC nastroje (proto ocekavame, ze S01 da krivku bliz tomu,
         co vyrobi napr. FreeCAD Draft/Curves workbench, nez S03).

Uziti (GL3): SM=S01>P(I),K[,[V1],[VK]]

    P(I) - pole uzlovych bodu krivky
    K    - pocet bodu vysledne krivky (POZOR: tohle GL3-urovnove K je
           POCET BODU, neplest s Fortranovym vnitrnim parametrem K v
           DSPN/GLSPL, ktery tam znamena DIMENZI 2D/3D - nase Point/
           Vector uz tuhle dimenzi nesou implicitne (x,y,z), takze ji
           neresime zvlast.)
    V1   - pocatecni tecny vektor (nezadano/nulovy = dopocita se)
    VK   - koncovy tecny vektor (stejne)

DULEZITY ROZDIL OPROTI S03: GLSPL.FOR po ziskani smeru z DSPN kazdy
smer JESTE PRESKALUJE skutecnou delkou tetivy KONKRETNIHO segmentu:

    UP(i) = smer(uzel i)   * delka_tetivy(segment i)   - tecna na zacatku segmentu i
    UK(i) = smer(uzel i+1) * delka_tetivy(segment i)   - tecna na konci segmentu i

Protoze se stejny uzel i muze dotykat dvou ruznych segmentu s ruznou
delkou tetivy, NEMA obecne jednu spolecnou tecnu - proto Spline nese
segment_tangents (dvojice tecen PO SEGMENTECH, viz gerlib.types.Spline),
ne jen jednu tecnu na uzel.
"""

from .types import Point, Vector, Spline
from .dspn import tangent_vectors, _chord


def make_spline(points_ref, k, v1=None, vk=None):
    k_int = int(round(k))
    if k_int < 2:
        raise ValueError("S01: K (pocet bodu krivky) musi byt >= 2 (dostal %r)" % (k,))

    if len(points_ref) < k_int:
        raise ValueError(
            "S01: pole bodu obsahuje jen %d prvku, ale je potreba %d (K=%d)"
            % (len(points_ref), k_int, k_int)
        )

    nodes = list(points_ref[:k_int])
    for i, p in enumerate(nodes):
        if p is None:
            raise ValueError("S01: uzlovy bod c. %d neni definovan" % (i + 1,))
        if not isinstance(p, Point):
            raise TypeError("S01: prvek c. %d neni bod (Point), ale %r" % (i + 1, p))

    if k_int == 2:
        # GLSPL.FOR: pro presne 2 body je to primy segment - smer je
        # sekanta (znormovana, ale pak zase vynasobena stejnou delkou
        # tetivy = beze zmeny), tedy proste rovnou surova sekanta.
        secant = Vector(nodes[1].x - nodes[0].x, nodes[1].y - nodes[0].y, nodes[1].z - nodes[0].z)

        def _pick(v):
            return v if (v is not None and (v.x, v.y, v.z) != (0.0, 0.0, 0.0)) else secant

        t0, t1 = _pick(v1), _pick(vk)
        return Spline(
            nodes, [t0, t1], closed=False,
            opcode="S01", parametrization="chordal",
            segment_tangents=[(t0, t1)],
        )

    directions = tangent_vectors(nodes, v1, vk)  # smery (chordalni vaha), jeden na uzel

    segment_tangents = []
    for i in range(k_int - 1):
        chord_len = _chord(nodes[i], nodes[i + 1])
        d_start, d_end = directions[i], directions[i + 1]
        t_start = Vector(d_start.x * chord_len, d_start.y * chord_len, d_start.z * chord_len)
        t_end = Vector(d_end.x * chord_len, d_end.y * chord_len, d_end.z * chord_len)
        segment_tangents.append((t_start, t_end))

    # 'tangents' (jedna na uzel) drzime jen informativne/pro zpetnou
    # kompatibilitu - autoritativni jsou segment_tangents. Konvence: pro
    # vnitrni uzel i pouzijeme tecnu z KONCE predchoziho segmentu (i-1).
    node_tangents = [segment_tangents[0][0]]
    for i in range(k_int - 1):
        node_tangents.append(segment_tangents[i][1])

    return Spline(
        nodes, node_tangents, closed=False,
        opcode="S01", parametrization="chordal",
        segment_tangents=segment_tangents,
    )
