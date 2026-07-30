# -*- coding: utf-8 -*-
"""
Offline test GL3Library/GL3Program bez skutecneho FreeCADu.

Simuluje presne to, co by FreeCAD udelal:
  1. vytvoreni objektu (Proxy.__init__ prida SourceFile/Library property)
  2. 1. recompute - jeste bez vyplnenych vstupu -> vytvori se in:/out:
     property s vychozimi hodnotami (BJM='', DH=0.0)
  3. uzivatel nastavi realne vstupy (BJM=cesta k E374.TXT, DH=15.2)
  4. 2. recompute - skutecny beh interpretu, PO/S se naplni

Overuje se: dynamicke vlastnosti sedi na SUBRO hlavicku, CALL/HLO se
rozresi pres GL3Library (adresar 'examples/'), a vysledek (PO, S) sedi
na uz drive overena data z gl3_test.py / proto_bezier_export.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


_TYPE_DEFAULTS = {
    "App::PropertyFloat": 0.0,
    "App::PropertyInteger": 0,
    "App::PropertyFileIncluded": "",
    "App::PropertyFile": "",
    "App::PropertyLink": None,
    "App::PropertyPythonObject": None,
    "App::PropertyStringList": [],
}


class FakeObj(object):
    """Minimalni napodobenina FreeCAD DocumentObject - jen addProperty +
    obycejne atributy, presne tolik, kolik GL3Program/GL3Library potrebuji."""

    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self._prop_types = {}

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        return self


def main():
    from gl3fc.gl3_library import GL3Library
    from gl3fc.gl3_program import GL3Program

    examples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples"))

    # --- GL3Library ---
    lib_obj = FakeObj("GL3Library")
    GL3Library(lib_obj)
    # GL3Library.__init__ uz sam predvyplni SearchPaths na dodavany
    # gl3/examples adresar (viz _default_examples_dir), takze rucni
    # add_path() tu neni potreba - jen si to overime:
    assert lib_obj.SearchPaths == [examples_dir], (
        "ocekavan vychozi SearchPaths = [%r], je: %r" % (examples_dir, lib_obj.SearchPaths)
    )
    print("Library.SearchPaths =", lib_obj.SearchPaths)

    # --- GL3Program (TEHLO) ---
    prog = FakeObj("TEHLO_Program")
    GL3Program(prog)
    prog.SourceFile = os.path.join(examples_dir, "TEHLO.GL3")
    prog.Library = lib_obj

    # 1. recompute - BJM/DH jeste na vychozich hodnotach ("" / 0.0). Schema
    # property se presto vytvori (sync_properties probehne pred interp.run()),
    # ale samotny beh spadne na IDEV, dokud BJM neukazuje na skutecny soubor -
    # presne tak by se zachoval i realny FreeCAD objekt (cervena chyba, dokud
    # uzivatel nevyplni povinny vstup).
    try:
        prog.Proxy.execute(prog)
        raised = False
    except OSError:
        raised = True
    print("Po 1. recompute (bez vyplnenych vstupu): ocekavana chyba =", raised)
    assert raised, "ocekavana OSError z IDEV na prazdnem BJM"

    print("  BJM =", repr(prog.BJM), " DH =", prog.DH)
    print("  ma PO?", hasattr(prog, "PO"), " ma S?", hasattr(prog, "S"))
    assert hasattr(prog, "BJM") and hasattr(prog, "DH")
    assert hasattr(prog, "PO") and hasattr(prog, "S")
    assert prog._prop_types["S"] == "App::PropertyPythonObject"
    assert prog._prop_types["PO"] == "App::PropertyPythonObject"
    assert prog._prop_types["DH"] == "App::PropertyFloat"

    # 2. uzivatel nastavi vstupy
    prog.BJM = os.path.join(examples_dir, "E374.TXT")
    prog.DH = 15.2

    # 3. skutecny recompute
    prog.Proxy.execute(prog)

    print("Po 2. recompute:")
    print("  PO['defined'] =", prog.PO["defined"], " pocet bodu =", len(prog.PO["items"]))
    print("  S['defined']  =", prog.S["defined"], " typ =", prog.S["type"])

    assert prog.PO["defined"] is True
    assert prog.PO["type"] == "Array"
    assert len(prog.PO["items"]) == 35

    assert prog.S["defined"] is True
    assert prog.S["type"] == "Spline"
    assert prog.S["points"]["defined"] is True
    assert len(prog.S["points"]["items"]) == 35

    # posledni bod PO musi sedet na drive overenou hodnotu (15.2, 0.0)
    last_point_slot = prog.PO["items"][-1]
    assert last_point_slot["defined"] is True
    x = last_point_slot["x"]
    y = last_point_slot["y"]
    assert abs(x - 15.2) < 1e-9 and abs(y - 0.0) < 1e-9, (x, y)

    print()
    print("VSE OK - GL3Program.execute() spravne generuje property, resolvuje")
    print("CALL/HLO pres GL3Library, a vystup sedi na jiz overena data.")


if __name__ == "__main__":
    main()
