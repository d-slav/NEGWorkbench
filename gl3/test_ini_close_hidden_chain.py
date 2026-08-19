# -*- coding: utf-8 -*-
"""
test_ini_close_hidden_chain.py - overuje INI/CLOSE ("skryty retezec"
kazde SUBRO, viz zadani uzivatele - zjednodusena nahrada puvodniho
INI/OPE...CLOSE do souboru CL2, ktery se v tomto portu nepouziva).

Klicove vlastnosti k overeni:
  - kazdy beh (run()) ma na zacatku nedefinovany skryty retezec
    (interp.hidden_chain je None, dokud nic nenakresli)
  - INI...CLOSE stavi body stejnou MOVE frazovou logikou jako CRE...
    ENDCRE, jen bez explicitniho cile (viz _active_move_builder)
  - vice INI...CLOSE bloku za sebou v jednom programu se spoji do
    jednoho skryteho retezce (sekvencne, ne vnorene)
  - skryty retezec volane SUBRO (CALL) se pri navratu pripoji na
    konec skryteho retezce volajiciho
  - SUBRO, ktera nic nekresli, nema zadny vliv na skryty retezec
    volajiciho
  - INI a CRE se navzajem vylucuji (nesmi bezet soucasne)
  - INI bez odpovidajiciho CLOSE pred koncem SUBRO je chyba
  - spravna chyba se NEMASKUJE nasledujici kontrolou v "finally" (viz
    _pop_hidden_chain_frame/suppress_dangling_check)
"""
from gl3_lang import parse_program
from gl3_interpreter import Interpreter, GL3RuntimeError


def _assert_close(a, b, msg, eps=1e-6):
    assert abs(a - b) < eps, "%s: %r != %r" % (msg, a, b)


def main():
    # --- 1) nic nenakresleno -> hidden_chain zustane None, zadna chyba ---
    src_empty = """
SUBRO/TEMPTY/out:DM
DM=1.0
RETSUB
END
"""
    subdef = parse_program(src_empty)
    interp = Interpreter()
    interp.run(subdef, {})
    assert interp.hidden_chain is None
    print("Nic nenakresleno -> hidden_chain je None, zadna chyba: OK")

    # --- 2) zakladni INI/MOVE/CLOSE v hlavnim programu ---
    src_basic = """
SUBRO/TBASIC/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
INI
MOVE/P1
MOVE*P2*P3
CLOSE
DM=1.0
RETSUB
END
"""
    subdef2 = parse_program(src_basic)
    interp2 = Interpreter()
    interp2.run(subdef2, {})
    pts = [(round(p.x, 6), round(p.y, 6)) for p in interp2.hidden_chain.points]
    assert pts == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], pts
    print("Zakladni INI/MOVE/CLOSE: OK - %r" % (pts,))

    # --- 3) dve INI...CLOSE bloky za sebou se spoji sekvencne ---
    src_multi = """
SUBRO/TMULTI/out:DM
P1=P00>0.0,0.0
P2=P00>1.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
P3=P00>5.0,5.0
P4=P00>6.0,5.0
INI
MOVE/P3
MOVE*P4
CLOSE
DM=1.0
RETSUB
END
"""
    subdef3 = parse_program(src_multi)
    interp3 = Interpreter()
    interp3.run(subdef3, {})
    pts3 = [(round(p.x, 6), round(p.y, 6)) for p in interp3.hidden_chain.points]
    assert pts3 == [(0.0, 0.0), (1.0, 0.0), (5.0, 5.0), (6.0, 5.0)], pts3
    print("Dve INI...CLOSE bloky za sebou (sekvencne): OK - %r" % (pts3,))

    # --- 4) skryty retezec volane SUBRO se pripoji k volajicimu ---
    src_sub = """
SUBRO/DRAWSQUARE/in:DUMMY
Q1=P00>0.0,0.0
Q2=P00>1.0,0.0
Q3=P00>1.0,1.0
INI
MOVE/Q1
MOVE*Q2*Q3
CLOSE
RETSUB
END
"""
    src_main = """
SUBRO/TMAIN/out:DM
P1=P00>0.0,0.0
P2=P00>5.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
DUM=1.0
CALL/DRAWSQUARE/DUM
DM=1.0
RETSUB
END
"""
    sub_def = parse_program(src_sub)
    main_def = parse_program(src_main)
    interp4 = Interpreter(registry={"DRAWSQUARE": sub_def})
    interp4.run(main_def, {})
    pts4 = [(round(p.x, 6), round(p.y, 6)) for p in interp4.hidden_chain.points]
    assert pts4 == [(0.0, 0.0), (5.0, 0.0), (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], pts4
    print("Skryty retezec volane SUBRO pripojen k volajicimu: OK - %r" % (pts4,))

    # --- 5) volana SUBRO, ktera nic nekresli, nema vliv na volajiciho ---
    src_nodraw = """
SUBRO/NODRAWSUB/in:DUMMY
X=1.0
RETSUB
END
"""
    src_main2 = """
SUBRO/TMAIN2/out:DM
P1=P00>0.0,0.0
P2=P00>5.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
DUM=1.0
CALL/NODRAWSUB/DUM
DM=1.0
RETSUB
END
"""
    nodraw_def = parse_program(src_nodraw)
    main_def2 = parse_program(src_main2)
    interp5 = Interpreter(registry={"NODRAWSUB": nodraw_def})
    interp5.run(main_def2, {})
    pts5 = [(round(p.x, 6), round(p.y, 6)) for p in interp5.hidden_chain.points]
    assert pts5 == [(0.0, 0.0), (5.0, 0.0)], pts5
    print("SUBRO bez kresleni neovlivni skryty retezec volajiciho: OK - %r" % (pts5,))

    # --- 6) INI bez CLOSE pred koncem SUBRO -> chyba ---
    src_dangling = """
SUBRO/TDANGLING/out:DM
P1=P00>0.0,0.0
P2=P00>1.0,0.0
INI
MOVE/P1
MOVE*P2
DM=1.0
RETSUB
END
"""
    subdef6 = parse_program(src_dangling)
    interp6 = Interpreter()
    try:
        interp6.run(subdef6, {})
        assert False, "INI bez CLOSE mela vyhodit chybu"
    except GL3RuntimeError as e:
        assert "CLOSE" in str(e)
    print("INI bez odpovidajiciho CLOSE: OK - spravne vyhozena GL3RuntimeError")

    # --- 7) CRE uvnitr otevreneho INI -> chyba (a NEMASKOVANA "INI bez CLOSE") ---
    src_conflict1 = """
SUBRO/TCONFLICT1/out:DM
P1=P00>0.0,0.0
P2=P00>1.0,0.0
INI
MOVE/P1
MOVE*P2
CRE,E1
DM=1.0
RETSUB
END
"""
    subdef7 = parse_program(src_conflict1)
    interp7 = Interpreter()
    try:
        interp7.run(subdef7, {})
        assert False, "CRE uvnitr INI mela vyhodit chybu"
    except GL3RuntimeError as e:
        msg = str(e)
        assert "INI...CLOSE" in msg, "spravna (CRE-vs-INI) chyba nesmi byt maskovana: %r" % msg
    print("CRE uvnitr otevreneho INI: OK - spravna chyba, nezamaskovana")

    # --- 8) INI uvnitr otevreneho CRE -> chyba ---
    src_conflict2 = """
SUBRO/TCONFLICT2/out:DM
P1=P00>0.0,0.0
P2=P00>1.0,0.0
CRE,E1
MOVE/P1
MOVE*P2
INI
DM=1.0
RETSUB
END
"""
    subdef8 = parse_program(src_conflict2)
    interp8 = Interpreter()
    try:
        interp8.run(subdef8, {})
        assert False, "INI uvnitr CRE mela vyhodit chybu"
    except GL3RuntimeError as e:
        assert "CRE...ENDCRE" in str(e)
    print("INI uvnitr otevreneho CRE: OK - spravna chyba")

    print("\nVsechny testy INI/CLOSE (skryty retezec) OK.")


if __name__ == "__main__":
    main()
