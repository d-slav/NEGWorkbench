# -*- coding: utf-8 -*-
"""
gl3_test.py - rychla kontrola bez FreeCADu:
  1. zparsuje XPROC.GL3 a SCARA.GL3
  2. ukaze odvozene smery parametru (in/out)
  3. zkusi SCARA spustit - ocekavame, ze dobehne az k prvni chybejici
     geometricke operaci (NotYetImplemented) - to je ocekavany a spravny
     vysledek v teto fazi (operace jeste cekaji na Fortran zdrojaky)
  4. zkusi XPROC spustit - ocekavame jasnou chybu na CALL/HLO, protoze
     HLO.GL3 jeste nemame
"""

from gl3_lang import parse_program
from gl3_analysis import get_param_directions
from gl3_interpreter import Interpreter
from gl3_ops import NotYetImplemented

EXAMPLES_DIR = "./examples/"


def load(name):
    with open("%s/%s" % (EXAMPLES_DIR, name), "r", encoding="utf-8", errors="replace") as f:
        return parse_program(f.read())


def main():
    test1 = load("TEST1.GL3")
    xproc = load("XPROC.GL3")
    scara = load("SCARA.GL3")
    tehlo = load("TEHLO.GL3")    
    hlo = load("HLO.GL3")    

    registry = {"TEST1": test1, "XPROC": xproc, "SCARA": scara, "TEHLO": tehlo, "HLO": hlo}

    print("=== Smery parametru (ted primo z anotace, ne odhadem) ===")
    for subdef in (test1, xproc, scara,tehlo,hlo):
        print("%s: %s" % (subdef.name, get_param_directions(subdef)))

    interp = Interpreter(registry=registry)

    print()
    print("=== Spousteni TEHLO ===")
    result = interp.run(tehlo, inputs={"BJM": "examples/E374.TXT", "DH":15.2})
    print("OK")

    # print()
    # print("=== Spousteni TEST1 (melo by kompletne dobehnout) ===")
    # result = interp.run(test1, inputs={"DI": 5})
    # print("OK, DO =", result.get("DO"), "(ocekavano 50.0)")

    # print()
    # print("=== Spousteni SCARA (ocekavame NotYetImplemented) ===")
    # try:
        # interp.run(scara, inputs={"SP": "DUMMY_CURVE"})
        # print("Prekvapive dobehlo bez chyby (nemelo by, vsechny ops jsou stub)")
    # except NotYetImplemented as e:
        # print("OK - zastaveno na ocekavanem miste:")
        # print(" ", e)
    # except Exception as e:
        # print("POZOR - jina chyba, nez se cekalo:", type(e).__name__, e)

    # print()
    # print("=== Spousteni XPROC (ocekavame chybu na CALL/HLO - chybi v registru) ===")
    # try:
        # interp.run(xproc, inputs={"P": [None, None], "K": 0})
        # print("Prekvapive dobehlo bez chyby")
    # except KeyError as e:
        # print("OK - zastaveno na ocekavanem miste:")
        # print(" ", e)
    # except Exception as e:
        # print("POZOR - jina chyba, nez se cekalo:", type(e).__name__, e)


if __name__ == "__main__":
    main()
