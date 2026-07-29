# -*- coding: utf-8 -*-
"""
Test, ze InitGui.py neselze na chybejicim __file__ - FreeCAD InitGui.py/
Init.py spousti pres exec (ne import), takze __file__ v jejich namespace
NENI k dispozici (znamy limit FreeCADu). Simulujeme presne tohle: exec()
zdrojoveho kodu InitGui.py v cistem globals dictu bez '__file__' klice.

Overuje jen to, ze se nacteni nezhrouti a _WB_DIR se spravne dopocita
pres sourozenecky modul gl3_wb_paths.py (fallback uroven 2) - nikoliv
skutecne chovani Gui.Workbench/toolbar (na to real FreeCAD).
"""
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)  # simuluje "FreeCAD uz pridal Mod/NEGWorkbench na sys.path"


class FakeWorkbenchBase(object):
    """Minimalni napodobenina Gui.Workbench - staci na to, aby "class
    NEGWorkbench(Gui.Workbench)" v InitGui.py fungovalo."""
    pass


class FakeGui(object):
    Workbench = FakeWorkbenchBase

    @staticmethod
    def addWorkbench(wb):
        FakeGui.registered = wb

    @staticmethod
    def addLanguagePath(path):
        pass

    @staticmethod
    def updateLocale():
        pass


def main():
    sys.modules["FreeCADGui"] = FakeGui()

    init_gui_path = os.path.join(_HERE, "InitGui.py")
    with open(init_gui_path, "r", encoding="utf-8") as f:
        source = f.read()

    code = compile(source, init_gui_path, "exec")

    # DULEZITE: globals dict BEZ '__file__' - presne simuluje FreeCAD
    namespace = {"__name__": "__main__"}
    assert "__file__" not in namespace

    exec(code, namespace)  # nesmi vyhodit NameError na __file__

    assert namespace["_WB_DIR"] == _HERE, (
        "fallback pres gl3_wb_paths.py musi dat stejny adresar jako "
        "skutecne umisteni InitGui.py: %r vs %r" % (namespace["_WB_DIR"], _HERE)
    )
    print("InitGui.py se nactl BEZ __file__ v namespace (presne jako v realnem FreeCADu)")
    print("_WB_DIR spravne dopocitan pres gl3_wb_paths.py fallback: %s" % namespace["_WB_DIR"])

    wb_class = namespace["NEGWorkbench"]
    expected_icon = os.path.join(_HERE, "Resources", "icons", "neg_workbench.svg")
    assert wb_class.Icon == expected_icon
    assert os.path.isfile(wb_class.Icon), "ikona workbenche musi existovat na disku"
    print("Workbench Icon cesta spravna a soubor existuje: %s" % wb_class.Icon)

    print()
    print("VSE OK - InitGui.py je odolny vuci chybejicimu __file__.")


if __name__ == "__main__":
    main()
