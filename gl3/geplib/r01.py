# -*- coding: utf-8 -*-
"""
Operace R01 (NEG jazykova specifikace) - Rovina normalou a vzdalenosti od pocatku.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz zadani uzivatele):

    RM=R01>>U,D

    U = vektor - smer normaly roviny. Normalovy vektor je odvozen
        normalizaci a smluvni orientaci.
    D = skalarni vyraz - vzdalenost roviny od pocatku ve smeru normaloveho
        vektoru.
"""
from .plane import Plane, make_plane_r01

__all__ = ["Plane", "make_plane_r01"]
