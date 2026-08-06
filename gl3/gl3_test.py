# -*- coding: utf-8 -*-
"""
gl3_test.py - rychla kontrola bez FreeCADu:
  1. zparsuje TEST1/XPROC/SCARA/HLO/TEHLO - vsechny z gl3test/ (vlastni
     fixture kopie, NE "zive" gl3sys/gl3examples/gl3data adresare, ktere
     jsou plne v rezii uzivatele - viz konverzace)
  2. ukaze odvozene smery parametru (in/out)
  3. spusti TEHLO -> SCARA retez na realnych datech (gl3test/E374.TXT)
     a overi, ze cely retez dobehne az do konce (viz historie projektu -
     SCARA byla puvodni motivace pro cely tenhle projekt)
"""
import os

from gl3_lang import parse_program
from gl3_analysis import get_param_directions
from gl3_interpreter import Interpreter

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GL3TEST_DIR = os.path.join(_ROOT_DIR, "gl3test")


def load(directory, name):
    with open(os.path.join(directory, name), "r", encoding="utf-8", errors="replace") as f:
        return parse_program(f.read())


def main():
    test1 = load(GL3TEST_DIR, "TEST1.GL3")
    xproc = load(GL3TEST_DIR, "XPROC.GL3")
    scara = load(GL3TEST_DIR, "SCARA.GL3")
    hlo = load(GL3TEST_DIR, "HLO.GL3")
    tehlo = load(GL3TEST_DIR, "TEHLO.GL3")

    registry = {"TEST1": test1, "XPROC": xproc, "SCARA": scara, "TEHLO": tehlo, "HLO": hlo}

    print("=== Smery parametru (primo z anotace, ne odhadem) ===")
    for subdef in (test1, xproc, scara, tehlo, hlo):
        print("%s: %s" % (subdef.name, get_param_directions(subdef)))

    interp = Interpreter(registry=registry)

    print()
    print("=== Spousteni TEHLO ===")
    result = interp.run(tehlo, inputs={"BJM": os.path.join(GL3TEST_DIR, "E374.TXT"), "DH": 15.2})
    print("OK")

    print()
    print("=== Spousteni SCARA (retez z vysledku TEHLO) ===")
    interp2 = Interpreter(registry=registry)
    scara_result = interp2.run(scara, inputs={"SP": result.get("S")})
    ss = scara_result.get("SS")
    cnab = scara_result.get("CNAB")
    assert ss is not None and len(ss.points) > 0, "SCARA: SS chybi nebo je prazdny"
    assert cnab is not None, "SCARA: CNAB chybi"
    print("OK - SS ma %d bodu, CNAB = %s" % (len(ss.points), cnab))


if __name__ == "__main__":
    main()
