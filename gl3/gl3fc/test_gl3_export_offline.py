# -*- coding: utf-8 -*-
"""
test_gl3_export_offline.py - overuje GL3Export.execute() (ne jen
build_shape() jako test_export_offline.py) proti FAKE Source objektu,
jehoz composite "out" property jsou (jak je od GL3Program ocekavano)
retezce se skutecnym JSON textem - viz gl3_program.py/_store_outputs().

Tenhle test predevsim hlida prave prechod PropertyPythonObject (holy
dict) -> PropertyString (JSON text) v execute(): json.loads() se musi
zavolat spravne a chybove hlasky u nevalidnich vstupu musi zustat
citelne.
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

from gl3fc.gl3_export import GL3Export  # noqa: E402


class FakeSource(object):
    """Minimalni nahrada za GL3Program objekt - jen to, co execute() cte."""

    def __init__(self, name="TEHLO001"):
        self.Name = name
        self.Placement = "PLACEMENT_STUB"
        self._touched = False

    def touch(self):
        self._touched = True


class FakeExportObj(object):
    def __init__(self, name="Export001"):
        self.Name = name
        self.Source = None
        self.OutputName = None
        self.Shape = None
        self.Placement = None
        self.ViewObject = None


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
    source = FakeSource()
    source.S = _valid_spline_json()

    obj = FakeExportObj()
    exp = GL3Export(obj)
    obj.Source = source
    obj.OutputName = "S"

    exp.execute(obj)
    assert obj.Shape is not None
    assert obj.Placement == "PLACEMENT_STUB", "Export ma prevzit Placement ze Source 1:1"
    assert source._touched, "execute() ma zavolat source.touch() (kvuli claimChildren refresh)"
    print("execute() s platnym JSON textem: OK - Shape vytvoren, Placement/touch() v poradku")

    # --- 2) property neni retezec (napr. nekdo omylem napoji scalar out) ---
    source2 = FakeSource()
    source2.J = 42  # scalar out, ne composite

    obj2 = FakeExportObj()
    exp2 = GL3Export(obj2)
    obj2.Source = source2
    obj2.OutputName = "J"

    try:
        exp2.execute(obj2)
        raise AssertionError("mel vyhodit ValueError - property neni retezec")
    except ValueError as e:
        assert "neni retezec" in str(e)
        print("execute() na ne-retezcove property: OK - jasna chyba (%s)" % e)

    # --- 3) property je retezec, ale neplatny JSON ---
    source3 = FakeSource()
    source3.S = "{neplatny json"

    obj3 = FakeExportObj()
    exp3 = GL3Export(obj3)
    obj3.Source = source3
    obj3.OutputName = "S"

    try:
        exp3.execute(obj3)
        raise AssertionError("mel vyhodit ValueError - neplatny JSON")
    except ValueError as e:
        assert "neni platny JSON" in str(e)
        print("execute() na neplatnem JSON textu: OK - jasna chyba (%s)" % e)

    # --- 4) OutputName neexistuje na Source ---
    source4 = FakeSource()
    obj4 = FakeExportObj()
    exp4 = GL3Export(obj4)
    obj4.Source = source4
    obj4.OutputName = "NEEXISTUJE"

    try:
        exp4.execute(obj4)
        raise AssertionError("mel vyhodit ValueError - property neexistuje")
    except ValueError as e:
        assert "nema property" in str(e)
        print("execute() na neexistujici property: OK - jasna chyba (%s)" % e)

    print()
    print("VSE OK - GL3Export.execute() spravne cte JSON text z composite 'out' property.")


if __name__ == "__main__":
    main()
