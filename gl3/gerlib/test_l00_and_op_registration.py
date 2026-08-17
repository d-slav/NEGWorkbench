# -*- coding: utf-8 -*-
"""test_l00_and_op_registration.py

Dve veci:
1) L00 (LM=L00>D1,D2,D3,D4 - primka slozkami bodu a vektoru) skutecne
   funguje pres interpret (byla definovana funkce _op_l00 v gl3_ops.py,
   ale chybela v registru OPERATIONS - hlasilo se "neznamy opcode",
   viz nahlaseny bug).
2) Regresni pojistka: KAZDA definovana _op_* funkce v gl3_ops.py musi
   byt take registrovana v OPERATIONS, aby se stejny druh chyby
   (definovano, ale zapomenuto zaregistrovat) uz nemohl tise vloudit
   znovu u jineho opcode.
"""
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
import gl3_ops


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- 1) L00 pres realny GL3 zdrojovy text ---
    src = """
SUBRO/TL00/out:LM
LM=L00>0,0,1,1
RETSUB
END
"""
    subdef = parse_program(src)
    interp = Interpreter()
    env = interp.run(subdef, {})
    lm = env["LM"]
    check(lm.origin.x == 0.0 and lm.origin.y == 0.0, "L00: pruchozi bod (0,0)")
    check(abs(lm.direction.x - lm.direction.y) < 1e-9, "L00: smerovy vektor (1,1) normalizovan, x==y")

    # --- 2) regresni pojistka: vsechny definovane _op_* jsou v OPERATIONS ---
    src_text = inspect.getsource(gl3_ops)
    defined = set(re.findall(r"^def (_op_\w+)\(", src_text, re.M))
    registered = set(re.findall(r"\":\s*(_op_\w+),", src_text))
    missing = sorted(defined - registered)
    check(not missing, "vsechny definovane _op_* funkce jsou zaregistrovany v OPERATIONS (chybi: %r)" % (missing,))

    print("Vse OK.")


if __name__ == "__main__":
    main()
