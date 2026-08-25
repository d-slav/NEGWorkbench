# -*- coding: utf-8 -*-
"""
test_recompute_on_open_offline.py - overeni RecomputeOnOpenDoc (zadani
uzivatele: moznost preskocit vzdy-drahy prepocet po otevreni dokumentu,
kdyz se od ulozeni fakticky nic nezmenilo).

self._exec_cache (GL3Program.execute()) je jen v pameti Proxy objektu -
po "otevreni dokumentu" (v tomhle testu simulovanem vytvorenim NOVEHO
Proxy na TOM SAMEM FakeObj - presne to, co dela __getstate__/__setstate__
vraceci None) je vzdy None, takze prvni execute() vzdy udela plny beh,
i kdyz RecomputeOnOpenDoc == False. Az DRUHY execute() (po "otevreni")
smi cache-hit vyuzit - a presne to se tu overuje.

Skutecny "beh interpretu" se pozna podle poctu volani parse_program()
(volane se jen na ceste PLNEHO behu, nikdy na cache-hit ceste) -
monkeypatch pocitadlo v gl3fc.gl3_program modulu.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_TYPE_DEFAULTS = {
    "App::PropertyFloat": 0.0,
    "App::PropertyInteger": 0,
    "App::PropertyFileIncluded": "",
    "App::PropertyFile": "",
    "App::PropertyLink": None,
    "App::PropertyPythonObject": None,
    "App::PropertyStringList": [],
    "App::PropertyBool": False,
    "App::PropertyString": "",
}


class FakeObj(object):
    """Stejna napodobenina jako v test_offline.py, navic setPropertyStatus
    (no-op - jen at neni potreba try/except AttributeError zavisely na
    tomhle testu) a Document (staci None - RecomputeOnOpenDoc/_ExecCache
    ho vubec nepotrebuji)."""

    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self.Document = None
        self._prop_types = {}
        self._prop_groups = {}
        self._prop_status = {}

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        self._prop_groups[name] = group
        return self

    def setPropertyStatus(self, name, status):
        self._prop_status[name] = status

    def removeProperty(self, name):
        if hasattr(self, name):
            delattr(self, name)
        self._prop_types.pop(name, None)
        self._prop_groups.pop(name, None)
        return True

    @property
    def PropertiesList(self):
        return list(self._prop_types.keys())

    def getGroupOfProperty(self, name):
        return self._prop_groups.get(name)

    def getTypeIdOfProperty(self, name):
        return self._prop_types.get(name)


def _reopen(obj):
    """Simuluje zavreni a znovuotevreni dokumentu: FreeCAD by vytvoril
    NOVY Proxy (viz __getstate__/__setstate__ v gl3_program.py, oboje
    vraci None - Python stav Proxy se NEPRENASI), ale VSECHNY FC
    properties (vc. _ExecCache a RecomputeOnOpenDoc) na 'obj' zustavaji
    tak, jak byly ulozeny."""
    from gl3fc.gl3_program import GL3Program
    GL3Program(obj)  # novy Proxy - novy __init__, self._exec_cache = None


def main():
    import gl3fc.gl3_program as gl3_program_mod
    from gl3fc.gl3_program import GL3Program
    from gl3fc.gl3_library import GL3Library

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    fixtures_dir = os.path.join(root_dir, "gl3test", "placeholder_test")
    src_path = os.path.join(fixtures_dir, "MAINPROG.GL3")
    assert os.path.isfile(src_path), "chybi fixture %r" % (src_path,)

    lib_obj = FakeObj("Lib1")
    GL3Library(lib_obj)
    lib_obj.SearchPaths = [fixtures_dir]  # resi CALL/CHILDPROG uvnitr MAINPROG.GL3

    call_count = {"n": 0}
    orig_parse_program = gl3_program_mod.parse_program

    def counting_parse_program(*args, **kwargs):
        call_count["n"] += 1
        return orig_parse_program(*args, **kwargs)

    gl3_program_mod.parse_program = counting_parse_program
    try:
        # --- 1) RecomputeOnOpenDoc vychozi hodnota na novem objektu ---
        obj = FakeObj("Prog1")
        GL3Program(obj)
        assert obj.RecomputeOnOpenDoc is True, obj.RecomputeOnOpenDoc
        print("Novy GL3Program: RecomputeOnOpenDoc vychozi True: OK")

        # --- 2) prvni beh (RecomputeOnOpenDoc == True, vychozi) ---
        obj.SourceFile = src_path
        obj.Library = lib_obj
        obj.Proxy.execute(obj)
        assert call_count["n"] == 1, call_count["n"]
        assert obj.D1 == 11.0, obj.D1
        assert obj._ExecCache, "_ExecCache se ma naplnit po uspesnem behu"
        print("Prvni beh: skutecny prepocet (parse_program zavolan): OK")

        # --- 3) "otevreni dokumentu" (novy Proxy), RecomputeOnOpenDoc
        #     zustava True (vychozi) -> i kdyz se nic nezmenilo, DALSI
        #     execute() musi udelat SKUTECNY beh znovu (bezpecny vychozi
        #     stav - viz diskuze s uzivatelem) ---
        _reopen(obj)
        obj.Proxy.execute(obj)
        assert call_count["n"] == 2, call_count["n"]
        print("Po 'otevreni dokumentu' s RecomputeOnOpenDoc=True: "
              "skutecny prepocet i beze zmeny: OK")

        # --- 4) uzivatel vypne RecomputeOnOpenDoc - ve STEJNE session
        #     (self._exec_cache v pameti pořád plati) execute() zustava
        #     no-op jako predtim (RecomputeOnOpenDoc ovlivnuje jen to, co
        #     se stane, kdyz self._exec_cache je None - viz nize) ---
        obj.RecomputeOnOpenDoc = False
        obj.Proxy.execute(obj)
        assert call_count["n"] == 2, call_count["n"]
        print("Zmena RecomputeOnOpenDoc na False sama o sobe (ve stejne "
              "session, self._exec_cache uz plati) nevynuti dalsi beh: OK")

        _reopen(obj)  # simuluje zavreni+otevreni - self._exec_cache -> None,
                       # ale obj._ExecCache (perzistentni) zustava
        obj.Proxy.execute(obj)
        assert call_count["n"] == 2, (
            "RecomputeOnOpenDoc=False + nezmeneny SourceFile/inputs -> "
            "prepocet se MEL preskocit, ale parse_program se zavolal "
            "znovu (count=%d)" % call_count["n"]
        )
        assert obj.D1 == 11.0, obj.D1  # vystup zustal spravne dopocitany z minula
        print("Po 'otevreni dokumentu' s RecomputeOnOpenDoc=False, nic "
              "se nezmenilo: skutecny prepocet PRESKOCEN (persistovana "
              "_ExecCache pouzita): OK - D1=%r" % (obj.D1,))

        # --- 5) zmena vstupu i pri RecomputeOnOpenDoc=False musi po
        #     'otevreni' vynutit skutecny beh (signatura uz nesedi) ---
        obj.D2 = 0.0  # vystup - nema vliv, jen simulace "necoho zmeneneho"
        # zmenime SourceFile na jiny soubor - signatura (path) uz nebude sedet
        alt_path = os.path.join(fixtures_dir, "CHILDPROG.GL3")
        obj.SourceFile = alt_path
        _reopen(obj)
        obj.Proxy.execute(obj)
        assert call_count["n"] == 3, call_count["n"]
        assert obj.D1 == 22.0, obj.D1  # CHILDPROG.GL3 cte child_data.txt
        print("Zmena SourceFile pred 'otevrenim' i s RecomputeOnOpenDoc=False "
              "-> skutecny prepocet SE PROVEDE (signatura nesedi): OK")

    finally:
        gl3_program_mod.parse_program = orig_parse_program

    print()
    print("VSE OK - RecomputeOnOpenDoc funguje (vychozi True = puvodni "
          "chovani, False + nezmeneny stav preskoci prepocet po otevreni).")


if __name__ == "__main__":
    main()
