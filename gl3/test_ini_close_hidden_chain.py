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

    # --- 3) dve INI...CLOSE bloky za sebou - zacina-li druhy blok '/'
    #     (jako tady), spojeni na predchozi blok je NEVIDITELNE (mezera,
    #     None) - viz zadani uzivatele o respektovani lomítka/nespojitosti
    #     retezce. (Pred touto zmenou se oba bloky vzdy spojovaly
    #     souvisle bez ohledu na pero zakladajiciho pohybu - to uz
    #     neplati, viz i pripad 3b nize pro puvodni souvisle chovani.)
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
    hc3 = interp3.hidden_chain
    none_idx3 = [i for i, p in enumerate(hc3.points) if p is None]
    assert none_idx3 == [2], hc3.points
    defined3 = [(round(p.x, 6), round(p.y, 6)) for p in hc3.points if p is not None]
    assert defined3 == [(0.0, 0.0), (1.0, 0.0), (5.0, 5.0), (6.0, 5.0)], defined3
    print("Dve INI...CLOSE bloky, druhy zacina '/': OK - mezera - %r" % (hc3.points,))

    # --- 3b) totez, ale druhy blok zacina '*' -> spojeni ZUSTAVA souvisle ---
    src_multi_star = """
SUBRO/TMULTISTAR/out:DM
P1=P00>0.0,0.0
P2=P00>1.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
P3=P00>5.0,5.0
P4=P00>6.0,5.0
INI
MOVE*P3
MOVE*P4
CLOSE
DM=1.0
RETSUB
END
"""
    subdef3b = parse_program(src_multi_star)
    interp3b = Interpreter()
    interp3b.run(subdef3b, {})
    pts3b = [(round(p.x, 6), round(p.y, 6)) for p in interp3b.hidden_chain.points]
    assert pts3b == [(0.0, 0.0), (1.0, 0.0), (5.0, 5.0), (6.0, 5.0)], pts3b
    print("Dve INI...CLOSE bloky, druhy zacina '*' (souvisle): OK - %r" % (pts3b,))

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
    hc4 = interp4.hidden_chain
    # DRAWSQUARE zacina zakladajicim pohybem '/' (MOVE/Q1) -> spojeni s
    # TMAIN je NEVIDITELNE (mezera, None) - viz zadani uzivatele o
    # respektovani lomítka/nespojitosti i pri spojovani pres CALL.
    none_idx4 = [i for i, p in enumerate(hc4.points) if p is None]
    assert none_idx4 == [2], hc4.points
    defined4 = [(round(p.x, 6), round(p.y, 6)) for p in hc4.points if p is not None]
    assert defined4 == [(0.0, 0.0), (5.0, 0.0), (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], defined4
    print("Skryty retezec volane SUBRO pripojen k volajicimu (s mezerou): OK - %r" % (hc4.points,))

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

    # --- 9) zakladajici fraze *E (cely retezec, pen down) - vsechny body,
    #     ne jen posledni (drivejsi bug: E/S v kresleni "tise" skoncily) ---
    src_founding_chain = """
SUBRO/TFOUND1/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
CRE,EE
MOVE/P1
MOVE*P2*P3
ENDCRE
INI
MOVE*EE
CLOSE
DM=1.0
RETSUB
END
"""
    subdef9 = parse_program(src_founding_chain)
    interp9 = Interpreter()
    interp9.run(subdef9, {})
    pts9 = [(round(p.x, 6), round(p.y, 6)) for p in interp9.hidden_chain.points]
    assert pts9 == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], pts9
    print("Zakladajici fraze *E (cely retezec, pero dolu): OK - %r" % (pts9,))

    # --- 10) zakladajici fraze /E (cely retezec, pen up) - jen bod doskoku ---
    src_founding_chain_up = """
SUBRO/TFOUND2/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>10.0,10.0
P4=P00>20.0,10.0
CRE,EE
MOVE/P1
MOVE*P2*P3
ENDCRE
INI
MOVE/EE
MOVE*P4
CLOSE
DM=1.0
RETSUB
END
"""
    subdef10 = parse_program(src_founding_chain_up)
    interp10 = Interpreter()
    interp10.run(subdef10, {})
    pts10 = [(round(p.x, 6), round(p.y, 6)) for p in interp10.hidden_chain.points]
    # /EE bez predchoziho bodu bere retezec od PRVNIHO bodu -> koncovy bod je P3
    assert pts10 == [(10.0, 10.0), (20.0, 10.0)], pts10
    print("Zakladajici fraze /E (cely retezec, pero nahoru): OK - %r" % (pts10,))

    # --- 11) pohyb "se zdviženym perem" (/) UPROSTRED bloku vytvori mezeru
    #     (None) v skrytem retezci misto drivejsiho NotYetImplemented ---
    src_gap_mid = """
SUBRO/TGAP1/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
P3=P00>20.0,0.0
P4=P00>30.0,0.0
INI
MOVE/P1*P2/P3*P4
CLOSE
DM=1.0
RETSUB
END
"""
    subdef11 = parse_program(src_gap_mid)
    interp11 = Interpreter()
    interp11.run(subdef11, {})
    hc11 = interp11.hidden_chain
    assert hc11.points[2] is None, hc11.points
    defined11 = [(round(p.x, 6), round(p.y, 6)) for p in hc11.points if p is not None]
    assert defined11 == [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0)], defined11
    print("Mezera (None) po pohybu se zdviženym perem uprostred bloku: OK")

    # --- 12) spojeni s vnorenou SUBRO pres CALL: zacina-li volana SUBRO
    #     lomítkem (/), spojeni je NEVIDITELNE (mezera) ---
    src_call_child_up = """
SUBRO/GAPCHILD/in:DUM
P5=P00>40.0,0.0
P6=P00>50.0,0.0
INI
MOVE/P5
MOVE*P6
CLOSE
RETSUB
END
"""
    src_call_main_up = """
SUBRO/TGAP2/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
DUM=1.0
CALL/GAPCHILD/DUM
DM=1.0
RETSUB
END
"""
    child_def = parse_program(src_call_child_up)
    main_def_up = parse_program(src_call_main_up)
    interp12 = Interpreter(registry={"GAPCHILD": child_def})
    interp12.run(main_def_up, {})
    hc12 = interp12.hidden_chain
    none_idx12 = [i for i, p in enumerate(hc12.points) if p is None]
    assert none_idx12 == [2], hc12.points
    print("CALL - volana SUBRO zacina '/' -> spojeni je mezera: OK")

    # --- 13) spojeni s vnorenou SUBRO pres CALL: zacina-li volana SUBRO
    #     hvezdickou (*), spojeni je VIDITELNE (souvisle, beze zmeny) ---
    src_call_child_down = """
SUBRO/NOGAPCHILD/in:DUM
P5=P00>40.0,0.0
P6=P00>50.0,0.0
INI
MOVE*P5*P6
CLOSE
RETSUB
END
"""
    src_call_main_down = """
SUBRO/TGAP3/out:DM
P1=P00>0.0,0.0
P2=P00>10.0,0.0
INI
MOVE/P1
MOVE*P2
CLOSE
DUM=1.0
CALL/NOGAPCHILD/DUM
DM=1.0
RETSUB
END
"""
    child_def2 = parse_program(src_call_child_down)
    main_def_down = parse_program(src_call_main_down)
    interp13 = Interpreter(registry={"NOGAPCHILD": child_def2})
    interp13.run(main_def_down, {})
    hc13 = interp13.hidden_chain
    none_idx13 = [i for i, p in enumerate(hc13.points) if p is None]
    assert none_idx13 == [], hc13.points
    print("CALL - volana SUBRO zacina '*' -> spojeni je souvisle (beze zmeny): OK")

    print("\nVsechny testy INI/CLOSE (skryty retezec) OK.")


if __name__ == "__main__":
    main()
