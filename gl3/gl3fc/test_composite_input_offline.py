# -*- coding: utf-8 -*-
"""
test_composite_input_offline.py - overuje podporu composite "in:"
parametru (napr. "P" na HLOCUT.gl3: 'in:P(2)') - predtim NEPODPOROVANO
(_sync_properties() rovnou vyhazovalo NotImplementedError, a tim padem
se nevytvorily ani zbyle property za nim v poradi hlavicky).

Format reference: JEDNA App::PropertyString property (stejne jmeno jako
parametr, napr. "P") drzici text 'JmenoObjektu.JmenoVystupu' (napr.
'TEHLO001.PO'), pod kapotou skryty Link '<jmeno>_Link' synchronizovany
pres onChanged() - viz gl3_props.py/gl3_program.py modulove docstringy.
Stejny mechanismus jako GL3Export.Input/Source (viz
test_gl3_export_offline.py).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3_lang import parse_program
from gl3fc.gl3_program import GL3Program


_HERE = os.path.dirname(__file__)
_GL3SYS_DIR = os.path.join(_HERE, "..", "..", "gl3sys")


class FakeDocument(object):
    def __init__(self):
        self._objects = {}
        self.recompute_calls = 0

    def register(self, obj):
        self._objects[obj.Name] = obj
        return obj

    def getObject(self, name):
        return self._objects.get(name)

    def recompute(self):
        self.recompute_calls += 1


_TYPE_DEFAULTS = {
    "App::PropertyFloat": 0.0,
    "App::PropertyInteger": 0,
    "App::PropertyFileIncluded": "",
    "App::PropertyFile": "",
    "App::PropertyLink": None,
    "App::PropertyString": "",
}


class FakeObj(object):
    """Stejny princip jako FakeExportObj v test_gl3_export_offline.py -
    kazde nastaveni property zavola Proxy.onChanged(self, name), presne
    jak to dela realny FreeCAD (na tom stoji synchronizace shadow Linku)."""

    def __init__(self, name, document=None):
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "Document", document)
        object.__setattr__(self, "Proxy", None)
        object.__setattr__(self, "ViewObject", None)
        object.__setattr__(self, "_prop_types", {})
        object.__setattr__(self, "_prop_groups", {})

    def addProperty(self, type_name, name, group=None, doc=None):
        if not hasattr(self, name):
            setattr(self, name, _TYPE_DEFAULTS.get(type_name))
        self._prop_types[name] = type_name
        self._prop_groups[name] = group
        return self

    def setPropertyStatus(self, name, status):
        pass

    def getGroupOfProperty(self, name):
        return self._prop_groups.get(name)

    @property
    def PropertiesList(self):
        return list(self._prop_types.keys())

    def removeProperty(self, name):
        if hasattr(self, name):
            object.__delattr__(self, name)
        self._prop_types.pop(name, None)
        self._prop_groups.pop(name, None)
        return True

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        proxy = object.__getattribute__(self, "Proxy")
        if proxy is not None and name != "Proxy" and hasattr(proxy, "onChanged"):
            proxy.onChanged(self, name)


def _valid_point_array_json():
    return json.dumps(
        {
            "defined": True,
            "type": "Array",
            "items": [
                {"defined": True, "type": "Point", "x": 0.0, "y": 0.0, "z": 0.0},
                {"defined": True, "type": "Point", "x": 1.0, "y": 2.0, "z": 0.0},
            ],
        }
    )


def main():
    with open(os.path.join(_GL3SYS_DIR, "HLOCUT.gl3"), "r", encoding="utf-8", errors="replace") as f:
        subdef = parse_program(f.read())

    assert subdef.name == "HLOCUT"
    param_dirs = {name: direction for name, _size, direction in subdef.params}
    assert param_dirs == {"I": "in", "P": "in", "DHLOUB": "in", "DSIRKA": "in", "SO": "out"}
    print("parse_program(HLOCUT.gl3): OK - params =", param_dirs)

    # --- 1) _sync_properties() se drive zlomilo na 'in:P' (NotImplementedError) ---
    doc = FakeDocument()
    hlocut = doc.register(FakeObj("HLOCUT001", document=doc))
    proxy = GL3Program(hlocut)

    proxy._sync_properties(hlocut, subdef)  # nesmi vyhodit NotImplementedError

    assert hlocut._prop_types["I"] == "App::PropertyInteger"
    assert hlocut._prop_types["P"] == "App::PropertyString", "composite in: je textova reference"
    assert hlocut._prop_types["P_Link"] == "App::PropertyLink", "skryty shadow Link musi existovat"
    assert hlocut._prop_types["DHLOUB"] == "App::PropertyFloat"
    assert hlocut._prop_types["DSIRKA"] == "App::PropertyFloat"
    assert hlocut._prop_types["SO"] == "App::PropertyString", "composite out: je JSON text"
    print("_sync_properties(HLOCUT): OK - vsechny property vytvoreny (drive NotImplementedError)")
    print("  ", {k: v for k, v in hlocut._prop_types.items()})

    # --- 2) _resolve_composite_input(): uspesny pripad ---
    source = doc.register(FakeObj("TEHLO001", document=doc))
    source.PO = _valid_point_array_json()

    hlocut.P = "TEHLO001.PO"  # -> onChanged() hned vyresolvuje P_Link
    assert hlocut.P_Link is source, "shadow Link se ma vyresolvovat automaticky pres onChanged()"

    value = proxy._resolve_composite_input(hlocut, "P")
    assert isinstance(value, list) and len(value) == 2, (
        "deserialize() vraci 'Array' jako obycejny Python list gerlib objektu (viz "
        "gerlib/serialize.py _decode_body), ne nejaky wrapper"
    )
    assert value[1].x == 1.0 and value[1].y == 2.0
    print("_resolve_composite_input(): OK - vraci spravne deserializovany gerlib objekt (list bodu)")

    # --- 3) chybovy stav: spatny format reference (bez tecky) ---
    hlocut.P = "spatnyformat"
    try:
        proxy._resolve_composite_input(hlocut, "P")
        raise AssertionError("mel vyhodit ValueError - spatny format")
    except ValueError as e:
        assert "musi byt ve formatu" in str(e)
        print("_resolve_composite_input() se spatnym formatem: OK - jasna chyba (%s)" % e)

    # --- 4) chybovy stav: odkazovany objekt neexistuje ---
    hlocut.P = "NEEXISTUJICI.PO"
    assert hlocut.P_Link is None
    try:
        proxy._resolve_composite_input(hlocut, "P")
        raise AssertionError("mel vyhodit ValueError - objekt neexistuje")
    except ValueError as e:
        assert "neexistuje" in str(e)
        print("_resolve_composite_input() s neexistujicim objektem: OK - jasna chyba (%s)" % e)

    # --- 5) chybovy stav: odkazovana property na zdroji neexistuje ---
    hlocut.P = "TEHLO001.NEEXISTUJE"
    try:
        proxy._resolve_composite_input(hlocut, "P")
        raise AssertionError("mel vyhodit ValueError - property neexistuje")
    except ValueError as e:
        assert "nema property" in str(e)
        print("_resolve_composite_input() s neexistujici property: OK - jasna chyba (%s)" % e)

    # --- 6) chybovy stav: odkazovana property neni retezec ---
    source.J = 42
    hlocut.P = "TEHLO001.J"
    try:
        proxy._resolve_composite_input(hlocut, "P")
        raise AssertionError("mel vyhodit ValueError - property neni retezec")
    except ValueError as e:
        assert "neni retezec" in str(e)
        print("_resolve_composite_input() s ne-retezcovou property: OK - jasna chyba (%s)" % e)

    # --- 7) index '(N)' na Array vystupu - uspesny pripad (1 = prvni prvek) ---
    hlocut.P = "TEHLO001.PO(1)"
    value = proxy._resolve_composite_input(hlocut, "P")
    assert not isinstance(value, list), "s indexem se ma vratit JEDEN prvek, ne cele pole"
    assert value.x == 0.0 and value.y == 0.0, "PO(1) = prvni bod (0.0, 0.0)"
    print("_resolve_composite_input() s indexem 'PO(1)': OK - vraci jeden Point (%r, %r)" % (value.x, value.y))

    hlocut.P = "TEHLO001.PO(2)"
    value = proxy._resolve_composite_input(hlocut, "P")
    assert value.x == 1.0 and value.y == 2.0, "PO(2) = druhy bod (1.0, 2.0)"
    print("_resolve_composite_input() s indexem 'PO(2)': OK - vraci jeden Point (%r, %r)" % (value.x, value.y))

    # --- 8) index mimo rozsah pole ---
    hlocut.P = "TEHLO001.PO(99)"
    try:
        proxy._resolve_composite_input(hlocut, "P")
        raise AssertionError("mel vyhodit ValueError - index mimo rozsah")
    except ValueError as e:
        assert "mimo rozsah" in str(e)
        print("_resolve_composite_input() s indexem mimo rozsah: OK - jasna chyba (%s)" % e)

    # --- 9) index pouzity na vystup, ktery neni Array ---
    source.PT = json.dumps({"defined": True, "type": "Point", "x": 3.0, "y": 4.0, "z": 0.0})
    hlocut.P = "TEHLO001.PT(1)"
    try:
        proxy._resolve_composite_input(hlocut, "P")
        raise AssertionError("mel vyhodit ValueError - index na ne-Array vystupu")
    except ValueError as e:
        assert "lze pouzit jen na Array" in str(e)
        print("_resolve_composite_input() s indexem na ne-Array vystupu: OK - jasna chyba (%s)" % e)

    # --- 10) zmena vstupu (SourceFile/Library/GL3 In) rovnou spusti
    # Document.recompute() - uzivatel nemusi po kazde zmene parametru
    # rucne kliknout Refresh ---
    calls_before = doc.recompute_calls
    hlocut.DHLOUB = 12.5  # bezny skalarni "GL3 In" parametr
    assert doc.recompute_calls == calls_before + 1, (
        "zmena GL3 In property (DHLOUB) ma rovnou spustit Document.recompute()"
    )
    print("auto-recompute pri zmene GL3 In property (DHLOUB): OK")

    calls_before = doc.recompute_calls
    hlocut.SourceFile = "/neco/jineho.gl3"
    assert doc.recompute_calls == calls_before + 1, (
        "zmena SourceFile ma rovnou spustit Document.recompute()"
    )
    print("auto-recompute pri zmene SourceFile: OK")

    # zmena vystupni (GL3 Out) property NEMA spustit recompute (ta se
    # prece pocita AZ VYSLEDKEM recomputu, ne pricinou dalsiho)
    hlocut.addProperty("App::PropertyString", "SO", "GL3 Out", "vystup")
    calls_before = doc.recompute_calls
    hlocut.SO = json.dumps({"defined": False})
    assert doc.recompute_calls == calls_before, (
        "zmena GL3 Out property NEMA spoustet dalsi recompute (jen vysledek, ne pricina)"
    )
    print("zadny auto-recompute pri zmene GL3 Out property: OK")

    # --- 11) parametr ODEBRANY ze SUBRO hlavicky se ma odstranit i z
    # objektu (drive zustaval "viset" navzdy, i po smazani z .GL3
    # souboru a rucnim "Reload GL3 Program") ---
    src_with_extra = (
        "SUBRO/TSTALE/in:I,in:P(2),in:DHLOUB,in:DSIRKA,in:DEXTRA,out:SO\r\n"
        "*\r\nSO=S03>P(1),I\r\nRETSUB\r\nEND\r\n"
    )
    subdef_extra = parse_program(src_with_extra)
    proxy._sync_properties(hlocut, subdef_extra)
    assert "DEXTRA" in hlocut._prop_types, "DEXTRA se mela pridat (docasne, simuluje puvodni SUBRO verzi)"

    # "uzivatel odebral DEXTRA ze zdrojoveho souboru" - dalsi _sync_properties()
    # (napr. pres "Reload GL3 Program") uz dostane HLAVICKU BEZ DEXTRA:
    proxy._sync_properties(hlocut, subdef)  # puvodni HLOCUT hlavicka (bez DEXTRA)
    assert "DEXTRA" not in hlocut._prop_types, (
        "DEXTRA uz neni v SUBRO hlavicce - _sync_properties() ho mela odstranit"
    )
    assert not hasattr(hlocut, "DEXTRA"), "i samotny atribut DEXTRA ma zmizet"
    # ostatni parametry (vc. P a jeho shadow P_Link) zustavaji beze zmeny
    assert "P" in hlocut._prop_types and "P_Link" in hlocut._prop_types
    assert "I" in hlocut._prop_types and "DHLOUB" in hlocut._prop_types
    print("Odebrany parametr (DEXTRA) se spravne odstrani z objektu pri dalsim _sync_properties(): OK")

    # property skupiny "GL3" (SourceFile/Library) se NIKDY neodstranuji,
    # i kdyz nejsou soucasti "current_names" (nejsou to SUBRO parametry)
    assert "SourceFile" in hlocut._prop_types and "Library" in hlocut._prop_types
    print("Property skupiny 'GL3' (SourceFile/Library) zustavaji zachovany: OK")

    print()
    print("VSE OK - composite 'in:' parametry (napr. HLOCUT.gl3 'P') se nyni spravne")
    print("vytvareji jako textova reference + skryty synchronizovany Link.")


if __name__ == "__main__":
    main()
