# -*- coding: utf-8 -*-
"""Test nahlaseny uzivatelem: GL3 program s DATA pro nepodporovany 3D
typ (Q) se ve FreeCADu tvaril, ze doebehl uspesne (vypis skoncil na
'Trace1', k 'Trace2' se nikdy nedostal, ale ZADNA chyba se nezobrazila
v Report View).

Korenova prycina: gl3_ops.NotYetImplemented (a
gerlib.move_geom.MovePhraseNotYetImplemented) drive dedily z
VESTAVENEHO Python NotImplementedError. FreeCAD tuhle konkretni
vyjimku, vyhozenou z GL3Program.execute() (respektive Proxy.execute()),
zjevne interpretuje jako "execute() neni pro tenhle pripad vubec
definovana" (bezna Python konvence pro abstraktni metody) a TISE
USPESNE dokonci recompute bez jakehokoliv hlaseni chyby - misto aby ji
zobrazil.

Tenhle test nekontroluje samotne FreeCAD chovani (na to nemame pristup
v teto offline sade), ale HLIDA KORENOVOU PRICINU: zadna z "jeste
neni implementovano" vyjimek pouzivanych kdekoliv v interpretu/exportu
nesmi (primo ani neprimo) dedit z vestaveneho NotImplementedError."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter
from gl3_ops import NotYetImplemented
from gerlib.move_geom import MovePhraseNotYetImplemented


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def main():
    # --- 1) korenova pricina: NASE vlastni "not yet implemented" tridy
    #     NESMI dedit z vestaveneho NotImplementedError ---
    check(
        not issubclass(NotYetImplemented, NotImplementedError),
        "gl3_ops.NotYetImplemented NESMI dedit (ani neprimo) z vestaveneho "
        "NotImplementedError (FreeCAD ho z Proxy.execute() tise polyka)",
    )
    check(
        issubclass(NotYetImplemented, RuntimeError),
        "gl3_ops.NotYetImplemented dedi z RuntimeError (bezpecna, viditelna "
        "vyjimka)",
    )
    check(
        not issubclass(MovePhraseNotYetImplemented, NotImplementedError),
        "gerlib.move_geom.MovePhraseNotYetImplemented NESMI dedit z "
        "vestaveneho NotImplementedError (stejny duvod)",
    )

    # --- 2) presny priklad z nahlaseni: DATA s nepodporovanym 3D typem
    #     (Q) vyhodi NASI vyjimku (viditelnou), NE vestaveny
    #     NotImplementedError (ktery by FreeCAD tise polknul) ---
    src = """
SUBRO/TQ/out:D1
DIMEN,Q1(4)
TYPE,'Trace1'
DATA,Q1,4
0,0,0
10,0,2
20,0,0
30,0,2
TYPE,'Trace2'
D1=1.0
RETSUB
END
"""
    subdef = parse_program(src)
    interp = Interpreter()
    try:
        interp.run(subdef, {})
        check(False, "DATA,Q1 (3D, nepodporovano) mela vyhodit chybu")
    except NotYetImplemented as e:
        check(
            not isinstance(e, NotImplementedError),
            "DATA,Q1 vyhodilo NotYetImplemented, ktera NENI (uz) vestaveny "
            "NotImplementedError - dostalo %r" % type(e),
        )

    print()
    print("Vsechny testy 'NotYetImplemented nesmi byt NotImplementedError' OK.")


if __name__ == "__main__":
    main()
