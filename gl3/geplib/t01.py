# -*- coding: utf-8 -*-
"""
Operace T01 (GL3 opcode T01, prostorova obdoba S01) - Otevrena krivka
prolozena mnozinou K bodu s okrajovymi tecnymi vektory, secnova
(chord-length) parametrizace.

Uziti (GL3): TM=T01>Q(I),K[,[U1][,UK]]

    Q(I) - pole uzlovych bodu krivky (3D)
    K    - pocet bodu vysledne krivky, K v <2,300> (viz G07.md,
           "Omezeni uzlu shora... pro krivky se secnovou parametrizaci
           (S01, T01, S10, T10) nesmi prekrocit 300 bodu")
    U1   - pocatecni tecny vektor (nezadano/nulovy = dopocita se)
    UK   - koncovy tecny vektor (stejne)

Otevrena krivka TM prochazi K body Q(I)..Q(I+K-1) a v koncovych bodech
se tecne dotyka vektoru U1 a UK (viz G10.md 'T01 - Otevrena krivka
prolozena mnozinou K bodu s okrajovymi tecnymi vektory'). Pro K=2 je
definovan jediny segment; nejsou-li U1/UK uvedeny, je to primy usek.
Pro K>2 bez U1/UK (nebo nulovych) krivka na okraji vybiha do primky
(relaxovana okrajova podminka). Tvar krivky neni ovlivnen DELKOU
vektoru U1/UK (na rozdil napr. od T03) - jen jejich SMEREM.

Zadny samostatny Fortran zdroj pro T01 neni k dispozici, ale G07.md
vyslovne rika, ze T01 pouziva stejnou secnovou (chord-length)
parametrizaci jako S01 (GLSPL.FOR) - a Point/Vector v tomto portu uz
VZDY nesou x,y,z (viz geplib/__init__.py docstring: rozdil P/Q a V/U
je jen jazykova konvence GL3 prefixu, ne odlisny Python typ). T01 je
proto cistokrevny tenky wrapper nad uz existujici gerlib.s01.
make_spline - jen s opcode="T01" pro spravnou provenience krivky.
"""
from gerlib.s01 import make_spline as _make_spline


def make_spatial_spline(points_ref, k, u1=None, uk=None):
    """T01: TM=T01>Q(I),K,U1,UK - otevrena prostorova krivka K body se
    dvema okrajovymi tecnymi vektory, secnova parametrizace (viz
    gerlib.s01.make_spline - shodna matematika, jen jina provenience
    oznaceni vysledne krivky)."""
    return _make_spline(points_ref, k, u1, uk, opcode="T01")
