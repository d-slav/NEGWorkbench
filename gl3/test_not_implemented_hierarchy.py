# -*- coding: utf-8 -*-
"""Test nahlaseny uzivatelem: GL3 program s DATA pro tehdy nepodporovany
3D typ (Q) se ve FreeCADu tvaril, ze doebehl uspesne (vypis skoncil na
'Trace1', k 'Trace2' se nikdy nedostal, ale ZADNA chyba se nezobrazila
v Report View). Q uz mezitim byla doplnena (viz test_data_command.py) -
tenhle test pouziva jiny, porad nepodporovany typ (E - "slozeny" objekt
s promennou delkou dat) na overeni STEJNE korenove priciny.

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

    # --- 2) korenova pricina puvodniho nahlaseni: DATA s NEpodporovanym
    #     typem (E - "slozeny" objekt s promennou delkou dat, viz
    #     G06.md/gl3_ops.DATA_CONSTANTS_PER_OBJECT - Q uz mezitim byla
    #     doplnena, viz test_data_command.py) vyhodi NASI vyjimku
    #     (viditelnou), NE vestaveny NotImplementedError (ktery by
    #     FreeCAD tise polknul) ---
    src = """
SUBRO/TE/out:D1
DIMEN,E1(1)
TYPE,'Trace1'
DATA,E1,1
1.0,2.0
TYPE,'Trace2'
D1=1.0
RETSUB
END
"""
    subdef = parse_program(src)
    interp = Interpreter()
    try:
        interp.run(subdef, {})
        check(False, "DATA,E1 ('slozeny' typ, nepodporovano) mela vyhodit chybu")
    except NotYetImplemented as e:
        check(
            not isinstance(e, NotImplementedError),
            "DATA,E1 vyhodilo NotYetImplemented, ktera NENI (uz) vestaveny "
            "NotImplementedError - dostalo %r" % type(e),
        )

    print()
    print("Vsechny testy 'NotYetImplemented nesmi byt NotImplementedError' OK.")


if __name__ == "__main__":
    main()
