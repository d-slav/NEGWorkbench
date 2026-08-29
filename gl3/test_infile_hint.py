# -*- coding: utf-8 -*-
"""Test rozsireni hlavicky SUBRO o hint '-f' (in-f:/out-f:) - zadani
uzivatele: explicitni rozliseni "B je obecny text" vs. "B je jmeno
souboru", varianta B z diskuze (hint jako ODDELENY 4. prvek n-tice,
'direction' zustava striktne 'in'/'out' - viz gl3_lang.parse_subro_header).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_subro_header


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- 1) beznbe in:/out: beze zmeny - hint je None ---
    name, params = parse_subro_header("SUBRO/SCARA/in:SP,out:SS,out:CNAB(11)")
    check(name == "SCARA", "jmeno SUBRO se parsuje spravne")
    check(
        params == [("SP", None, "in", None), ("SS", None, "out", None), ("CNAB", 11, "out", None)],
        "obycejne in:/out: dava 4-tici s hint=None",
    )

    # --- 2) in-f: na B-parametru -> hint='file' ---
    name, params = parse_subro_header("SUBRO/T/in-f:BJM,out:D1")
    check(params == [("BJM", None, "in", "file"), ("D1", None, "out", None)],
          "in-f:BJM -> hint='file', ostatni parametry beze zmeny")

    # --- 3) out-f: na B-parametru -> direction zustava 'out', hint='file' ---
    name, params = parse_subro_header("SUBRO/T/out-f:BOUT")
    check(params == [("BOUT", None, "out", "file")],
          "out-f:BOUT -> direction='out' (NENI treti hodnota direction), hint='file'")

    # --- 4) case-insensitive IN-F:/OUT-F: ---
    name, params = parse_subro_header("SUBRO/T/IN-F:BJM")
    check(params == [("BJM", None, "in", "file")], "IN-F: (velka pismena) funguje stejne jako in-f:")

    # --- 5) pole s hintem - velikost zustava zachovana ---
    name, params = parse_subro_header("SUBRO/T/in-f:BARR(5)")
    check(params == [("BARR", 5, "in", "file")], "in-f:BARR(5) - velikost pole zachovana spolu s hintem")

    # --- 6) hint '-f' na NE-B parametru -> jasna SyntaxError ---
    try:
        parse_subro_header("SUBRO/T/in-f:DJM")
        check(False, "in-f: na D-parametru mela vyhodit SyntaxError")
    except SyntaxError as e:
        check("B-parametru" in str(e) or "DJM" in str(e), "in-f: na D-parametru -> jasna SyntaxError (%s)" % e)

    # --- 7) chybejici in:/out: prefix porad davá jasnou chybu (beze zmeny) ---
    try:
        parse_subro_header("SUBRO/T/SP")
        check(False, "chybejici in:/out: prefix mel vyhodit SyntaxError")
    except SyntaxError:
        check(True, "chybejici in:/out: prefix -> jasna SyntaxError (beze zmeny)")

    print()
    print("Vsechny testy hint '-f' (in-f:/out-f:) v hlavicce SUBRO OK.")


if __name__ == "__main__":
    main()
