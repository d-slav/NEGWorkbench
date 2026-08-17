# -*- coding: utf-8 -*-
"""
Procedura P66            n.p. LET Uh. Hradiste          RNDr. Krusina
Knihovna GL3E2                                       Unor 1985, str. 4560

Ucel:    Bod na retezci souradnici.

Uziti:   PM=P66>>E,D,KK

Bod PM lezi na retezci E a jedna jeho souradnice ma hodnotu D. Vyberove
cislo KK v sobe desitkove bali DVA udaje (K2=KK/10, K1=KK-K2*10, viz
G10.md 'P66 - Bod na retezci souradnici' a stejna konvence jako u
C32/C33/C34):
    K1=0 ... x-ova souradnice bodu PM ma hodnotu D
    K1=1 ... y-ova souradnice bodu PM ma hodnotu D
    K2    ... poradove cislo bodu (pruseciku) od pocatku orientovaneho
              retezce, v rozsahu <1,M>, kde M je skutecny pocet
              pruseciku retezce s prislusnou souradnicovou primkou.

Neni-li prusecik daneho poradi nalezen, je hlasena chyba (puvodni
IER=566). Je-li prusecikem CELA usecka retezce (lezi cela presne na
souradnici D), je take hlasena chyba (puvodni IER=568) - takovy usek
ale poradove cislo pruseciku posouva o jednu dal (tzn. i kdyz sam
nejde vratit jako jednoznacny bod, "zabira" jedno poradove cislo K2).

Puvodni P66.FOR pracuje primo se zaznamy CL2 (LINK flag pro fiktivni/
uzaverova spojeni, ktera nas Curve model - jedna souvisla posloupnost
bodu - nema). Tento port prochazi primo curve.points a resi stejny
problem, jaky original resi pres LINK/JIER: aby se prusecik prave NA
SDILENEM UZLU dvou sousednich useku (nebo na hranici "cely usek na
primce" behu) nepocital dvakrat.

Klicovy postreh z rozboru puvodniho Fortranu: krizeni, ktere padne
PRESNE NA KONEC useku (t=1), se NEPOCITA hned - pokud existuje
navazujici usek, "odlozi se" a zapocita ho az TEN (jako svuj vlastni
zacatek, t=0) - viz nize 'in_run' (analogie puvodniho JIER). Vyjimka:
je-li to posledni usek celeho retezce (neni uz co by prevzalo), musi
se zapocitat hned. Diky tomu:
  - krizeni presne ve sdilenem uzlu dvou "genuinnich" (nekonstantnich)
    useku se zapocita prave jednou (via t=0 navazujiciho useku),
  - genuinni usek doteka na okraj "cely usek na primce" behu se
    NEZAPOCITAVA vubec (uz ho zapocital beh sam), presne jak dela
    puvodni JIER=1 kontrola pri navratu z konstantniho useku.
"""
import math

from .types import Point, Curve
from .p13 import interpolate_point

_EQ_TOL = 1e-6     # shodnost souradnic (jako ve Fortranu 1E-6)
_SEG_TOL = 1e-3    # degenerovany (temer nulovy) usek (jako ve Fortranu 1E-3 pro D610)
_PARAM_TOL = 1e-6  # tolerance parametru t mimo <0,1>


def point_on_chain_by_coord(curve, d, kk):
    """P66: PM=P66>E,D,KK - bod na retezci E s K1-tou souradnici (x/y)
    rovnou D, K2-ty v poradi od pocatku retezce (viz hlavicka modulu).
    'kk' je baleny vyber K2*10+K1, presne jako ve Fortranu."""
    if not isinstance(curve, Curve):
        raise TypeError("P66: prvni argument musi byt retezec (Curve), dostal %r" % (curve,))

    kk_int = int(round(kk))
    k1 = kk_int % 10
    k2 = kk_int // 10

    if k2 < 1 or k1 not in (0, 1):
        raise ValueError(
            "P66: neplatne vyberove cislo KK=%d (ocekava K2=KK//10 >= 1 "
            "a K1=KK%%10 v {0,1}) (puvodni IER=567)" % kk_int
        )

    pts = curve.points
    n = len(pts)
    if n < 2:
        raise ValueError("P66: retezec ma min nez 2 body")

    def coord(p):
        return p.x if k1 == 0 else p.y

    ik = 0
    in_run = False  # jsme uvnitr (nebo prave skoncili) "cely usek na primce" beh - analogie puvodniho JIER

    n_segments = n - 1

    for i in range(n_segments):
        a, b = pts[i], pts[i + 1]
        seg_len = math.hypot(b.x - a.x, b.y - a.y)
        if seg_len < _SEG_TOL:
            continue  # degenerovany (temer nulovy) usek - preskocit, stav se nemeni

        ca, cb = coord(a), coord(b)
        is_last_segment = (i == n_segments - 1)

        if abs(cb - ca) < _EQ_TOL:
            # K1-ta souradnice je podel cele usecky konstantni
            if abs(ca - d) < _EQ_TOL:
                if not in_run:
                    ik += 1
                    if ik == k2:
                        raise ValueError(
                            "P66: %d. prusecik je cely usek retezce lezici "
                            "na souradnici D - nelze vratit jednoznacny bod "
                            "(puvodni IER=568)" % k2
                        )
                in_run = True
            else:
                in_run = False
            continue

        # "genuinni" (nekonstantni) usek
        was_in_run = in_run
        in_run = False

        t = (d - ca) / (cb - ca)
        if t < -_PARAM_TOL or t > 1.0 + _PARAM_TOL:
            continue
        t = max(0.0, min(1.0, t))

        if t < _EQ_TOL:
            # krizeni na POCATKU tohoto useku
            if was_in_run:
                # uz zapocitano prave skoncenym "cely usek na primce" behem
                continue
            # jinak: bud i==0 (zacatek retezce lezi na D), nebo prevzeti
            # odlozeneho (t=1) krizeni predchoziho genuinniho useku
            crossing = interpolate_point(a, b, 0.0)
            ik += 1
            if ik == k2:
                return Point(crossing.x, crossing.y, 0.0)
            continue

        if t > 1.0 - _EQ_TOL and not is_last_segment:
            # krizeni na KONCI tohoto useku, ale existuje navazujici usek
            # -> odlozit (nezapocitavat ted), prevezme ho dalsi usek jako
            # sve vlastni t=0
            continue

        # vnitrni prusecik (0<t<1), nebo t=1 na POSLEDNIM useku retezce
        # (tam neni co by odlozene krizeni prevzalo, musi se zapocitat hned)
        crossing = interpolate_point(a, b, t)
        ik += 1
        if ik == k2:
            return Point(crossing.x, crossing.y, 0.0)

    raise ValueError(
        "P66: pozadovany prusecik poradi K2=%d nebyl nalezen (puvodni IER=566)" % k2
    )
