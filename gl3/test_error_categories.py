# -*- coding: utf-8 -*-
"""Test rozdeleni chyb do kategorii (viz konverzace):
  1. Python bug - beze zmeny (netestuje se tady, je to defaultni chovani)
  2. Chyba v GL3 programu (GL3RuntimeError) - promenna neexistuje (2a),
     neznamy opcode (2c), undefined pouzite ve vypoctu (2b)
  3. Varovani (NoSolution) - GL3 program pokracuje, cil = undefined
     (None), testovatelne pres IFN. Rizeno MESS/NOMESS (disp_warning).

Pilotni implementace na tecnych kruznicich (C32/C33/C34) - viz
gerlib/errors.py."""
import io
import os
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter, GL3RuntimeError


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def run(src, inputs=None):
    return Interpreter().run(parse_program(src), inputs=inputs or {})


def run_capturing(src, inputs=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        env = run(src, inputs)
    return env, buf.getvalue()


def main():
    # --- kategorie 3: C32 s rovnobeznymi primkami -> varovani, pokracuje ---
    src_warn = """
SUBRO/CWARN/out:CM,out:FLAG
DIMEN,L(2)
DATA,L,2
0.0,0.0,1.0,0.0
0.0,5.0,1.0,0.0
CM=C32>L(1),L(2),3.0,0
FLAG=0
IFN/CM/FLAG=1
RETSUB
END
"""
    env, out = run_capturing(src_warn)
    check(env.get("CM") is None, "kategorie 3: CM zustava undefined (None) po varovani")
    check(env.get("FLAG") == 1, "kategorie 3: IFN spravne detekuje undefined CM")
    check("[Warning]" in out, "kategorie 3: varovani se vypsalo")
    check("CWARN" in out, "kategorie 3: hlaska obsahuje jmeno programu")
    check("C32" in out, "kategorie 3: hlaska obsahuje jmeno operace")
    print("(zachyceny vystup varovani: %r)" % out.strip())

    # --- NOMESS potlaci vypis, ale CM je porad undefined ---
    src_nomess = """
SUBRO/CNOMESS/out:CM,out:FLAG
NOMESS
DIMEN,L(2)
DATA,L,2
0.0,0.0,1.0,0.0
0.0,5.0,1.0,0.0
CM=C32>L(1),L(2),3.0,0
FLAG=0
IFN/CM/FLAG=1
RETSUB
END
"""
    env2, out2 = run_capturing(src_nomess)
    check(env2.get("CM") is None, "NOMESS: CM je porad undefined")
    check(env2.get("FLAG") == 1, "NOMESS: IFN funguje stejne")
    check(out2.strip() == "", "NOMESS: zadny vypis varovani (%r)" % out2)

    # --- kategorie 2b: pouziti undefined promenne ve vypoctu -> tvrda chyba ---
    src_2b = """
SUBRO/C2B/out:X
DIMEN,L(2)
DATA,L,2
0.0,0.0,1.0,0.0
0.0,5.0,1.0,0.0
CM=C32>L(1),L(2),3.0,0
X=C01>(P00>1.0,1.0),CM
RETSUB
END
"""
    try:
        run(src_2b)
        check(False, "kategorie 2b: pouziti undefined CM melo vyhodit GL3RuntimeError")
    except GL3RuntimeError as e:
        check("[Error]" in str(e), "kategorie 2b: [Error] v hlasce (%s)" % e)
        check("undefined" in str(e), "kategorie 2b: zminuje undefined (%s)" % e)

    # --- kategorie 2a: neexistujici promenna ---
    src_2a = """
SUBRO/C2A/out:X
X=NEEXISTUJE
RETSUB
END
"""
    try:
        run(src_2a)
        check(False, "kategorie 2a: neexistujici promenna mela vyhodit GL3RuntimeError")
    except GL3RuntimeError as e:
        check("[Error]" in str(e) and "C2A" in str(e), "kategorie 2a: spravny format (%s)" % e)

    # --- C33/C34 take pouzivaji NoSolution (stejny mechanismus) ---
    src_c34 = """
SUBRO/C34WARN/out:CM,out:FLAG
DIMEN,C(2)
DATA,C,2
0.0,0.0,5.0
100.0,0.0,5.0
CM=C34>C(1),C(2),3.0,111
FLAG=0
IFN/CM/FLAG=1
RETSUB
END
"""
    env3, out3 = run_capturing(src_c34)
    check(env3.get("CM") is None, "C34: prilis vzdalene kruznice -> undefined")
    check(env3.get("FLAG") == 1, "C34: IFN detekuje undefined")
    check("[Warning]" in out3 and "C34" in out3, "C34: varovani obsahuje jmeno operace")

    # --- kategorie 2: PRINT/WRITE na nedefinovanem objektu (nahlaseno
    #     uzivatelem - format vypisu se drive "zatoulal", chybelo
    #     [Error]/jmeno programu/cislo radku) ---
    src_print_undef = """
SUBRO/Plocha/out:D1
*PP=P00>10,10
PRINT,PP
D1=1.0
RETSUB
END
"""
    try:
        run(src_print_undef)
        check(False, "PRINT na nedefinovanem objektu mel vyhodit GL3RuntimeError")
    except GL3RuntimeError as e:
        msg = str(e)
        check(msg.startswith("[Error] Plocha/"), "PRINT: hlaska zacina [Error] jmeno_programu/: %s" % msg)
        check("/PRINT:" in msg, "PRINT: hlaska obsahuje operaci PRINT: %s" % msg)
        check("objekt 'PP' neni definovan" in msg, "PRINT: text hlasky zachovan: %s" % msg)
        check(msg == "[Error] Plocha/4/PRINT: objekt 'PP' neni definovan", (
            "PRINT: presny format i cislo radku (3 - radek s PRINT,PP, "
            "komentar na radku 2 se nepocita): %s" % msg
        ))

    # --- totez pro indexovany cil a WRITE (WRITE na nedefinovanem se
    #     tise preskoci - viz G13.md - na rozdil od PRINT) ---
    src_print_undef_idx = """
SUBRO/Plocha2/out:D1
DIMEN,PP(3)
PRINT,PP(2)
D1=1.0
RETSUB
END
"""
    try:
        run(src_print_undef_idx)
        check(False, "PRINT na nedefinovanem prvku pole mel vyhodit GL3RuntimeError")
    except GL3RuntimeError as e:
        msg = str(e)
        check(msg == "[Error] Plocha2/4/PRINT: 'PP(2)' neni definovan", (
            "PRINT indexovany: presny format: %s" % msg
        ))

    env_write, _ = run_capturing("""
SUBRO/Plocha3/out:D1
DIMEN,PP(3)
WRITE,PP(2)
D1=1.0
RETSUB
END
""")
    check(env_write.get("D1") == 1.0, "WRITE na nedefinovanem prvku pole se tise preskoci (beze zmeny)")

    print("Vse OK.")


if __name__ == "__main__":
    main()
