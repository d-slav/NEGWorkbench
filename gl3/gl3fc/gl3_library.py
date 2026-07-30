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
from gl3fc.gl3_props import add_property


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


def create(doc, name="GL3Library"):
    """Pomocna funkce pro vytvoreni GL3Library objektu v danem dokumentu."""
    obj = doc.addObject("App::FeaturePython", name)
    GL3Library(obj)
    if getattr(obj, "ViewObject", None) is not None:
        obj.ViewObject.Visibility = True
    return obj
