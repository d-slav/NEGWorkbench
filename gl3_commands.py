# -*- coding: utf-8 -*-
"""
gl3_commands.py - Gui.Command definice pro NEGWorkbench.

Zatim jen jeden prikaz: vytvoreni GL3Library objektu. Dalsi prikazy
(GL3Program, GL3Export, editace Library, ...) pribudou postupne az bude
tenhle prvni krok spolehlive fungovat (viz README.md).
"""

import os
import sys

_WB_DIR = os.path.dirname(__file__)
_GL3_DIR = os.path.join(_WB_DIR, "gl3")
if _GL3_DIR not in sys.path:
    sys.path.insert(0, _GL3_DIR)

import FreeCAD as App
import FreeCADGui as Gui

_ICON_DIR = os.path.join(_WB_DIR, "Resources", "icons")


class CreateGL3LibraryCommand(object):
    """Vytvori novy GL3Library objekt (viz gl3fc/gl3_library.py) v aktivnim
    dokumentu - pokud zadny neni otevreny, novy dokument se vytvori."""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(_ICON_DIR, "create_library.svg"),
            "MenuText": "Vytvorit GL3 Library",
            "ToolTip": (
                "Vytvori novy GL3Library objekt - seznam adresaru, ve "
                "kterych se hledaji .GL3 soubory volane pres CALL z "
                "GL3Program objektu."
            ),
        }

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument()

        from gl3fc.gl3_library import create as create_library

        obj = create_library(doc)
        doc.recompute()

        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        return obj

    def IsActive(self):
        return True


Gui.addCommand("NEG_CreateLibrary", CreateGL3LibraryCommand())
