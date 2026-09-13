# -*- coding: utf-8 -*-
"""
Operace T47 (GL3 opcode T47, prostorova obdoba S47) - Spojeni dvou
3D krivek.

Uziti (GL3): TM=T47>T1,T2[,K]

Zadani uzivatele: S47 a T47 pochazeji ze STEJNEHO zdrojoveho souboru
(S47.FOR - jedna FORTRAN procedura implementuje obe, dispatch podle
volajiciho prikazu) - proto (stejne jako T01 nad S01, T03 nad S03, T10
nad S10) cistokrevny tenky wrapper nad gerlib.s47.make_joined_spline.
Vyznam K viz tamni docstring.
"""
from gerlib.s47 import make_joined_spline as _make_joined_spline


def make_joined_spatial_spline(spline1, spline2, k=None):
    """T47: TM=T47>T1,T2[,K] - spojeni dvou prostorovych krivek (viz
    gerlib.s47.make_joined_spline - shodna matematika, jen jina
    provenience oznaceni vysledne krivky)."""
    return _make_joined_spline(spline1, spline2, k, opcode="T47")
