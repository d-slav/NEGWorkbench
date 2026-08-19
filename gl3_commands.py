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


def _exec_dialog(dialog):
    """Qt QDialog.exec() (PySide6/novejsi PySide2) vs. starsi .exec_()
    (exec byl v Pythonu 2 rezervovane slovo, nektere starsi bindingy si
    tenhle nazev drzely i po prechodu na Python 3) - zkusit postupne."""
    if hasattr(dialog, "exec"):
        return dialog.exec()
    return dialog.exec_()


def _last_dir_param():
    """FreeCAD parametr pro zapamatovani posledne pouziteho adresare pri
    vyberu .GL3 souboru - na rozdil od App::PropertyPath na objektu
    (ta by platila jen pro TENHLE konkretni objekt) prezije zavreni
    FreeCADu a sdili se napric vsemi vytvorenymi GL3Program objekty."""
    return App.ParamGet("User parameter:BaseApp/Preferences/Mod/NEGWorkbench")


def _get_last_source_dir():
    """Naposledy pouzity adresar pro vyber .GL3 souboru (prazdny retezec,
    pokud jeste zadny nebyl vybran - QFileDialog to bere jako 'vychozi
    adresar OS')."""
    return _last_dir_param().GetString("LastGL3SourceDir", "")


def _set_last_source_dir(directory):
    """Zapamatuje 'directory' jako vychozi pro pristi vyber .GL3 souboru.
    Prazdny/None vstup se ignoruje (napr. kdyz uzivatel dialog zrusil)."""
    if directory:
        _last_dir_param().SetString("LastGL3SourceDir", directory)


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
            _get_last_source_dir(),
            "GL3 soubory (*.GL3 *.gl3);;Vsechny soubory (*)",
        )
        if path:
            _set_last_source_dir(os.path.dirname(path))
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

        # Zpracovat cekajici Gui udalosti (vc. prekresleni stromu s novym
        # claimChildren() vysledkem) PRED vyberem noveho objektu - jinak se
        # muze stat, ze strom jeste nema Export zarazeny pod Program, kdyz
        # se ho pokusime vybrat, a polozka Program se tak neexpanduje.
        Gui.updateGui()

        # Explicitne rozbalit polozku Program ve strome, at je hned videt
        # novy Export jako jeho potomek (pouhy vyber noveho objektu strom
        # sam o sobe nerozbali). Std_TreeExpand je standardni FreeCAD
        # prikaz "rozbal vybrane polozky ve strome".
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(source)
        try:
            Gui.runCommand("Std_TreeExpand")
        except Exception:
            pass  # napr. headless/testovaci prostredi bez tohohle prikazu

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
        box = widgets.QMessageBox(Gui.getMainWindow())
        box.setWindowTitle("Výběr prvku pole")
        box.setText(
            "Výstup '%s' je pole (%d prvků). Exportovat jen jeden prvek "
            "místo celého pole?" % (output_name, len(items))
        )
        btn_one = box.addButton("Jeden prvek", widgets.QMessageBox.YesRole)
        btn_all = box.addButton("Celé pole", widgets.QMessageBox.NoRole)
        box.setDefaultButton(btn_all)
        _exec_dialog(box)
        if box.clickedButton() is not btn_one:
            return None

        index, ok = widgets.QInputDialog.getInt(
            Gui.getMainWindow(),
            "Index prvku",
            "Číslo prvku (1 = první, max %d):" % len(items),
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
        internich atributech Proxy - funguje i po znovunacteni dokumentu.

        Navic (na konci seznamu) 'Drawing', pokud je definovana (skryty
        retezec z INI...CLOSE - viz gl3_program.py) - je ve skupine
        "GL3" (ne "GL3 Out", protoze neni odvozena z SUBRO hlavicky), ale
        jde o stejny druh exportovatelneho vystupu, jen bez pojmenovaneho
        out: parametru."""
        names = []
        for prop_name in source.PropertiesList:
            try:
                group = source.getGroupOfProperty(prop_name)
                type_id = source.getTypeIdOfProperty(prop_name)
            except AttributeError:
                continue
            if group == "GL3 Out" and type_id == "App::PropertyString":
                names.append(prop_name)
        if hasattr(source, "Drawing"):
            try:
                if json.loads(source.Drawing).get("defined"):
                    names.append("Drawing")
            except (ValueError, TypeError, AttributeError):
                pass
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


class ReloadGL3ProgramCommand(object):
    """Prinuti vybrany GL3Program objekt znovu nacist a rozparsovat svuj
    SourceFile a projit _sync_properties() - i kdyz FreeCAD sam o sobe
    nema duvod si myslet, ze je objekt "touched" (zmena SOUBORU NA DISKU
    mimo FreeCAD, napr. pridani noveho in:/out: parametru do SUBRO
    hlavicky, se property SourceFile samotne netyka - jeji HODNOTA
    (cesta) zustava stejna, takze FreeCAD zadnou zmenu nezaznamena a
    execute() by se bez tohohle znovu nespustilo).

    Bez tohohle prikazu je jedina cesta, jak donutit FreeCAD znovu
    zavolat execute() po rucni editaci .GL3 souboru, rucni "Mark to
    recompute" (pravym tlacitkem na objekt ve strome) + Refresh - tohle
    je jen pohodlnejsi zkratka presne pro GL3Program."""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(_ICON_DIR, "program.svg"),
            "MenuText": QT_TRANSLATE_NOOP("NEG_ReloadProgram", "Reload GL3 Program"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "NEG_ReloadProgram",
                "Forces the selected GL3Program to re-read its SourceFile and "
                "re-sync in/out properties - use after editing the .GL3 file "
                "on disk (e.g. adding a new parameter) without needing to "
                "delete and recreate the object.",
            ),
        }

    def Activated(self):
        sel = Gui.Selection.getSelection()
        programs = [
            o
            for o in sel
            if getattr(getattr(o, "Proxy", None), "Type", None) == "GL3Program"
        ]
        if len(programs) != 1:
            App.Console.PrintError(
                "NEG_ReloadProgram: vyber v Model strome prave jeden GL3Program "
                "objekt (aktualne vybrano: %d).\n" % len(programs)
            )
            return None

        obj = programs[0]
        obj.touch()
        obj.Document.recompute()
        return obj

    def IsActive(self):
        return True


Gui.addCommand("NEG_ReloadProgram", ReloadGL3ProgramCommand())
