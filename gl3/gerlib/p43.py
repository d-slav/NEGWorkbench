# -*- coding: utf-8 -*-
"""
GL3 opcode P43

Ucel:    Patni bod na primce ze stredu kruznice.

Uziti:   PM=P43>>C,L
         PM = patni bod kolmice spustene ze stredu kruznice C na
              primku L (viz G10.md 'P43 - Patni bod na primce ze
              stredu kruznice').

Parametry:
    C (circle): Kruznice (Circle)
    L (line):   Primka (Line)

Zdroj:   puvodni Fortran nedodan - trivialni kombinace jiz existujicich
         operaci (stred kruznice, viz P47/gerlib.p47, + patni bod na
         primce, viz P40/gerlib.p40), zadana primo uzivatelem.
"""
from .p40 import foot_point_on_line


def foot_point_from_circle_center(circle, line):
    """P43: Patni bod kolmice spustene ze stredu kruznice 'circle' na
    primku 'line'. Lezi-li stred kruznice na primce, jsou oba body
    totozne (stejne chovani jako P40)."""
    return foot_point_on_line(circle.center, line)
