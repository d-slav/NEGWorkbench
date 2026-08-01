# -*- coding: utf-8 -*-
"""
gl3_commands.py - Gui.Command definice pro NEGWorkbench.

Zatim: vytvoreni GL3Library, GL3Program a GL3Export objektu. Dalsi
prikazy (editace Library pres UI dialog, ...) pribudou postupne az
bude tenhle krok spolehlive fungovat (viz README.md).
"""

import os
import sys
import json

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


def _qtwidgets():
    """FreeCAD 1.0+ pouziva PySide6, starsi 0.2x PySide2 (a velmi stare
    jeste PySide/QtGui) - zkusit postupne, at prikazy funguji napric
    verzemi bez natvrdo zavisleho importu."""
    try:
        from PySide6 import QtWidgets
    except ImportError:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            from PySide import QtGui as QtWidgets
    return QtWidgets


def _sanitize_name(text, fallback):
    """FreeCAD interni Name nesmi mit mezery/specialni znaky - jen
    alnum/podtrzitko, jinak fallback."""
    safe = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in text)
    return safe or fallback


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
        widgets = _qtwidgets()
        path, _selected_filter = widgets.QFileDialog.getOpenFileName(
            Gui.getMainWindow(),
            "Vyber .GL3 soubor (hlavni SUBRO programu)",
            "",
            "GL3 soubory (*.GL3 *.gl3);;Vsechny soubory (*)",
        )
        return path or None

    @staticmethod
    def _object_name_from_file(source_file):
        """Interni Name objektu odvozeny ze jmena souboru (jen pro tree/
        Python konzoli - nemusi sedet na skutecne jmeno SUBRO uvnitr,
        to se overuje az v execute())."""
        stem = os.path.splitext(os.path.basename(source_file))[0]
        return _sanitize_name(stem, fallback="GL3Program")

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


class CreateGL3ExportCommand(object):
    """Vytvori novy GL3Export objekt (viz gl3fc/gl3_export.py) z composite
    "out" vystupu prave jednoho vybraneho GL3Program objektu ve strome.

    Vyzaduje, aby byl v Model strome vybrany (Gui.Selection) prave jeden
    GL3Program objekt. Pokud ma vic nez jeden composite vystup (napr. PO
    i S soucasne), zepta se dialogem, ktery z nich exportovat; pri jednom
    vystupu se pouzije rovnou bez ptani."""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(_ICON_DIR, "create_export.svg"),
            "MenuText": QT_TRANSLATE_NOOP("NEG_CreateExport", "Create GL3 Export"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "NEG_CreateExport",
                "Creates a new GL3Export object from a composite output of the "
                "selected GL3Program - converts it into a native Part shape.",
            ),
        }

    def Activated(self):
        source = self._find_selected_program()
        if source is None:
            return None

        outputs = self._composite_outputs(source)
        if not outputs:
            App.Console.PrintError(
                "NEG_CreateExport: GL3Program '%s' nema zadny composite 'out' "
                "vystup (skupina 'GL3 Out') k exportu.\n" % source.Name
            )
            return None

        if len(outputs) == 1:
            output_name = outputs[0]
        else:
            output_name = self._ask_output_name(outputs)
            if output_name is None:
                return None  # uzivatel dialog zrusil - nic nevytvarime

        from gl3fc.gl3_export import create as create_export

        index = self._maybe_ask_array_index(source, output_name)

        doc = source.Document
        name = _sanitize_name("%s_%s" % (source.Name, output_name), fallback="GL3Export")

        obj = create_export(doc, name, source, output_name, index=index)
        doc.recompute()

        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        return obj

    @staticmethod
    def _maybe_ask_array_index(source, output_name):
        """Pokud je vybrany vystup typu Array, zepta se uzivatele, jestli
        chce exportovat jen jeden jeho prvek (viz gl3_props.py - format
        reference s indexem '(N)') - rovnou pri vytvareni, at neni nutne
        Input dodatecne rucne prepisovat v Property View."""
        try:
            slot = json.loads(getattr(source, output_name))
        except (ValueError, TypeError):
            return None  # neplatny/prazdny JSON - necha se to spadnout az na execute()
        if not (isinstance(slot, dict) and slot.get("type") == "Array"):
            return None
        items = slot.get("items", [])
        if not items:
            return None

        widgets = _qtwidgets()
        choice = widgets.QMessageBox.question(
            Gui.getMainWindow(),
            "Vyber prvku pole",
            "Vystup '%s' je pole (%d prvku). Exportovat jen jeden konkretni "
            "prvek misto cele pole?" % (output_name, len(items)),
            widgets.QMessageBox.Yes | widgets.QMessageBox.No,
            widgets.QMessageBox.No,
        )
        if choice != widgets.QMessageBox.Yes:
            return None

        index, ok = widgets.QInputDialog.getInt(
            Gui.getMainWindow(),
            "Index prvku",
            "Cislo prvku (1 = prvni, max %d):" % len(items),
            1, 1, len(items), 1,
        )
        return index if ok else None

    @staticmethod
    def _find_selected_program():
        sel = Gui.Selection.getSelection()
        programs = [
            o
            for o in sel
            if getattr(getattr(o, "Proxy", None), "Type", None) == "GL3Program"
        ]
        if len(programs) != 1:
            App.Console.PrintError(
                "NEG_CreateExport: vyber v Model strome prave jeden GL3Program "
                "objekt (aktualne vybrano: %d).\n" % len(programs)
            )
            return None
        return programs[0]

    @staticmethod
    def _composite_outputs(source):
        """Jmena property ve skupine 'GL3 Out' typu App::PropertyString -
        presne takhle GL3Program uklada composite vystupy (JSON text, viz
        gl3_program.py). Cte se jen z verejneho FC API (PropertiesList +
        getGroupOfProperty/getTypeIdOfProperty), zadna zavislost na
        internich atributech Proxy - funguje i po znovunacteni dokumentu."""
        names = []
        for prop_name in source.PropertiesList:
            try:
                group = source.getGroupOfProperty(prop_name)
                type_id = source.getTypeIdOfProperty(prop_name)
            except AttributeError:
                continue
            if group == "GL3 Out" and type_id == "App::PropertyString":
                names.append(prop_name)
        return names

    @staticmethod
    def _ask_output_name(outputs):
        widgets = _qtwidgets()
        item, ok = widgets.QInputDialog.getItem(
            Gui.getMainWindow(),
            "Vyber vystup k exportu",
            "Composite vystup (GL3 Out):",
            outputs,
            0,
            False,
        )
        return item if ok else None

    def IsActive(self):
        return True


Gui.addCommand("NEG_CreateExport", CreateGL3ExportCommand())
