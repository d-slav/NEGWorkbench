# -*- coding: utf-8 -*-
"""Round-trip test gerlib.serialize - bez FreeCADu."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gerlib.types import Point, Vector, Line, Circle, Plane, Spline, Curve
from gerlib.serialize import serialize, deserialize, is_defined, dump_json, load_json
from gerlib.e01 import make_chain


def pts_equal(a, b, tol=1e-12):
    return len(a) == len(b) and all(
        (abs(x.x - y.x) < tol and abs(x.y - y.y) < tol and abs(x.z - y.z) < tol)
        for x, y in zip(a, b)
    )


def roundtrip_json(obj):
    """serialize -> json.dumps -> json.loads -> deserialize, over pameti."""
    data = serialize(obj)
    text = json.dumps(data)
    data2 = json.loads(text)
    return deserialize(data2)


def check(label, obj, compare_fn):
    restored = roundtrip_json(obj)
    ok = compare_fn(obj, restored)
    print("%-10s %s" % (label, "OK" if ok else "SELHALO"))
    assert ok, "%s: round-trip neodpovida originalu" % label


def main():
    # --- zakladni skalarni typy ---
    p = Point(1.5, -2.25, 0.0)
    check("Point", p, lambda a, b: (a.x, a.y, a.z) == (b.x, b.y, b.z))

    v = Vector(0.0, 1.0, 0.0)
    check("Vector", v, lambda a, b: (a.x, a.y, a.z) == (b.x, b.y, b.z))

    ln = Line(Point(0, 0), Vector(1, 0))
    check("Line", ln, lambda a, b: (a.origin.x, a.origin.y) == (b.origin.x, b.origin.y)
          and (a.direction.x, a.direction.y) == (b.direction.x, b.direction.y))

    c = Circle(Point(1, 1), 5.0, Vector(0, 0, 1))
    check("Circle", c, lambda a, b: a.radius == b.radius
          and (a.center.x, a.center.y) == (b.center.x, b.center.y))

    pl = Plane(Point(0, 0, 0), Vector(0, 0, 1))
    check("Plane", pl, lambda a, b: (a.origin.x, a.normal.z) == (b.origin.x, b.normal.z))

    # --- Curve primo z E01 na realnych bodech ---
    src_points = [Point(0, 0), Point(1, 1), Point(2, 0), Point(0, 0)]  # uzavreny
    curve = make_chain(src_points)
    check(
        "Curve(E01)",
        curve,
        lambda a, b: pts_equal(a.points, b.points)
        and a.closed == b.closed
        and a.indices == b.indices
        and a.is_end == b.is_end
        and a.eps == b.eps,
    )
    print("  closed =", curve.closed, " indices =", curve.indices, " is_end =", curve.is_end)

    # --- Spline primo z realneho behu TEHLO (S03) ---
    from gl3_lang import parse_program
    from gl3_interpreter import Interpreter

    # vlastni fixture kopie v gl3test/, ne "zive" gl3sys/gl3data/gl3examples
    # adresare (ty jsou v plne rezii uzivatele - viz konverzace/README)
    root_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    gl3test_dir = os.path.join(root_dir, "gl3test")

    def load(directory, name):
        with open(os.path.join(directory, name), "r", encoding="utf-8", errors="replace") as f:
            return parse_program(f.read())

    tehlo = load(gl3test_dir, "TEHLO.GL3")
    hlo = load(gl3test_dir, "HLO.GL3")
    interp = Interpreter(registry={"TEHLO": tehlo, "HLO": hlo})
    result = interp.run(tehlo, inputs={"BJM": os.path.join(gl3test_dir, "E374.TXT"), "DH": 15.2})
    spline = result["S"]

    check(
        "Spline(S03, TEHLO)",
        spline,
        lambda a, b: pts_equal(a.points, b.points)
        and pts_equal(a.tangents, b.tangents)
        and a.closed == b.closed,
    )
    print("  uzlu =", len(spline.points))

    # --- pole s dirami (None) - napr. vystup PO pred plnym naplnenim ---
    sparse = [Point(0, 0), None, Point(2, 2)]
    slot = serialize(sparse)
    text = json.dumps(slot)
    slot2 = json.loads(text)
    restored = deserialize(slot2)
    assert restored[1] is None and pts_equal([restored[0], restored[2]], [sparse[0], sparse[2]])
    print("%-10s %s" % ("Pole+None", "OK"))

    # --- explicitni 'defined' priznak ---
    assert is_defined(serialize(Point(0, 0))) is True
    assert is_defined(serialize(None)) is False
    # kazdy prvek pole ma vlastni 'defined', ne jen pole jako celek
    items = slot2["items"]
    assert is_defined(items[0]) is True
    assert is_defined(items[1]) is False
    assert is_defined(items[2]) is True
    print("%-10s %s" % ("Defined-flag", "OK"))

    # top-level nedefinovany vystup (napr. out: parametr, ktery vetev
    # podprogramu nikdy nenastavila) musi jit rozpoznat bez importu gerlib
    undefined_output = serialize(None)
    assert undefined_output == {"defined": False}
    assert deserialize(undefined_output) is None
    print("%-10s %s" % ("Top-level None", "OK"))

    print()
    print("VSE OK - serializace je bezeztratova (JSON round-trip) na realnych datech")
    print("a nese 'defined' priznak jen na cele hodnote/prvku pole (viz dale).")

    # --- format v2: 'defined' NENI na vnorenych polich jiz definovaneho
    # objektu (Point.x/y/z, Line.origin, Spline.closed...) - jen na celem
    # objektu a na prvcich poli ---
    ln_slot = serialize(Line(Point(0, 0), Vector(1, 0)))
    assert "defined" not in ln_slot["origin"], "Line.origin nemá mít vlastní 'defined'"
    assert "defined" not in ln_slot["direction"]
    assert isinstance(ln_slot["origin"]["x"], (int, float)), "x/y/z jsou holé hodnoty, ne dalsi slot"
    print("%-10s %s" % ("Format v2", "OK (zadne 'defined' na vnorenych polich)"))

    spline_slot = serialize(spline)
    assert isinstance(spline_slot["closed"], bool), "Spline.closed je hola hodnota"
    assert spline_slot["points"]["defined"] is True, "ale Spline.points (seznam) svuj 'defined' ma"
    assert spline_slot["points"]["items"][0]["defined"] is True, "... a kazdy prvek seznamu taky"

    # --- skutecny JSON text (ne Pythonuv repr) ---
    text = dump_json(Point(1.5, -2.25, 0.0))
    assert '"' in text and "'" not in text, "dump_json musi pouzivat uvozovky, ne apostrofy"
    restored_point = load_json(text)
    assert (restored_point.x, restored_point.y, restored_point.z) == (1.5, -2.25, 0.0)
    print("%-10s %s" % ("dump_json", "OK (%s)" % text.replace(chr(10), " ")))

    text2 = dump_json(closed_spline_for_json_test := Spline(
        [Point(0, 0), Point(1, 1)], [Vector(1, 1), Vector(1, -1)], closed=False
    ))
    assert '"closed": false' in text2, "bool se ma zapsat jako lowercase 'false', ne 'False'"
    print("%-10s OK ('closed' se zapsalo jako lowercase 'false', ne Pythonovske 'False')"
          % "bool fmt")


if __name__ == "__main__":
    main()
