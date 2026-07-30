# -*- coding: utf-8 -*-
"""
test_props_offline.py - overuje, ze gl3_props.add_property() vola
setPropertyStatus(name, "-Hidden") POUZE PRI PRVNIM VYTVORENI property,
ne pri kazdem opakovanem volani (viz docstring v gl3_props.py).

Duvod: GL3Program._sync_properties() vola add_property() znovu pri
KAZDEM execute()/recompute. Pokud by se setPropertyStatus volalo
opakovane i na uz existujici property, hrozi (podle pozorovani na
realnem FreeCADu) prepnuti property zpet na Hidden po lichem poctu
volani - to se pak projevi jako "GL3 In" property zbytecne zluta v
Property View, i kdyz jde o bezne typy s vlastnim editorem
(PropertyFloat/-Integer/-FileIncluded), ktere by mely byt videt vzdy.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeObjRecordingStatus(object):
    """Minimalni FreeCAD-like objekt, ktery si navic pamatuje POCET
    volani setPropertyStatus na kazde jmeno property."""

    def __init__(self):
        self._status_calls = {}
        self._last_status = {}

    def addProperty(self, type_name, name, group=None, doc=None):
        setattr(self, name, None)
        return self

    def setPropertyStatus(self, name, status):
        self._status_calls[name] = self._status_calls.get(name, 0) + 1
        self._last_status.setdefault(name, []).append(status)


def main():
    from gl3fc.gl3_props import add_property

    obj = FakeObjRecordingStatus()

    # Simulace opakovanych recomputu (5x = lichy pocet, presne scenar,
    # kde se puvodni bug projevil) volajicich add_property() se stejnymi
    # argumenty pro tutez property - jako _sync_properties() pri kazdem
    # execute().
    for _ in range(5):
        add_property(obj, "App::PropertyFloat", "DH", "GL3 In", "GL3 in: DH")

    calls = obj._status_calls.get("DH", 0)
    print("setPropertyStatus('DH', ...) zavolano celkem %dx (pri 5 add_property() volanich)" % calls)
    assert calls == 1, (
        "setPropertyStatus se ma zavolat jen pri prvnim vytvoreni property, "
        "ne pri kazdem opakovanem add_property() volani - zavolano %dx" % calls
    )

    # Ruzne property se pochopitelne pocitaji zvlast.
    add_property(obj, "App::PropertyFloat", "J", "GL3 In", "GL3 in: J")
    assert obj._status_calls.get("J", 0) == 1
    assert obj._status_calls.get("DH", 0) == 1, "volani pro jinou property nesmi ovlivnit pocitadlo DH"

    print()
    print("VSE OK - add_property() nastavuje '-Hidden' status jen jednou na property.")

    # --- read_only=True (pro vypocitane "out" property, viz gl3_program.py) ---
    out_obj = FakeObjRecordingStatus()
    for _ in range(3):
        add_property(
            out_obj, "App::PropertyString", "PO", "GL3 Out", "GL3 out: PO", read_only=True
        )
    assert out_obj._status_calls.get("PO", 0) == 2, (
        "s read_only=True se ma setPropertyStatus zavolat 2x (jednou pro -Hidden, "
        "jednou pro ReadOnly), zavolano: %r" % (out_obj._status_calls.get("PO", 0),)
    )
    assert out_obj._last_status["PO"] == ["-Hidden", "ReadOnly"]
    print("read_only=True: OK - status '-Hidden' i 'ReadOnly' nastaveny presne jednou.")

    # bez read_only (default False) se ReadOnly vubec nevola
    in_obj = FakeObjRecordingStatus()
    add_property(in_obj, "App::PropertyFloat", "DH", "GL3 In", "GL3 in: DH")
    assert in_obj._last_status["DH"] == ["-Hidden"]
    print("read_only=False (default): OK - vola se jen '-Hidden'.")


if __name__ == "__main__":
    main()
