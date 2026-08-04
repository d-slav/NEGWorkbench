# -*- coding: utf-8 -*-
"""
Procedura P48 (dispatch) + P48E + P48S     n.p. LET Kunovice / GL3E2
Puvodni Fortran: P48.FOR (dispatch podle typu 2. argumentu), P48E.FOR
(retezec, typ E), P48S.FOR (krivka, typ S) - Leden 1983

Ucel:    Vyjmuti K-teho uzloveho bodu retezce nebo krivky.

Uziti:   PM=P48>pg,K<        K - index <1,N>
         (pg = retezec typu E / Curve, nebo krivka typu S / Spline)

Chyba:   K mimo rozsah <1,N> -> puvodni IER=256

POZNAMKA k puvodnimu Fortranu: P48E/P48S pracuji primo se souborovymi
zaznamy interni ukladaci struktury (pole R()/IIN(), cislovane zaznamy
souboru otevreneho pres OPEOLD, format viz E3.INC) - to je implementacni
detail tehdejsiho ukladani objektu na disk, ktery uz na nasi in-memory
reprezentaci (Curve.points / Spline.points = obycejny Python seznam)
nema smysl replikovat bajt po bajtu (chybi nam i E3.INC). Prevedeno je
proto FUNKCNI chovani, ktere z obou zdrojaku jasne vyplyva:

  - normalne (K < N) vrat bod na indexu K (1-based) beze zmeny
  - pro POSLEDNI bod (K == N, a N != 1) vrat souradnice bodu N, ale
    "vracime se" o jeden segment zpet: vysledny index je N-1 misto N
    a priznak "konec segmentu" (puvodni PARAM=1D0 misto 0D0) je True

Tohle 1:1 odpovida tomu, jak uz E01.FOR znacil posledni bod nasi Curve
(indices[-1] = N-1, is_end[-1] = True) - tehdy jsme nevedeli, k cemu to
bude, ted uz vime: P48 na poslednim bode musi ukazovat na KONEC
posledniho (N-1-tveho) segmentu krivky/retezce, ne na "zacatek"
neexistujiciho N-teho segmentu (dulezite napr. pro tecnu na krivce v
danem bode).

Vraceny GL3 typ "P" je proste bod (x, y, 0) - o nic vic se nasim typem
Point nezajima. Index/is_end jsou navic k dispozici pres chain_node()/
spline_node() primo (ne skrz curve_node(), ktery vraci jen Point), pro
pripad, ze by je pozdeji potrebovala navazujici operace (typicky P42 -
projekce na krivku v danem segmentu).
"""

from .types import Point, Curve, Spline


def _node_index_and_flag(k, n):
    """Spolecna logika P48E/P48S: pro K==N (posledni bod, N != 1) vrat
    (N-1, True), jinak (K, False). Chyba pro K mimo <1,N> (puvodni
    IER=256)."""
    if k < 1 or k > n:
        raise ValueError("P48: index K=%r mimo rozsah <1,%d> (puvodni chyba 256)" % (k, n))
    if k == n and n != 1:
        return n - 1, True
    return k, False


def chain_node(curve, k):
    """P48E: K-ty uzlovy bod retezce (Curve). Vraci (Point, index,
    is_end) - viz poznamka v hlavicce modulu."""
    n = len(curve.points)
    idx, is_end = _node_index_and_flag(k, n)
    p = curve.points[k - 1]
    return Point(p.x, p.y, 0.0), idx, is_end


def spline_node(spline, k):
    """P48S: K-ty uzlovy bod krivky (Spline). Vraci (Point, index,
    is_end) - viz poznamka v hlavicce modulu."""
    n = len(spline.points)
    idx, is_end = _node_index_and_flag(k, n)
    p = spline.points[k - 1]
    return Point(p.x, p.y, 0.0), idx, is_end


def curve_node(curve_or_spline, k):
    """P48: dispatch podle typu (retezec E = Curve, krivka S = Spline),
    viz P48.FOR (BT1.EQ.'E'). Vraci jen Point - GL3 vidi navratovy typ
    P (bod); index/is_end jsou pristupne primo pres chain_node()/
    spline_node(), kdyby je pozdeji potrebovala navazujici operace."""
    if isinstance(curve_or_spline, Curve):
        point, _, _ = chain_node(curve_or_spline, k)
    elif isinstance(curve_or_spline, Spline):
        point, _, _ = spline_node(curve_or_spline, k)
    else:
        raise TypeError(
            "P48: ocekaval retezec (Curve/E) nebo krivku (Spline/S), "
            "dostal %r" % (type(curve_or_spline),)
        )
    return point
