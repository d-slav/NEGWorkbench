# -*- coding: utf-8 -*-
"""
Procedura C430          LET, k.p., Uh.Hradiste
Knihovna GERLIBPC                       Listopad 1989

Ucel:    Kruznice daneho polomeru prochazejici danym bodem a
         dotykajici se dane primky.

Uziti:   CALL C430(X1,Y1,X2,Y2,A2,B2,X3,X,Y,A,K,J)
         GL3:  CM=C30>>P,L,D,K

Parametry:  X1,Y1        R*4  Vstupni bod P
            X2,Y2,A2,B2  R*4  Vstupni primka L
            X3           R*4  Polomer D
            K            I*2  Vyberove cislo:
                Bod lezi mimo primku:
                    K=0 dotykovy bod je prvni, postupujeme-li po
                        primce v kladnem smeru
                    K=1 dotykovy bod je druhy
                Bod lezi na primce:
                    K=0 kruznice lezi vlevo od primky
                    K=1 kruznice lezi vpravo od primky
            X,Y,A        R*4  Vysledna kruznice
            J            I*2  J=0 kruznice definovana,
                               J=4300 polomer prakticky nulovy,
                               J=4301 bod je od primky vzdalen o
                               hodnotu vetsi nez prumer (2*D) - kruznice
                               pozadovaneho polomeru neexistuje

Volane moduly puvodniho C430.FOR (P140, P118, P121, L321, V201, V220,
V241) nemaji v tomto portu samostatny protejsek - misto rekonstrukce
jejich (nedodaneho) obsahu je nize odvozena a pouzita EKVIVALENTNI,
ale primociarejsi konstrukce ze standardni analyticke geometrie
(stejny pristup jako uz drive u C32/C33/C34, viz gerlib/circle_geom.py):

  Hledany stred O kruznice CM musi soucasne splnovat:
    (a) |O - P| = D                (kruznice prochazi bodem P)
    (b) vzdalenost O od primky L = D   (kruznice je tecna k L)

  Lezi-li P primo na L, je P sam dotykovym bodem a O = P + D * kolmice
  k L na strane K (viz V230/parallel_line, K=0 vlevo, K=1 vpravo).

  Lezi-li P mimo L, plyne z (b), ze O lezi na jedne ze dvou primek
  rovnobeznych s L ve vzdalenosti D (viz L20/parallel_line). Rozborem
  (viz PYTHAGorovska substituce pro primku L=osa x, P=(0,py)) lze
  ukazat, ze RESENI EXISTUJE JEN NA TE ROVNOBEZCE, KTERA LEZI NA
  STEJNE STRANE OD L JAKO BOD P (druha strana dava vzdy zaporny
  diskriminant) - staci tedy tuto jednu rovnobezku protnout s kruznici
  se stredem P a polomerem D (viz P120/circle_geom.line_circle_
  intersection). Prusecik(y) jsou jiz serazeny vzestupne podle
  parametru podel kladneho smeru primky - presne v poradi, jake
  vyzaduje vyberove cislo K (0=prvni, 1=druhy). Neexistuje-li prusecik
  (bod je od primky vzdalen vice nez 2*D), je to legitimni "bez reseni"
  pripad (NoSolution, viz errors.py) - odpovida puvodnimu J=4301.
"""
import math

from .types import Point, Circle
from .p40 import foot_point_on_line
from .l20 import parallel_line
from .v230 import perpendicular_vector
from .circle_geom import line_circle_intersection
from .errors import NoSolution

_TOL = 1e-3  # stejna tolerance jako C430.FOR (1E-3)


def tangent_through_point(point, line, radius, k):
    """C30: CM=C30>P,L,D,K - kruznice polomeru D tecna k primce L a
    prochazejici bodem P (C430.FOR). Viz hlavicka modulu pro odvozeni."""
    r = abs(radius)
    if r < _TOL:
        raise ValueError(
            "C30: polomer je prakticky nulovy (< %s) - kruznice neni "
            "definovana (puvodni J=4300)" % _TOL
        )
    k = int(round(k))

    foot = foot_point_on_line(point, line)
    dist = math.hypot(point.x - foot.x, point.y - foot.y)

    if dist <= _TOL:
        # Bod P lezi na primce - je primo dotykovym bodem.
        perp = perpendicular_vector(line.direction, k)
        center = Point(point.x + r * perp.x, point.y + r * perp.y, 0.0)
        return Circle(center, r)

    # Bod P mimo primku - zjistime, na ktere strane primky lezi (stejna
    # konvence jako V230/parallel_line: K=0 vlevo), a posuneme primku
    # na TUTO stranu o polomer r.
    perp_left = perpendicular_vector(line.direction, 0)
    on_left = (point.x - foot.x) * perp_left.x + (point.y - foot.y) * perp_left.y >= 0.0
    side = 0 if on_left else 1
    offset_line = parallel_line(line, r, side)

    candidates = line_circle_intersection(offset_line, point, r)
    if not candidates:
        raise NoSolution(
            "C30: bod je od primky vzdalen vice nez prumer (2*D) - "
            "kruznice pozadovaneho polomeru neexistuje (puvodni J=4301)"
        )
    if len(candidates) == 1:
        return Circle(candidates[0], r)
    return Circle(candidates[0] if k == 0 else candidates[1], r)
