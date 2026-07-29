# -*- coding: utf-8 -*-
"""
InitGui.py - vstupni bod FreeCAD GUI doplnku NEGWorkbench.

FreeCAD tenhle soubor automaticky najde a nacte pri startu, POKUD je
tahle slozka primo pod uzivatelskym Mod/ adresarem (napr.
%APPDATA%\\FreeCAD\\Mod\\NEGWorkbench\\InitGui.py na Windows,
~/.local/share/FreeCAD/Mod/NEGWorkbench/InitGui.py na Linuxu) - staci
zkopirovat/naklonovat cely tenhle repozitar tam a restartovat FreeCAD.

Zatim jen jeden prikaz (vytvoreni GL3Library) - dalsi (GL3Program,
GL3Export, editace Library, ...) pribudou postupne, az bude tenhle
zakladni krok spolehlive fungovat - viz README.md a docs/cs/.
"""

import os
import sys

_WB_DIR = os.path.dirname(__file__)
if _WB_DIR not in sys.path:
    sys.path.insert(0, _WB_DIR)

import FreeCADGui as Gui


class NEGWorkbench(Gui.Workbench):
    MenuText = "NEG/GL3"
    ToolTip = (
        "NEG/GL3 - integrace historickeho geometrickeho jazyka "
        "(LET Kunovice / Aircraft Industries a.s.) do FreeCADu"
    )
    Icon = os.path.join(_WB_DIR, "Resources", "icons", "neg_workbench.svg")

    def Initialize(self):
        # Import az tady (ne na urovni modulu) - FreeCAD nacita InitGui.py
        # pri kazdem startu, i kdyz se workbench nikdy neaktivuje; import
        # gl3_commands (a s nim gl3fc/gerlib) chceme az pri prvni aktivaci.
        import gl3_commands  # noqa: F401 - registruje Gui.Command objekty

        self.command_list = ["NEG_CreateLibrary"]
        self.appendToolbar("NEG/GL3", self.command_list)
        self.appendMenu("NEG/GL3", self.command_list)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(NEGWorkbench())
