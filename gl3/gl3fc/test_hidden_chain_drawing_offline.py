# -*- coding: utf-8 -*-
"""
test_hidden_chain_drawing_offline.py - overuje, ze GL3Program.execute()
uklada vysledny "skryty retezec" (viz Interpreter.hidden_chain, INI/
CLOSE) do vzdy pritomne property 'Drawing' (JSON slot text, stejny
format jako ostatni composite out: vystupy - viz gerlib.serialize), a
ze GL3Export z ni umi postavit Shape (pres uz existujici build_shape(),
Curve->Wire).

Dve situace:
  1. program, ktery NIC nekresli -> Drawing = {"defined": false} (zadna
     chyba pri execute()), GL3Export na tenhle vystup napojeny hlasi
     STEJNOU, uz existujici chybu jako u kteregokoliv jineho
     nedefinovaneho vystupu.
  2. program, ktery kresli INI...CLOSE (vc. vnoreneho CALL, jehoz
     skryty retezec se pripoji) -> Drawing = platny Curve JSON,
     GL3Export postavi Wire se spravnymi body.
"""
import json
import os
import sys
import tempfile

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
    """Stejna minimalni napodobenina FreeCAD DocumentObject jako v
    test_offline.py."""

    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self._prop_types = {}
        self._prop_groups = {}

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        self._prop_groups[name] = group
        return self

    def removeProperty(self, name):
        if hasattr(self, name):
            delattr(self, name)
        self._prop_types.pop(name, None)
        self._prop_groups.pop(name, None)
        return True

    @property
    def PropertiesList(self):
        return list(self._prop_types.keys())

    def getGroupOfProperty(self, name):
        return self._prop_groups.get(name)

    def getTypeIdOfProperty(self, name):
        return self._prop_types.get(name)


def _write_gl3(tmpdir, filename, source):
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    return path


def main():
    from gl3fc.gl3_program import GL3Program

    tmpdir = tempfile.mkdtemp(prefix="gl3_hidden_chain_test_")

    # --- 1) program bez kresleni -> Drawing je nedefinovany, zadna chyba ---
    src_nodraw = """
SUBRO/TNODRAW/out:DM
DM=1.0
RETSUB
END
"""
    path_nodraw = _write_gl3(tmpdir, "TNODRAW.GL3", src_nodraw)
    prog_nodraw = FakeObj("PROG_NODRAW")
    GL3Program(prog_nodraw)
    prog_nodraw.SourceFile = path_nodraw
    prog_nodraw.Proxy.execute(prog_nodraw)

    drawing_slot = json.loads(prog_nodraw.Drawing)
    assert drawing_slot == {"defined": False}, drawing_slot
    print("Program bez kresleni: Drawing = {'defined': False}, zadna chyba: OK")

    # --- 2) program, ktery kresli (INI/MOVE/CLOSE) ---
    src_draw = """
SUBRO/TDRAW/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
INI
MOVE/P1
MOVE*P2*P3
CLOSE
DM=1.0
RETSUB
END
"""
    path_draw = _write_gl3(tmpdir, "TDRAW.GL3", src_draw)
    prog_draw = FakeObj("PROG_DRAW")
    GL3Program(prog_draw)
    prog_draw.SourceFile = path_draw
    prog_draw.Proxy.execute(prog_draw)

    drawing_slot2 = json.loads(prog_draw.Drawing)
    assert drawing_slot2["defined"] is True
    assert drawing_slot2["type"] == "Curve"
    pts = [(item["x"], item["y"]) for item in drawing_slot2["points"]["items"]]
    assert pts == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], pts
    print("Program s INI/MOVE/CLOSE: Drawing = platny Curve JSON: OK - %r" % (pts,))

    # --- 3) 'Drawing' prezije opakovane execute() (neni ve stale-cleanup) ---
    prog_draw.Proxy.execute(prog_draw)
    assert hasattr(prog_draw, "Drawing")
    drawing_slot3 = json.loads(prog_draw.Drawing)
    assert drawing_slot3["defined"] is True
    print("'Drawing' property prezije opakovany execute() (neni smazana _remove_stale_properties): OK")

    # --- 4) GL3Export postavi Shape z 'Drawing' (Curve -> Wire) ---
    import types as _types

    class FakeVector(object):
        __slots__ = ("x", "y", "z")

        def __init__(self, x, y, z=0.0):
            self.x, self.y, self.z = x, y, z

    fake_freecad = _types.ModuleType("FreeCAD")
    fake_freecad.Vector = FakeVector
    fake_part = _types.ModuleType("Part")
    fake_part.makeLine = lambda a, b: ("LineEdge", a, b)
    fake_part.Wire = lambda edges: ("Wire", edges)
    sys.modules["FreeCAD"] = fake_freecad
    sys.modules["Part"] = fake_part

    # gl3_export cached "App"/"Part" pri prvnim importu - pripadny drivejsi
    # import (bez fake modulu) by se musel odstranit z sys.modules, aby se
    # provedl znovu s temito staby. Testy v teto sade importuji gl3_export
    # jen jednou za proces, takze cisty import tady je bezpecny.
    if "gl3fc.gl3_export" in sys.modules:
        del sys.modules["gl3fc.gl3_export"]
    from gl3fc.gl3_export import build_shape

    shape = build_shape(drawing_slot2)
    kind, edges = shape
    assert kind == "Wire"
    assert len(edges) == 2  # 3 body -> 2 usecky
    print("GL3Export.build_shape() z 'Drawing' postavi Wire se 2 usekami: OK")

    print("\nVSE OK - GL3Program vystavuje skryty retezec (INI/CLOSE) pres 'Drawing'.")


if __name__ == "__main__":
    main()
