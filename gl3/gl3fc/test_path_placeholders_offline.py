# -*- coding: utf-8 -*-
"""
test_path_placeholders_offline.py - overeni zastupnych textu
${workbench_path}/${fc_file_path}/${gl3_file_path} (viz gl3_placeholders.py,
gl3fc/gl3_placeholder_context.py) bez skutecneho FreeCADu, na skutecnych
souborech na disku (gl3test/placeholder_test/ - viz ten adresar).

Overuje vsechny tri pozadovane povrchy:
  1. GL3Program.SourceFile muze obsahovat ${workbench_path}/${fc_file_path}.
  2. GL3Library.SearchPaths muze obsahovat totez (resi CALL/CHILDPROG).
  3. IDEV uvnitr .GL3 zdroje muze pouzit vsechny tri vc. ${gl3_file_path},
     ktery se spravne meni mezi hlavnim programem a volanou SUBRO (CALL).

Fixture: gl3test/placeholder_test/{MAINPROG,CHILDPROG}.GL3 + *_data.txt.
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
}


class FakeDocument(object):
    """Minimalni nahrada za FreeCAD.Document - jen FileName, coz je vsechno,
    co gl3_placeholder_context.fc_file_path() cte."""
    def __init__(self, file_name=""):
        self.FileName = file_name


class FakeObj(object):
    """Stejna napodobenina jako v test_offline.py (viz tam pro komentar) -
    minimalni DocumentObject: addProperty + obycejne atributy."""

    def __init__(self, name, document=None):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self.Document = document
        self._prop_types = {}
        self._prop_groups = {}

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        self._prop_groups[name] = group
        return self

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


def main():
    from gl3fc.gl3_library import GL3Library
    from gl3fc.gl3_program import GL3Program
    from gl3fc import gl3_placeholder_context

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    fixtures_dir = os.path.join(root_dir, "gl3test", "placeholder_test")
    assert os.path.isdir(fixtures_dir), "chybi fixture adresar %r" % (fixtures_dir,)

    # Skutecny workbench_path() teto instalace (root_dir) - overime, ze to
    # opravdu sedi na to, co spocita gl3_placeholder_context, at se test
    # nerozbije, kdyz nekdo strukturu adresaru zmeni.
    assert gl3_placeholder_context.workbench_path() == root_dir, (
        gl3_placeholder_context.workbench_path(), root_dir,
    )

    fc_doc = FakeDocument(file_name=os.path.join(root_dir, "gl3test", "MujModel.FCStd"))

    # --- 1) GL3Library.SearchPaths s ${workbench_path} - resi CALL/CHILDPROG ---
    lib_obj = FakeObj("GL3Library", document=fc_doc)
    GL3Library(lib_obj)
    lib_obj.SearchPaths = ["${workbench_path}/gl3test/placeholder_test"]

    # --- 2) GL3Program.SourceFile s ${workbench_path} ---
    prog = FakeObj("MAINPROG_Program", document=fc_doc)
    GL3Program(prog)
    prog.SourceFile = "${workbench_path}/gl3test/placeholder_test/MAINPROG.GL3"
    prog.Library = lib_obj

    prog.Proxy.execute(prog)

    # --- 3) IDEV uvnitr MAINPROG pouzil ${workbench_path} (main_data.txt),
    #     IDEV uvnitr CHILDPROG (volane pres CALL) pouzil ${gl3_file_path},
    #     ktery se SPRAVNE lisi od hlavniho programu (adresar CHILDPROG.GL3,
    #     ne MAINPROG.GL3 - v tomto pripade jsou stejne, ale mechanismus se
    #     overuje jeste primo na interpretu nize) ---
    assert prog.D1 == 11.0, prog.D1  # main_data.txt
    assert prog.D2 == 22.0, prog.D2  # child_data.txt (pres CALL/CHILDPROG)
    print("GL3Program.SourceFile + GL3Library.SearchPaths + IDEV s "
          "${workbench_path}/${gl3_file_path}: OK - D1=%r D2=%r" % (prog.D1, prog.D2))

    # --- 4) ${fc_file_path} - dokument ULOZEN (FileName nastaven) ---
    prog2 = FakeObj("MAINPROG_Program2", document=fc_doc)
    GL3Program(prog2)
    # fc_file_path() ukazuje na .../gl3test - '${fc_file_path}/placeholder_test/...'
    prog2.SourceFile = "${fc_file_path}/placeholder_test/MAINPROG.GL3"
    prog2.Library = lib_obj
    prog2.Proxy.execute(prog2)
    assert prog2.D1 == 11.0, prog2.D1
    print("${fc_file_path} (dokument ulozen): OK - D1=%r" % (prog2.D1,))

    # --- 5) ${fc_file_path} - dokument NEULOZEN (FileName == "") -> jasna
    #     chyba, ne tichy spatny vysledek ---
    unsaved_doc = FakeDocument(file_name="")
    prog3 = FakeObj("MAINPROG_Program3", document=unsaved_doc)
    GL3Program(prog3)
    prog3.SourceFile = "${fc_file_path}/placeholder_test/MAINPROG.GL3"
    prog3.Library = lib_obj
    try:
        prog3.Proxy.execute(prog3)
        assert False, "ocekavana chyba pro ${fc_file_path} na neulozenem dokumentu"
    except ValueError as e:
        assert "fc_file_path" in str(e), e
        print("${fc_file_path} (dokument NEulozen) -> jasna chyba: OK -", e)

    # --- 6) neznamy zastupny text v SourceFile -> jasna chyba ---
    prog4 = FakeObj("MAINPROG_Program4", document=fc_doc)
    GL3Program(prog4)
    prog4.SourceFile = "${nesmysl}/placeholder_test/MAINPROG.GL3"
    prog4.Library = lib_obj
    try:
        prog4.Proxy.execute(prog4)
        assert False, "ocekavana chyba pro neznamy zastupny text"
    except ValueError as e:
        assert "nesmysl" in str(e), e
        print("Neznamy zastupny text v SourceFile -> jasna chyba: OK -", e)

    # --- 7) ${gl3_file_path} v GL3Library.SearchPaths -> nedava smysl,
    #     jasna chyba (i kdyz je jinak validni zastupny text) ---
    lib_obj2 = FakeObj("GL3Library2", document=fc_doc)
    GL3Library(lib_obj2)
    lib_obj2.SearchPaths = ["${gl3_file_path}/placeholder_test"]
    prog5 = FakeObj("MAINPROG_Program5", document=fc_doc)
    GL3Program(prog5)
    prog5.SourceFile = "${workbench_path}/gl3test/placeholder_test/MAINPROG.GL3"
    prog5.Library = lib_obj2
    try:
        prog5.Proxy.execute(prog5)
        assert False, "ocekavana chyba pro ${gl3_file_path} v SearchPaths"
    except ValueError as e:
        assert "gl3_file_path" in str(e), e
        print("${gl3_file_path} v GL3Library.SearchPaths -> jasna chyba: OK -", e)

    # --- 8) novy GL3Library ma vychozi SearchPaths = ["${workbench_path}/gl3sys"]
    #     (jako ZASTUPNY TEXT, ne uz predem resolvovana absolutni cesta) ---
    from gl3fc.gl3_library import _default_search_paths
    lib_obj_fresh = FakeObj("GL3LibraryFresh", document=fc_doc)
    GL3Library(lib_obj_fresh)
    assert lib_obj_fresh.SearchPaths == ["${workbench_path}/gl3sys"], lib_obj_fresh.SearchPaths
    assert lib_obj_fresh.SearchPaths == _default_search_paths()
    print("Novy GL3Library: vychozi SearchPaths == "
          "['${workbench_path}/gl3sys']: OK - %r" % (lib_obj_fresh.SearchPaths,))

    # --- 9) ${fc_file_path} se automaticky prohledava JAKO PRVNI, pred
    #     adresari z SearchPaths (stejnojmenna SUBRO na obou mistech -
    #     musi vyhrat ta z ${fc_file_path}) ---
    fc_doc_prio = FakeDocument(
        file_name=os.path.join(fixtures_dir, "fc_dir", "MyOpenModel.FCStd")
    )
    lib_obj3 = FakeObj("GL3Library3", document=fc_doc_prio)
    GL3Library(lib_obj3)
    lib_obj3.SearchPaths = ["${workbench_path}/gl3test/placeholder_test"]
    registry = lib_obj3.Proxy.build_registry(lib_obj3)
    prio_def = registry["PRIOTEST"]
    assert prio_def.body, "PRIOTEST nenalezeno vubec"
    # over primo obsahem D1=999.0 (z ${fc_file_path}/PRIOTEST.GL3), ne
    # D1=111.0 (z SearchPaths/PRIOTEST.GL3)
    assert os.path.dirname(prio_def.source_path) == os.path.join(fixtures_dir, "fc_dir"), (
        prio_def.source_path
    )
    print("${fc_file_path} ma prednost pred SearchPaths pri hledani CALL: OK - "
          "nalezeno v %r" % (prio_def.source_path,))

    # --- 10) neulozeny dokument (FileName=="") -> ${fc_file_path} se pri
    #     hledani TISE preskoci (zadna chyba), hleda se jen v SearchPaths ---
    lib_obj4 = FakeObj("GL3Library4", document=unsaved_doc)
    GL3Library(lib_obj4)
    lib_obj4.SearchPaths = ["${workbench_path}/gl3test/placeholder_test"]
    registry2 = lib_obj4.Proxy.build_registry(lib_obj4)
    prio_def2 = registry2["PRIOTEST"]
    # tady uz JEN SearchPaths verze (D1=111.0) - ${fc_file_path} adresar
    # neexistuje/nema smysl, tise se vynechal
    assert os.path.dirname(prio_def2.source_path) == fixtures_dir, prio_def2.source_path
    print("Neulozeny dokument -> ${fc_file_path} se tise vynecha (jen "
          "SearchPaths se prohledavaji): OK - nalezeno v %r" % (prio_def2.source_path,))

    print()
    print("VSE OK - ${workbench_path}/${fc_file_path}/${gl3_file_path} funguji "
          "v GL3Program.SourceFile, GL3Library.SearchPaths i IDEV; vychozi "
          "SearchPaths i priorita ${fc_file_path} pred SearchPaths tez OK.")


if __name__ == "__main__":
    main()
