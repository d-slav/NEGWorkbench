# -*- coding: utf-8 -*-
"""
gl3_commands.py - Gui.Command definice pro NEGWorkbench.

Zatim: vytvoreni GL3Library a GL3Program objektu. Dalsi prikazy
(GL3Export, editace Library pres UI dialog, ...) pribudou postupne az
bude tenhle druhy krok spolehlive fungovat (viz README.md).
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


def QT_TRANSLATE_NOOP(context, text):
    """Viz InitGui.py - zatim jen znaceni pro budouci lupdate extract."""
    return text


class CreateGL3LibraryCommand(object):
    """Vytvori novy GL3Library objekt (viz gl3fc/gl3_library.py) v aktivnim
    dokumentu - pokud zadny neni otevreny, novy dokument se vytvori."""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(_ICON_DIR, "create_library.svg"),
            "MenuText": QT_TRANSLATE_NOOP("NEG_CreateLibrary", "Create GL3 Library"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "NEG_CreateLibrary",
                "Creates a new GL3Library object - a list of directories to "
                "search for .GL3 files called via CALL from a GL3Program object.",
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


class CreateGL3ProgramCommand(object):
    """Vytvori novy GL3Program objekt (viz gl3fc/gl3_program.py) z vybraneho
    .GL3 souboru - in:/out: property se vygeneruji automaticky ze SUBRO
    hlavicky toho souboru (viz GL3Program.execute() -> _sync_properties()).

    Pokud aktivni dokument obsahuje prave jednu GL3Library, automaticky se
    pripoji jako Library (pro pripadny CALL na dalsi SUBRO). Pri zadne nebo
    vice nez jedne Library se property Library necha prazdna - da se
    dodatecne nastavit rucne v Property editoru (je to obycejny Link)."""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(_ICON_DIR, "create_program.svg"),
            "MenuText": QT_TRANSLATE_NOOP("NEG_CreateProgram", "Create GL3 Program"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "NEG_CreateProgram",
                "Creates a new GL3Program object from a .GL3 SUBRO file - "
                "in/out properties are generated automatically from its header.",
            ),
        }

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument()

        source_file = self._ask_source_file()
        if not source_file:
            return None  # uzivatel dialog zrusil - nic nevytvarime

        from gl3fc.gl3_program import create as create_program

        name = self._object_name_from_file(source_file)
        library = self._find_single_library(doc)

        obj = create_program(doc, name, source_file, library=library)
        doc.recompute()

        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        return obj

    def _ask_source_file(self):
        widgets = self._qtwidgets()
        path, _selected_filter = widgets.QFileDialog.getOpenFileName(
            Gui.getMainWindow(),
            "Vyber .GL3 soubor (hlavni SUBRO programu)",
            "",
            "GL3 soubory (*.GL3 *.gl3);;Vsechny soubory (*)",
        )
        return path or None

    @staticmethod
    def _qtwidgets():
        """FreeCAD 1.0+ pouziva PySide6, starsi 0.2x PySide2 (a velmi stare
        jeste PySide/QtGui) - zkusit postupne, at prikaz funguje napric
        verzemi bez natvrdo zavisleho importu."""
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtGui as QtWidgets
        return QtWidgets

    @staticmethod
    def _object_name_from_file(source_file):
        """Interni Name objektu odvozeny ze jmena souboru (jen pro tree/
        Python konzoli - nemusi sedet na skutecne jmeno SUBRO uvnitr,
        to se overuje az v execute()). FreeCAD Name nesmi mit mezery/
        specialni znaky, proto sanitizace."""
        stem = os.path.splitext(os.path.basename(source_file))[0]
        safe = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in stem)
        return safe or "GL3Program"

    @staticmethod
    def _find_single_library(doc):
        libraries = [
            o
            for o in doc.Objects
            if getattr(getattr(o, "Proxy", None), "Type", None) == "GL3Library"
        ]
        return libraries[0] if len(libraries) == 1 else None

    def IsActive(self):
        return True


Gui.addCommand("NEG_CreateProgram", CreateGL3ProgramCommand())
