# -*- coding: utf-8 -*-
"""
test_gl3_export_offline.py - overuje GL3Export.execute() (ne jen
build_shape() jako test_export_offline.py) proti FAKE Source objektu.

Krome puvodniho JSON-text parsovani (viz gl3_program.py PropertyString
vystupy) tenhle test hlavne overuje novy format reference: Input je
JEDNA textova property 'JmenoObjektu.JmenoVystupu' (napr. 'TEHLO001.S'),
pod kapotou drzena synchronizovana se skrytym Linkem "Source" pres
onChanged() - viz gl3_props.py/gl3_export.py modulove docstringy.

FakeExportObj proto (na rozdil od jednodussich testu jinde v projektu)
simuluje realne FreeCAD chovani, kdy kazde nastaveni property
(`obj.Input = ...`) automaticky zavola Proxy.onChanged(obj, name) -
presne to je mechanismus, ktery drzi skryty Link aktualni JESTE PRED
recompute (viz gl3_props.py).
"""
import sys
import os
import types
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- stejne lehke FreeCAD/Part stuby jako v test_export_offline.py ---

class FakeVector(object):
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __add__(self, other):
        return FakeVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return FakeVector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return FakeVector(self.x * scalar, self.y * scalar, self.z * scalar)


class FakeBSplineCurve(object):
    def buildFromPolesMultsKnots(self, poles, mults, knots, periodic, degree):
        self.poles = list(poles)

    def toShape(self):
        return ("BSplineEdge", self.poles)


fake_freecad = types.ModuleType("FreeCAD")
fake_freecad.Vector = FakeVector

fake_part = types.ModuleType("Part")
fake_part.BezierCurve = None
fake_part.BSplineCurve = FakeBSplineCurve
fake_part.Circle = None
fake_part.Vertex = lambda v: ("Vertex", v)
fake_part.makeCompound = lambda shapes: ("Compound", shapes)
fake_part.makeLine = lambda a, b: ("LineEdge", a, b)
fake_part.Wire = lambda edges: ("Wire", edges)

sys.modules["FreeCAD"] = fake_freecad
sys.modules["Part"] = fake_part

from gl3fc.gl3_export import GL3Export, create as create_export  # noqa: E402


class FakeDocument(object):
    """Jen tolik, kolik _resync_source() potrebuje: jmenny prostor objektu."""

    def __init__(self):
        self._objects = {}
        self._counter = 0
        self.recompute_calls = 0

    def register(self, obj):
        self._objects[obj.Name] = obj
        return obj

    def getObject(self, name):
        return self._objects.get(name)

    def recompute(self):
        self.recompute_calls += 1

    def addObject(self, type_name, name):
        self._counter += 1
        obj = FakeExportObj("%s%03d" % (name, self._counter), document=self)
        return self.register(obj)


class FakeSource(object):
    """Minimalni nahrada za GL3Program objekt - jen to, co execute() cte."""

    def __init__(self, name="TEHLO001"):
        self.Name = name
        self.Placement = "PLACEMENT_STUB"
        self._touched = False

    def touch(self):
        self._touched = True


class FakeExportObj(object):
    """Na rozdil od FakeSource/jinych fake objektu v projektu SIMULUJE
    realne FreeCAD chovani: kazde nastaveni property zavola
    Proxy.onChanged(self, name) - presne mechanismus, na kterem stoji
    synchronizace skryteho Linku "Source" (viz modulovy docstring)."""

    def __init__(self, name="Export001", document=None):
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "Document", document)
        object.__setattr__(self, "Proxy", None)
        object.__setattr__(self, "Source", None)
        object.__setattr__(self, "Input", None)
        object.__setattr__(self, "Shape", None)
        object.__setattr__(self, "Placement", None)
        object.__setattr__(self, "ViewObject", None)
        object.__setattr__(self, "_status_calls", {})

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, None)
        return self

    def setPropertyStatus(self, name, status):
        self._status_calls.setdefault(name, []).append(status)

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        proxy = object.__getattribute__(self, "Proxy")
        if proxy is not None and name != "Proxy" and hasattr(proxy, "onChanged"):
            proxy.onChanged(self, name)


def _valid_spline_json():
    # minimalni, ale platny Spline slot (2 body, spolecne tecny) - viz
    # gerlib.serialize / test_export_offline.py pro plny format
    return json.dumps(
        {
            "defined": True,
            "type": "Spline",
            "closed": False,
            "points": {
                "defined": True,
                "type": "Array",
                "items": [
                    {"defined": True, "type": "Point", "x": 0.0, "y": 0.0, "z": 0.0},
                    {"defined": True, "type": "Point", "x": 1.0, "y": 1.0, "z": 0.0},
                ],
            },
            "tangents": {
                "defined": True,
                "type": "Array",
                "items": [
                    {"defined": True, "type": "Vector", "x": 1.0, "y": 0.0, "z": 0.0},
                    {"defined": True, "type": "Vector", "x": 1.0, "y": 0.0, "z": 0.0},
                ],
            },
        }
    )


def main():
    # --- 1) uspesny pripad: platny JSON text (jak ho uklada GL3Program) ---
    doc = FakeDocument()
    source = doc.register(FakeSource("TEHLO001"))
    source.S = _valid_spline_json()

    obj = FakeExportObj("Export001", document=doc)
    exp = GL3Export(obj)
    assert obj._status_calls.get("Placement") == ["Hidden"], (
        "Placement je 100% odvozeny ze Source (execute() ho pokazde prepise) - "
        "ma byt skryty, at nepusobi zdanlive editovatelne"
    )
    obj.Input = "TEHLO001.S"  # -> onChanged() hned vyresolvuje Source

    assert obj.Source is source, (
        "Source se ma vyresolvovat AUTOMATICKY pres onChanged() hned pri "
        "nastaveni Input, jeste pred execute()"
    )

    exp.execute(obj)
    assert obj.Shape is not None
    assert obj.Placement == "PLACEMENT_STUB", "Export ma prevzit Placement ze Source 1:1"
    assert not source._touched, (
        "execute() uz NEMA volat source.touch() - to se presunulo do create() "
        "(zavolane JEDNOU pred prvnim recomputem), aby FreeCAD nehlasil "
        "'still touched after recompute' (Source touchnuty UPROSTRED "
        "prave probihajiciho recompute)"
    )
    print("execute() s platnym JSON textem: OK - Source vyresolven, Shape vytvoren, "
          "Placement v poradku (a zadne 'still touched' - touch() se nevola tady)")

    # --- 2) property neni retezec (napr. nekdo omylem napoji scalar out) ---
    doc2 = FakeDocument()
    source2 = doc2.register(FakeSource("PROG002"))
    source2.J = 42  # scalar out, ne composite

    obj2 = FakeExportObj("Export002", document=doc2)
    exp2 = GL3Export(obj2)
    obj2.Input = "PROG002.J"

    try:
        exp2.execute(obj2)
        raise AssertionError("mel vyhodit ValueError - property neni retezec")
    except ValueError as e:
        assert "neni retezec" in str(e)
        print("execute() na ne-retezcove property: OK - jasna chyba (%s)" % e)

    # --- 3) property je retezec, ale neplatny JSON ---
    doc3 = FakeDocument()
    source3 = doc3.register(FakeSource("PROG003"))
    source3.S = "{neplatny json"

    obj3 = FakeExportObj("Export003", document=doc3)
    exp3 = GL3Export(obj3)
    obj3.Input = "PROG003.S"

    try:
        exp3.execute(obj3)
        raise AssertionError("mel vyhodit ValueError - neplatny JSON")
    except ValueError as e:
        assert "neni platny JSON" in str(e)
        print("execute() na neplatnem JSON textu: OK - jasna chyba (%s)" % e)

    # --- 4) vystupni property neexistuje na Source ---
    doc4 = FakeDocument()
    source4 = doc4.register(FakeSource("PROG004"))

    obj4 = FakeExportObj("Export004", document=doc4)
    exp4 = GL3Export(obj4)
    obj4.Input = "PROG004.NEEXISTUJE"

    try:
        exp4.execute(obj4)
        raise AssertionError("mel vyhodit ValueError - property neexistuje")
    except ValueError as e:
        assert "nema property" in str(e)
        print("execute() na neexistujici property: OK - jasna chyba (%s)" % e)

    # --- 5) Input bez tecky (spatny format reference) ---
    doc5 = FakeDocument()
    obj5 = FakeExportObj("Export005", document=doc5)
    exp5 = GL3Export(obj5)
    obj5.Input = "spatnyformat"

    try:
        exp5.execute(obj5)
        raise AssertionError("mel vyhodit ValueError - spatny format reference")
    except ValueError as e:
        assert "musi byt ve formatu" in str(e)
        print("execute() se spatnym formatem Input: OK - jasna chyba (%s)" % e)

    # --- 6) Input s indexem '(N)' na Array vystupu - uspesny pripad ---
    doc7 = FakeDocument()
    source7 = doc7.register(FakeSource("TEHLO007"))
    source7.PO = json.dumps(
        {
            "defined": True,
            "type": "Array",
            "items": [
                {"defined": True, "type": "Point", "x": 0.0, "y": 0.0, "z": 0.0},
                {"defined": True, "type": "Point", "x": 5.0, "y": 6.0, "z": 0.0},
                {"defined": True, "type": "Point", "x": 9.0, "y": 9.0, "z": 0.0},
            ],
        }
    )

    obj7 = FakeExportObj("Export007", document=doc7)
    exp7 = GL3Export(obj7)
    obj7.Input = "TEHLO007.PO(2)"  # 1 = prvni prvek -> (2) je stredni bod

    exp7.execute(obj7)
    assert obj7.Shape is not None
    print("execute() s indexem 'PO(2)' na Array vystupu: OK - Shape z 2. prvku vytvoren")

    # --- 7) index mimo rozsah pole ---
    obj7b = FakeExportObj("Export007b", document=doc7)
    exp7b = GL3Export(obj7b)
    obj7b.Input = "TEHLO007.PO(99)"

    try:
        exp7b.execute(obj7b)
        raise AssertionError("mel vyhodit ValueError - index mimo rozsah")
    except ValueError as e:
        assert "mimo rozsah" in str(e)
        print("execute() s indexem mimo rozsah: OK - jasna chyba (%s)" % e)

    # --- 8) index pouzity na vystup, ktery neni Array ---
    obj9 = FakeExportObj("Export009", document=doc7)
    exp9 = GL3Export(obj9)
    obj9.Input = "TEHLO007.PO(1)"
    # nejdriv normalne (bez indexu) - jen se ujistit, ze PO(1) na Array funguje
    exp9.execute(obj9)
    assert obj9.Shape is not None

    doc9b = FakeDocument()
    source9b = doc9b.register(FakeSource("TEHLO009"))
    source9b.S = _valid_spline_json()  # Spline, ne Array

    obj9b = FakeExportObj("Export009b", document=doc9b)
    exp9b = GL3Export(obj9b)
    obj9b.Input = "TEHLO009.S(1)"

    try:
        exp9b.execute(obj9b)
        raise AssertionError("mel vyhodit ValueError - index na ne-Array vystupu")
    except ValueError as e:
        assert "lze pouzit jen na Array" in str(e)
        print("execute() s indexem na ne-Array vystupu: OK - jasna chyba (%s)" % e)

    # --- 9) Input odkazuje na objekt, ktery v dokumentu neexistuje ---
    doc6 = FakeDocument()
    obj6 = FakeExportObj("Export006", document=doc6)
    exp6 = GL3Export(obj6)
    obj6.Input = "NEEXISTUJICI.S"

    assert obj6.Source is None, "neexistujici objekt -> Source ma zustat None"
    try:
        exp6.execute(obj6)
        raise AssertionError("mel vyhodit ValueError - zdrojovy objekt neexistuje")
    except ValueError as e:
        assert "neexistuje" in str(e)
        print("execute() s neexistujicim zdrojovym objektem: OK - jasna chyba (%s)" % e)

    # --- 10) create() (ne execute()) je to, co ma touchnout Source - JEDNOU,
    # driv, nez volajici stihne zavolat prvni doc.recompute() (viz komentar
    # v gl3_export.create()) ---
    doc10 = FakeDocument()
    source10 = doc10.register(FakeSource("TEHLO010"))
    source10.PO = json.dumps(
        {"defined": True, "type": "Array", "items": [
            {"defined": True, "type": "Point", "x": 0.0, "y": 0.0, "z": 0.0},
        ]}
    )
    assert not source10._touched
    export10 = create_export(doc10, "Export010", source10, "PO")
    assert source10._touched, "create() ma touchnout Source JEDNOU, pred prvnim recomputem"
    assert export10.Input == "TEHLO010.PO"
    print("create(): OK - touchne Source presne jednou, pred vracenim noveho objektu")

    print()
    print("VSE OK - GL3Export.execute() spravne resolvuje 'Objekt.Vystup' referenci")
    print("(pres onChanged() synchronizovany skryty Link) a cte JSON text z vystupu.")


if __name__ == "__main__":
    main()
