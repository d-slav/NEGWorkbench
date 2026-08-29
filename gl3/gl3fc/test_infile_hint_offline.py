# -*- coding: utf-8 -*-
"""
test_infile_hint_offline.py - overeni, ze hint '-f' v hlavicce SUBRO
(in-f:/out-f: - viz gl3_lang.parse_subro_header) spravne ovlivnuje FC
property typ, ktery GL3Program._sync_properties() vygeneruje pro
B-prefixovy parametr - bez skutecneho FreeCADu.

Zadani uzivatele (varianta B z diskuze): 'B' je vychozi App::PropertyString
(obecny text - viz gl3_ops.TYPE_PREFIX_INFO), 'in-f:' hint prepne na
App::PropertyFile (hezke file-browse tlacitko) - ale JEN pro in:, 'out-f:'
ma zustat App::PropertyString (vystupni "property = jmeno souboru" ve
FreeCADu nedava smysl - hint tam ma jen dokumentacni hodnotu pro
pripadne vnorene volani SUBRO).
"""
import os
import sys
import tempfile
import textwrap

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


class FakeObj(object):
    """Stejna napodobenina jako v test_offline.py (viz tam pro komentar) -
    minimalni DocumentObject: addProperty + obycejne atributy."""

    def __init__(self, name):
        self.Name = name
        self.Proxy = None
        self.ViewObject = None
        self.Document = None
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


def main():
    from gl3fc.gl3_program import GL3Program

    tmpdir = tempfile.mkdtemp()
    src_path = os.path.join(tmpdir, "TESTB.GL3")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent("""\
            SUBRO/TESTB/in-f:BJM,in:BTXT,out:BOUT,out-f:BOUTF
            BOUT=BTXT
            BOUTF=BJM
            RETSUB
            END
            """))

    obj = FakeObj("TestB")
    GL3Program(obj)
    obj.SourceFile = src_path
    obj.Library = None
    obj.Proxy.execute(obj)

    assert obj._prop_types["BJM"] == "App::PropertyFile", obj._prop_types["BJM"]
    print("in-f:BJM -> App::PropertyFile (file-browse tlacitko): OK")

    assert obj._prop_types["BTXT"] == "App::PropertyString", obj._prop_types["BTXT"]
    print("in:BTXT (bez hintu) -> App::PropertyString (obecny text): OK")

    assert obj._prop_types["BOUT"] == "App::PropertyString", obj._prop_types["BOUT"]
    print("out:BOUT -> App::PropertyString: OK")

    assert obj._prop_types["BOUTF"] == "App::PropertyString", (
        "out-f: hint musi byt IGNOROVAN pro FC property (jen "
        "dokumentacni pro vnorene CALL) - ma %r" % obj._prop_types["BOUTF"]
    )
    print("out-f:BOUTF -> App::PropertyString (hint ignorovan pro out:): OK")

    # program se skutecne provedl (BOUT/BOUTF spravne naplnene)
    assert obj.BOUT == obj.BTXT
    print("Program se provedl spravne (BOUT/BOUTF naplnene): OK")

    print()
    print("VSE OK - hint '-f' (in-f:/out-f:) v hlavicce SUBRO spravne "
          "ovlivnuje FC property typ jen pro in:.")


if __name__ == "__main__":
    main()
