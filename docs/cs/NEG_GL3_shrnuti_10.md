## Shrnuti 10

**Anchor:** HEAD `c6e28ec` (Shrnuti 9 - broad error sweep). Vse nize je serie commitu na tomto zaklade, konci na `4bc13c7`.

### 1. GL3Program - recompute chovani

- **RecomputeOnOpenDoc -> RecomputeOnlyManually** (`aa70538`): prejmenovano a OTOCENA logika (default `False` = puvodni automaticke chovani). Property ted rika DVE veci najednou: (1) puvodni vyznam - preskoci vzdy-plny-prepocet po otevreni dokumentu na zaklade `_ExecCache`; (2) NOVE - kdyz `True`, potlaci i auto-prepocet z `onChanged()` po zmene `in:` parametru (jen rucne - tlacitko "Reload GL3 Program" nebo FreeCAD "Mark to recompute"+Refresh). Migrace ze stare property automaticka (hodnota invertovana).
- **Debounce auto-recompute** (`aa70538`): `onChanged()` misto okamziteho `recompute()` pouziva `_schedule_recompute()` - `QTimer.singleShot` 500ms, restartuje se pri kazde dalsi zmene (reseni "prepocet po kazdem napsanem znaku"). Bez GUI/QTimer padá zpet na puvodni synchronni chovani.
- **Bugfix** (`5c03c01`): FreeCAD pri otevreni ULOZENEHO dokumentu NEVOLA `__init__` (Proxy se obnovuje pres `__setstate__`), takze `self._recompute_timer` na cerstve nactenem objektu neexistoval -> `AttributeError` pri prvni zmene property po otevreni. Opraveno: `__init__` rozdelen na `_reset_transient_state()` + `_setup_properties()`, obe se ted volaji i z JIZ EXISTUJICIHO `onDocumentRestored()` hooku (drive tam byl jen `self.Type = ...`). Navic `getattr(self, '_recompute_timer', None)` jako dalsi pojistka.
- **Prubezny vypis PRINT/WRITE/TYPE** (`dcca5b3`): `_emit_line()` pouziva `App.Console.PrintMessage()` + `Gui.updateGui()` po kazdem radku (misto ceho, ze se cely vystup objevil az po dobehnuti celeho programu) - `Gui.updateGui()` donuti Qt zpracovat frontu udalosti (vc. prekresleni Report View) hned, bez cekani na navrat z `execute()`.

### 2. GL3Export

- **Uzavrena Spline = JEDNA hrana** (`0e5e68c`): odstranena zbytecna podminka `not closed` u `_single_bspline_edge` - uzavrena krivka (S10/T10) uz sama nese opakovany uzaviraci bod + kompletni `segment_tangents`, takze jde exportovat stejne jako otevrena, bez rozsekani na segmenty. Fallback (Wire po segmentech) zustava pro castecne nedefinovanou Spline.
- **Placement** (diskutovano, NEIMPLEMENTOVANO): `GL3Export.Placement` je schvalne Hidden a pri kazdem `execute()` prepsan na `source.Placement` - zjisteno pri kontrole, proc "vlastni placement nefunguje". Uzivatel rozhodl NERESIT ted (mozne smery: skladat se Source.Placement, nebo ho nahrazovat - zatim otevrene).

### 3. Interpret - CALL

- **Indexovany cil pro `out:`** (`775eb92`): `CALL/Sub/args,T(3)` ted zapise vysledek primo do `T(3)` (drive fungoval jen holy identifikator `TT`). Pole `T` musi byt uz `DIMEN`ovano.
- **Bugfix out:X(1)** (`dbc26eb`): kdyz callee deklaruje `out:` parametr S DIM=1 (napr. `out:T(1)`), zapis zpet (holy identifikator I indexovany cil) hodnotu OBALOVAL do jednoprvkoveho listu (`[Point(...)]` misto `Point(...)`) - navazny kod cekajici napr. Point dostal spatny typ a tise se s nim nepocitalo. Opraveno: dim==1 + jednoprvkovy list se pred zapisem odbali (stejna "scalar-as-array-of-1" konvence jako uz existuje v `_eval_array_ref`). Skutecna multi-element pole (dim>1) beze zmeny.
- **Otevrene, NEIMPLEMENTOVANO** (uzivatel vyslovne odlozil): kdyz je SAMOTNY `out:` parametr pole s dim>1 (napr. `out:PO(5)`) a volajici by chtel vysledek zapsat jen CASTECNE do sveho vetsiho pole od daneho prvku (`T(3)` -> `T(3..7)`) - analogie k `P(1),N` adresaci u `in:` array-ref opcodu.

### 4. Interpret - DATA

- **Hodnoty smi byt vyrazy** (`12b792a`): `DATA,Q1,2 / DX(1), 0, 65 / DX(2), 0, 19` ted funguje. Kdyz je `count` DOSLOVNY LITERAL a cil ma znamy pevny pocet slozek na objekt (`DATA_CONSTANTS_PER_OBJECT`, presunuto z `gl3_ops.py` do `gl3_lang.py` kvuli cyklickemu importu), parser zna presny pocet hodnot uz pri parsovani a sbira je jako vyrazy (obecny `parse_expr_text`) pres libovolny pocet radku - misto puvodni "vypada radek jako konstanty" heuristiky. Bezpecnostni pojistka: kandidatni radek se rovnou zkusi cely naparsovat, pri neuspechu (uz je to jiny prikaz) se nekonzumuje - spatny pocet hodnot pak hlasi (jako drive) az runtime `GL3RuntimeError`, ne syntax chyba.
- **Otevrene, NEIMPLEMENTOVANO** (uzivatel vyslovne odlozil): `count` jako promenna/vyraz (ne literal) - zustava puvodni chovani (jen hole konstanty na pokracovacich radcich).

### 5. Nove opcody a opravy krivek

- **S10/T10** (`f35d394`): uzavrene/periodicke krivky. **POZOR** - prvni pokus (periodicke "phantom" rozsireni o 1 bod, volani stejne OTEVRENE `tangent_vectors()`) byl OVEREN JAKO CHYBNY (nesymetricky vysledek na symetrickem ctverci) - opraveno skutecnym cyklickym trojdiagonalnim resicem (`gerlib/gtrin.py: solve_cyclic_tridiagonal`, Sherman-Morrison, `gerlib/dspn.py: tangent_vectors_closed`).
- **Fix S01/T01 K=2** (`75cc326`): delka V1/VK byla chybne respektovana (spatne zkopirovano z S03, kde na delce ZALEZI) - ted normovana na smer, jako uz drive u K>2.
- **T03** (`587aa7b`): tenky wrapper nad S03 (stejny fortranovy zdroj dle uzivatele). Vedlejsi fix: S03 nikdy fakticky nekontrolovalo K<=128 (jen v docstringu).
- **Q02, Q15** (`057ad86`): jednoduche bodove operace bez fortranoveho zdroje, primo podle G10.md.
- **S47/T47** (`d3c3e74`): spojeni dvou krivek, vc. NEDOKUMENTOVANEHO parametru K (0=kazda strana spoje si necha svou tecnu, 1=tecna prvni krivky, 2=tecna druhe krivky, 3=prumer) - odvozeno uzivatelem ze zdrojoveho kodu S47.FOR (dodano uzivatelem), overeno. `closed` vysledne krivky se pocita NEZAVISLE na K, z puvodnich (neupravenych) tecen/poloh obou vstupnich krivek (presne jak to dela S47.FOR na puvodnich souborech pred K-patchovanim). Pribyla i `gerlib/angl70.py` (3D obdoba existujiciho `a510.py` - uhel dvou vektoru).
- **V00, V01, V20, V42, V41** (`956f6bd`, `5463fe4`, `4bc13c7`): jednoduche vektorove operace bez fortranoveho zdroje, primo podle G10.md. V20/V41 hlasi chybu na nulovem vektoru (kdyz je pozadovana nenulova delka) - POZOR, propaguje se jako obycejny `ValueError`, ne `GL3RuntimeError` (viz bod 6 nize).

### 6. Znama, dosud NEVYRESENA mezera (nikde konkretne nezadana, jen zjistena cestou)

`eval_expr`'s `OpCall` dispatch (v `gl3_interpreter.py`) chyta pri volani `OPERATIONS[opcode](*args)` jen `NoSolution` - jakakoliv jina vyjimka (napr. `ValueError`/`TypeError` z gerlib/geplib, jako u S01 s K=1, nebo V20/V41 na nulovem vektoru) propaguje jako HOLA vyjimka, NE ve standardnim `[Error] program/radek/operace` formatu zavedenem drive (Shrnuti 9). Netykalo se to zadneho z aktualne zadanych ukolu, takze zustava neresene - zminovano pro uplnost, kdyby na to Dusan chtel navazat.

### 7. Testy a stav

`pytest` (z korene repo): **23 passed**. Ostatni `test_*.py` skripty: vsechny OK krome stale stejne (rostouci) skupiny preexistujicich, na zadnem z tehle zmen nezavislych selhani zpusobenych kolizi `gerlib/types.py` se stdlib `types` pri PRIMEM skriptovem spusteni souboru lezicich uvnitr `gl3/gerlib/` (`cd`/`python3 gl3/gerlib/test_X.py` z korene vklada `gl3/gerlib` jako `sys.path[0]`) - tyhle testy VZDY projdou cistě, kdyz se spusti jako modul (`python3 -c "import gerlib.test_X as t; t.main()"` z `gl3/`) - overeno u kazdeho z nich. Aktualni seznam (17): `test_p66, test_p17, test_p21, test_p43, test_p58, test_p51, test_l00_and_op_registration, test_l42, test_v34, test_move_geom, test_d28, test_s01, test_serialize, test_p14, test_p40, test_v_vectors, test_plane_r01` (`geplib/`).

### 8. Otevrene body z drivejsich diskuzi (uzivatel odlozil, zadne z nich neni zapomenuto)

- Bod 1 (prazdne `in:` property = nedefinovana promenna, vyjimka `in:B`) - odlozeno, uzivatel slibil popsat "jak si to predstavuje" v dalsim kroku.
- `GL3Export.Placement` - vlastni/skladany placement - odlozeno.
- `CALL` s castecnym zapisem pole do pole (viz bod 3 vyse) - odlozeno.
- `DATA` s `count` jako promennou/vyrazem (viz bod 4 vyse) - odlozeno.
