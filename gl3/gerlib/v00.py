# -*- coding: utf-8 -*-
"""
Operace V00 (NEG jazykova specifikace) - Vektor slozkami x', y'.

Zdrojovy Fortran kod NENI k dispozici - implementovano primo podle
jazykove specifikace prikazu (viz G10.md 'V00 - Vektor slozkami x', y''
a zadani uzivatele):

    VM=V00>D1,D2

    D1,D2 = skalarni vyrazy - x-ova a y-ova slozka noveho vektoru
            (z-ova slozka je 0 - rovinny vektor).

G10.md navic zminuje, ze V00 "podleha okamzite nastavene vstup/
vystupni transformaci (viz odst. 9.3.1 a 9.3.2)" - stejna poznamka
jako u Q00/U00 (viz geplib/q00.py) - tahle transformace neni v tomto
portu (zatim) nikde implementovana, takze V00 (stejne jako Q00/U00)
vraci slozky beze zmeny.
"""
from .types import Vector


def make_vector2(d1, d2):
    """V00: VM=V00>D1,D2 - rovinny vektor danymi slozkami x, y (z=0)."""
    return Vector(d1, d2, 0.0)
