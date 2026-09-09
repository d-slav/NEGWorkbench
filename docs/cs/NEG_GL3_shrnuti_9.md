## Shrnuti 9

**Anchor:** HEAD `7e94c75` (Shrnuti 7 - Opraveny ikony). Vse nize je v jednom commitu na tomto zaklade.

### 1. EditCommand default - HOTOVO

`GL3Program.EditCommand` default zmenen z `'edit ${gl3_file_path}/${gl3_file_name}'` na
`'Notepad ${gl3_file_path}/${gl3_file_name}'` - `gl3/gl3fc/gl3_program.py`, `gl3_commands.py`
(docstring), `test_gl3_commands_offline.py` (3 assertions), `README.md`.

### 2. Broad error-message sweep v gl3_interpreter.py - HOTOVO

Kazda GL3-programova bezova chyba ted konci jako `GL3RuntimeError` ve formatu
`[Error] program/radek/operace: text` (pres `self._raise_gl3_error(operation, message)`), misto
holeho `NameError`/`ValueError`/`TypeError`/`KeyError`/`SyntaxError`/`OSError`.

Prevedeno: `_eval_array_ref`/`_set_indexed`/`_assign_result` (ted maji `operation=None`
parametr), Assign (nedeklarovane pole), DIMEN (prepis in: parametru), DoLoop krok==0,
BREAK/CONTINUE mimo cyklus (v `run()` i `_exec_call()`), `_exec_data` (DATA), `SCALE`, neznamy
prikaz, CRE/ENDCRE/INI/CLOSE, MOVE (obe faze - zakladajici i nezakladajici), DCOOS3, TRA23,
CALL (neregistrovany cil), IDEV (spatny typ jmena/kanal/soubor se neotevrel), a cely
GET/READ blok (`_next_raw_line`, `_next_record`, `_component_count`, `_make_value`,
`_assign_target`, `_exec_input` - vsechny maji `operation=None` parametr, `_exec_input` predava
`stmt.command`).

Ponechano jako `NotYetImplemented`, ale obalene `self._format_report("Error", operation,
message)`: DATA na nepodporovanem typu (S/E/T/H/F), GET/READ na nepodporovanych typech
(textova promenna pres GET, jiny typ nez skalar/P), cteni z terminalu (GETT/READT).

Neresolveno (schvalne, jde o interni bug signal, ne o chybu GL3 programu): neznamy typ AST
uzlu, neznamy operator/relace, `_exec_stmt` neznamy typ statementu, `KeyError` na
`COMMANDS.get("SCALE"/"ACCUR")` (dispatch uz predtim shodil jmeno, tenhle lookup nemuze
legitimne selhat), posledni `raise NotYetImplemented` v `_build_data_object` (nedosazitelne -
`DATA_CONSTANTS_PER_OBJECT` uz predem filtruje presne tytez prefixy).

**Vedlejsi bugfix objeveny pri sweepu:** v `run()` a `_exec_call()` `finally` blocich se
`_program_name_stack`/`_source_path_stack`/`current_line_no` ted popuji/obnovuji AZ PO
volani `_pop_hidden_chain_frame()` (drive to bylo obracene) - jinak by chybova hlaska z
dangling-INI kontroly uvnitr te metody mela spatny (uz odskocenej) kontext programu/radku.
Zduvodneno inline komentarem na obou mistech.

### 3. Testy - HOTOVO, VSE ZELENE

Upraveno (stary bare-exception-type assertions nahrazeny za `GL3RuntimeError`/spravny format,
resp. `except OSError` -> `except Exception` tam, kde IDEV chyba ted prochazi jako
`GL3RuntimeError` misto `OSError`):
- `test_gl3_commands_offline.py`
- `gl3/gl3fc/test_offline.py`
- `gl3/gl3fc/test_short_traceback_offline.py` (assertion na obsah zpravy - novy format nema
  uz substring `"DATA,E1"`, ale `"[Error]"`/`"DATA"`/`"E1"`/`"'E'"`)
- `gl3/test_dcoos3_tra23_interpreter.py` (import `GL3RuntimeError`, 2x `except ValueError` ->
  `except GL3RuntimeError`)
- `gl3/test_data_command.py` (import `GL3RuntimeError`, `except ValueError`/`except NameError`
  -> `except GL3RuntimeError`)
- `gl3/test_dimen_input_guard.py` (import `GL3RuntimeError`, `except ValueError` ->
  `except GL3RuntimeError`)

Pridana nova dedikovana pokryti do `gl3/test_error_categories.py` pro presny format hlasky
(`[Error] program/radek/OPERACE: text`) u: SCALE, DCOOS3, TRA23, CALL (neregistrovany cil),
IDEV (soubor se neotevrel), GET (zaznam moc kratky).

**Vysledky:**
- `pytest` (z korene repo): 23 passed.
- Vsechny ostatni `test_*.py` skripty (spousteny jednotlive jako `python3 cesta/test_x.py`,
  BEZ `cd` do jejich adresare - `cd` do `gl3/gerlib/` zpusobi, ze si Python plete vlastni
  `gerlib/types.py` se standardni knihovnou `types`, viz nize): vsechny OK krome 16
  preexistujicich, na sweepu NEZAVISLYCH selhani, vsechna v `gl3/gerlib/*.py` (13x presne
  tahle kolize se stdlib `types`) a `gl3/gerlib/test_move_geom.py` (relativni import bez
  package kontextu) + `gl3/geplib/test_plane_r01.py` (`ModuleNotFoundError: No module named
  'gerlib'` kdyz se spusti izolovane) - to vse jsou znama, na tomto sweepu nezavisla
  strukturalni omezeni zpusobu spousteni testu v teto konkretni sesii, ne regrese.

### 4. Dalsi kroky

Sweep i testy jsou hotove a overene - zbyva jen commit (jeden, na `7e94c75`) a git bundle
pro Dusana.
