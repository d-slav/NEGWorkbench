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
import json

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)


_TYPE_DEFAULTS = {
    "App::PropertyFloat": 0.0,
    "App::PropertyInteger": 0,
    "App::PropertyFileIncluded": "",
    "App::PropertyFile": "",
    "App::PropertyLink": None,
    "App::PropertyPythonObject": None,
    "App::PropertyString": "",
    "App::PropertyStringList": [],
}


class FakeObj(object):
    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self.Document = None
        self._prop_types = {}
        self._prop_groups = {}
        self._touched = False

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        self._prop_groups[name] = group
        return self

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        # Simulace realneho FreeCAD chovani: kazde nastaveni property
        # zavola Proxy.onChanged(self, name) - na tomhle stoji
        # synchronizace skrytych Linku (viz gl3_props.py/gl3_export.py/
        # gl3_program.py - "Objekt.Vystup" reference format).
        proxy = self.__dict__.get("Proxy")
        if proxy is not None and name != "Proxy" and hasattr(proxy, "onChanged"):
            proxy.onChanged(self, name)

    def setPropertyStatus(self, name, status):
        pass  # FakeObj nema skutecny "Hidden"/"ReadOnly" stav, jen se tu nesmi spadnout

    @property
    def PropertiesList(self):
        return list(self._prop_types.keys())

    def getGroupOfProperty(self, name):
        return self._prop_groups.get(name)

    def getTypeIdOfProperty(self, name):
        return self._prop_types.get(name)

    def removeProperty(self, name):
        if hasattr(self, name):
            delattr(self, name)
        self._prop_types.pop(name, None)
        self._prop_groups.pop(name, None)
        return True

    def touch(self):
        self._touched = True


class FakeDocument(object):
    def __init__(self):
        self.Objects = []
        self._counter = 0
        self.recompute_calls = 0

    def addObject(self, type_name, name):
        self._counter += 1
        obj = FakeObj("%s%03d" % (name, self._counter))
        obj.Document = self
        self.Objects.append(obj)
        return obj

    def recompute(self):
        self.recompute_calls += 1

    def getObject(self, name):
        for obj in self.Objects:
            if obj.Name == name:
                return obj
        return None


class FakeConsole(object):
    @staticmethod
    def PrintError(msg):
        sys.stderr.write(msg)


class FakeParam(object):
    """Stub za App.ParamGet(...) navratovy objekt - jen in-memory
    slovnik, ale se stejnym rozhranim (GetString/SetString) jako
    skutecny FreeCAD parametr."""
    def __init__(self):
        self._values = {}

    def GetString(self, name, default=""):
        return self._values.get(name, default)

    def SetString(self, name, value):
        self._values[name] = value


class FakeApp(object):
    ActiveDocument = None
    Console = FakeConsole()
    _param = FakeParam()

    @staticmethod
    def newDocument():
        doc = FakeDocument()
        FakeApp.ActiveDocument = doc
        return doc

    @staticmethod
    def ParamGet(path):
        return FakeApp._param


class FakeSelection(object):
    _selection = []

    @staticmethod
    def clearSelection():
        pass

    @staticmethod
    def addSelection(obj):
        pass

    @staticmethod
    def getSelection():
        return list(FakeSelection._selection)


class FakeGui(object):
    Selection = FakeSelection()

    @staticmethod
    def addCommand(name, cmd):
        pass

    @staticmethod
    def updateGui():
        pass

    @staticmethod
    def runCommand(name):
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

    assert obj.SearchPaths == gl3_library_mod._default_search_paths(), (
        "SearchPaths se ma po vytvoreni inicializovat na zastupny text "
        "${workbench_path}/gl3sys, misto: %r" % (obj.SearchPaths,)
    )
    assert obj.Proxy.Type == "GL3Library"
    print(
        "Activated(): OK - vytvoren GL3Library objekt '%s' s vychozimi cestami %s"
        % (obj.Name, obj.SearchPaths)
    )

    print()
    print("--- CreateGL3ProgramCommand ---")

    prog_cmd = gl3_commands.CreateGL3ProgramCommand()
    res = prog_cmd.GetResources()
    assert "Pixmap" in res and os.path.isfile(res["Pixmap"]), "ikona create_program.svg musi existovat"
    assert "MenuText" in res and "ToolTip" in res
    print("GetResources(): OK (ikona nalezena na disku)")
    assert prog_cmd.IsActive() is True

    examples_dir = os.path.join(_HERE, "gl3test")
    tehlo_path = os.path.join(examples_dir, "TEHLO.GL3")
    assert os.path.isfile(tehlo_path), "ocekavana fixture TEHLO.GL3 v gl3test/ nenalezena"

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

    # --- zapamatovani posledniho adresare (bez Qt - primo funkce, ktere
    # _ask_source_file pouziva; QFileDialog samotny se testovat nema smysl) ---
    assert gl3_commands._get_last_source_dir() == "", "pred prvnim pouzitim nic nezapamatovano"
    gl3_commands._set_last_source_dir(examples_dir)
    assert gl3_commands._get_last_source_dir() == examples_dir, (
        "po _set_last_source_dir() se ma _get_last_source_dir() vratit se stejnou hodnotou"
    )
    gl3_commands._set_last_source_dir(None)  # zruseny dialog -> nic se neprepise
    assert gl3_commands._get_last_source_dir() == examples_dir, (
        "_set_last_source_dir(None/'') nesmi prepsat drive zapamatovanou hodnotu"
    )
    print("_get_last_source_dir()/_set_last_source_dir(): OK - hodnota prezije pres FakeApp.ParamGet")

    # zruseni dialogu (uzivatel dal Cancel) -> zadny objekt se nevytvori
    prog_cmd._ask_source_file = lambda: None
    assert prog_cmd.Activated() is None
    print("Activated() se zrusenym dialogem: OK - nic se nevytvorilo")

    print()
    print("VSE OK - gl3_commands.CreateGL3LibraryCommand i CreateGL3ProgramCommand funguji")
    print("(offline, bez realneho FreeCADu).")

    print()
    print("--- CreateGL3ExportCommand ---")

    export_cmd = gl3_commands.CreateGL3ExportCommand()
    res = export_cmd.GetResources()
    assert "Pixmap" in res and os.path.isfile(res["Pixmap"]), "ikona create_export.svg musi existovat"
    assert "MenuText" in res and "ToolTip" in res
    print("GetResources(): OK (ikona nalezena na disku)")
    assert export_cmd.IsActive() is True

    # nic neni vybrano -> jasna chyba, zadny objekt
    FakeSelection._selection = []
    assert export_cmd.Activated() is None
    print("Activated() bez vyberu: OK - nic se nevytvorilo")

    # vybran objekt, ktery neni GL3Program -> stejne tak
    FakeSelection._selection = [obj]  # obj = GL3Library z testu vyse
    assert export_cmd.Activated() is None
    print("Activated() s vyberem GL3Library (ne GL3Program): OK - nic se nevytvorilo")

    # skutecny GL3Program bez jakekoliv schematu (jeste nikdy nerecomputnuty)
    # nema zadnou "GL3 Out" property -> take chyba
    fresh_prog = FakeObj("FreshProgram")
    from gl3fc.gl3_program import GL3Program

    GL3Program(fresh_prog)
    FakeSelection._selection = [fresh_prog]
    assert export_cmd.Activated() is None
    print("Activated() s GL3Program bez GL3 Out property: OK - nic se nevytvorilo")

    # prog_obj (z testu vyse) jeste taky nema schema (Activated() jen
    # zavola create_program(), ktery pouziva FakeDocument.recompute() = no-op,
    # execute() se tedy nikdy nezavola) - dopocitame schema rucne, presne
    # jak by to udelal skutecny FreeCAD prvnim recompute (viz test_offline.py:
    # 1. recompute selze na IDEV, ale property uz vytvori).
    try:
        prog_obj.Proxy.execute(prog_obj)
    except OSError:
        pass  # ocekavano - BJM/DH jeste nejsou vyplnene, schema uz ale existuje

    assert prog_obj._prop_types.get("PO") == "App::PropertyString"
    assert prog_obj._prop_types.get("S") == "App::PropertyString"

    FakeSelection._selection = [prog_obj]

    # Skutecny Qt vyberovy dialog nema smysl v offline testu volat (a v
    # tomhle sandboxu stejne neni PySide nainstalovany) - nahradime ho
    # pevnou hodnotou, presne jako u _ask_source_file v Program testu vyse.
    export_cmd._ask_output_name = lambda outputs: None  # simulace Cancel
    exp_obj = export_cmd.Activated()
    assert exp_obj is None, (
        "PO i S jsou 2 composite vystupy - bez vybrane hodnoty z dialogu se "
        "nema nic vytvorit (viz _ask_output_name)"
    )
    print("Activated() s vice composite vystupy a zrusenym dialogem: OK - nic se nevytvorilo")

    # ted simulujeme, ze uzivatel v dialogu vybral "S"
    export_cmd._ask_output_name = lambda outputs: "S"
    exp_obj = export_cmd.Activated()
    assert exp_obj is not None
    assert exp_obj.Source is prog_obj
    assert exp_obj.Input == "%s.S" % prog_obj.Name
    assert exp_obj.Proxy.Type == "GL3Export"
    assert exp_obj.Document is prog_obj.Document, "Export se ma vytvorit ve stejnem dokumentu jako Source"
    print("Activated() s vybranym vystupem 'S': OK - vytvoren GL3Export objekt '%s'" % exp_obj.Name)

    # --- novy krok: pokud je vybrany vystup Array, ma se zeptat na index ---
    prog_obj.PO = json.dumps(
        {
            "defined": True,
            "type": "Array",
            "items": [
                {"defined": True, "type": "Point", "x": 0.0, "y": 0.0, "z": 0.0},
                {"defined": True, "type": "Point", "x": 1.0, "y": 1.0, "z": 0.0},
                {"defined": True, "type": "Point", "x": 2.0, "y": 2.0, "z": 0.0},
            ],
        }
    )

    export_cmd._ask_output_name = lambda outputs: "PO"
    export_cmd._maybe_ask_array_index = lambda source, output_name: 2
    exp_obj_idx = export_cmd.Activated()
    assert exp_obj_idx is not None
    assert exp_obj_idx.Input == "%s.PO(2)" % prog_obj.Name, (
        "vybrany index se ma rovnou promitnout do Input jako '(N)' - bez nutnosti "
        "to pak dodatecne rucne prepisovat"
    )
    print("Activated() s Array vystupem + zvolenym indexem 2: OK - Input = '%s'" % exp_obj_idx.Input)

    # zamitnuti dialogu (uzivatel chce cele pole, ne jeden prvek) -> zadny index
    export_cmd._maybe_ask_array_index = lambda source, output_name: None
    exp_obj_noidx = export_cmd.Activated()
    assert exp_obj_noidx is not None
    assert exp_obj_noidx.Input == "%s.PO" % prog_obj.Name, "bez zvoleneho indexu se ma pouzit cele pole"
    print("Activated() s Array vystupem bez zvoleneho indexu: OK - Input = '%s'" % exp_obj_noidx.Input)

    print()
    print("VSE OK - gl3_commands.CreateGL3ExportCommand funguje (offline, bez realneho FreeCADu).")

    print()
    print("--- ReloadGL3ProgramCommand ---")

    reload_cmd = gl3_commands.ReloadGL3ProgramCommand()
    res = reload_cmd.GetResources()
    assert "Pixmap" in res and os.path.isfile(res["Pixmap"])
    assert "MenuText" in res and "ToolTip" in res
    print("GetResources(): OK (ikona nalezena na disku)")
    assert reload_cmd.IsActive() is True

    # nic neni vybrano -> jasna chyba, zadny objekt
    FakeSelection._selection = []
    assert reload_cmd.Activated() is None
    print("Activated() bez vyberu: OK - nic se nestalo")

    # vybran objekt, ktery neni GL3Program -> stejne tak
    FakeSelection._selection = [obj]  # obj = GL3Library z testu vyse
    assert reload_cmd.Activated() is None
    print("Activated() s vyberem GL3Library (ne GL3Program): OK - nic se nestalo")

    # vybran GL3Program -> touch() + Document.recompute()
    prog_obj._touched = False  # reset (prog_obj uz mohl byt touchnuty drivejsimi testy vyse)
    calls_before = prog_obj.Document.recompute_calls
    FakeSelection._selection = [prog_obj]
    result = reload_cmd.Activated()
    assert result is prog_obj
    assert prog_obj._touched is True, "Reload ma zavolat obj.touch()"
    assert prog_obj.Document.recompute_calls == calls_before + 1, (
        "Reload ma zavolat Document.recompute() - donuti tim execute() znovu "
        "precist SourceFile a doplnit pripadny novy parametr"
    )
    print("Activated() s vybranym GL3Program: OK - touch() + Document.recompute() zavolany")

    print()
    print("VSE OK - gl3_commands.ReloadGL3ProgramCommand funguje (offline, bez realneho FreeCADu).")


if __name__ == "__main__":
    main()
