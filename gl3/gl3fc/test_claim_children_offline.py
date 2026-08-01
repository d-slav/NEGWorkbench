# -*- coding: utf-8 -*-
"""
test_claim_children_offline.py - overuje
ViewProviderGL3Program.claimChildren() proti scenari, kde kandidat
(GL3Export) jeste NEMA nastaveny Proxy.Type (simulace zavodu poradi
pri otevirani ulozeneho dokumentu - viz komentar v claimChildren()):
onDocumentRestored() na GL3Export kandidatovi jeste nemusi probehnout
drive, nez FreeCAD zavola claimChildren() na GL3Program ViewProvideru.

Pred opravou (detekce pres Proxy.Type) by tenhle kandidat spadl mimo
"potomky" a zobrazil se ve strome na stejne urovni jako GL3Program -
presne pozorovany bug po znovuotevreni dokumentu.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gl3fc.gl3_program import ViewProviderGL3Program


class FakeDoc(object):
    def __init__(self, objects):
        self.Objects = objects


class FakeObj(object):
    def __init__(self, name, doc=None):
        self.Name = name
        self.Document = doc
        self.Proxy = None


def _export_like(name, source, proxy_type_set, doc):
    """Kandidat s FC property Source/Input (jak je ma skutecny
    GL3Export) - proxy_type_set=False simuluje stav TESNE PO nacteni
    dokumentu, kdy jeste nedoslo na onDocumentRestored()."""
    cand = FakeObj(name, doc=doc)
    cand.Source = source
    cand.Input = "S"
    if proxy_type_set:
        class _Proxy(object):
            Type = "GL3Export"
        cand.Proxy = _Proxy()
    # jinak cand.Proxy zustava None - presne stav "jeste nerestorovano"
    return cand


def main():
    doc = FakeDoc(objects=[])
    prog = FakeObj("TEHLO001", doc=doc)
    other_prog = FakeObj("HLO001", doc=doc)

    export_normal = _export_like("Export001", prog, proxy_type_set=True, doc=doc)
    export_not_yet_restored = _export_like("Export002", prog, proxy_type_set=False, doc=doc)
    export_of_other_program = _export_like("Export003", other_prog, proxy_type_set=True, doc=doc)

    unrelated = FakeObj("SomethingElse001", doc=doc)  # zadne Source/Input

    doc.Objects = [prog, other_prog, export_normal, export_not_yet_restored, export_of_other_program, unrelated]

    vp = ViewProviderGL3Program.__new__(ViewProviderGL3Program)  # bez volani __init__ (nepotrebujeme vobj)
    vp.Object = prog

    children = vp.claimChildren()
    names = sorted(c.Name for c in children)

    assert "Export001" in names, "normalni jiz-restorovany Export se ma zobrazit jako potomek"
    assert "Export002" in names, (
        "Export BEZ jeste nastaveneho Proxy.Type (simulace stavu tesne po otevreni "
        "dokumentu) se MA STEJNE TAK zobrazit jako potomek - to je presne opravovany bug"
    )
    assert "Export003" not in names, "Export patrici jinemu GL3Programu se nema zobrazit"
    assert "SomethingElse001" not in names, "objekt bez Source/Input neni GL3Export kandidat"
    assert len(names) == 2

    print("claimChildren(): OK - najde i kandidata bez jeste nastaveneho Proxy.Type (%r)" % names)
    print()
    print("VSE OK - claimChildren() prezije poradi-zavod pri otevirani ulozeneho dokumentu.")


if __name__ == "__main__":
    main()
