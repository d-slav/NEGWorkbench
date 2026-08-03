# NEG/GL3 → FreeCAD – shrnutí stavu projektu (pokračování 4)

Navazuje na `NEG_GL3_shrnuti.md`, `_2.md` a `_3.md`. Tohle vlákno se
posunulo od prvního funkčního propojení s FreeCADem (stav na konci
minula) k **plně otestované trojici objektů `GL3Library`/`GL3Program`/
`GL3Export`** provozované reálně ve FreeCADu, a k **prvnímu kroku do
prostorové (3D) geometrie** (`DCOOS3`, `TRA23`, `Q00`, `U00`).

Na konci vlákna byl vytvořen git tag **`v0.1-fc-integration`** –
formální milník "napojení na FreeCAD hotové".

## Architektura – beze změny, jen doladěná

Tři vrstvy objektů (`GL3Library`/`GL3Program`/`GL3Export`) zůstávají
podle rozhodnutí z minula. Co se změnilo je **formát propojení mezi
objekty** a **spolehlivost** celého řetězce v reálném FreeCADu.

### Formát reference `"JmenoObjektu.JmenoVystupu[(Index)]"`

Nahradil původní dvojici property (`Source` [Link] + `OutputName`
[String]) na `GL3Export`, a stejným způsobem řeší i **composite `in:`
vstup** na `GL3Program` (dřív `NotImplementedError`, teď funguje – viz
`HLOCUT.gl3`, `in:P(2)`):

- Uživatel vidí/edituje **jednu** textovou property (`GL3Export.Input`,
  nebo přímo jméno GL3 parametru u composite vstupu, např. `P`) –
  čitelné, editovatelné, dá se vložit odkudkoli, formát
  `"TEHLO002.PO"`, volitelně s indexem prvku pole `"TEHLO002.PO(1)"`
  (`1` = první prvek – hodí se, když vstup/export čeká jeden prvek, ale
  zdrojový výstup je celé pole).
- Pod kapotou skrytá (`Hidden`) `App::PropertyLink` (`Source`, resp.
  `<jméno>_Link`), **synchronizovaná přes `onChanged()`** – FreeCAD ho
  volá synchronně hned při změně textu (i programově), takže skrytý
  Link je aktuální ještě před sestavením pořadí pro recompute. Díky
  tomu FreeCAD pořád vidí skutečnou závislost v grafu (správné pořadí
  recompute), i když uživatel edituje jen jednu prostou property.
- `gl3fc/gl3_props.py`: `parse_ref()` (regex, `(obj, výstup, index)`),
  `add_hidden_link()` (skutečně skrytá Link, opak `add_property()`).

### Composite výstup: `App::PropertyPythonObject` → `App::PropertyString`

`GL3Program`'s `out:` composite property (dřív holý Python dict) teď
drží **skutečný kompaktní JSON text** (`gerlib/serialize.dump_json(...,
indent=None)` – žádné `\n`, jinak by řádek v Property View narostl na
víc řádků). Status `ReadOnly` (počítaná hodnota, needitovat ručně).
Důvod: `PropertyPythonObject` nemá v Property View editor – property se
nezobrazí vůbec bez "Show all", a i pak jen jako šedý needitovatelný
fallback. `PropertyString` má běžný textový editor, vidět vždy.
Přesnost floatů se JSON cyklem neztrácí (Python `json` kóduje floaty
přes `repr()` – bit-přesný round-trip).

Stejně tak string/file `in:` parametry (`BJM` apod.) přešly z
`App::PropertyFileIncluded` (kopíruje vybraný soubor do `.FCStd`
dokumentu, čte z dočasné rozbalené kopie) na `App::PropertyFile` (jen
cesta, žádné kopírování) – opravený bug, ne designové rozhodnutí.

## Prostorová (3D) geometrie – první krok

Nový balíček **`gl3/geplib/`** (GEometrie Prostorová LIBrary), oddělený
od `gerlib` (ten zůstává čistě 2D port originálního Fortranu). `geplib`
drží prostorové GL3 příkazy, pro které originální Fortran zdroják
**není k dispozici** – implementováno přímo podle jazykové
specifikace:

- **`DCOOS3,vi,vg1,vg2,vg3`** – definice prostorové s.s. č. `vi`
  (1..10): počátek (`vg1`, bod) + směr osy x' (`vg2`, Q/U/M) + "nápověda"
  pro osu y' (`vg3`, Q/U/M, Gram-Schmidt). Osa z' = `ex' × ey'` –
  soustava je vždy pravotočivá.
- **`TRA23,pg1,pg2,vi1,vi2`** – transformace z roviny do prostoru pomocí
  soustavy `vi2`. Podporované typové dvojice zatím: `P→Q` (bod),
  `S→T` (křivka/Spline), `E→H` (řetězec/diskretizovaná křivka, výstup
  `E01`). Rozlišení pole (`P(1),N`, počítá se `vi1`) vs. jednotlivý
  objekt (celá křivka, `vi1` se netýká – "platí pouze pro pole") se řeší
  až za běhu podle skutečné hodnoty `pg2`, protože GL3 jazyk sám typ
  staticky nerozlišuje.
- **`Q00`/`U00`** – `QM=Q00>D1,D2,D3` (bod třemi souřadnicemi),
  `UM=U00>D1,D2,D3` (vektor třemi složkami) – jednoduché konstruktory
  pro testování bez nutnosti spoléhat na builtin konstanty.
- Souřadnicové soustavy (`Interpreter.coordinate_systems`, 1..10) jsou
  **izolované na jeden běh** (nový `Interpreter()` = nový běh, tj.
  každé `GL3Program.execute()`), ale sdílené přes celý `CALL` strom
  uvnitř jednoho běhu – přesně podle zadání.
- Point/Vector/Line/Spline/Curve zůstávají jednotné pro 2D i 3D použití
  (`gerlib.types`) – rozdíl `P` vs. `Q` (`S` vs. `T`, `E` vs. `H`) je
  jen jazyková konvence GL3 prefixu jména proměnné, ne jiný Python typ.
  `geplib` proto importuje typy přímo z `gerlib.types`.

Otestováno na dvou úrovních – čistá geometrie (ortonormalita,
pravotočivost, Q/U/M ekvivalence, degenerovaný vstup) a skutečný GL3
zdrojový text (`parse_program` + `Interpreter.run()`, včetně chybových
stavů a izolace mezi běhy).

## Opravené bugy z reálného testování (chronologicky)

1. **`claimChildren()` po znovuotevření dokumentu** – `Export` se
   zobrazoval ve stromu na stejné úrovni jako `Program`, ne jako jeho
   potomek. Příčina: detekce přes `Proxy.Type` (Python atribut,
   nastavený až v `__init__()`/`onDocumentRestored()`) – po otevření
   souboru není zaručeno pořadí `onDocumentRestored()` (pro všechny
   objekty) vs. `claimChildren()` (na `Program` ViewProvideru). Oprava:
   detekce přes FC property (`Source`+`Input`) – ty jsou součástí stavu
   objektu samotného, spolehlivé bez ohledu na Proxy lifecycle timing.
2. **Nutnost nejdřív aktivovat workbench, pak teprve otevřít soubor** s
   NEG objekty. Příčina: `gl3fc.gl3_library/gl3_program/gl3_export`
   (Proxy třídy) se importovaly až uvnitř `Gui.Command.Activated()` –
   `Workbench.Initialize()` (kde se to importuje) se volá až při
   **první aktivaci** workbenche v GUI. Oprava: nový **`Init.py`**
   (App-level, bez Gui) – FreeCAD ho spouští pro každý doplněk vždy při
   startu (i konzole), bez ohledu na aktivaci workbenche.
3. **"Unnamed#TEHLO still touched after recompute"** – `GL3Export.
   execute()` volalo `source.touch()` uprostřed už probíhající
   recompute davky. Přesunuto do `create()` (zavolá se jednou, před
   prvním `doc.recompute()`).
4. **Visibility se po každém recomputu přepisovala na `True`** – i pro
   objekt, co si uživatel ručně schoval. `Visibility = True` se teď
   nastavuje jen jednou, při vytvoření.
5. **Skutečná kaskádová viditelnost (parent hides children) –
   pokus a revert.** Zkusili jsme `App::GeoFeatureGroupExtension` +
   `Gui::ViewProviderGeoFeatureGroupExtensionPython` (mechanismus
   `PartDesign::Body`) – vytvořilo to ale **cyklus v grafu závislostí**
   (`Group` znamená hranu Program→Export, `Source` znamená hranu
   Export→Program) a FreeCAD recompute úplně přestal fungovat ("The
   graph must be a DAG"). **Revert.** Independentní `Visibility` mezi
   `Program` a `Export` beze změny (bez kaskádování žádným směrem) je
   momentálně finální stav – viz otevřené otázky níže.
6. **Odebraný parametr ze `.GL3` hlavičky zůstával "viset" navždy** na
   objektu – `_sync_properties()` property jen přidávala, nikdy
   neodebírala. Oprava: sestaví se `current_names` (aktuální hlavička)
   a na konci se odstraní každá `GL3 In`/`GL3 Out` property, co v ní
   není (`GL3`-skupinové, `SourceFile`/`Library`, se nikdy neodstraňují).
7. **Přidaný parametr se neprojevil bez smazání+znovuvytvoření
   objektu.** `_sync_properties()` sama o sobě funguje správně (čte
   soubor od nuly při každém `execute()`), problém byl, že FreeCAD
   nemá důvod objekt označit jako "touched", když se změní jen OBSAH
   souboru na disku (cesta `SourceFile` zůstává stejná). Nový příkaz
   **"Reload GL3 Program"** (`obj.touch()` + `doc.recompute()`) i
   obecnější **auto-recompute na vstupu** (změna `SourceFile`/
   `Library`/`GL3 In`/`Input` rovnou spustí `Document.recompute()`).

## Nové GUI příkazy (celkem 4 + workbench sám)

```
NEG_CreateLibrary   - vytvoreni GL3Library
NEG_CreateProgram   - vytvoreni GL3Program z .GL3 souboru (file dialog)
NEG_CreateExport    - vytvoreni GL3Export z vybraneho composite vystupu
                      (dialog na vyber vystupu + volitelny index prvku pole)
NEG_ReloadProgram   - vynuti znovunacteni SourceFile + resync in/out property
```

Ikony ve stromu (`getIcon()`) teď používají vlastní `.svg` **bez**
symbolu "+" (ten patří jen na toolbar tlačítko "Create...", ne na
existující objekt ve stromu) – `Resources/icons/library.svg`,
`program.svg`, `export.svg` – oddělené od `create_*.svg` (i tam, kde je
teď obsah stejný, je do budoucna připraveno na nezávislý redesign).

## Repozitář

`https://github.com/d-slav/NEGWorkbench`. Bundly/diffy se dál předávají
ručně (Claude nemá push přístup) – **důležité: vždy nejdřív ověřit
skutečný `git log --oneline -3` na straně uživatele**, tohle vlákno
narazilo na situaci, kdy se lokální stav rozešel s tím, z čeho Claude
vycházel (uživatel mezitím sám/v jiné session udělal vlastní commity –
ikony, `HLOCUT.gl3` úpravy, `gerlib` drobnosti) – řešeno čerstvým
klonem a ručním porovnáním, ne slepou aplikací starých bundlů.

Tag **`v0.1-fc-integration`** označuje stav "napojení na FreeCAD
hotové, dál jde geometrie".

## Testy (bez FreeCADu, `gl3/` adresář)

```bash
python3 gl3_test.py                          # interpret - regrese
python3 -m gerlib.test_serialize              # serializace
python3 -m gerlib.test_s01                    # S01 vs S03
python3 test_dcoos3_tra23.py                  # DCOOS3/TRA23/Q00/U00 - cista geometrie
python3 test_dcoos3_tra23_interpreter.py      # DCOOS3/TRA23/Q00/U00 - skutecny GL3 zdroj
python3 -m gl3fc.test_offline                 # GL3Library/GL3Program (mock FC)
python3 -m gl3fc.test_props_offline           # Hidden/ReadOnly status wiring
python3 -m gl3fc.test_parse_ref_offline       # parse_ref() vc. indexu "(N)"
python3 -m gl3fc.test_export_offline          # GL3Export dispatch + Bezier matematika
python3 -m gl3fc.test_gl3_export_offline      # GL3Export.execute() end-to-end
python3 -m gl3fc.test_claim_children_offline  # strom prezije restart FreeCADu
python3 -m gl3fc.test_composite_input_offline # composite in: (HLOCUT), auto-recompute, stale property
# z korene repo:
python3 test_gl3_commands_offline.py          # vsechny 4 Gui prikazy (mock FC/FCGui)
python3 test_init_no_file_offline.py          # Init.py registruje tridy uz pri startu
python3 test_initgui_no_file_offline.py       # verna simulace FreeCAD exec() mechanismu
```

14 testovacích souborů, 0 známých regresí.

## Otevřené otázky / co zbývá

- **Kaskádová viditelnost (parent hides children)** – `GeoFeatureGroup
  Extension` cestou nejde (cyklus v grafu závislostí, viz bug #5 výše).
  `Visibility` je momentálně nezávislá mezi `Program` a `Export`.
  Nevyzkoušená alternativa: `GL3Export.execute()` by mohl kontrolovat
  `source.ViewObject.Visibility` a při skrytém zdroji nastavit prázdný
  `Shape` (bez zásahu do vlastní `Visibility` property) – nevýhoda:
  změna se projeví až po recomputu, ne okamžitě jako u `PartDesign`.
- **`S09`/`T09`** (uzavřené splajny) – pořád blokováno na `GTRIP.FOR`.
- **Další typové dvojice `TRA23`** (`V→U`, `L→M`, `C→G`) – přidají se
  stejným způsobem, až budou potřeba.
- **Export `Line`/`Plane` a dalších 3D typů** z `GL3Export` – zatím
  neimplementováno.
- **Systémová SUBRA** (typ 3, globálně dostupná) – vědomě odloženo.
- **In-app editor `.GL3` kódu** – zatím jen externí soubor + "Reload
  GL3 Program"/auto-recompute.
- **Editace `Library.SearchPaths` přes UI dialog** – zatím jen ruční
  úprava property (funguje, `App::PropertyStringList` má vestavěný
  editor, ale žádný dedikovaný Gui příkaz na to není).
