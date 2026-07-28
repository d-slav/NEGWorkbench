# -*- coding: utf-8 -*-
"""
gerlib.serialize - prevod gerlib objektu (Point, Vector, Line, Circle,
Plane, Spline, Curve) na JSON-safe strukturu (dict) a zpet.

Ucel: hranice mezi GL3 modulem a Export modulem ve FreeCADu (viz
shrnuti projektu). GL3 objekt ulozi composite vystup jako
PropertyPythonObject obsahujici vysledek serialize() - obycejny dict,
zadna zavislost na gerlib tridach pri cteni. Export modul tak nemusi
gerlib vubec importovat.

Format (v2 - zjednoduseno na zaklade zpetne vazby z realneho pouziti):
"defined" priznak nese jen CELY objekt a KAZDY PRVEK POLE - presne tam,
kde GL3 opravdu muze mit "diru" (IFN idiom, _set_indexed v interpretu).
Jednotliva pole JIZ DEFINOVANEHO objektu (Point.x/y/z, Line.origin,
Circle.radius, Spline.closed, ...) uz svuj vlastni "defined" nemaji -
kdyz objekt existuje, jeho pole existuji s nim, netreba to opakovat na
kazde urovni zvlast:

    {"defined": False}                                   - nedefinovano
    {"defined": True, "value": <scalar>}                  - skalar
    {"defined": True, "type": "Array", "items": [slot, ...]}
    {"defined": True, "type": "Point", "x": 1.5, "y": -2.25, "z": 0.0}
    {"defined": True, "type": "Line",
     "origin": {"type": "Point", "x": ..., "y": ..., "z": ...},
     "direction": {"type": "Vector", "x": ..., "y": ..., "z": ...}}
    {"defined": True, "type": "Spline",
     "points": {"defined": True, "type": "Array", "items": [...]},
     "tangents": {"defined": True, "type": "Array", "items": [...]},
     "closed": False}

Vsimnete si: "origin"/"direction" uvnitr Line nemaji vlastni "defined"
klic (jsou to obycejne vnorene dicty s "type"+poli) - jsou zarucene
pritomne, protoze Line jako celek uz je oznacen jako "defined". Naproti
tomu "points"/"tangents" jsou seznamy (mohly by mit diru), takze jdou
pres stejnou serialize() cestu jako cokoliv jineho v poli - kazdy prvek
ma svuj vlastni "defined".

dump_json()/load_json() jsou pohodlne pomocniky pro skutecny textovy
JSON (s uvozovkami a lowercase true/false/null) - napr. pro ulozeni do
souboru a prohlizeni v beznem textovem editoru. Bez nich FreeCAD
konzole/Report View vypisuje Pythonuv repr() slovniku (apostrofy,
"True" s velkym pismenem) - to NENI bug, jen Pythonuv vlastni format
vypisu, ne skutecny JSON text.
"""

import json

from .types import Point, Vector, Line, Circle, Plane, Spline, Curve

_SCALAR_TYPES = (int, float, str, bool)


def _body(obj):
    """Vraci 'type'+pole dict BEZ 'defined' klice - pro pole slozeneho
    objektu, o kterem uz vime, ze existuje (protoze rodicovsky objekt uz
    sam je 'defined'). Skalarni/vektorova pole se ukladaji primo (holy
    Python float/bool), vnorene composite hodnoty rekurzivne pres tuhle
    stejnou funkci, seznamy VZDY pres serialize() (tam ma smysl sledovat
    definovanost jednotlivych prvku)."""
    if isinstance(obj, Point):
        return {"type": "Point", "x": obj.x, "y": obj.y, "z": obj.z}

    if isinstance(obj, Vector):
        return {"type": "Vector", "x": obj.x, "y": obj.y, "z": obj.z}

    if isinstance(obj, Line):
        return {
            "type": "Line",
            "origin": _body(obj.origin),
            "direction": _body(obj.direction),
        }

    if isinstance(obj, Circle):
        return {
            "type": "Circle",
            "center": _body(obj.center),
            "radius": obj.radius,
            "normal": _body(obj.normal),
        }

    if isinstance(obj, Plane):
        return {
            "type": "Plane",
            "origin": _body(obj.origin),
            "normal": _body(obj.normal),
        }

    if isinstance(obj, Spline):
        return {
            "type": "Spline",
            "points": serialize(obj.points),
            "tangents": serialize(obj.tangents),
            "closed": obj.closed,
        }

    if isinstance(obj, Curve):
        return {
            "type": "Curve",
            "points": serialize(obj.points),
            "closed": obj.closed,
            "indices": list(obj.indices),
            "is_end": list(obj.is_end),
            "eps": obj.eps,
        }

    raise TypeError("gerlib.serialize: neznamy typ %r" % (type(obj),))


def serialize(obj):
    """gerlib objekt / scalar / list / None -> JSON-safe 'slot' dict.

    'defined' se objevuje jen tady (top-level vystup, nebo kazdy prvek
    pole) - viz modulovy docstring."""
    if obj is None:
        return {"defined": False}

    if isinstance(obj, _SCALAR_TYPES):
        return {"defined": True, "value": obj}

    if isinstance(obj, (list, tuple)):
        return {"defined": True, "type": "Array", "items": [serialize(item) for item in obj]}

    return {"defined": True, **_body(obj)}


def _decode_body(d):
    """Dekoduje dict s 'type'(+poli), bez ohledu na to, jestli vedle nese
    i 'defined' (top-level/prvek pole), nebo ne (vnorene pole jiz
    definovaneho objektu - viz _body())."""
    kind = d.get("type")

    if kind is None:
        return d["value"]

    if kind == "Array":
        return [deserialize(item) for item in d["items"]]

    if kind == "Point":
        return Point(d["x"], d["y"], d["z"])

    if kind == "Vector":
        return Vector(d["x"], d["y"], d["z"])

    if kind == "Line":
        return Line(_decode_body(d["origin"]), _decode_body(d["direction"]))

    if kind == "Circle":
        return Circle(_decode_body(d["center"]), d["radius"], _decode_body(d["normal"]))

    if kind == "Plane":
        return Plane(_decode_body(d["origin"]), _decode_body(d["normal"]))

    if kind == "Spline":
        return Spline(deserialize(d["points"]), deserialize(d["tangents"]), closed=d["closed"])

    if kind == "Curve":
        return Curve(
            deserialize(d["points"]),
            closed=d["closed"],
            indices=d["indices"],
            is_end=d["is_end"],
            eps=d["eps"],
        )

    raise TypeError("gerlib.deserialize: neznamy 'type' v datech: %r" % (kind,))


def deserialize(slot):
    """JSON-safe 'slot' dict (viz serialize()) -> gerlib objekt / list /
    scalar / None."""
    if not isinstance(slot, dict):
        raise TypeError("gerlib.deserialize: ocekavan slot-dict, dostal %r" % (type(slot),))

    if not slot.get("defined", False):
        return None

    return _decode_body(slot)


def is_defined(slot):
    """Pohodlny pomocnik pro Export modul - nemusi importovat gerlib
    vubec, jen se zepta na tenhle plochy dict dotaz."""
    return bool(isinstance(slot, dict) and slot.get("defined", False))


def dump_json(obj, indent=2):
    """gerlib objekt -> SKUTECNY JSON text (uvozovky, lowercase
    true/false/null) - napr. pro ulozeni do .json souboru a prohlizeni v
    beznem textovem editoru (Notepad++, ...). Bez tohohle FreeCAD
    konzole/Report View vypisuje Pythonuv repr() slovniku (apostrofy,
    'True' s velkym pismenem) - to neni chyba formatu, jen jiny vypis."""
    return json.dumps(serialize(obj), indent=indent, ensure_ascii=False)


def load_json(text):
    """Skutecny JSON text (viz dump_json()) -> gerlib objekt."""
    return deserialize(json.loads(text))
