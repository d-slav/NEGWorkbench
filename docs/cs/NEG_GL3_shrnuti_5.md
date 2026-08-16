# NEGWorkbench — shrnutí sezení

Chronologický přehled toho, co bylo v tomto sezení uděláno. Detaily a zdůvodnění
jsou v jednotlivých commitech (`git log`).

## 1. Dokončení SCARA.GL3 — 13 chybějících GL3 opcodů

Doplněny a otestovány: `L02`, `P49`, `C49`, `P47`, `C02`, `L20`, `NPO`, `P48`,
`P42`, `D50`, `P22`, `L45`, `E45`.

- Kde nebyl dostupný Fortran zdroj (`GLPLY`→`GLDPL3`, `GLPAT`), nahrazeno
  nezávislou, ale funkčně rovnocennou implementací (vlastní hledač kořenů
  polynomu, vždy hledání nejbližšího bodu na křivce místo cachované návaznosti).
- Přidán příkaz `ACCUR` (globální přesnost pro `E45`/budoucí `H45`/`H96`),
  izolovaný per běh interpretu.
- Opraveny dvě reálné mezery v interpretu nalezené při ověřování:
  - `SCALE` nyní umí pracovat i s jediným (ne polovým) objektem.
  - `SCALE` nyní umí škálovat i typ `Spline` (`S`).
- **Výsledek:** `SCARA.GL3` (původní motivace celého projektu) proběhne
  od začátku do konce na reálných datech (`E374.TXT`) i v reálném FreeCADu.

## 2. Reorganizace adresářové struktury

Podle zadání uživatele: `gl3data/`, `gl3examples/`, `gl3sys/`, `gl3test/`
na úrovni kořene doplňku (dřív vše pod `gl3/examples/`).

- Výchozí `SearchPaths` pro `GL3Library` ukazuje jen na `gl3sys/`.
- `gl3data/`, `gl3examples/`, `gl3sys/` jsou plně v režii uživatele — žádná
  úprava tam nesmí rozbít Python testy. `gl3test/` obsahuje **vlastní kopie**
  fixture souborů, na kterých stojí celá regresní sada, nezávisle na živých
  adresářích.
- Git tag `v0.2-scara-complete`.

## 3. Vstup dat z FreeCADu do GL3 programu

- Composite `in:` vstup (např. `in:P(N)`) teď umí číst i přímo nativní
  seznam bodů z FreeCAD geometrie (typicky `.Points` u Draft BSpline/Wire),
  ne jen JSON výstup jiného GL3 objektu. Beze změny syntaxe hlavičky SUBRO.
- Plný import FreeCAD křivky (Edge/Wire → GL3 křivka/prostorový typ) zvážen
  a zamítnut jako zbytečně složitý — bodové pole + `S01`/`S03` v programu
  stačí.
- `GL3Program`: dialog pro výběr `.GL3` souboru si pamatuje naposledy použitý
  adresář (FreeCAD `ParamGet`, přežije zavření FreeCADu).

## 4. `NPO` na poli bodů + oprava `DIMEN`

- `NPO` nově funguje i na obyčejném poli bodů (délka pole), nejen na
  `Curve`/`Spline` — potřeba pro `in:P(N)` vstupy s neznámou délkou předem.
- Nalezena a opravena reálná chyba interpretu: `DIMEN` dřív tiše přepsal
  i už svázaný `in:` vstupní parametr na prázdné pole. Teď vyhodí jasnou
  chybu.

## 5. `S51` — ekvidistantní (rovnoběžná) křivka

Nejsložitější dosud implementovaná procedura — přesná ekvidistanta kubiky
obecně není kubika, `S51` proto po segmentech aproximuje novou Hermitovou
kubikou a adaptivně dělí, když odchylka od skutečné ekvidistanty (měřeno
`SGPAT`) překročí přesnost.

- `FS51`, `SGPAT` přeloženy 1:1. `DNSBM` (Brentova metoda, Hitachi 1980)
  nahrazena vlastním tlumeným Newton-Raphsonem se stejným kontraktem.
- Po testování na reálné křivce (`SPLTES.GL3`) nalezeny a opraveny dva
  skutečné bugy: špatné znaménko při porovnání odchylky (záporný offset
  vždy selhal) a chybná logika počítání pokusů o zmenšení segmentu.
- Na výslovné přání uživatele: vynechané `D2` (přesnost) používá aktuální
  globální `ACCUR` — vědomý odklon od originálu (ten by nastavil `ACCUR=0`).
- **Otevřený bod:** na jedné konkrétní reálné křivce (segment blízko
  inflexního bodu) `offset=3` s `ACCUR=0.01` u nás stále selhává, ačkoliv
  na originálním systému prochází. Diagnostikováno až k neshodě v konvergenci
  Newtona vs. původní Brentovy metody — nedořešeno, odloženo.

## 6. Nové jednoduché a tečné konstrukce

`P00`, `C00`, `C01` (triviální), `C32` (tečna dvěma přímkám), `C34` (tečna
dvěma kružnicím) — bez Fortran zdroje, odvozeno ze slovního popisu,
implementováno s vysokou důvěrou. `C33` (tečna přímce a kružnici) má jednu
otevřenou nejednoznačnost u výběrového čísla `K1`, jasně označenou v kódu.
Testy ověřují geometrickou správnost (skutečná tečnost, správný poloměr)
nezávisle na této nejistotě.

## 7. Oprava příkazu `DATA`

Původní implementace byla jen "jedna řádka čísel = holé skaláry". Podle
manuálu opraveno na skutečné chování: cíl může být indexovaný (`P(2)`),
typ objektu (bod/vektor/přímka/kružnice/skalár/int/text) se pozná z
prefixu jména a určuje počet konstant na objekt, hodnoty se čtou z
libovolného počtu následujících řádků, víc objektů může být na jednom
řádku. Zatím jen rovinné typy (`A,D,I,B,P,V,C,L`) — 3D typy vrací jasnou
chybu místo tichého selhání.

## 8. Rozdělení chyb do tří kategorií

- **1 — Python bug:** beze změny, standardní traceback.
- **2 — chyba v GL3 programu** (`GL3RuntimeError`, vždy zastaví běh):
  neexistující proměnná, neznámý opcode, použití `undefined` hodnoty ve
  výpočtu.
- **3 — varování** (`gerlib.errors.NoSolution`): geometrická konstrukce
  nemá řešení — legitimní stav, ne bug. Cíl přiřazení dostane `None`
  (využívá se existující mechanismus `IFN`/undefined), běh pokračuje.
  Řízeno příkazy `MESS`/`NOMESS` (`disp_warning`, izolováno per běh).

Formát hlášky: `[Warning|Error] jmeno_programu/cislo_radku/operace: text`
(FreeCAD `Console.PrintWarning`/offline `print`). Do AST doplněna čísla
řádků (dřív nebyla vůbec). Pilotně zapojeno na tečných kružnicích
(`C32`/`C33`/`C34`), zbytek `gerlib` se bude přeznačovat postupně později.

## Stav repozitáře

Všechno je commitnuté na `master`, poslední tag `v0.2-scara-complete`.
Celá Python regresní sada (gerlib testy, `gl3_test.py` vč. end-to-end
`TEHLO→SCARA`, `gl3fc` offline testy, root-level testy) prochází.