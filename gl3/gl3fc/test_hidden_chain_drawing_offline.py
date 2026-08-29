# -*- coding: utf-8 -*-
"""
test_hidden_chain_drawing_offline.py - overuje, ze GL3Program.execute()
vykresluje vysledny "skryty retezec" (viz Interpreter.hidden_chain,
INI/CLOSE) PRIMO na sebe (obj.Shape) - GL3Program je Part::
FeaturePython, takze uz ma vlastni nativni Shape, zadny samostatny
GL3Export objekt ani JSON property tu neni potreba (viz zpetna vazba -
puvodni navrh s property 'Drawing' + separatnim GL3Exportem byl
prehnany).

Situace k overeni:
  1. program, ktery NIC nekresli -> Shape zustane prazdny (Part.Shape()),
     zadna chyba.
  2. program, ktery kresli INI...CLOSE (vc. vnoreneho CALL, jehoz skryty
     retezec se pripoji) -> Shape = Wire postaveny primo z Interpreter.
     hidden_chain (pres uz existujici gl3_export.build_shape()).
  3. GL3Program bez 'Drawing' property vubec (nova verze uz ji
     nepridava) - jen aby nedoslo k regresi na starou architekturu.
  4. cache (_exec_cache): opakovany execute() beze zmeny neprepocitava
     znovu (Shape zustane, jak byl), zmena mtime souboru vynuti novy beh.
"""
import os
import sys
import tempfile
import types as _types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_TYPE_DEFAULTS = {
    "App::PropertyFloat": 0.0,
    "App::PropertyInteger": 0,
    "App::PropertyFileIncluded": "",
    "App::PropertyFile": "",
    "App::PropertyLink": None,
    "App::PropertyPythonObject": None,
    "App::PropertyStringList": [],
    "App::PropertyString": "",
}


class FakeVector(object):
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z


class FakeShape(object):
    """Napodobenina prazdneho Part.Shape() - jen aby "nic nenakresleno"
    slo odlisit od skutecne postaveneho Wire (viz FakeWire)."""
    def __repr__(self):
        return "FakeShape(empty)"


class FakeWire(object):
    def __init__(self, edges):
        self.edges = edges

    def __repr__(self):
        return "FakeWire(%d edges)" % len(self.edges)


class FakeCompound(object):
    """Napodobenina Part.Compound - pouzivano, kdyz retezec obsahuje
    mezery (viz gl3_export._build_curve) a vznikne tak vic nez jeden
    samostatny Part.Wire."""
    def __init__(self, wires):
        self.wires = wires

    def __repr__(self):
        return "FakeCompound(%d wires)" % len(self.wires)


def _install_fake_freecad_modules():
    """Nainstaluje minimalni FreeCAD/Part staby do sys.modules PRED
    (prvnim) importem gl3_program/gl3_export - oba na modulove urovni
    delaji 'import Part' a gl3_export definuje build_shape() pouzivajici
    Part.makeLine/Part.Wire/Part.makeCompound/FreeCAD.Vector."""
    fake_freecad = _types.ModuleType("FreeCAD")
    fake_freecad.Vector = FakeVector
    fake_part = _types.ModuleType("Part")
    fake_part.makeLine = lambda a, b: ("LineEdge", a, b)
    fake_part.Wire = lambda edges: FakeWire(edges)
    fake_part.makeCompound = lambda wires: FakeCompound(wires)
    fake_part.Shape = lambda: FakeShape()
    sys.modules["FreeCAD"] = fake_freecad
    sys.modules["Part"] = fake_part
    # Cisty reimport - predchozi (bez fake modulu) verze v sys.modules by
    # jinak porad ukazovala na puvodni (mozna None) App/Part reference.
    for mod_name in ("gl3fc.gl3_export", "gl3fc.gl3_program"):
        if mod_name in sys.modules:
            del sys.modules[mod_name]


class FakeObj(object):
    """Stejna minimalni napodobenina FreeCAD DocumentObject jako v
    test_offline.py, navic se Shape atributem (viz Part::FeaturePython)."""

    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self.Shape = FakeShape()
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
    _install_fake_freecad_modules()
    from gl3fc.gl3_program import GL3Program

    tmpdir = tempfile.mkdtemp(prefix="gl3_hidden_chain_test_")

    # --- 1) program bez kresleni -> Shape zustane prazdny, zadna chyba ---
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

    assert isinstance(prog_nodraw.Shape, FakeShape), prog_nodraw.Shape
    print("Program bez kresleni: Shape zustane prazdny, zadna chyba: OK")

    # --- 2) program, ktery kresli (INI/MOVE/CLOSE) -> Shape = Wire ---
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

    assert isinstance(prog_draw.Shape, FakeWire), prog_draw.Shape
    assert len(prog_draw.Shape.edges) == 2  # 3 body -> 2 usecky
    print("Program s INI/MOVE/CLOSE: Shape je primo postaveny Wire (2 usecky): OK")

    # --- 3) 'Drawing' property UZ NEEXISTUJE (stara architektura, viz
    # zpetna vazba - kresleni jde primo na Shape, ne pres JSON property) ---
    assert not hasattr(prog_draw, "Drawing"), "'Drawing' property nema existovat (viz zpetna vazba)"
    print("'Drawing' property neexistuje (kresleni jde primo na Shape): OK")

    # --- 4) skryty retezec z volane SUBRO (CALL) se take vykresli primo ---
    src_sub = """
SUBRO/DRAWSQUARE/in:DUMMY
Q1=P00>0.0,0.0
Q2=P00>1.0,0.0
Q3=P00>1.0,1.0
INI
MOVE/Q1
MOVE*Q2*Q3
CLOSE
RETSUB
END
"""
    src_main = """
SUBRO/TMAIN/out:DM
P1=P00>0.0,0.0
P2=P00>5.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
DUM=1.0
CALL/DRAWSQUARE/DUM
DM=1.0
RETSUB
END
"""
    path_sub = _write_gl3(tmpdir, "DRAWSQUARE.GL3", src_sub)
    path_main = _write_gl3(tmpdir, "TMAIN.GL3", src_main)

    class _FakeLibraryProxy(object):
        @staticmethod
        def build_registry(library_obj, extra=None):
            from gl3fc.gl3_registry import Gl3FileRegistry
            return Gl3FileRegistry(search_entries=[tmpdir], extra=extra or {})

    class _FakeLibrary(object):
        Name = "LIB"
        Proxy = _FakeLibraryProxy()

    prog_main = FakeObj("PROG_MAIN")
    GL3Program(prog_main)
    prog_main.SourceFile = path_main
    prog_main.Library = _FakeLibrary()
    prog_main.Proxy.execute(prog_main)

    assert isinstance(prog_main.Shape, FakeCompound), prog_main.Shape
    # 2 (hlavni) + 3 (volana SUBRO, pripojeno) = 5 bodu, ale DRAWSQUARE
    # zacina zakladajicim pohybem '/' (MOVE/Q1) -> spojeni s TMAIN je
    # NEVIDITELNE (mezera mezi P2 a Q1) - viz zadani uzivatele o
    # respektovani lomítka/nespojitosti pri spojovani pres CALL. Vznikaji
    # tak DVA samostatne Part.Wire (P1-P2, Q1-Q2-Q3) zabalene v
    # Part.Compound (viz gl3_export._build_curve - realne OCC Part.Wire()
    # nesouvisle hrany neprijme, viz puvodni chyba "BRep_API: command not
    # done" nahlasena uzivatelem).
    assert len(prog_main.Shape.wires) == 2, prog_main.Shape
    assert len(prog_main.Shape.wires[0].edges) == 1  # P1-P2
    assert len(prog_main.Shape.wires[1].edges) == 2  # Q1-Q2-Q3
    print("Skryty retezec volane SUBRO (CALL pres Library) se take vykresli primo, s mezerou na spoji: OK")

    # --- 5) cache: opakovany execute() beze zmeny NEudela skutecny beh ---
    sentinel_shape = FakeShape()
    prog_draw.Shape = sentinel_shape
    prog_draw.Proxy.execute(prog_draw)
    assert prog_draw.Shape is sentinel_shape, (
        "execute() bez zmeny vstupu nesmi delat skutecny beh (cache-hit)"
    )
    print("Cache: opakovany execute() beze zmeny preskoci skutecny beh: OK")

    # --- 6) cache: zmena mtime souboru vynuti skutecny beh znovu ---
    import time as _time
    _time.sleep(0.05)
    with open(path_draw, "a", encoding="utf-8") as f:
        f.write("\n")
    prog_draw.Proxy.execute(prog_draw)
    assert isinstance(prog_draw.Shape, FakeWire) and prog_draw.Shape is not sentinel_shape
    print("Cache: zmena mtime souboru vynuti skutecny beh: OK")

    print("\nVSE OK - GL3Program vykresluje skryty retezec (INI/CLOSE) primo na sebe (Shape).")


if __name__ == "__main__":
    main()
