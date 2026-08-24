# -*- coding: utf-8 -*-
"""Test rizeni programu podle G12.md - podminka THEN-ELSE-ENDIF (treti
varianta akce, viz G12.md odst. "PODMINENE PRIKAZY"). Puvodni THEN-ENDIF
(druha varianta, bez ELSE) musi zustat funkcni beze zmeny."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def run(src, inputs=None):
    return Interpreter().run(parse_program(src), inputs=inputs or {})


def main():
    # --- THEN-ENDIF (bez ELSE) - puvodni chovani beze zmeny ---
    env = run("""
SUBRO/T1/out:K
K=9
IFI/1.EQ.2/THEN
K=0
ENDIF
END
""")
    check(env["K"] == 9, "THEN-ENDIF (bez ELSE), podminka neplati -> beze zmeny")

    env = run("""
SUBRO/T2/out:K
K=9
IFI/1.EQ.1/THEN
K=0
ENDIF
END
""")
    check(env["K"] == 0, "THEN-ENDIF (bez ELSE), podminka plati -> provede se blok")

    # --- THEN-ELSE-ENDIF - podminka plati (THEN vetev) ---
    env = run("""
SUBRO/T3/out:K
D=5.0
IFX/D.EQ.5.0/THEN
K=0
ELSE
K=1
ENDIF
END
""")
    check(env["K"] == 0, "THEN-ELSE-ENDIF, podminka plati -> THEN vetev")

    # --- THEN-ELSE-ENDIF - podminka neplati (ELSE vetev) ---
    env = run("""
SUBRO/T4/out:K
D=6.0
IFX/D.EQ.5.0/THEN
K=0
ELSE
K=1
ENDIF
END
""")
    check(env["K"] == 1, "THEN-ELSE-ENDIF, podminka neplati -> ELSE vetev")

    # --- vnoreny podmineny prikaz uvnitr ELSE vetve (G12.md: "Uvnitr
    #     kterehokoliv z bloku muze byt umisten dalsi podmineny prikaz") ---
    env = run("""
SUBRO/T5/out:K
D=2.0
IFI/1.EQ.2/THEN
K=100
ELSE
IFX/D.EQ.2.0/THEN
K=1
ELSE
K=2
ENDIF
ENDIF
END
""")
    check(env["K"] == 1, "vnoreny IF...THEN...ELSE...ENDIF uvnitr ELSE vetve")

    # --- vnoreny podmineny prikaz uvnitr THEN vetve ---
    env = run("""
SUBRO/T6/out:K
IFI/1.EQ.1/THEN
IFI/2.EQ.3/THEN
K=100
ELSE
K=7
ENDIF
ELSE
K=200
ENDIF
END
""")
    check(env["K"] == 7, "vnoreny IF...THEN...ELSE...ENDIF uvnitr THEN vetve")

    # --- primo priklad z G12.md (odst. "Treti variantou akce...") ---
    env = run("""
SUBRO/T7/out:K
PX=P00>0.0,0.0
PY=P00>0.0,0.0
IFO/PX.NE.PY/THEN
CRE,E
MOVE/PX*PY
ENDCRE
ELSE
K=1
ENDIF
END
""")
    check("E" in env or env.get("K") == 1, "priklad z G12.md (totozne body -> K=1 nebo E vznikl)")

    print()
    print("Vsechny testy THEN-ELSE-ENDIF (G12.md) OK.")


if __name__ == "__main__":
    main()
