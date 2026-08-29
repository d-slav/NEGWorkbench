# -*- coding: utf-8 -*-
"""
test_integer_output_offline.py - regrese nahlasena uzivatelem:

    SUBRO/ErrOotInt/out:K
    K=100
    RETSUB
    END

hlasilo 'TypeError: type must be int, not float' pri ukladani vystupu -
interpret pocita vzdy s Python float (i pro I/J/K promenne), ale
App::PropertyInteger nekterych verzi FreeCADu striktne odmita setattr
s float (na rozdil od nasi offline FakeObj v ostatnich testech, ktera
je v tomhle lenivejsi nez skutecny FreeCAD - proto tenhle bug prosel
skrz ostatni testy nepovsimnuty).

Pouziva vlastni "prisny" fake objekt, ktery presne replikuje tohle
chovani skutecneho FreeCADu - viz StrictIntObj nize.
"""
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
    "App::PropertyString": "",
}


class StrictIntObj(object):
    """Jako FakeObj v ostatnich offline testech, ale __setattr__ navic
    STRIKTNE odmita float na App::PropertyInteger property - presne
    chovani skutecneho FreeCADu, ktere zpusobilo nahlaseny bug (ostatni
    testy pouzivaji lenivejsi FakeObj, ktery by tenhle konkretni bug
    nezachytil)."""

    def __init__(self, name):
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "Proxy", None)
        object.__setattr__(self, "ViewObject", None)
        object.__setattr__(self, "Document", None)
        object.__setattr__(self, "_prop_types", {})
        object.__setattr__(self, "_prop_groups", {})
        object.__setattr__(self, "_values", {})

    def addProperty(self, type_name, name, group=None, doc=None):
        if name not in self._prop_types:
            self._values[name] = _TYPE_DEFAULTS.get(type_name)
        self._prop_types[name] = type_name
        self._prop_groups[name] = group
        return self

    def __setattr__(self, name, value):
        if name in ("Name", "Proxy", "ViewObject", "Document") or name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        if self._prop_types.get(name) == "App::PropertyInteger" and not isinstance(value, int):
            raise TypeError("type must be int, not float")
        self._values[name] = value

    def __getattr__(self, name):
        # volano jen kdyz normalni atribut lookup selze (tj. name NENI
        # v __dict__) - takze self._values je tu vzdy uz nastavene
        values = object.__getattribute__(self, "_values")
        if name in values:
            return values[name]
        raise AttributeError(name)

    def removeProperty(self, name):
        self._prop_types.pop(name, None)
        self._prop_groups.pop(name, None)
        self._values.pop(name, None)
        return True

    @property
    def PropertiesList(self):
        return list(self._prop_types.keys())

    def getGroupOfProperty(self, name):
        return self._prop_groups.get(name)

    def getTypeIdOfProperty(self, name):
        return self._prop_types.get(name)


def main():
    from gl3fc.gl3_program import GL3Program

    tmpdir = tempfile.mkdtemp()
    src_path = os.path.join(tmpdir, "ErrOotInt.GL3")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write("SUBRO/ErrOotInt/out:K\nK=100\nRETSUB\nEND\n")

    obj = StrictIntObj("ErrOotInt")
    GL3Program(obj)
    obj.SourceFile = src_path
    obj.Library = None
    obj.Proxy.execute(obj)  # drive: TypeError: type must be int, not float

    assert obj.K == 100, obj.K
    assert isinstance(obj.K, int), (
        "out:K (I/J/K = celociselny typ) musi ulozit skutecny Python int, "
        "ne float - dostal %r" % type(obj.K)
    )
    print("out:K=100 (interpret pocita s float) ulozeno jako skutecny "
          "int bez TypeError: OK - K=%r (%s)" % (obj.K, type(obj.K).__name__))

    print()
    print("VSE OK - App::PropertyInteger vystup uz nespada na "
          "'type must be int, not float'.")


if __name__ == "__main__":
    main()
