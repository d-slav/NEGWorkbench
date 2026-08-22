# -*- coding: utf-8 -*-
"""
test_h02.py - Testy operace H02 (retezec mnozinou vyjmenovanych bodu,
viz G10.md 'H02 - Retezec mnozinou vyjmenovanych bodu'; prostorova
obdoba E01, zadny samostatny Fortran zdroj k dispozici - viz
geplib/h02.py hlavicka).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point
from geplib.h02 import make_chain3
from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- otevreny retezec, 3 body (nenulova Z - skutecne 3D) ---
    c = make_chain3(Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0), Point(1.0, 1.0, 1.0))
    check(c.closed is False, "3 ruzne body: otevreny retezec")
    pts = [(p.x, p.y, p.z) for p in c.points]
    check(pts == [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 1.0)], "body v zadanem poradi")

    # --- uzavreny retezec (prvni a posledni bod totozny vc. Z) ---
    c2 = make_chain3(
        Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 1.0), Point(1.0, 1.0, 1.0), Point(0.0, 0.0, 0.0)
    )
    check(c2.closed is True, "prvni a posledni bod totozny -> uzavreny retezec")

    # --- KLICOVY test 3D uzavrenosti: stejne X,Y ale RUZNE Z se NESMI
    # povazovat za uzavreny (na rozdil od 2D E01, ktere Z ignoruje) ---
    c3 = make_chain3(Point(0.0, 0.0, 0.0), Point(1.0, 1.0, 1.0), Point(0.0, 0.0, 5.0))
    check(c3.closed is False, "stejne X,Y ale ruzne Z NENI uzavreny retezec (3D, ne 2D test)")

    # --- minimalni pocet bodu (2) ---
    c_min = make_chain3(Point(0.0, 0.0, 0.0), Point(1.0, 0.0, 0.0))
    check(len(c_min.points) == 2, "minimalni pocet bodu (2) funguje")

    # --- maximalni pocet bodu (7) ---
    pts7 = [Point(float(i), 0.0, 0.0) for i in range(7)]
    c_max = make_chain3(*pts7)
    check(len(c_max.points) == 7, "maximalni pocet bodu (7) funguje")

    # --- chybove stavy: prilis malo / prilis mnoho bodu ---
    try:
        make_chain3(Point(0.0, 0.0, 0.0))
        check(False, "1 bod mel vyhodit ValueError")
    except ValueError:
        check(True, "1 bod (prilis malo) -> ValueError")

    try:
        make_chain3(*[Point(float(i), 0.0, 0.0) for i in range(8)])
        check(False, "8 bodu melo vyhodit ValueError")
    except ValueError:
        check(True, "8 bodu (prilis mnoho) -> ValueError")

    # --- test pres realny GL3 zdrojovy text ---
    gl3_code = """
SUBRO/TESTH02/out:HM
QA=Q00>0.0,0.0,0.0
QB=Q00>1.0,0.0,0.0
QC=Q00>1.0,1.0,0.0
HM=H02>QA,QB,QC
RETSUB
END
"""
    program = parse_program(gl3_code)
    interpreter = Interpreter()
    env = interpreter.run(program, {})
    hm = env["HM"]
    check(hm.closed is False, "GL3: otevreny retezec")
    check(
        [(p.x, p.y, p.z) for p in hm.points] == [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)],
        "GL3: body odpovidaji zadanym Q1,Q2,Q3",
    )

    print("\nVSE OK - H02 (geplib.h02) je plne funkcni.")


if __name__ == "__main__":
    main()
