Shrnutí této relace (od CRE/MOVE po Q48) pro navázání v novém vlákně:

## Aktuální stav
- **GitHub repo:** `https://github.com/d-slav/NEGWorkbench.git`
- **Poslední HEAD, na který jsem já pracoval:** `112c293` → po posledním bundlu (Q48) by měl být `513e063` (musíš mít zmergováno)

## Co bylo implementováno

**Kreslení (gl3/gl3_interpreter.py, gl3_lang.py, gerlib/move_geom.py):**
- `CRE,pg` / `ENDCRE` — vytváření pojmenovaného řetězce pomocí `MOVE`
- `INI` / `CLOSE` — "skrytý řetězec" každého běhu SUBRO (bez CL2), skrytý řetězec volané SUBRO se při `CALL` připojuje k volajícímu
- `MOVE` — frázová logika (bodové, obloukové, řetězové fráze), sdílená mezi CRE i INI
- Obecná podpora vynechaných pozic v argumentech (`,,`) — `Omitted`/`OMITTED` sentinel v parseru

**GL3 opcody (gerlib/, geplib/):**
L04, P43, P14, C30 (+C430.FOR), D28, P58, P66, P17, P21, T01 (3D obdoba S01), Q38 (přes zobecněné GLPRU, K=2/K=3), V34, L42, U19 (Rodriguesův vzorec, ověřeno numericky proti VECT75/POIN93/CS999/VECT99), H02, Q48 (3D obdoba P48)

**Nalezené a opravené bugy mimo zadání:**
- L00 nebyla zaregistrovaná v `OPERATIONS` dict
- `_node_index_and_flag` (P48) nekonvertovala K na int → spadlo na float K z reálného interpretu (opraveno, sdíleno s Q48)
- S01 chyběla horní mez K≤300

**FreeCAD integrace (gl3/gl3fc/):**
- `GL3Program` teď kreslí svůj skrytý řetězec **přímo na sebe** (`obj.Shape`, je `Part::FeaturePython`) — žádná `Drawing` property, žádný nutný `GL3Export`
- `GL3Export` zůstává jen pro materializaci pojmenovaných `out:` výstupů
- `_exec_cache` v `GL3Program.execute()` — přeskočí drahý běh interpretu, pokud se nezměnilo nic na SourceFile/mtime/Library/in: hodnotách (nutné, protože `gl3_export.create()` musí `touch()`-nout Source kvůli správnému zařazení do stromu)
- **Neověřeno naživo:** zda se export po vytvoření skutečně řadí pod Program (potvrdil jsi to po vrácení `touch()`), ale nově přidané kreslení `Shape` na `GL3Program` samotném stojí za manuální ověření v reálném FreeCADu, pokud jsi to ještě nezkusil s aktuálním HEAD.


