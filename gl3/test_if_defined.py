# -*- coding: utf-8 -*-
"""Test klicoveho slova holy IF (test definovanosti objektu, negace
IFN) - viz gl3_keywords.json: 'IF' = 'Akce podminena definovanosti
objektu', 'IFN' = 'Akce podminena nedefinovanosti objektu' - obe
puvodni, samostatna klicova slova z historicke dokumentace, jen IFN
byla dosud jedina implementovana (IF/x/... driv proste neparsoval -
regex vyzadoval presne jedno pismeno za IF)."""
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
    return Interpreter().run(parse_program(src), inputs or {})


def main():
    # --- 1) IF (kratka forma) - prvek definovany -> akce se provede ---
    env = run("""
SUBRO/T1/out:K
DIMEN,PI(3)
PI(1)=1.0
K=0
IF/PI(1)/K=1
RETSUB
END
""")
    check(env["K"] == 1, "IF/definovany/akce - akce se provede")

    # --- 2) IF (kratka forma) - prvek NEdefinovany -> akce se NEprovede ---
    env = run("""
SUBRO/T2/out:K
DIMEN,PI(3)
K=0
IF/PI(1)/K=1
RETSUB
END
""")
    check(env["K"] == 0, "IF/nedefinovany/akce - akce se NEprovede")

    # --- 3) IF/.../THEN...ELSE...ENDIF - definovany -> THEN vetev ---
    env = run("""
SUBRO/T3/out:K
DIMEN,PI(3)
PI(1)=5.0
IF/PI(1)/THEN
K=1
ELSE
K=2
ENDIF
RETSUB
END
""")
    check(env["K"] == 1, "IF/.../THEN...ELSE...ENDIF, definovany -> THEN vetev")

    # --- 4) totez, nedefinovany -> ELSE vetev ---
    env = run("""
SUBRO/T4/out:K
DIMEN,PI(3)
IF/PI(1)/THEN
K=1
ELSE
K=2
ENDIF
RETSUB
END
""")
    check(env["K"] == 2, "IF/.../THEN...ELSE...ENDIF, nedefinovany -> ELSE vetev")

    # --- 5)+6) IFN zustava beze zmeny (presna negace IF) ---
    env = run("""
SUBRO/T5/out:K
DIMEN,PI(3)
K=0
IFN/PI(1)/K=1
RETSUB
END
""")
    check(env["K"] == 1, "IFN/nedefinovany/akce - beze zmeny, akce se provede")

    env = run("""
SUBRO/T6/out:K
DIMEN,PI(3)
PI(1)=9.0
K=0
IFN/PI(1)/K=1
RETSUB
END
""")
    check(env["K"] == 0, "IFN/definovany/akce - beze zmeny, akce se NEprovede")

    # --- 7) IF v idiomu "opakuj dokud" (navesti + zpetny GOTO) ---
    env = run("""
SUBRO/T7/out:K
DIMEN,PI(5)
PI(1)=1.0
PI(2)=2.0
PI(3)=3.0
K=0
10:K=K+1
IF/PI(K)/10
RETSUB
END
""")
    check(env["K"] == 4, "IF v REPEATWHILE idiomu (navesti+GOTO): zastavi se na prvnim nedefinovanem")

    print()
    print("Vsechny testy holeho IF (test definovanosti, negace IFN) OK.")


if __name__ == "__main__":
    main()
