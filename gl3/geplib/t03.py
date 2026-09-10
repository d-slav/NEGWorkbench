# -*- coding: utf-8 -*-
"""
Operace T03 (GL3 opcode T03, prostorova obdoba S03) - Otevrena hranicni
krivka plochy prolozena K body s okrajovymi tecnymi vektory,
parametrizace 0-1 (uniformni).

Uziti (GL3): TM=T03>Q(I),K[,[U1],[UK][,N]]

    Q(I) - pole uzlovych bodu krivky (3D, "adresa prvniho bodu",
           Fortran konvence 'Q(1),N' jako u S03/E01/S01)
    K    - pocet bodu vysledne krivky, K v <2,128> (viz G10.md - stejna
           horni mez jako S03/S02, sdilena infrastruktura RTAB)
    U1   - pocatecni tecny vektor (nezadano/nulovy = dopocita se)
    UK   - koncovy tecny vektor (stejne)
    N    - kazdy N-ty bod puvodniho pole se stane uzlem vysledne
           krivky (nezadano = 1, kazdy bod)

Otevrena krivka TM prochazi K body Q(I)..Q(I+K-1) a v koncovych bodech
se tecne dotyka vektoru U1 a UK, parametrizovana 0-1 - urcena pro
pouziti jako definicni krivka plochy (viz G10.md 'T03 - Otevrena
hranicni krivka plochy prolozena body parametrizovana 0-1'). Pro K=2
je definovan jediny segment; nejsou-li U1/UK uvedeny, je to primy
usek. Pro K>2 bez U1/UK (nebo nulovych) krivka na okraji vybiha do
primky (relaxovana okrajova podminka).

NA ROZDIL OD T01/S01: vysledny tvar krivky JE ovlivnen i DELKOU
vektoru U1/UK, ne jen jejich smerem (viz G10.md - explicitne uvedeno u
T03/S03, na rozdil od T01/S01, kde delka nehraje roli - viz oprava v
gerlib/s01.py). Kratsi/delsi U1/UK pri stejnem smeru tedy zamerne
davaji RUZNOU krivku.

Zadani uzivatele: "[T03] je stejny [fortranovy zdroj] jako S03, a tu
mame" - zadny dalsi fortranovy kod tedy netreba, T03 je (stejne jako
T01 nad S01) cistokrevny tenky wrapper nad uz existujici gerlib.s03.
make_spline - jen s opcode="T03" pro spravnou provenience krivky
(Point/Vector v tomto portu uz VZDY nesou x,y,z, viz geplib/__init__.py
docstring - rozdil P/Q a V/U je jen jazykova konvence GL3 prefixu, ne
odlisny Python typ, takze zadna dalsi prostorova logika navic netreba).
"""
from gerlib.s03 import make_spline as _make_spline


def make_spatial_spline(points_ref, k, u1=None, uk=None, n=None):
    """T03: TM=T03>Q(I),K[,[U1],[UK][,N]] - otevrena prostorova krivka
    K body se dvema okrajovymi tecnymi vektory (delka vektoru NA TVAR
    MA VLIV, na rozdil od T01), parametrizace 0-1 (viz
    gerlib.s03.make_spline - shodna matematika, jen jina provenience
    oznaceni vysledne krivky)."""
    return _make_spline(points_ref, k, u1, uk, n, opcode="T03")
