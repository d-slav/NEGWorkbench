# -*- coding: utf-8 -*-
"""
test_parse_ref_offline.py - unit testy pro gl3_props.parse_ref(), hlavne
volitelny syntax indexu prvku pole '(N)' (1 = prvni prvek), napr.
'TEHLO002.PO(1)' - viz gl3_props.py modulovy docstring.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3fc.gl3_props import parse_ref


def main():
    # --- bez indexu (puvodni format, musi zustat beze zmeny) ---
    assert parse_ref("TEHLO002.PO") == ("TEHLO002", "PO", None)
    assert parse_ref("  TEHLO002.PO  ") == ("TEHLO002", "PO", None)
    print("parse_ref bez indexu: OK")

    # --- s indexem ---
    assert parse_ref("TEHLO002.PO(1)") == ("TEHLO002", "PO", 1)
    assert parse_ref("TEHLO002.PO(10)") == ("TEHLO002", "PO", 10)
    assert parse_ref("  TEHLO002.PO(3)  ") == ("TEHLO002", "PO", 3)
    print("parse_ref s indexem: OK")

    # --- neplatne vstupy -> (None, None, None) ---
    for bad in (
        "",
        None,
        "spatnyformat",       # zadna tecka
        "TEHLO002.",          # prazdne jmeno vystupu
        ".PO",                # prazdne jmeno objektu
        "TEHLO002.PO(",       # nedovrena zavorka
        "TEHLO002.PO(abc)",   # neciselny index
        "TEHLO002.PO(1",      # nedovrena zavorka s cislem
        "TEHLO002.PO(1))",    # prebytecna zavorka
        "TEHLO002.PO.S",      # dve tecky
    ):
        assert parse_ref(bad) == (None, None, None), "melo vratit (None, None, None) pro %r" % (bad,)
    print("parse_ref na neplatnych vstupech: OK - vzdy (None, None, None)")

    print()
    print("VSE OK - parse_ref() spravne parsuje 'Objekt.Vystup' i 'Objekt.Vystup(Index)'.")


if __name__ == "__main__":
    main()
