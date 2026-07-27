# NEG/GL3 → FreeCAD – shrnutí stavu projektu

## Cíl projektu

Integrace vlastního geometrického jazyka **NEG** (Numerická Etalonní Geometrie,
Let Kunovice), konkrétně jeho konstrukční podmnožiny **GL-3**, do FreeCADu.
Motivace: hobby tvorba modelů letadel/vrtulníků, konkrétně generování ploch
povrchu zadaných parametricky (typicky křídelní profily), tak aby změna
vstupních dat automaticky přepočítala navazující geometrii.

Explicitně **vyřazeno** z rozsahu: technologické příkazy (CNC/obrábění) a
kreslicí příkazy směřující do CL2 (postprocesor obráběcího stroje) – GL-3 byl
v originále APT-like CAM jazyk, ale pro FreeCAD dává smysl jen geometrická
konstrukční vrstva + řízení běhu.

## Klíčová architektonická rozhodnutí

1. **Dva oddělené moduly:**
   - **GL3 modul** – zpracuje jeden GL3 podprogram jako FreeCAD objekt
     (plánováno: `App::FeaturePython` s vlastním `Placement`, podobně jako
     Sketch – lokální souřadný systém, umístěný v prostoru).
   - **Export modul** – z vybraného výstupu GL3 objektu vyrobí skutečný
     nativní FreeCAD objekt (s reálným `Placement`, ne jen kosmetickým
     Shape) použitelný dál v Attachmentu/Sketch external geometry/atd.
     Cesta je jednosměrná: GL3 → Export → FreeCAD. Nikdy zpátky.

2. **Typový systém (co smí téct kam):**

   | Typ | Příklad prefixu | Vstup z FC | Vstup z jiného GL3 | Výstup zpět do FC |
   |---|---|---|---|---|
   | Skalár | D, K, I | ano (konstanta i expression) | ano | ano |
   | Řetězec/soubor | B | ano, jen konstanta (cesta) | ne | ne |
   | Složený + pole | P, L, C, S, E, Array[...] | **ne** | ano (Link+String) | ne (jen přes Export) |

   Do GL3 smí zvenčí (z FreeCADu) téct **jen skaláry a cesty k souborům**.
   Geometrie (body, přímky, kružnice, křivky, pole) vzniká výhradně uvnitř
   GL3 a ven z GL3 světa se dostává jen přes Export modul.

3. **Placement transformace** se týká výhradně composite typů nesoucích
   polohu – skaláry a řetězce jsou vůči Placementu invariantní.

4. **Podprogram volaný uvnitř jiného (inline)** sdílí stejný souřadný
   systém jako volající – žádná další transformace. Volání s vlastním
   umístěním (relativním k volajícímu) je otevřená možnost pro budoucno,
   zatím neřešeno.

5. **GOTO se v jazyce obecně nepodporuje.** Jediný nalezený reálný idiom
   (návěští + zpětný podmíněný skok = "opakuj dokud") se automaticky při
   parsování překládá na strukturovaný `RepeatWhile` blok. Jiný GOTO
   parser odmítne s jasnou chybou.

6. **`in:`/`out:` je v hlavičce `SUBRO` povinné**, explicitně u každého
   parametru (např. `SUBRO/SCARA/in:SP,out:SS,out:CNAB`). Nahrazuje to
   dřívější pokus o automatické odvození z použití v těle (heuristika byla
   nespolehlivá – prokázáno na `XPROC`, kde heuristika chybně určila `K`
   jako výstup kvůli způsobu volání `HLO`). Účel: donutit vědomé rozhodnutí
   při portování starého kódu, ne slepé převzetí.

7. **P49 a analogické "kopírovací" operace** (`C49`, ...) byly v originále
   nutné jen kvůli historické absenci hodnotového přiřazení. V novém jazyce
   se řeší tím, že vnitřní geometrické typy budou **immutable** – obyčejné
   přiřazení je vždy bezpečná kopie hodnoty, žádná zvláštní operace není
   potřeba.

## Stav kódu (adresář `gl3/`)

- `gl3_lang.py` – lexer, AST, parser. Zvládá: přiřazení, aritmetické výrazy
  s vnořenými `OPCODE>args` voláními, `DO/ENDDO`, `IFx/cond/THEN...ENDIF`,
  krátké `IFx/cond/akce`, `DIMEN`, `DATA`, `CALL/name/args`, komentáře (`*`
  na začátku řádku), povinnou `in:`/`out:` anotaci v `SUBRO` hlavičce,
  automatický překlad GOTO idiomu na `RepeatWhile`.
- `gl3_ops.py` – registr operací (`OPERATIONS`) a příkazů (`COMMANDS`).
  Všechny geometrické operace (`D10`, `P48`, `C02`, `S01`, `SCALE`, ...) jsou
  zatím **stub** (vyhodí `NotYetImplemented` s popisem) – čekají na Fortran
  zdrojáky. `ABS` je jediná plně funkční (triviální).
- `gl3_analysis.py` – `get_param_directions()` čte směr přímo z anotace.
  `suggest_directions()` je zachovaná stará heuristika, používá se jen jako
  pomocný návrh při ručním anotování starého zdroje, nikdy automaticky.
- `gl3_interpreter.py` – prochází AST, volá `OPERATIONS`/`COMMANDS`, řeší
  vnořené `CALL` (kopie vstupů dovnitř, kopie výstupů ven – žádné sdílení
  paměti mezi podprogramy), `DoLoop`, `IfBlock`, `IfShort`, `RepeatWhile`.
- `gl3_test.py` – ověřovací skript bez závislosti na FreeCADu. Testováno na
  `TEST1.GL3` (kompletně doběhne), `SCARA.GL3` a `XPROC.GL3` (obě korektně
  zastaví na první chybějící operaci / chybějícím `HLO` v registru).
- `examples/` – kopie `TEST1.GL3`, `XPROC.GL3`, `SCARA.GL3` s novou povinnou
  `in:`/`out:` syntaxí (originály v uploads jsou needitovatelné a navíc
  **uživatel musí svoje reálné `.GL3` soubory přepsat na tento formát ručně**).

Samostatně (mimo `gl3/`) vznikly i dva samostatné FreeCAD makro-moduly
z dřívější fáze experimentování s Placement/Export konceptem:
- `QUPoint.py` – jednoduchý FeaturePython s `Q` (bod) a `U` (vektor),
  kosmetický Shape jen pro vizuální kontrolu.
- `NegExport.py` – obecné extraktory (`NegPointExport`, `NegLineExport`),
  které z libovolného zdrojového objektu vytáhnou pojmenovanou Vector
  property a postaví z ní objekt se **skutečným** `Placement` (ne jen
  kosmetickým Shape) – použitelný přímo jako Attachment support/External
  geometry jinde ve FreeCADu. Tohle byl koncepční předchůdce dnešního
  "Export modulu" v zobecněné podobě.

## Co ještě chybí / další kroky

1. **`HLO.GL3`** – uživatel ho dodá (je to standardní GL3 podprogram, ne
   speciální systémová rutina, jak se původně předpokládalo).
2. **Fortran zdrojáky** k použitým geometrickým operacím (`D10`, `D11`,
   `D30`, `D50`, `P10`, `P13`, `P22`, `P42`, `P44`, `P47`, `P48`, `L02`,
   `L20`, `L45`, `C02`, `C49`, `S01`, `E45`, `NPO`, `SCALE`) – uživatel je
   zatím nemá u sebe, dodá později.
3. **`gl3_object.py`** – FreeCAD `FeaturePython` wrapper: dynamické
   generování properties podle `SUBRO` hlavičky (skalární nativní
   property vs. Link+String pro composite vstupy, `PropertyPythonObject`
   pro composite výstupy), `Placement` + `to_local`/`to_global` transformace
   pro composite hodnoty. **Zatím nezapočato.**
4. Otevřená otázka z dřívějška: zda composite parametry volané jako
   inline podprogram (sdílený souřadný systém) vs. umístěný podprogram
   (relativní Placement) – koncept navržen, needimplementováno.

## Soubory k dispozici (outputs)

```
gl3/gl3_lang.py
gl3/gl3_ops.py
gl3/gl3_analysis.py
gl3/gl3_interpreter.py
gl3/gl3_test.py
gl3/examples/TEST1.GL3
gl3/examples/XPROC.GL3
gl3/examples/SCARA.GL3
QUPoint.py
NegExport.py
```
