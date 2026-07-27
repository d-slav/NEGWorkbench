# -*- coding: utf-8 -*-
"""
gl3_registry.py - lazy registr SUBRO podprogramu pro Interpreter.

Interpreter (gl3_interpreter.py) pouziva registry jen pres `in` a `[...]`
(viz `stmt.name not in self.registry` / `self.registry[stmt.name]`), takze
staci drop-in objekt s __contains__/__getitem__ - neni potreba predem
naplnit cely dict, muze si SUBRO donacitat na pozadani (a vysledek si
zapamatovat, aby se pri opakovanem CALL/behem jednoho recompute soubor
necetl a neparsoval znovu).

Konvence hledani: soubor pro SUBRO jmena "HLO" se jmenuje "HLO.GL3"
(case-insensitive) v jednom z prohledavanych adresaru (GL3Library.SearchPaths).
Adresar s priznakem hidden=True se prohledava stejne (jen se typicky
nenabizi v UI jako "uzivatelsky" - pripraveno pro budouci system SUBRA,
viz shrnuti projektu, bod 3).
"""

import os

from gl3_lang import parse_program


class Gl3FileRegistry(object):
    """search_entries - list dictu {"path": adresar, "hidden": bool}
    extra - dict {jmeno: SubroutineDef} pro predem znama SUBRO (typicky
            vlastni SUBRO GL3Program objektu, ktery tenhle registry pouziva -
            at CALL na sve vlastni jmeno, kdyby k tomu doslo, nemusi chodit
            na disk)."""

    def __init__(self, search_entries=None, extra=None):
        self._search_entries = list(search_entries or [])
        self._cache = dict(extra or {})

    def __contains__(self, name):
        if name in self._cache:
            return True
        return self._find_path(name) is not None

    def __getitem__(self, name):
        if name not in self._cache:
            path = self._find_path(name)
            if path is None:
                raise KeyError(
                    "SUBRO '%s' nenalezeno (hledano jako '%s.GL3' v: %s)"
                    % (name, name, ", ".join(e["path"] for e in self._search_entries))
                )
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                subdef = parse_program(f.read())
            if subdef.name != name:
                raise ValueError(
                    "Soubor '%s' obsahuje SUBRO/%s, ale ocekavalo se SUBRO/%s "
                    "(nazev souboru musi odpovidat jmenu SUBRO)"
                    % (path, subdef.name, name)
                )
            self._cache[name] = subdef
        return self._cache[name]

    def _find_path(self, name):
        target = (name + ".GL3").lower()
        for entry in self._search_entries:
            directory = entry["path"] if isinstance(entry, dict) else entry
            if not directory or not os.path.isdir(directory):
                continue
            try:
                for fname in os.listdir(directory):
                    if fname.lower() == target:
                        return os.path.join(directory, fname)
            except OSError:
                continue
        return None

    def preload(self, name):
        """Vynuti nacteni ted (napr. pro rannou validaci v execute()), jinak
        se resolvuje lenive az pri prvnim CALL na dane jmeno."""
        return self[name]
