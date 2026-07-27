# -*- coding: utf-8 -*-
"""
Procedura P120 (GL3 opcode P20)     LET, k.p., Uh.Hradiste     P.Franc
Knihovna GERLIBPC                                  Listopad 1989

Ucel:    Prusecik dvou primek.

Uziti:   CALL P120(X1,Y1,A1,B1,X2,Y2,A2,B2,X,Y,J)

Parametry: X1,Y1,A1,B1  R*4  Parametry prvni primky (bod + smer)
           X2,Y2,A2,B2  R*4  Parametry druhe primky
           X,Y          R*4  Souradnice pruseciku
           J            I*2  J=0 prusecik existuje, J=1200 rovnobezne primky

Existuje i varianta P120A (primka zadana dvema body misto bodu+smeru) -
podle uzivatele kvuli tomu, ze puvodni vypocet bezel na float (ne double)
a bylo casem potreba resit, ktere z primek se ma vysledny bod povazovat za
"blizsi" v hranicnich pripadech. Tady pocitame na Python double (bez teto
ztraty presnosti), takze staci tahle jedna, primejsi varianta (ktera navic
primo odpovida nasi Line - bod+smer).
"""

from .types import Point


def line_intersection(line1, line2):
    """Prusecik dvou primek zadanych bodem a smerem. Vysledek nezavisi na
    velikosti smerovych vektoru (nemusi byt jednotkove). Chyba, kdyz jsou
    primky rovnobezne (nebo totozne) - puvodni J=1200."""
    x1, y1 = line1.origin.x, line1.origin.y
    a1, b1 = line1.direction.x, line1.direction.y
    x2, y2 = line2.origin.x, line2.origin.y
    a2, b2 = line2.direction.x, line2.direction.y

    d = a2 * b1 - a1 * b2
    if abs(d) < 1e-6:
        raise ValueError(
            "P120/P20: primky jsou rovnobezne (nebo totozne) - prusecik neexistuje"
        )

    t = (a2 * (y2 - y1) - b2 * (x2 - x1)) / d
    return Point(x1 + t * a1, y1 + t * b1, 0.0)
