# -*- coding: utf-8 -*-
"""
convert.py - jednorazovy prevod Gl3Key.dat (stara C++/MFC editor
aplikace, viz Gl3_Keywords.h/.cpp) do gl3_keywords.json.

Spustit rucne, kdyz se zmeni/doplni Gl3Key.dat - neni soucasti
zadneho automatickeho buildu (vstupni .dat soubor neni v repu).
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from parse_gl3key import parse

# OBJ_TYPE enum jmeno -> pismeno prefixu promenne, jak uz pouziva
# gl3_ops.TYPE_PREFIX_INFO/classify() - Type_ (statementy/klicova slova
# bez vraceneho typu) -> None.
OBJ_TYPE_TO_PREFIX = {
    "Type_": None,
    "TypeI": "I", "TypeD": "D", "TypeA": "A", "TypeC": "C", "TypeE": "E",
    "TypeF": "F", "TypeG": "G", "TypeH": "H", "TypeL": "L", "TypeM": "M",
    "TypeP": "P", "TypeQ": "Q", "TypeR": "R", "TypeS": "S", "TypeT": "T",
    "TypeU": "U", "TypeV": "V",
}


def main():
    dat_path = os.path.join(_HERE, "Gl3Key.dat")
    out_path = os.path.join(_HERE, "..", "..", "gl3_keywords.json")
    version, records = parse(dat_path)
    out = {}
    for r in records:
        key = r["key"]
        entry = {
            "type": OBJ_TYPE_TO_PREFIX[r["obj_type"]],
            "syntax": r["syntax"],
            "comment": r["comment"],
            "menu": r["menu"],
            "html_help_file": r["html_help_file"] or None,
        }
        if key not in out:
            out[key] = entry
            continue
        # Genuiny preteceny opkod (napr. NPO/NSE - stejne jmeno, ruzna
        # signatura podle typu objektu - F vs. S/E/T/H) - SLOUCIT do
        # jednoho hesla (vicero syntaxi/komentaru oddelenych radkem),
        # ne tise zahodit jeden z vyskytu.
        existing = out[key]
        if entry["syntax"] not in existing["syntax"].split("\n"):
            existing["syntax"] += "\n" + entry["syntax"]
        if entry["comment"] not in existing["comment"].split("\n\n"):
            existing["comment"] += "\n\n" + entry["comment"]
        if existing["type"] != entry["type"]:
            print("POZOR: klic %r ma ve vyskytech RUZNY typ (%r vs %r) - "
                  "ponechan prvni" % (key, existing["type"], entry["type"]), file=sys.stderr)
        if not existing["html_help_file"] and entry["html_help_file"]:
            existing["html_help_file"] = entry["html_help_file"]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
    print("Zapsano %d hesel do %s (zdroj: Gl3Key.dat verze %d, %d zaznamu)"
          % (len(out), out_path, version, len(records)))


if __name__ == "__main__":
    main()
