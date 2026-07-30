# -*- coding: utf-8 -*-
"""
Verny test toho, jak FreeCAD skutecne spousti InitGui.py.

Realny FreeCAD zdrojak (FreeCADGuiInit.py, funkce RunInitGuiPy) dela:

    def RunInitGuiPy(Dir):
        with open(InstallFile) as f:
            exec(compile(f.read(), InstallFile, "exec"))

`exec(code)` BEZ explicitnich globals/locals, zavolany UVNITR FUNKCE,
pouzije DVE ODDELENE veci: globals() teto funkce (= skutecny modul
FreeCADGuiInit.py) a locals() teto funkce (jeji vlastni lokalni
promenne). Cokoliv InitGui.py na nejvyssi urovni prirsadi, konci v teto
"locals" dict - NE ve skutecnych globals. Trida/metody v InitGui.py ale
pri hledani nedefinovanych jmen koukaji JEN do skutecnych globals.

Muj puvodni test (predchozi verze tohohle souboru) tohle NEreplikoval
verne - pouzival `exec(code, jeden_sdileny_dict)`, kde globals==locals,
takze chyba se neprojevila (falesny pozitivni vysledek). Tenhle test to
dela spravne - simuluje RunInitGuiPy jako SKUTECNOU funkci s vlastnim
__globals__ (fake modul, ktery ma jen 'os' - stejne jako realny
FreeCADGuiInit.py nejspis ma - a NIC z naseho InitGui.py).
"""
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)


class FakeWorkbenchBase(object):
    pass


class FakeGui(object):
    Workbench = FakeWorkbenchBase
    registered = None
    commands = {}

    @staticmethod
    def addWorkbench(wb):
        FakeGui.registered = wb

    @staticmethod
    def addLanguagePath(path):
        pass

    @staticmethod
    def updateLocale():
        pass

    @staticmethod
    def addCommand(name, cmd):
        FakeGui.commands[name] = cmd


def main():
    sys.modules["FreeCADGui"] = FakeGui()
    sys.modules["FreeCAD"] = types.ModuleType("FreeCAD")  # gl3_commands.py needs 'import FreeCAD as App'

    init_gui_path = os.path.join(_HERE, "InitGui.py")

    # --- simulace FreeCADGuiInit.py jako samostatneho "modulu" (fake
    # globals dict) - obsahuje jen 'os' (realny FreeCADGuiInit.py si ho
    # jiste taky importuje pro sve vlastni ucely), NIC z NASEHO kodu ---
    fake_freecad_gui_init_module = {"os": os, "__name__": "FreeCADGuiInit_sim"}

    # RunInitGuiPy definovana PRES EXEC do fake modulu, aby jeji
    # __globals__ byl SKUTECNE fake_freecad_gui_init_module (ne nas
    # testovaci skript) - presne jako v realnem FreeCADu.
    exec(
        "def RunInitGuiPy(path):\n"
        "    with open(path, 'r', encoding='utf-8') as f:\n"
        "        src = f.read()\n"
        "    code = compile(src, path, 'exec')\n"
        "    exec(code)\n",
        fake_freecad_gui_init_module,
    )
    run_init_gui_py = fake_freecad_gui_init_module["RunInitGuiPy"]

    # Tohle musi projit BEZ vyjimky - presne to same volani, jako dela
    # FreeCAD (exec() uvnitr funkce, dve oddelene globals/locals).
    run_init_gui_py(init_gui_path)

    print("InitGui.py se nactl pod VERNOU simulaci FreeCAD exec() (oddelene")
    print("globals/locals uvnitr funkce) - bez vyjimky.")

    registered = FakeGui.registered
    assert isinstance(registered, FakeWorkbenchBase)
    print("Gui.addWorkbench() bylo zavolano s instanci NEGWorkbench: OK")

    expected_icon = os.path.join(_HERE, "Resources", "icons", "neg_workbench.svg")
    assert registered.Icon == expected_icon, (registered.Icon, expected_icon)
    assert os.path.isfile(registered.Icon), "ikona workbenche musi existovat na disku"
    print("Workbench Icon cesta spravna (dopoctena zevnitr tela tridy) a soubor existuje: %s"
          % registered.Icon)

    # --- a ted i Initialize() sama (registruje prikazy, addLanguagePath) ---
    registered.command_list = None
    registered.appendToolbar = lambda name, cmds: setattr(registered, "_toolbar", (name, cmds))
    registered.appendMenu = lambda name, cmds: setattr(registered, "_menu", (name, cmds))
    registered.Initialize()

    assert registered.command_list == ["NEG_CreateLibrary"]
    assert registered._toolbar[1] == ["NEG_CreateLibrary"]
    assert registered._menu[1] == ["NEG_CreateLibrary"]
    print("Initialize() probehla bez vyjimky a spravne zaregistrovala prikaz: OK")

    print()
    print("VSE OK - InitGui.py je odolny vuci FreeCAD skutecnemu zpusobu spousteni")
    print("(exec() s oddelenymi globals/locals).")


if __name__ == "__main__":
    main()
