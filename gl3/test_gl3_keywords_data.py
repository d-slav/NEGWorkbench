# -*- coding: utf-8 -*-
"""Test gl3_keywords.json (nápověda pro klíčová slova/opkódy, převedeno
z historického Gl3Key.dat - viz tools/gl3key_import/README.md).

Nekontroluje obsah textů (to je data, ne kód) - jen strukturu a soulad
se skutečnou implementací (gl3_ops.OPERATIONS/COMMANDS), aby JSON
"nezrezivěl" nepozorovaně, kdyby někdo přidal/přejmenoval opkód a
zapomněl na dokumentaci."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gl3_ops

_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gl3_keywords.json")

_VALID_TYPES = set(gl3_ops.TYPE_PREFIX_INFO.keys())

# Nase vlastni rozsireni nad ramec puvodniho GL-3 (viz G12.md) - v
# historickych datech (Gl3Key.dat) logicky chybi, zadny historicky
# zaklad neexistuje.
_OUR_EXTENSIONS = {"BREAK", "CONTINUE"}

# Opkody, ktere mame implementovane, ale historicka dokumentace o nich
# nevi (viz tools/gl3key_import/README.md - nejasny duvod, mozna
# pridany do jazyka az po zachyceni teto dokumentace).
_KNOWN_UNDOCUMENTED = {"D01", "D02"}


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    with open(_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    check(isinstance(data, dict) and len(data) > 500, "gl3_keywords.json se nacetl a ma rozumny pocet hesel (%d)" % len(data))

    # Kazde heslo ma vsech 5 ocekavanych poli, spravnych typu.
    for key, entry in data.items():
        assert isinstance(entry, dict), key
        for field in ("type", "syntax", "comment", "menu", "html_help_file"):
            assert field in entry, "%s: chybi pole %r" % (key, field)
        assert entry["type"] is None or entry["type"] in _VALID_TYPES, (
            "%s: neplatny type %r (znama pismena: %s)" % (key, entry["type"], sorted(_VALID_TYPES))
        )
        assert isinstance(entry["syntax"], str) and entry["syntax"], "%s: syntax je prazdna" % key
        assert isinstance(entry["comment"], str), key
        assert isinstance(entry["menu"], str), key
        assert entry["html_help_file"] is None or isinstance(entry["html_help_file"], str), key
    print("OK  vsechna hesla maji ocekavanou strukturu (type/syntax/comment/menu/html_help_file)")

    # Kazdy DNES implementovany opkod/prikaz (OPERATIONS + COMMANDS) MA
    # zaznam v gl3_keywords.json - jinak by LSP/hover na nem tise mlcel.
    implemented = set(gl3_ops.OPERATIONS.keys()) | set(gl3_ops.COMMANDS.keys())
    missing = sorted(implemented - set(data.keys()) - _KNOWN_UNDOCUMENTED)
    check(
        not missing,
        "kazdy implementovany opkod/prikaz ma zaznam v gl3_keywords.json "
        "(krome znamych vyjimek %s)%s" % (sorted(_KNOWN_UNDOCUMENTED), (" - CHYBI: %r" % missing) if missing else ""),
    )

    # "type" v JSON navazuje na klasifikaci podle PRVNIHO PISMENE JMENA
    # OBJEKTU (viz gl3_ops.classify()), ne opkodu - plati tedy jen pro
    # opkody, jejichz jmeno OPRAVDU kopiruje typ vysledku (geometricke
    # konstruktory jako D10/P00/C00/...). Genericke matematicke funkce
    # (SIN/COS/TAN/ABS - vzdy vraci D, jmeno s tim nesouvisi) a COMMANDS
    # (ACCUR/SCALE - nejsou typovane opkody vubec, jsou to prikazy) do
    # tohohle pravidla nepatri - i kdyz jejich prvni pismeno nahodou
    # vypada jako platny typovy prefix.
    _NAME_NOT_TYPE_INDICATIVE = {"SIN", "COS", "TAN", "ABS"} | set(gl3_ops.COMMANDS.keys())
    mismatches = []
    for key in implemented:
        if key in _KNOWN_UNDOCUMENTED or key not in data or key in _NAME_NOT_TYPE_INDICATIVE:
            continue
        first_letter = key[0].upper()
        if first_letter not in _VALID_TYPES:
            continue
        expected_type = first_letter
        actual_type = data[key]["type"]
        if actual_type != expected_type:
            mismatches.append((key, expected_type, actual_type))
    check(
        not mismatches,
        "'type' v gl3_keywords.json odpovida prvnimu pismenu jmena opkodu "
        "pro vsechny implementovane opkody%s" % ((" - NESEDI: %r" % mismatches) if mismatches else ""),
    )

    print()
    print("Vsechny testy gl3_keywords.json OK (%d hesel)." % len(data))


if __name__ == "__main__":
    main()
