# -*- coding: utf-8 -*-
"""Test V00, V01, V08, V20, V41, V42 (viz G10.md - 'V - vektor rovinny')."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector
from gerlib.v00 import make_vector2
from gerlib.v01 import make_vector_between
from gerlib.v08 import rotate_vector
from gerlib.v20 import make_unit_vector
from gerlib.v41 import scale_to_length
from gerlib.v42 import scale_vector
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    assert cond, msg


def main():
    # --- V00: slozky x,y (z=0) ---
    v00 = make_vector2(3.0, 4.0)
    check((v00.x, v00.y, v00.z) == (3.0, 4.0, 0.0), "V00: slozky x,y, z=0")

    # --- V01: vektor mezi dvema body ---
    v01 = make_vector_between(Point(1.0, 2.0, 3.0), Point(4.0, 6.0, 3.0))
    check((v01.x, v01.y, v01.z) == (3.0, 4.0, 0.0), "V01: orientovan z P1 do P2")

    v01_same = make_vector_between(Point(5.0, 5.0, 5.0), Point(5.0, 5.0, 5.0))
    check((v01_same.x, v01_same.y, v01_same.z) == (0.0, 0.0, 0.0), "V01: totozne body -> nulovy vektor")

    # --- V08: vektor otoceny o uhel (delka zachovana) ---
    v08_90 = rotate_vector(Vector(1.0, 0.0, 0.0), 90.0)
    check(abs(v08_90.x) < 1e-9 and abs(v08_90.y - 1.0) < 1e-9,
          "V08: default K=0, (1,0) o +90 stupnu -> (0,1) (ccw)")

    v08_k0 = rotate_vector(Vector(1.0, 0.0, 0.0), 90.0, 0)
    check(abs(v08_k0.x - v08_90.x) < 1e-9 and abs(v08_k0.y - v08_90.y) < 1e-9,
          "V08: explicitni K=0 == default")

    v08_k1 = rotate_vector(Vector(1.0, 0.0, 0.0), 90.0, 1)
    check(abs(v08_k1.x) < 1e-9 and abs(v08_k1.y + 1.0) < 1e-9,
          "V08: K=1, (1,0) o +90 stupnu -> (0,-1) (cw, opacne nez K=0)")

    v08_len = Vector(3.0, 4.0, 0.0)
    v08_rot = rotate_vector(v08_len, 37.0)
    check(abs(math.hypot(v08_rot.x, v08_rot.y) - 5.0) < 1e-9, "V08: delka vektoru zachovana")

    v08_360 = rotate_vector(Vector(3.0, -4.0, 0.0), 360.0)
    check(abs(v08_360.x - 3.0) < 1e-6 and abs(v08_360.y + 4.0) < 1e-6,
          "V08: otoceni o 360 stupnu vraci puvodni vektor")

    v08_neg_a = rotate_vector(Vector(1.0, 0.0, 0.0), -90.0)
    check(abs(v08_neg_a.x) < 1e-9 and abs(v08_neg_a.y + 1.0) < 1e-9,
          "V08: zaporny uhel obraci smysl otaceni (K=0, -90 stupnu -> cw)")

    try:
        rotate_vector(Vector(0.0, 0.0, 0.0), 45.0)
        check(False, "V08 s nulovym vstupnim vektorem melo vyhodit ValueError")
    except ValueError as e:
        check("V08" in str(e), "V08 s nulovym vstupnim vektorem -> ValueError (%s)" % e)

    # --- V20: jednotkovy vektor ---
    v20 = make_unit_vector(Vector(3.0, 4.0, 0.0))
    check(abs(v20.x - 0.6) < 1e-9 and abs(v20.y - 0.8) < 1e-9 and v20.z == 0.0, "V20: jednotkovy vektor (3,4,0) -> (0.6,0.8,0)")

    try:
        make_unit_vector(Vector(0.0, 0.0, 0.0))
        check(False, "V20 na nulovem vektoru melo vyhodit ValueError")
    except ValueError as e:
        check("V20" in str(e), "V20 na nulovem vektoru -> ValueError (%s)" % e)

    # --- V42: vektor nasobeny skalarem ---
    v42 = scale_vector(Vector(3.0, 4.0, 0.0), 2.5)
    check((v42.x, v42.y, v42.z) == (7.5, 10.0, 0.0), "V42: D-nasobek vektoru (3,4,0)*2.5")

    v42_neg = scale_vector(Vector(1.0, -2.0, 3.0), -1.0)
    check((v42_neg.x, v42_neg.y, v42_neg.z) == (-1.0, 2.0, -3.0), "V42: zaporny skalar obraci smer")

    v42_zero = scale_vector(Vector(5.0, 5.0, 5.0), 0.0)
    check((v42_zero.x, v42_zero.y, v42_zero.z) == (0.0, 0.0, 0.0), "V42: nasobeni nulou dava nulovy vektor")

    # --- V41: vektor dane delky rovnobezny s V ---
    v41 = scale_to_length(Vector(3.0, 4.0, 0.0), 10.0)
    check(abs(v41.x - 6.0) < 1e-9 and abs(v41.y - 8.0) < 1e-9 and v41.z == 0.0,
          "V41: (3,4,0) na delku 10 -> (6,8,0), stejny smer")

    v41_neg = scale_to_length(Vector(3.0, 4.0, 0.0), -10.0)
    check(abs(v41_neg.x + 6.0) < 1e-9 and abs(v41_neg.y + 8.0) < 1e-9,
          "V41: zaporne D -> opacny smer, velikost |D|")

    v41_zero_d = scale_to_length(Vector(3.0, 4.0, 0.0), 0.0)
    check((v41_zero_d.x, v41_zero_d.y, v41_zero_d.z) == (0.0, 0.0, 0.0),
          "V41: D=0 -> nulovy vektor (bez ohledu na V)")

    v41_zero_v_zero_d = scale_to_length(Vector(0.0, 0.0, 0.0), 0.0)
    check((v41_zero_v_zero_d.x, v41_zero_v_zero_d.y, v41_zero_v_zero_d.z) == (0.0, 0.0, 0.0),
          "V41: V=0 a D=0 -> nulovy vektor beze chyby")

    try:
        scale_to_length(Vector(0.0, 0.0, 0.0), 5.0)
        check(False, "V41 s V=0 a D!=0 melo vyhodit ValueError")
    except ValueError as e:
        check("V41" in str(e), "V41 s V=0 a D!=0 -> ValueError (%s)" % e)

    # --- test pres realny GL3 zdrojovy text ---
    src = """
SUBRO/TESTV/out:D1
V1=V00>3,4
Q1=Q00>0,0,0
Q2=Q00>10,0,0
V2=V01>Q1,Q2
V3=V20>V2
V4=V42>V1,2.5
V5=V41>V1,10
V6=V08>V3,90.0
V7=V08>V3,90.0,1.0
D1=1.0
RETSUB
END
"""
    env = Interpreter().run(parse_program(src), {})
    check((env["V1"].x, env["V1"].y) == (3.0, 4.0), "GL3: V00>3,4")
    check((env["V2"].x, env["V2"].y) == (10.0, 0.0), "GL3: V01>Q1,Q2")
    check((env["V3"].x, env["V3"].y) == (1.0, 0.0), "GL3: V20>V2 (jednotkovy)")
    check((env["V4"].x, env["V4"].y) == (7.5, 10.0), "GL3: V42>V1,2.5")
    check(abs(env["V5"].x - 6.0) < 1e-9 and abs(env["V5"].y - 8.0) < 1e-9, "GL3: V41>V1,10")
    check(abs(env["V6"].x) < 1e-9 and abs(env["V6"].y - 1.0) < 1e-9, "GL3: V08>V3,90.0 (default K=0)")
    check(abs(env["V7"].x) < 1e-9 and abs(env["V7"].y + 1.0) < 1e-9, "GL3: V08>V3,90.0,1.0 (K=1)")

    print("\nVSE OK - V00, V01, V08, V20, V41, V42.")


if __name__ == "__main__":
    main()
