# -*- coding: utf-8 -*-
"""
gl3_library.py - GL3Library: FreeCAD objekt drzici seznam adresaru, kde se
hledaji SUBRO soubory volane pres CALL z GL3Program objektu (typ 2 z
diskuze - uzivatelem definovana SUBRO). Nenese zadnou geometrii ani
vlastni Placement - je to cisty "registr cest".

Format SearchPaths (PropertyStringList): prosty seznam retezcu
    ["/abs/cesta/k/adresari", ...]

Puvodne PropertyPythonObject s dvojici {"path":..., "hidden":...} -
zmeneno na PropertyStringList, protoze PropertyPythonObject nema v
Property View zadny editor (viz FreeCAD PR #3535/realthunder): property
bez editoru se nezobrazi vubec, dokud uzivatel nezapne "Show all", a i
pak je jen ke cteni - nejde ji z GUI nastavit. PropertyStringList ma
vestaveny editor (dvojklik otevre seznam radku), takze je videt a
editovatelna hned po vytvoreni objektu.

Priznak "hidden" (pro budouci systemova SUBRA, typ 3 z diskuze) timhle
zjednodusenim odpadl - az na to dojde, resit zvlast (napr. samostatna
property SystemSearchPaths, nebo UI dialog misto primeho Property View
editoru).

Editace kodu samotnych .GL3 souboru je v teto fazi projektu vyrizena
externe (bezny textovy editor na disku) - Library jen rika, KDE ty
soubory hledat; recompute Programu je znovu nacte ze souboru (viz
Gl3FileRegistry - zadny interni cache napric recompute, vzdy cerstve
cteni pri kazdem CALL, tzn. zmena souboru se projevi po pristim
recomputu bez nutnosti cokoliv rucne "reloadovat").
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3fc.gl3_registry import Gl3FileRegistry
from gl3fc.gl3_props import add_property, icon_path


def _default_search_dirs():
    """Vychozi adresare pro hledani CALL-ovatelnych SUBRO:
    <doplnek>/gl3sys      - systemove GL3 subrutiny (HLO, SCARA, HLOCUT...)
    <doplnek>/gl3examples - ukazkove programy (TEHLO, E374...), ktere
                            systemove subrutiny samy volaji.
    gl3test/ (interni testovaci programy pro Python regresni sadu) se
    zamerne NEnabizi jako vychozi - nejsou urcene pro bezne pouziti ve
    FreeCADu."""
    # tenhle soubor: <doplnek>/gl3/gl3fc/gl3_library.py
    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return [
        os.path.join(addon_dir, "gl3sys"),
        os.path.join(addon_dir, "gl3examples"),
    ]


class GL3Library(object):
    """Proxy pro App::FeaturePython objekt typu GL3Library."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "GL3Library"
        add_property(
            obj,
            "App::PropertyStringList",
            "SearchPaths",
            "GL3",
            "Seznam adresaru pro hledani <JMENO>.GL3 souboru",
        )
        if obj.SearchPaths is None:
            obj.SearchPaths = []
        if not obj.SearchPaths:
            default_dirs = [d for d in _default_search_dirs() if os.path.isdir(d)]
            if default_dirs:
                obj.SearchPaths = default_dirs

    def add_path(self, obj, path):
        entries = list(obj.SearchPaths or [])
        entries.append(path)
        obj.SearchPaths = entries

    def build_registry(self, obj, extra=None):
        """Vrati Gl3FileRegistry pripraveny k pouziti jako Interpreter(registry=...)."""
        entries = list(obj.SearchPaths or [])
        return Gl3FileRegistry(search_entries=entries, extra=extra)

    def execute(self, obj):
        # Library sama o sobe nic nepocita, jen drzi data.
        pass

    def onDocumentRestored(self, obj):
        self.Type = "GL3Library"


class ViewProviderGL3Library(object):
    """Minimalni ViewProvider - jedina vlastni veci je ikona ve stromu
    (viz getIcon()), stejna jako v toolbaru/menu. GL3Library nenese
    zadnou geometrii, takze zadne dalsi View chovani neresi."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return icon_path("library.svg")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def create(doc, name="GL3Library"):
    """Pomocna funkce pro vytvoreni GL3Library objektu v danem dokumentu."""
    obj = doc.addObject("App::FeaturePython", name)
    GL3Library(obj)
    if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        ViewProviderGL3Library(obj.ViewObject)
        obj.ViewObject.Visibility = True
    return obj
