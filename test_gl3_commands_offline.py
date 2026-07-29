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
    assert obj.SearchPaths == [], "SearchPaths se ma inicializovat na prazdny seznam"
    assert obj.Proxy.Type == "GL3Library"
    print("Activated(): OK - vytvoren GL3Library objekt '%s' s prazdnym SearchPaths" % obj.Name)

    print()
    print("VSE OK - gl3_commands.CreateGL3LibraryCommand funguje (offline, bez realneho FreeCADu).")


if __name__ == "__main__":
    main()
