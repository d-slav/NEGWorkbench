# NEG/GL3 → FreeCAD – shrnutí stavu projektu (pokračování 3)

Navazuje na `NEG_GL3_shrnuti.md` a `NEG_GL3_shrnuti_2.md`. Tohle vlákno
se posunulo od hotového jazyka/interpretu (stav na konci minula) k
**funkční FreeCAD integraci** – od prvního prototypu exportu křivky až po
**reálně vyzkoušenou parametrickou plochu křídla** ve FreeCADu – a k
**prvnímu kroku směrem ke skutečnému instalovatelnému doplňku**.

## Cíl projektu (beze změny)

Integrace jazyka NEG/GL-3 (LET Kunovice, nyní Aircraft Industries a.s.)
do FreeCADu jako parametrický nástroj pro generování geometrie
(typicky profily křídel/vrtulí). Nezávislá reimplementace v Pythonu, ne
odvozeno z originálních Fortran zdrojáků (jen názvy opcodů/konvence
zachovány kvůli dohledatelnosti).

## Architektura – tři vrstvy FreeCAD objektů (rozhodnuto a implementováno)

1. **`GL3Library`** (`gl3fc/gl3_library.py`) – drží `SearchPaths`
   (seznam `{"path":..., "hidden":...}`) – adresáře, kde se hledají
   `<JMÉNO>.GL3` soubory volané přes `CALL`. `hidden` zatím bez
   funkčního významu – připraveno pro budoucí systémová SUBRA (typ 3,
   zatím odloženo).
2. **`GL3Program`** (`gl3fc/gl3_program.py`, `Part::FeaturePython` – má
   vlastní `Placement`) – typ 1: FreeCAD objekt, který FreeCAD skutečně
   spouští. `in:`/`out:` property se generují automaticky ze `SUBRO`
   hlavičky vlastního `.GL3` souboru. `CALL` na další SUBRO (typ 2, např.
   `HLO`) se řeší líně přes `Gl3FileRegistry` a připojenou `Library`.
   Composite vstup **není podporován** (architektonické rozhodnutí –
   composite smí do GL3 jen přes `Link` z jiného GL3 objektu, zatím
   neimplementováno, není to zatím potřeba).
3. **`GL3Export`** (`gl3fc/gl3_export.py`, `Part::FeaturePython`) – z
   vybraného composite výstupu `GL3Program` vyrobí skutečnou nativní
   geometrii (`Part.Shape`) s reálným `Placement` (převzatým 1:1 od
   zdrojového `GL3Program`). Cesta je jednosměrná: `GL3Program →
   GL3Export`, nikdy zpátky. `claimChildren()` na `GL3Program`u zanoří
   Export objekty ve stromu.

Editace `.GL3` zdroje je (zatím záměrně) jen přes **externí soubor** –
žádný in-app editor. Auto-expand SUBRO jako child objektů (varianta D
z diskuze) byl zavržen kvůli křehkosti (ochrana proti smazání sdíleného
objektu) ve prospěch varianty C (Library).

## Serializace (`gerlib/serialize.py`) – hranice GL3 ↔ Export

Composite hodnoty (Point/Vector/Line/Circle/Plane/Spline/Curve) se
serializují do JSON-safe "slot" dictu, který Export čte **beze
závislosti na `gerlib`** (architektonické rozhodnutí – GL3 modul a
Export modul mají zůstat oddělené). Formát (po zpětnovazebním
zjednodušení – **v2**):

```python
{"defined": False}                                    # nedefinovano
{"defined": True, "value": 15.2}                      # skalar
{"defined": True, "type": "Array", "items": [slot,...]}
{"defined": True, "type": "Point", "x": 1.5, "y": -2.25, "z": 0.0}
```

`defined` je **jen na celé hodnotě a na prvcích pole** – ne na každém
vnořeném poli už definovaného objektu (`Point.x/y/z`, `Line.origin`,
`Spline.closed` jsou holé hodnoty) – přesně tam, kde GL3 opravdu může
mít "díru" (`IFN` idiom, `_set_indexed`), nic víc. `dump_json()`/
`load_json()` dávají skutečný JSON text (uvozovky, `true`/`false`) –
Pythonův `repr()` slovníku v FreeCAD konzoli (apostrofy, `True` s
velkým písmenem) není bug, jen jiný způsob výpisu.

## Dvě metody prokládání křivky – S03 vs. S01

Uživatel dodal originální Fortran zdrojáky (`SPLINE.FOR`, `GLSPL.FOR`,
`DSPN.FOR`, `DSPP.FOR`), na jejichž základě byl implementován **`S01`**
vedle už existujícího `S03`:

- **`S03`** (`gerlib/dsn.py`) – **uniformní** parametrizace, ignoruje
  skutečné vzdálenosti mezi body.
- **`S01`** (`gerlib/dspn.py`, `gerlib/s01.py`) – **chordální**
  (chord-length) parametrizace – blíž tomu, jak typicky parametrizují
  křivky i CAD jádra (OCC). Reálně odlišná křivka (~0.066 mm na profilu
  `E374` s tětivou 15.2 mm – ověřeno testem, ne jen šum).
- Objevený strukturální rozdíl: u chordální parametrizace nemá vnitřní
  uzel jednu sdílenou tečnu (na rozdíl od `S03`) – každý segment
  škáluje svou vlastní délkou tětivy. `Spline` typ proto nese
  `opcode`/`parametrization` (vlajka původu – i pro budoucí pravidla,
  které křivky lze použít pro plochy) a `segment_tangents` (obecná
  reprezentace tečen po segmentech, `segment_tangent_pair(i)` funguje
  stejně pro `S03` i `S01`).
- **`S09`/`T09`** (uzavřená verze) zůstává **blokovaná** – chybí
  `GTRIP.FOR` (periodický tridiagonální řešič); `DSPP.FOR` už máme, ale
  bez `GTRIP.FOR` by šlo jen hádat.

## Ověřeno v reálném FreeCADu

- `TEHLO` (přes `GL3Program`) + `Export` (`S`, `PO`) – funguje, výstupy
  odpovídají.
- **Dva `TEHLO` objekty → plocha křídla** – po změně profilu, velikosti
  (`DH`) i umístění (`Placement`) celého `TEHLO` objektu se plocha
  **správně přepočítala**. Triviální úloha, ale potvrzuje, že
  architektura reálně funguje pro parametrizaci práce s plochami.
- `S01` zatím čeká na večerní/reálné vyzkoušení (kód i testy hotové).

## Opravené bugy z reálného testování (chronologicky)

1. Composite/skalární property skryté, dokud se nezapnulo "Show
   hidden" → `gl3fc/gl3_props.py` (`add_property()` explicitně
   odkrývá).
2. Objekty neviditelné, dokud se soubor neuložil a znovu nenačetl →
   `Visibility = True` se (znovu) nastavuje **až po** existenci
   reálného obsahu (Shape/property), ne jen jednou při vytvoření.
3. Export objekty nezanořené pod `GL3Program` ve stromu → oprava
   `claimChildren()` (porovnání přes jméno+dokument, ne Python `is` –
   FreeCAD může vracet nový wrapper při každém čtení `PropertyLink`) +
   `source.touch()` v `GL3Export.execute()`, aby FreeCAD strom
   přehodnotil.
4. Křivka byla 34 samostatných Bézierových hran (šlo vybírat jednotlivé
   segmenty) → export teď staví **jednu** `Part.BSplineCurve` (stejné
   kontrolní body, jen jinak zabalené – standardní "Bezier segmenty
   jako jeden BSpline", násobnost uzlu = stupeň).
5. `InitGui.py` – FreeCAD ho spouští přes `exec()` **uvnitř funkce** bez
   explicitních `globals`/`locals` → cokoliv na nejvyšší úrovni
   souboru přiřazené (`_WB_DIR = ...`) skončí v oddělené "locals" dict,
   **neviditelné** zevnitř těla třídy/metod (ty koukají jen do
   skutečných globals). Řešení: třída i každá metoda si vše potřebné
   importuje/počítá **znovu, ve svém vlastním scope** – nic nezávisí na
   proměnné z vrcholu souboru. Ověřeno testem, který věrně simuluje
   FreeCAD `exec()` mechanismus (ne naivní `exec(code, jedna_dict)`,
   který dal falešně pozitivní výsledek).

## FreeCAD Workbench – první krok

Repo kořen == obsah `Mod/NEGWorkbench/` (funguje po zkopírování/
naklonování rovnou):

```
InitGui.py           - Gui.Workbench registrace, toolbar/menu
gl3_commands.py      - Gui.Command definice (zatim: Create GL3 Library)
gl3_wb_paths.py       - pomocny modul (spolehlivy __file__, viz bug #5)
Resources/icons/      - 2 rucne psane SVG ikonky
translations/         - prazdne, pripraveno na budouci .ts/.qm
```

Lokalizace připravena (`QT_TRANSLATE_NOOP`, zdrojový jazyk angličtina),
žádný `.ts`/`.qm` zatím neexistuje. **Zatím jen jeden příkaz** – další
(`GL3Program` z `.GL3` souboru, `GL3Export`, editace `Library` search
paths) přijdou postupně, jeden po druhém, až tenhle první krok bude
spolehlivě fungovat.

## Repozitář

Veřejný GitHub repozitář: `https://github.com/d-slav/NEGWorkbench`
(MIT licence, copyright Dušan Slavětínský). Historie: ~10 commitů,
`Co-authored-by: Claude <noreply@anthropic.com>` v textu. Kvůli
sandboxovému prostředí (Claude nemá přístup k pushnutí) se změny
předávají jako `git bundle` (a nově i jako `git diff` na vyžádání) k
ručnímu pullu/pushi.

## Testy (bez FreeCADu, `gl3/` adresář)

```bash
python3 gl3_test.py                    # interpret - regrese
python3 -m gerlib.test_serialize        # serializace v2
python3 -m gerlib.test_s01              # S01 vs S03 na realnych datech
python3 -m gl3fc.test_offline           # GL3Library/GL3Program (mock FC)
python3 -m gl3fc.test_export_offline    # GL3Export dispatch + Bezier matematika
# z korene repo:
python3 test_gl3_commands_offline.py    # workbench prikaz (mock FC/FCGui)
python3 test_initgui_no_file_offline.py # verna simulace FreeCAD exec() mechanismu
```

## Otevřené otázky / co zbývá

- **`S09`/`T09`** (uzavřené splajny) – blokováno na `GTRIP.FOR`.
- **Composite `in:` přes `Link`** (napojení výstupu jednoho GL3 objektu
  na vstup druhého, ne jen přes soubor) – zatím neimplementováno,
  vyhazuje jasnou `NotImplementedError`.
- **Export `Line`/`Plane`/3D typů** (`Q,U,R,M,G,T,H,F`) – zatím
  neimplementováno (nejednoznačné číslování složek u `M`/`G`, viz
  minulé shrnutí).
- **Systémová SUBRA** (typ 3, globálně dostupná, ne ve stromu) –
  vědomě odloženo.
- **In-app editor `.GL3` kódu** – zatím jen externí soubor + recompute.
- **Další workbench příkazy** – vytvoření `GL3Program`/`GL3Export` přes
  UI (ne jen Python konzoli), editace `Library.SearchPaths` přes UI.
- **Auto-expand SUBRO jako child objektů** (varianta D) – zavrženo pro
  teď kvůli křehkosti, může se vrátit později jako čistě kosmetická
  nadstavba.
