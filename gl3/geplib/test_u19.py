# -*- coding: utf-8 -*-
"""
test_u19.py - Testy operace U19 (vektor otoceny o uhel kolem primky,
viz G10.md 'U19 - Vektor otoceny o uhel kolem primky', Fortran
VECT75.FOR - viz geplib/u19.py hlavicka pro odvozeni Rodriguesova
vzorce a numericke overeni proti primemu portu puvodniho retezce
VECT75->POIN93->CS999->VECT99 (200 nahodnych zkousek, shoda na 1e-7)).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line
from geplib.u19 import rotate_vector_about_line
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def isclose(a, b, eps=1e-6):
    return abs(a - b) < eps


def vec_isclose(v, x, y, z, eps=1e-6):
    return isclose(v.x, x, eps) and isclose(v.y, y, eps) and isclose(v.z, z, eps)


def main():
    axis_z = Line(Point(0.0, 0.0, 0.0), Vector(0.0, 0.0, 1.0))
    v = Vector(1.0, 0.0, 0.0)

    # --- K=0 (default) vs K=1 - opacne smery rotace ---
    r_default = rotate_vector_about_line(v, axis_z, 90.0)
    r_k0 = rotate_vector_about_line(v, axis_z, 90.0, 0)
    r_k1 = rotate_vector_about_line(v, axis_z, 90.0, 1)
    check(vec_isclose(r_default, 0.0, -1.0, 0.0), "default K=0: 90 stupnu kolem osy z")
    check(vec_isclose(r_k0, r_default.x, r_default.y, r_default.z), "explicitni K=0 == default")
    check(vec_isclose(r_k1, 0.0, 1.0, 0.0), "K=1: opacny smer nez K=0")

    # --- velikost vektoru se zachovava ---
    check(isclose(math.hypot(r_default.x, r_default.y, r_default.z), 1.0), "velikost vektoru zachovana")

    # --- vektor rovnobezny s osou zustava beze zmeny ---
    v_parallel = Vector(0.0, 0.0, 5.0)
    r_parallel = rotate_vector_about_line(v_parallel, axis_z, 45.0)
    check(vec_isclose(r_parallel, 0.0, 0.0, 5.0), "vektor rovnobezny s osou zustava beze zmeny")

    # --- smerovy vektor primky nemusi byt jednotkovy ---
    axis_nonunit = Line(Point(1.0, 2.0, 3.0), Vector(0.0, 0.0, 5.0))
    r_nonunit = rotate_vector_about_line(v, axis_nonunit, 90.0)
    check(vec_isclose(r_nonunit, r_default.x, r_default.y, r_default.z),
          "nejednotkovy smerovy vektor primky da stejny vysledek (normalizuje se)")

    # --- poloha primky na vysledek nema vliv (jen smer) ---
    axis_shifted = Line(Point(100.0, -50.0, 7.0), Vector(0.0, 0.0, 1.0))
    r_shifted = rotate_vector_about_line(v, axis_shifted, 90.0)
    check(vec_isclose(r_shifted, r_default.x, r_default.y, r_default.z),
          "poloha primky na vysledek nema vliv, jen jeji smer")

    # --- obecna (ne osove rovnobezna) osa - 360 stupnu vraci puvodni vektor ---
    axis_gen = Line(Point(0.0, 0.0, 0.0), Vector(1.0, 1.0, 1.0))
    v_gen = Vector(2.0, -3.0, 5.0)
    r_full = rotate_vector_about_line(v_gen, axis_gen, 360.0)
    check(vec_isclose(r_full, v_gen.x, v_gen.y, v_gen.z, eps=1e-4), "otoceni o 360 stupnu vraci puvodni vektor")

    # --- nulovy smerovy vektor primky -> chyba ---
    try:
        rotate_vector_about_line(v, Line(Point(0.0, 0.0, 0.0), Vector(0.0, 0.0, 0.0)), 45.0)
        check(False, "nulovy smerovy vektor primky mel vyhodit ValueError")
    except ValueError:
        check(True, "nulovy smerovy vektor primky -> ValueError")

    # --- test pres realny GL3 zdrojovy text (M dodana jako in: parametr,
    # protoze GL3 zatim nema 3D konstruktor primky) ---
    gl3_code = """
SUBRO/TESTU19/in:M,out:VM1,out:VM2
V=U00>1.0,0.0,0.0
VM1=U19>V,M,90.0
VM2=U19>V,M,90.0,1.0
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {"M": axis_z})
    check(vec_isclose(env["VM1"], 0.0, -1.0, 0.0), "GL3: default K=0")
    check(vec_isclose(env["VM2"], 0.0, 1.0, 0.0), "GL3: K=1")

    print("\nVSE OK - U19 (geplib.u19) je plne funkcni.")


if __name__ == "__main__":
    main()
