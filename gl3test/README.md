# gl3test/

Fixture soubory pro Python regresní sadu (`gl3/gl3_test.py`, `gl3/gerlib/test_*.py`,
`gl3/gl3fc/test_*_offline.py`, `test_gl3_commands_offline.py`).

**Tenhle adresář je v plné režii Claude/regresní sady.** Obsahuje vlastní
kopie souborů, na kterých testy stojí (`TEST1.GL3`, `XPROC.GL3`,
`IOTEST.GL3` a fixture kopie `HLO.GL3`, `SCARA.GL3`, `HLOCUT.gl3`,
`TEHLO.GL3`, `E374.TXT`) - záměrně **oddělené** od `gl3sys/`,
`gl3examples/` a `gl3data/`, které jsou plně v režii uživatele.

Smysl oddělení: úpravy v `gl3sys/`/`gl3examples/`/`gl3data/` (přejmenování,
smazání, změna obsahu) nesmí rozbít Python testy. Pokud fixture kopie tady
zastarají vůči reálným souborům, nevadí - jsou to jen testovací data, ne
zdroj pravdy.

Výchozí `SearchPaths` pro `GL3Library` ve FreeCADu ukazuje na `gl3sys/`,
ne sem - tenhle adresář není určený pro běžné použití ve FreeCADu.
