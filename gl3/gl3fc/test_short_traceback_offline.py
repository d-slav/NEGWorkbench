# -*- coding: utf-8 -*-
"""
test_short_traceback_offline.py - overeni "zkraceneho tracebacku" u
execute() (GL3Program i GL3Export) - zadani uzivatele: FreeCAD do
Report View vypisuje CELY Python traceback pri kazde vyjimce
prosakujici z execute() (jeho obecne chovani, ne neco specifickeho
pro nas), a ta puvodni hloubka interniho volaciho retezce interpretu
(interp.run -> _exec_block -> _exec_stmt -> _exec_data -> ...) nema
pro autora GL3 programu zadnou informacni hodnotu - jen "sum".

execute() je ted tenky wrapper okolo _execute_impl(), ktery pri
vyjimce vyhodi CERSTVOU (type(e)(str(e)), 'from None') misto
propagace puvodni - stejny typ i zprava, jen mnohem kratsi traceback.
"""
import os
import sys
import tempfile
import traceback

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
    """Stejna napodobenina jako v ostatnich offline testech (viz
    test_offline.py pro komentar)."""

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


def _frame_count(exc):
    return sum(
        1 for line in traceback.format_exception(type(exc), exc, exc.__traceback__)
        if line.strip().startswith("File ")
    )


def main():
    from gl3fc.gl3_program import GL3Program
    from gl3_ops import NotYetImplemented

    # --- 1) presny priklad z nahlaseni (DATA pro nepodporovany 3D typ) -
    #     vyjimka ma STEJNY typ a zpravu, ale JEN par ramcu tracebacku,
    #     ne celou hloubku interp.run -> _exec_block -> _exec_stmt ->
    #     _exec_data (>= 4 dalsi ramce navic, kdyby se nezkracovalo) ---
    tmpdir = tempfile.mkdtemp()
    src_path = os.path.join(tmpdir, "TQ.GL3")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write("SUBRO/TQ/out:D1\nDIMEN,Q1(4)\nTYPE,'Trace1'\nDATA,Q1,4\n"
                "0,0,0\n10,0,2\n20,0,0\n30,0,2\nTYPE,'Trace2'\nD1=1.0\n"
                "RETSUB\nEND\n")

    obj = FakeObj("Plocha")
    GL3Program(obj)
    obj.SourceFile = src_path
    obj.Library = None

    try:
        obj.Proxy.execute(obj)
        assert False, "DATA,Q1 (3D, nepodporovano) mela vyhodit chybu"
    except NotYetImplemented as e:
        msg = str(e)
        assert "DATA,Q1" in msg and "Q" in msg, msg
        frames = _frame_count(e)
        assert frames <= 2, (
            "traceback ma %d ramcu - ocekavano nejvyse 2 (volaci misto + "
            "'raise short from None'), interni hloubka interpretu unikla "
            "ven" % frames
        )
        print("DATA,Q1 -> NotYetImplemented se stejnou zpravou, traceback "
              "zkracen na %d ramce (misto cele hloubky interpretu): OK" % frames)

    # --- 2) fallback: kdyby type(e)(str(e)) selhalo (neobvykly typ bez
    #     jednoargumentoveho konstruktoru), spadne se bezpecne na
    #     RuntimeError se stejnou zpravou, misto aby to zpusobilo JINOU
    #     (matouci) vyjimku ---
    class WeirdError(Exception):
        def __init__(self, code, message):
            self.code = code
            super().__init__(message)

        def __str__(self):
            return "weird error message"

    class FakeProxyWithWeirdError(object):
        def _execute_impl(self, o):
            raise WeirdError(42, "boom")

        def execute(self, o):
            try:
                self._execute_impl(o)
            except Exception as e:
                try:
                    short = type(e)(str(e))
                except Exception:
                    short = RuntimeError(str(e))
                raise short from None

    try:
        FakeProxyWithWeirdError().execute(obj)
        assert False, "WeirdError mela byt vyhozena (v nejake podobe)"
    except WeirdError:
        assert False, "WeirdError (2 povinne argumenty) nemela projit " \
                       "primo pres type(e)(str(e)) - fallback selhal"
    except RuntimeError as e:
        assert str(e) == "weird error message", e
        print("Vyjimka bez jednoargumentoveho konstruktoru -> bezpecny "
              "fallback na RuntimeError se stejnou zpravou: OK")

    print()
    print("VSE OK - execute() zkracuje traceback, se spolehlivym fallbackem.")


if __name__ == "__main__":
    main()
