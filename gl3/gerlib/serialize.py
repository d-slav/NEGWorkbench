# -*- coding: utf-8 -*-
"""
gerlib.serialize - prevod gerlib objektu (Point, Vector, Line, Circle,
Plane, Spline, Curve) na JSON-safe strukturu (dict) a zpet.

Ucel: hranice mezi GL3 modulem a Export modulem ve FreeCADu (viz
shrnuti projektu). GL3 objekt ulozi composite vystup jako
PropertyPythonObject obsahujici vysledek serialize() - obycejny dict,
zadna zavislost na gerlib tridach pri cteni. Export modul tak nemusi
gerlib vubec importovat.

Kazda hodnota (skalar, composite objekt, prvek pole) je zabalena jako
"slot" s explicitnim priznakem "defined":

    {"defined": False}                                  - nedefinovano
    {"defined": True, "value": <scalar>}                 - skalar
    {"defined": True, "type": "Array", "items": [slot, ...]}
    {"defined": True, "type": "Point", "x": slot, "y": slot, "z": slot}
    ... (Vector/Line/Circle/Plane/Spline/Curve analogicky, kazde pole
    objektu je opet slot, rekurzivne)

Duvod: GL3 samo rozlisuje definovane/nedefinovane hodnoty na urovni
kazdeho objektu (IFN idiom, PRINT vs WRITE u poli - viz shrnuti
projektu) - format proto stejnou informaci nese explicitne u kazdeho
slotu, misto aby se spolehal na implicitni Python/JSON None, ktere by
konzument (Export modul) mohl zamenit s "hodnota chybi/nebyla ulozena".

Zpetna rekonstrukce (deserialize) je potreba jen uvnitr GL3 sveta -
napr. kdyz composite vystup jednoho GL3 objektu ma jit pres Link jako
composite vstup do dalsiho GL3 podprogramu, ktery pro vypocet potrebuje
skutecne gerlib instance, ne dict. Export modul deserialize nepouziva.
"""

from .types import Point, Vector, Line, Circle, Plane, Spline, Curve

_SCALAR_TYPES = (int, float, str, bool)


def serialize(obj):
    """gerlib objekt / scalar / list / None -> JSON-safe 'slot' dict."""
    if obj is None:
        return {"defined": False}

    if isinstance(obj, _SCALAR_TYPES):
        return {"defined": True, "value": obj}

    if isinstance(obj, (list, tuple)):
        return {"defined": True, "type": "Array", "items": [serialize(item) for item in obj]}

    if isinstance(obj, Point):
        return {
            "defined": True,
            "type": "Point",
            "x": serialize(obj.x),
            "y": serialize(obj.y),
            "z": serialize(obj.z),
        }

    if isinstance(obj, Vector):
        return {
            "defined": True,
            "type": "Vector",
            "x": serialize(obj.x),
            "y": serialize(obj.y),
            "z": serialize(obj.z),
        }

    if isinstance(obj, Line):
        return {
            "defined": True,
            "type": "Line",
            "origin": serialize(obj.origin),
            "direction": serialize(obj.direction),
        }

    if isinstance(obj, Circle):
        return {
            "defined": True,
            "type": "Circle",
            "center": serialize(obj.center),
            "radius": serialize(obj.radius),
            "normal": serialize(obj.normal),
        }

    if isinstance(obj, Plane):
        return {
            "defined": True,
            "type": "Plane",
            "origin": serialize(obj.origin),
            "normal": serialize(obj.normal),
        }

    if isinstance(obj, Spline):
        return {
            "defined": True,
            "type": "Spline",
            "points": serialize(obj.points),
            "tangents": serialize(obj.tangents),
            "closed": serialize(obj.closed),
        }

    if isinstance(obj, Curve):
        return {
            "defined": True,
            "type": "Curve",
            "points": serialize(obj.points),
            "closed": serialize(obj.closed),
            "indices": serialize(list(obj.indices)),
            "is_end": serialize(list(obj.is_end)),
            "eps": serialize(obj.eps),
        }

    raise TypeError("gerlib.serialize: neznamy typ %r" % (type(obj),))


def deserialize(data):
    """JSON-safe 'slot' dict (viz serialize()) -> gerlib objekt / list / scalar / None."""
    if not isinstance(data, dict):
        raise TypeError("gerlib.deserialize: ocekavan slot-dict, dostal %r" % (type(data),))

    if not data.get("defined", False):
        return None

    kind = data.get("type")

    if kind is None:
        # skalarni slot: {"defined": True, "value": ...}
        return data["value"]

    if kind == "Array":
        return [deserialize(item) for item in data["items"]]

    if kind == "Point":
        return Point(deserialize(data["x"]), deserialize(data["y"]), deserialize(data["z"]))

    if kind == "Vector":
        return Vector(deserialize(data["x"]), deserialize(data["y"]), deserialize(data["z"]))

    if kind == "Line":
        return Line(deserialize(data["origin"]), deserialize(data["direction"]))

    if kind == "Circle":
        return Circle(
            deserialize(data["center"]),
            deserialize(data["radius"]),
            deserialize(data["normal"]),
        )

    if kind == "Plane":
        return Plane(deserialize(data["origin"]), deserialize(data["normal"]))

    if kind == "Spline":
        return Spline(
            deserialize(data["points"]),
            deserialize(data["tangents"]),
            closed=deserialize(data["closed"]),
        )

    if kind == "Curve":
        return Curve(
            deserialize(data["points"]),
            closed=deserialize(data["closed"]),
            indices=deserialize(data["indices"]),
            is_end=deserialize(data["is_end"]),
            eps=deserialize(data["eps"]),
        )

    raise TypeError("gerlib.deserialize: neznamy 'type' v datech: %r" % (kind,))


def is_defined(slot):
    """Pohodlny pomocnik pro Export modul - nemusi importovat gerlib vubec,
    jen se zepta na tenhle plochy dict dotaz. Napr.:
        if not is_defined(data["S"]): skip export teto vetve
    """
    return bool(isinstance(slot, dict) and slot.get("defined", False))
