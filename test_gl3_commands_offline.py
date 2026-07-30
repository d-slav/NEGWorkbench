# -*- coding: utf-8 -*-
"""
Offline test gl3_commands.py bez realneho FreeCADu - stubuje FreeCAD/
FreeCADGui natolik, aby slo provolat CreateGL3LibraryCommand.Activated()
a overit, ze vznikne funkcni GL3Library objekt (SearchPaths pritomny).

Nenahrazuje test v realnem FreeCADu (Gui.Workbench/toolbar/ikony se tu
neresi vubec), jen overuje, ze prikaz samotny (import, Activated())
nespadne na hlouposti drive, nez se to zkusi naostro.
"""
import os
import sys
import types

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)


_TYPE_DEFAULTS = {
    "App::PropertyPythonObject": None,
}


class FakeObj(object):
    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self._prop_types = {}

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        return self

    def setPropertyStatus(self, name, status):
        pass  # FakeObj nema skutecny "Hidden" stav, jen se tu nesmi spadnout


class FakeDocument(object):
    def __init__(self):
        self.Objects = []
        self._counter = 0

    def addObject(self, type_name, name):
        self._counter += 1
        obj = FakeObj("%s%03d" % (name, self._counter))
        self.Objects.append(obj)
        return obj

    def recompute(self):
        pass


class FakeApp(object):
    ActiveDocument = None

    @staticmethod
    def newDocument():
        doc = FakeDocument()
        FakeApp.ActiveDocument = doc
        return doc


class FakeSelection(object):
    @staticmethod
    def clearSelection():
        pass

    @staticmethod
    def addSelection(obj):
        pass


class FakeGui(object):
    Selection = FakeSelection()

    @staticmethod
    def addCommand(name, cmd):
        pass


def main():
    sys.modules["FreeCAD"] = FakeApp()
    sys.modules["FreeCADGui"] = FakeGui()

    import gl3_commands

    cmd = gl3_commands.CreateGL3LibraryCommand()

    res = cmd.GetResources()
    assert "Pixmap" in res and os.path.isfile(res["Pixmap"]), "ikona create_library.svg musi existovat"
    assert "MenuText" in res and "ToolTip" in res
    print("GetResources(): OK (ikona nalezena na disku)")

    assert cmd.IsActive() is True

    obj = cmd.Activated()
    assert obj is not None
    assert hasattr(obj, "SearchPaths"), "GL3Library musi mit property SearchPaths"

    import gl3fc.gl3_library as gl3_library_mod

    expected_default = gl3_library_mod._default_examples_dir()
    assert obj.SearchPaths == [expected_default], (
        "SearchPaths se ma po vytvoreni inicializovat na vychozi "
        "adresar gl3/examples dodavany s doplnkem, misto: %r" % (obj.SearchPaths,)
    )
    assert obj.Proxy.Type == "GL3Library"
    print(
        "Activated(): OK - vytvoren GL3Library objekt '%s' s vychozi cestou %s"
        % (obj.Name, expected_default)
    )

    print()
    print("--- CreateGL3ProgramCommand ---")

    prog_cmd = gl3_commands.CreateGL3ProgramCommand()
    res = prog_cmd.GetResources()
    assert "Pixmap" in res and os.path.isfile(res["Pixmap"]), "ikona create_program.svg musi existovat"
    assert "MenuText" in res and "ToolTip" in res
    print("GetResources(): OK (ikona nalezena na disku)")
    assert prog_cmd.IsActive() is True

    examples_dir = os.path.join(_HERE, "gl3", "examples")
    tehlo_path = os.path.join(examples_dir, "TEHLO.GL3")
    assert os.path.isfile(tehlo_path), "ocekavany priklad TEHLO.GL3 nenalezen"

    # Skutecny Qt file-dialog nema smysl v offline testu volat - nahradime
    # ho pevnou hodnotou (viz _ask_source_file volane jen z Activated()).
    prog_cmd._ask_source_file = lambda: tehlo_path

    prog_obj = prog_cmd.Activated()
    assert prog_obj is not None
    assert prog_obj.SourceFile == tehlo_path
    assert prog_obj.Proxy.Type == "GL3Program"
    assert prog_obj.Name.startswith("TEHLO"), "Name se ma odvodit ze jmena souboru (+ counter FakeDocument)"
    # v dokumentu uz existuje presne jedna GL3Library (z testu vyse) ->
    # ocekavame automaticke pripojeni
    assert getattr(prog_obj, "Library", None) is obj, (
        "s jedinou GL3Library v dokumentu se ma automaticky pripojit jako Library"
    )
    print("Activated(): OK - vytvoren GL3Program objekt '%s' ze souboru %s" % (prog_obj.Name, tehlo_path))

    # zruseni dialogu (uzivatel dal Cancel) -> zadny objekt se nevytvori
    prog_cmd._ask_source_file = lambda: None
    assert prog_cmd.Activated() is None
    print("Activated() se zrusenym dialogem: OK - nic se nevytvorilo")

    print()
    print("VSE OK - gl3_commands.CreateGL3LibraryCommand i CreateGL3ProgramCommand funguji")
    print("(offline, bez realneho FreeCADu).")


if __name__ == "__main__":
    main()
