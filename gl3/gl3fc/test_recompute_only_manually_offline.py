# -*- coding: utf-8 -*-
"""
test_recompute_only_manually_offline.py - overeni RecomputeOnlyManually
(zadani uzivatele: prejmenovane + logicky obracene RecomputeOnOpenDoc,
navic rozsirene o gating auto-prepoctu v onChanged() - viz gl3_program.py).

self._exec_cache (GL3Program.execute()) je jen v pameti Proxy objektu -
po "otevreni dokumentu" (v tomhle testu simulovanem vytvorenim NOVEHO
Proxy na TOM SAMEM FakeObj - presne to, co dela __getstate__/__setstate__
vraceci None) je vzdy None, takze prvni execute() vzdy udela plny beh,
i kdyz RecomputeOnlyManually == True. Az DRUHY execute() (po "otevreni")
smi cache-hit vyuzit - a presne to se tu overuje.

Skutecny "beh interpretu" se pozna podle poctu volani parse_program()
(volane se jen na ceste PLNEHO behu, nikdy na cache-hit ceste) -
monkeypatch pocitadlo v gl3fc.gl3_program modulu.

App (FreeCAD) neni v tomhle offline prostredi k dispozici (viz
gl3_program.py - "App = None" fallback), takze _schedule_recompute()
vzdy pouzije svou synchronni fallback vetev (zadny QTimer/debounce) -
presne to umoznuje testovat GATING (RecomputeOnlyManually potlaci
onChanged()-driven auto-recompute) jednoduse pres pocitadlo volani
FakeDocument.recompute(), bez nutnosti simulovat Qt event loop.
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


class FakeDocument(object):
    """Jen pocita, kolikrat se na nem zavolalo recompute() - pro overeni
    gatingu v onChanged() (viz _schedule_recompute v gl3_program.py)."""

    def __init__(self, name):
        self.Name = name
        self.recompute_calls = 0

    def recompute(self):
        self.recompute_calls += 1


class FakeObj(object):
    """Stejna napodobenina jako v test_offline.py, navic setPropertyStatus
    (no-op - jen at neni potreba try/except AttributeError zavisely na
    tomhle testu), removeProperty (pro migrate_renamed_property) a
    Document jako FakeDocument (pro pocitani recompute() volani z
    onChanged())."""

    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self.Document = FakeDocument(name + "Doc")
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
    properties (vc. _ExecCache a RecomputeOnlyManually) na 'obj'
    zustavaji tak, jak byly ulozeny."""
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
        # --- 1) RecomputeOnlyManually vychozi hodnota na novem objektu ---
        obj = FakeObj("Prog1")
        GL3Program(obj)
        assert obj.RecomputeOnlyManually is False, obj.RecomputeOnlyManually
        print("Novy GL3Program: RecomputeOnlyManually vychozi False: OK")

        # --- 2) prvni beh (RecomputeOnlyManually == False, vychozi) ---
        obj.SourceFile = src_path
        obj.Library = lib_obj
        obj.Proxy.execute(obj)
        assert call_count["n"] == 1, call_count["n"]
        assert obj.D1 == 11.0, obj.D1
        assert obj._ExecCache, "_ExecCache se ma naplnit po uspesnem behu"
        print("Prvni beh: skutecny prepocet (parse_program zavolan): OK")

        # --- 3) "otevreni dokumentu" (novy Proxy), RecomputeOnlyManually
        #     zustava False (vychozi) -> i kdyz se nic nezmenilo, DALSI
        #     execute() musi udelat SKUTECNY beh znovu (bezpecny vychozi
        #     stav - viz diskuze s uzivatelem) ---
        _reopen(obj)
        obj.Proxy.execute(obj)
        assert call_count["n"] == 2, call_count["n"]
        print("Po 'otevreni dokumentu' s RecomputeOnlyManually=False: "
              "skutecny prepocet i beze zmeny: OK")

        # --- 4) uzivatel zapne RecomputeOnlyManually - ve STEJNE session
        #     (self._exec_cache v pameti pořád plati) execute() zustava
        #     no-op jako predtim (RecomputeOnlyManually ovlivnuje jen to,
        #     co se stane, kdyz self._exec_cache je None - viz nize) ---
        obj.RecomputeOnlyManually = True
        obj.Proxy.execute(obj)
        assert call_count["n"] == 2, call_count["n"]
        print("Zmena RecomputeOnlyManually na True sama o sobe (ve stejne "
              "session, self._exec_cache uz plati) nevynuti dalsi beh: OK")

        _reopen(obj)  # simuluje zavreni+otevreni - self._exec_cache -> None,
                       # ale obj._ExecCache (perzistentni) zustava
        obj.Proxy.execute(obj)
        assert call_count["n"] == 2, (
            "RecomputeOnlyManually=True + nezmeneny SourceFile/inputs -> "
            "prepocet se MEL preskocit, ale parse_program se zavolal "
            "znovu (count=%d)" % call_count["n"]
        )
        assert obj.D1 == 11.0, obj.D1  # vystup zustal spravne dopocitany z minula
        print("Po 'otevreni dokumentu' s RecomputeOnlyManually=True, nic "
              "se nezmenilo: skutecny prepocet PRESKOCEN (persistovana "
              "_ExecCache pouzita): OK - D1=%r" % (obj.D1,))

        # --- 5) zmena vstupu i pri RecomputeOnlyManually=True musi po
        #     'otevreni' vynutit skutecny beh (signatura uz nesedi) ---
        obj.D2 = 0.0  # vystup - nema vliv, jen simulace "necoho zmeneneho"
        # zmenime SourceFile na jiny soubor - signatura (path) uz nebude sedet
        alt_path = os.path.join(fixtures_dir, "CHILDPROG.GL3")
        obj.SourceFile = alt_path
        _reopen(obj)
        obj.Proxy.execute(obj)
        assert call_count["n"] == 3, call_count["n"]
        assert obj.D1 == 22.0, obj.D1  # CHILDPROG.GL3 cte child_data.txt
        print("Zmena SourceFile pred 'otevrenim' i s RecomputeOnlyManually=True "
              "-> skutecny prepocet SE PROVEDE (signatura nesedi): OK")

        # --- 6) migrace ze stare property "RecomputeOnOpenDoc" (dokument
        #     ulozeny PRED touto zmenou) - hodnota se invertuje, aby
        #     fakticke chovani (bod 1 z diskuze - "skip po otevreni")
        #     zustalo stejne jako drive pod starym jmenem/logikou ---
        old_true = FakeObj("OldTrue")
        old_true.addProperty("App::PropertyBool", "RecomputeOnOpenDoc", "GL3 Options", "stara")
        old_true.RecomputeOnOpenDoc = True  # stare "vzdy prepocitat po otevreni"
        GL3Program(old_true)
        assert not hasattr(old_true, "RecomputeOnOpenDoc"), "stara property se mela odstranit"
        assert old_true.RecomputeOnlyManually is False, old_true.RecomputeOnlyManually
        print("Migrace RecomputeOnOpenDoc=True -> RecomputeOnlyManually=False: OK")

        old_false = FakeObj("OldFalse")
        old_false.addProperty("App::PropertyBool", "RecomputeOnOpenDoc", "GL3 Options", "stara")
        old_false.RecomputeOnOpenDoc = False  # stare "presuskocit, pokud nic nezmeneno"
        GL3Program(old_false)
        assert not hasattr(old_false, "RecomputeOnOpenDoc"), "stara property se mela odstranit"
        assert old_false.RecomputeOnlyManually is True, old_false.RecomputeOnlyManually
        print("Migrace RecomputeOnOpenDoc=False -> RecomputeOnlyManually=True: OK")

        # --- 7) onChanged() gating: RecomputeOnlyManually=True potlaci
        #     auto-recompute po zmene "GL3 In" vstupu (App je v tomhle
        #     offline prostredi None, takze _schedule_recompute() by
        #     jinak pouzila svou synchronni fallback vetev - viz modulovy
        #     docstring) ---
        gated = FakeObj("Gated1")
        GL3Program(gated)
        gated.addProperty("App::PropertyFloat", "D9", "GL3 In", "test vstup")
        gated.RecomputeOnlyManually = True
        gated.Proxy.onChanged(gated, "D9")
        assert gated.Document.recompute_calls == 0, (
            "RecomputeOnlyManually=True mel potlacit auto-recompute z onChanged()"
        )
        print("onChanged() s RecomputeOnlyManually=True: recompute() NEvyvolan: OK")

        gated.RecomputeOnlyManually = False
        gated.Proxy.onChanged(gated, "D9")
        assert gated.Document.recompute_calls == 1, (
            "RecomputeOnlyManually=False ma auto-recompute pustit (synchronne, "
            "App je v testu None -> zadny debounce)"
        )
        print("onChanged() s RecomputeOnlyManually=False: recompute() vyvolan: OK")

        # --- 8) presna reprodukce hlaseneho bugu: pri skutecnem otevreni
        #     ulozeneho dokumentu FreeCAD NEVOLA __init__ (Proxy se
        #     obnovuje pres __setstate__, viz jeho docstring nize) - jen
        #     "holy" Proxy (__new__ bez __init__), na ktery muze prijit
        #     onChanged() (napr. behem obnovy hodnot property ze souboru)
        #     JESTE PRED onDocumentRestored(). self._recompute_timer v tu
        #     chvili jeste vubec neexistuje - drive to zpusobovalo
        #     AttributeError (viz hlaseni uzivatele) ---
        raw = FakeObj("RawRestore")
        raw.addProperty("App::PropertyFloat", "D9", "GL3 In", "test vstup")
        bare_proxy = GL3Program.__new__(GL3Program)  # presne to, co dela FreeCAD restore
        raw.Proxy = bare_proxy
        bare_proxy.onChanged(raw, "D9")  # nesmi spadnout na AttributeError
        assert raw.Document.recompute_calls == 1, (
            "i bez predchoziho __init__/onDocumentRestored se ma prepocet "
            "provest (fallback synchronni cesta, App je v testu None)"
        )
        print("onChanged() na Proxy BEZ predchoziho __init__/onDocumentRestored "
              "(presna reprodukce hlaseneho bugu) NESPADNE: OK")

        # --- 9) onDocumentRestored() dopni chybejici property (vc.
        #     migrace) i na takovem "holem" Proxy ---
        raw2 = FakeObj("RawRestore2")
        raw2.addProperty("App::PropertyBool", "RecomputeOnOpenDoc", "GL3 Options", "stara")
        raw2.RecomputeOnOpenDoc = True
        bare_proxy2 = GL3Program.__new__(GL3Program)
        raw2.Proxy = bare_proxy2
        bare_proxy2.onDocumentRestored(raw2)
        assert not hasattr(raw2, "RecomputeOnOpenDoc"), "stara property se mela odstranit"
        assert raw2.RecomputeOnlyManually is False, raw2.RecomputeOnlyManually
        assert hasattr(raw2, "SourceFile"), "onDocumentRestored ma dopnit i chybejici property"
        print("onDocumentRestored() dopni property (vc. migrace) i na 'holem' Proxy: OK")

    finally:
        gl3_program_mod.parse_program = orig_parse_program

    print()
    print("VSE OK - RecomputeOnlyManually funguje (vychozi False = puvodni "
          "automaticke chovani, True preskoci prepocet po otevreni A "
          "potlaci auto-recompute z onChanged() - jen rucne), vc. migrace "
          "ze stare RecomputeOnOpenDoc.")


if __name__ == "__main__":
    main()
