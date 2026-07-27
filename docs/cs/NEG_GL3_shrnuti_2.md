# NEG/GL3 → FreeCAD – shrnutí stavu projektu (pokračování)

Toto shrnutí navazuje na `NEG_GL3_shrnuti.md` z předchozího vlákna a
popisuje stav po jeho dokončení: jazyk GL3 (parser + interpret) je teď
dost hotový na to, aby reálný testovací program (`TEHLO`→`HLO`) doběhl
od načtení dat ze souboru až po výslednou vyhlazenou křivku profilu.
Další krok je implementace do FreeCADu (`gl3_object.py`, Export modul).

## Cíl projektu (beze změny)

Integrace vlastního geometrického jazyka **NEG** (Numerická Etalonní
Geometrie, Let Kunovice), konkrétně jeho konstrukční podmnožiny **GL-3**,
do FreeCADu. Motivace: hobby tvorba modelů letadel/vrtulníků – generování
ploch povrchu zadaných parametricky (typicky křídelní profily), tak aby
změna vstupních dat automaticky přepočítala navazující geometrii.

Vyřazeno z rozsahu: technologické příkazy (CNC/obrábění) a CL2 (postprocesor
obráběcího stroje).

## Architektonická rozhodnutí (beze změny, potvrzeno provozem)

1. **Dva oddělené moduly** – GL3 modul (`App::FeaturePython` s vlastním
   `Placement`) a Export modul (z výstupu GL3 objektu vyrobí skutečný
   nativní FreeCAD objekt s reálným `Placement`). Cesta je jednosměrná:
   GL3 → Export → FreeCAD, nikdy zpátky.
2. **Typový systém** – do GL3 smí zvenčí (z FreeCADu) téct jen skaláry
   a cesty k souborům; geometrie vzniká výhradně uvnitř GL3.
3. Placement transformace se týká jen composite typů nesoucích polohu.
4. Inline volání sdílí souřadný systém volajícího; volání s vlastním
   umístěním zůstává otevřenou otázkou pro budoucno.
5. GOTO se obecně nepodporuje; jediný idiom (návěští + zpětný podmíněný
   skok) se automaticky překládá na `RepeatWhile`.
6. `in:`/`out:` je v hlavičce `SUBRO` povinné a explicitní u každého
   parametru – ale **velikost pole v hlavičce (např. `PI(2)`) je jen
   orientační/zastaralá**, ne závazná (viz níže, bod o `_set_indexed`).
7. Immutabilní vnitřní hodnoty → obyčejné přiřazení je vždy bezpečná
   kopie.

## Co je nově hotové: jazyk GL3 (`gl3_lang.py`, `gl3_interpreter.py`)

Oproti minulému shrnutí přibylo:

- **Koncové komentáře `< ...`** – běžná součást GL3 zdroje (potvrzeno
  dokumentací i reálnými soubory uživatele); ořezávají se v kódu i
  v datových souborech čtených přes `READ`/`GET`.
- **Řetězcové literály** (`'jméno_souboru'`) v lexeru – potřeba pro
  `IDEV`.
- **Vstup ze souboru**: `IDEV,'soubor'[,kanál]` (kanál 0/1/2, default 0),
  `READ`/`READ1/2/T`, `GET`/`GET1/2/T` – čtení skalárů, 2D bodů (`P`) a
  textových (`B`) řádků. Na konci souboru se cíli přiřadí `None`
  (nevyhazuje se výjimka) – umožňuje to idiom `IFN`.
- **`IFN/X/THEN...ENDIF`** – obecně: pokud `IFx` podmínka neobsahuje
  relaci (`GT/LT/...`), bere se jako test „je `X` nedefinováno?".
- **`DO` smyčka „živě" kontroluje čítač** po každém průchodu – idiom
  „nastav čítač na koncovou hodnotu" uvnitř těla smyčku skutečně ukončí
  (běžný způsob, jak staré GL3 programy končí čtení dat předčasně).
- **Výstup na konzoli**: `PRINT`/`PRINT1/2/T`/`TRACE`, `WRITE`/`WRITE1/2/T`
  (přesně podle kap. 8.3 dokumentace: `PRINT` na nedefinovaný objekt
  spadne s chybou, `WRITE` ho tiše přeskočí; bez indexu `WRITE` vypíše
  všechny definované prvky pole). Zatím vždy jde na konzoli – `ODEV`/
  `ODEVB` (zápis do souboru) není implementováno.
- **Vestavěné konstanty** (`gerlib.constants.builtin_constants()`,
  vždy čerstvá kopie v každém novém scope) – `DPI`, `P0/V0/VX/VY/VXN/VYN/
  LX/LY` (2D), `Q0/U0/UX/UY/UZ/UXN/UYN/UZN/MX/MY/MZ/RXY/RXZ/RYZ` (3D).
- **Opravená typová tabulka** – celočíselné jsou jen `I, J, K` (ne
  Fortran `IMPLICIT` I-N, jak jsem si dřív mylně myslel); `D, A` skalár;
  `P,V,C,L,S,E` 2D; `Q,U,R,M,G,T,H,F` 3D; `B` text; cokoliv jiného =
  skalár (float).
- **`CALL` opraveno**: pole se předávají kopií (`list(value)`), ne sdílenou
  referencí; `out` pole se automaticky alokují podle velikosti v hlavičce
  (ale viz další bod – i to je jen výchozí odhad).
- **`_set_indexed`** – jakýkoliv indexovaný zápis do pole (`Assign`,
  `GET`/`READ`, `SCALE`) pole automaticky dorovná `None`, pokud index
  přesahuje současnou délku. Nutné, protože velikosti v `SUBRO` hlavičce
  (`PI(2)`, `PO(2)` apod.) jsou v reálných programech jen orientační.
- **`SCALE` přepracováno** na smyčku přes pole (`pg1,pg2,vr,vi` – stejná
  Fortran konvence `P(1),N` jako `E01`), volá `gerlib.scale` na každý
  prvek zvlášť.
- **Oprava `HLO.GL3`** (uživatel) – parametr, který dřív sloužil jako
  in i out zároveň (přes referenci), teď má oddělené `PI`/`PO`.

## Nová knihovna: `gerlib` (GEometrie Rovinná LIBrary)

Na žádost uživatele **oddělená, na GL3/FreeCADu nezávislá knihovna**,
použitelná i mimo tenhle projekt. Organizace: **jeden soubor = jedna
operace, pojmenovaná podle GL3 opcode** (nízkoúrovňové pomocné operace
bez vlastního opcode si nechaly původní Fortran jméno). Každý soubor má
nahoře krátkou hlavičku ve stylu originálu (Účel/Užití/Parametry).
Žije v `gl3/gerlib/` (jen jedna kopie, tam, kam sahá interpret).

```
gerlib/
    types.py       - Point, Vector, Line, Circle, Plane, Curve, Spline
    constants.py   - builtin_constants()
    v220.py        - unit_vector (normalizace vektoru)
    a521.py        - polar_angle_deg (úhel vektoru od osy X)
    a510.py        - angle_between_deg (úhel dvou vektorů; ZDROJÁK NEMÁME,
                     odvozeno z použití - matematicky nedvojznačné)
    vnorm.py       - is_zero_vector
    gtrin.py       - solve_tridiagonal (Thomasův algoritmus)
    dsn.py         - tangent_vectors (tečné vektory otevřeného splajnu)
    d01.py .. d43.py  - skaláry, vzdálenosti, obsahy (viz tabulka níže)
    p10.py, p20.py    - posun bodu, průsečík přímek
    e01.py            - retězec (Curve) z bodů + tangent_point_on_chain
                        (sdílené jádro pro P85/P86/L46)
    p85.py, p86.py, l46.py - tečný bod/přímka na řetězci
    s03.py            - křivka (Spline) K body + okrajové tečné vektory
    scale.py          - měřítková transformace
```

### Implementované GL3 operace

| GL3 opcode | Interní Fortran | Účel |
|---|---|---|
| D01 | D601 | součet/rozdíl skalárů |
| D02 | D602 | součin/podíl skalárů |
| D10 | D610 | vzdálenost bod–bod |
| D11 | D611 | vzdálenost bod–přímka |
| D20 | D620 | velikost vektoru |
| D30 | *(jen dokumentace)* | vytažená složka objektu (x/y/z, střed+poloměr, počátek+směr) |
| D40 | D640 | obsah trojúhelníku (3 body) |
| D41 | D641 | obsah trojúhelníku (3 přímky, přes P20) |
| D42 | D642 | obsah trojúhelníku se znaménkem |
| D43 | D643 | obsah kruhu |
| P10 | P110 | bod posunutý o (dx, dy) |
| P20 | P120 | průsečík dvou přímek |
| P85 | P85 | dotykový bod na řetězci rovnoběžně s vektorem |
| P86 | P86 | dotykový bod na řetězci rovnoběžně s přímkou |
| L46 | L46 | tečná přímka k řetězci (přes P86) |
| E01 | E01 | retězec (Curve) z pole bodů |
| S03 | SPLIN+DSN+GTRIN+VNORM | křivka (Spline) K body, okrajové tečné vektory, parametrizace 0-1 |
| SCALE | SCALEX | měřítková transformace (Point/Vector/Line/Circle/Curve) |

### Zbývající stuby (a jejich přesné závislosti)

- `D27` (délka oblouku) – potřebuje `A512.FOR`.
- `D50` – čistě spekulativní stub z rané fáze, žádný reálný program ho
  zatím nepoužil.
- `L02, L20, L45, P13, P22, P42, P44, P47, P48, P49, C02, C49, E45, NPO`
  – čekají na Fortran zdrojáky.
- `S01` (křivka B-splajnu obecně), `S02` (B-spline K řídicími body) –
  uživatel je vědomě odložil na později.
- `S09`/`T09` (uzavřená verze `S03`/`T03`) – máme `DSP.FOR`/`DSPP.FOR`,
  ale chybí `GTRIP.FOR` (periodický tridiagonální řešič).
- `S05`/`T04` (chordal parametrizace) – máme `DSPN.FOR`, ale chybí thin
  wrapper analogický `SPLIN.FOR`, který by ho volal (nemáme jistotu
  o přesném GL3 opcode/signatuře).

### Vědomá zjednodušení / otevřené nejistoty

- `A510` nemáme jako zdroják – implementace (`acos(dot)`) je ale
  matematicky jednoznačná operace, riziko chyby minimální.
- `D30` je jen z dokumentace (žádný `.FOR`); číslování složek u 3D
  přímky (`M`) a 3D kružnice (`G`) je nejednoznačné (naše `Line`/`Circle`
  třídy nerozlišují 2D/3D použití) – zatím používáme 2D (`L`/`C`)
  konvenci, pro `M`/`G` by bylo potřeba vědět skutečný GL3 typový prefix.
- `SCALE` podporuje jen typy, které máme jako Python třídy (2D
  Point/Vector/Line/Circle/Curve) – 3D typy a křivky S/T/H zatím
  vyhodí jasnou chybu.

## Ověřené příklady (`gl3/examples/`)

- **TEST1.GL3** – kompletně doběhne (`DO=50.0`).
- **SCARA.GL3**, **XPROC.GL3** – zastaví se na očekávaném místě (chybějící
  stub / chybějící `HLO` v registru) – slouží jako regresní test parseru
  a interpretu.
- **HLO.GL3** + **TEHLO.GL3** + **E374.TXT** – **kompletně doběhne od
  načtení profilu ze souboru až po vyhlazenou křivku (`S03`)**. Fyzikálně
  ověřeno: normovaný profil (tětiva 0→1) se correctly přeškáluje na
  zadanou hloubku `DH=15.2`, náběžná hrana vyjde přesně v počátku,
  odtoková na `(DH, 0)`.

## Soubory k dispozici

```
gl3/
    gl3_lang.py         - lexer, parser, AST
    gl3_ops.py          - registr OPERATIONS/COMMANDS, typová tabulka,
                          tenká adaptérová vrstva nad gerlib
    gl3_interpreter.py  - interpret (Environment, CALL, I/O kanály, ...)
    gl3_analysis.py     - odvození směrů parametrů z in:/out: anotace
    gl3_test.py         - regresní test (TEST1/XPROC/SCARA/HLO/TEHLO)
    gerlib/             - samostatná geometrická knihovna (viz výše)
    examples/
        TEST1.GL3, XPROC.GL3, SCARA.GL3
        HLO.GL3, TEHLO.GL3, E374.TXT
```

## Další kroky – implementace do FreeCADu

1. **`gl3_object.py`** – `FeaturePython` wrapper: dynamické generování
   properties podle `SUBRO` hlavičky (skalární nativní property vs.
   Link+String pro composite vstupy, `PropertyPythonObject` pro composite
   výstupy), `Placement` + `to_local`/`to_global` transformace pro
   composite hodnoty. **Zatím nezapočato.**
2. **Export modul** – z vybraného výstupu GL3 objektu vyrobit skutečný
   nativní FreeCAD objekt s reálným `Placement`. Konkrétně teď potřeba:
   - **export pole bodů** (`PO`, typ `P` pole) – asi jako `Part::Vertex`
     objekty nebo `Points` feature.
   - **export křivky** (`S`, typ `Spline` s body+tečnami v uzlech) –
     nejspíš přes `Part.BezierCurve` po segmentech (z Hermitových bodů+
     tečen na Bézierovy řídicí body) nebo `Part.BSplineCurve` s tečnými
     omezeními (`interpolate` s `Tangents`/`TangentFlags`).
3. Otevřená otázka z minula: composite parametry volané jako inline
   podprogram (sdílený souřadný systém) vs. umístěný podprogram
   (relativní Placement) – koncept navržen, needimplementováno.
