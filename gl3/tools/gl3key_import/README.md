# gl3key_import

Jednorázový import staré nápovědy pro klíčová slova a opkódy GL3 z
dřívějšího C++/MFC editoru (`CGl3Keywords`, viz `Gl3_Keywords.h`/`.cpp`)
do `../../gl3_keywords.json`.

## Vstup

`Gl3Key.dat` — binární dump vytvořený `CGl3Keywords::Serialize()` (MFC
`CArchive`). Formát (ověřeno přímo na bajtech souboru, ne jen odvozeno
ze zdrojáku):

```
LONG   version           (4B, = 1)
DWORD  count              (4B, počet záznamů)
count × záznam:
    string HtmlHelpFile   (DWORD délka BEZ null bajtu, pak délka+1 bajtů vč. terminátoru)
    LONG   ObjType         (4B, enum OBJ_TYPE — pořadí viz Gl3_Keywords.h)
    string Key             (stejné kódování jako HtmlHelpFile)
    string Syntax
    string Comment
    string Menu
```

Všechna celá čísla little-endian, řetězce v CP1250 (česká Windows
kódová stránka — stará MFC aplikace, `CHAR` ne `WCHAR`).

Význam polí (jak je popsal Dušan): `m_HtmlHelpFile` odkaz na plnou
dokumentaci, `m_Menu` text nabídky pro autocomplete podle typu objektu
(`m_ObjType`), `m_Syntax` první řádek tooltipu, `m_Comment` další řádky
tooltipu.

## Výstup — `gl3_keywords.json`

Slovník `{klíč: {type, syntax, comment, menu, html_help_file}}`.
`type` je písmeno prefixu proměnné stejné jako
`gl3_ops.TYPE_PREFIX_INFO`/`classify()` (`"D"`, `"P"`, `"Q"`, ...), nebo
`null` pro klíčová slova/příkazy bez vráceného typu (`Type_` v původním
enumu — `DO`, `CALL`, `THEN`, `ELSE`, `MOVE`, ...).

Dva klíče (`NPO`, `NSE`) měly ve zdrojových datech dva záznamy —
skutečné přetížení (jiná syntaxe pro plochu `F` než pro řetězec/křivku
`S`/`E`/`T`/`H`), ne chyba — `convert.py` je sloučí do jednoho hesla
(`syntax`/`comment` spojené novým řádkem), místo aby jeden tiše zahodil.

## Porovnání se současnou implementací (stav při importu)

- Všech ~23 namátkou zkontrolovaných implementovaných opkódů (D10, P00,
  C00, S01, E01, L46, P85, ...) sedí 1:1 jménem se starými daty.
- `ELSE`, `THEN`, `ENDIF`, `FOR`, `NEXT`, `ENDDO` už byly v původní
  dokumentaci — potvrzuje, že šlo o obnovení historické funkčnosti
  (G12.md), ne o vymyšlení nové.
- `BREAK`/`CONTINUE` ve starých datech chybí — to jsou skutečně naše
  vlastní rozšíření nad rámec původního GL3, žádný historický základ
  neexistuje.
- `D01`/`D02` (u nás implementované) ve starých datech chybí — malá
  nesrovnalost, důvod neznámý (možná přidány do jazyka až po zachycení
  téhle dokumentace).
- `D27`/`P44` (u nás zatím jen stub bez implementace) ve starých datech
  MAJÍ svůj záznam s přesnou syntaxí — `DM=D27>C,P1,P2,K[,L]` a
  `PM=P44>P,S` — užitečné jako specifikace pro budoucí dokončení.

## Jak znovu spustit

```
python3 convert.py
```

Přepíše `../../gl3_keywords.json`. Spouštět ručně jen když se `Gl3Key.dat`
změní/doplní — není součástí žádného automatického buildu ani testovací
sady.
