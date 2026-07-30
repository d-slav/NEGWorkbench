# -*- coding: utf-8 -*-
"""
gl3_props.py - sdileny helper pro pridavani property na FeaturePython
objekty v GL3Library/GL3Program/GL3Export.

Duvod existence: v realnem FreeCADu se ukazalo, ze nove pridane property
(pres obj.addProperty(...)) nebyly v Property editoru videt, dokud
uzivatel nezapnul "Show hidden" - i kdyz addProperty() bylo volano se
standardnimi (nehidden) argumenty. Tahle funkce proto po pridani property
jeste explicitne zavola setPropertyStatus(name, "-Hidden"), aby se na
defaultu FreeCADu/verzi nemuselo spolehat.

POZOR: tohle NEPOMUZE u property typu, ktere v Property View nemaji zadny
editor (napr. App::PropertyPythonObject, App::PropertyVectorList) - takove
property se nezobrazi vubec, dokud uzivatel nezapne "Show all", a i pak
jsou jen ke cteni, bez ohledu na "-Hidden" (viz FreeCAD PR #3535,
realthunder). Pro cokoliv, co ma byt v Property View editovatelne hned po
vytvoreni, pouzij typ s vestavenym editorem (PropertyString, -Float,
-Bool, -StringList, ...).
"""


def add_property(obj, type_name, name, group, doc):
    """Prida property (pokud jeste neexistuje) a zajisti, ze neni skryta."""
    if not hasattr(obj, name):
        obj.addProperty(type_name, name, group, doc)
    try:
        obj.setPropertyStatus(name, "-Hidden")
    except AttributeError:
        pass  # starsi FreeCAD bez setPropertyStatus - neni kriticke
    return obj
