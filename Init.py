# -*- coding: utf-8 -*-
"""
Init.py - App-level (bez Gui) vstupni bod doplnku NEGWorkbench.

FreeCAD tenhle soubor spusti pro KAZDY nainstalovany doplnek HNED PRI
STARTU (App-level, i v konzolovem rezimu bez GUI, FreeCADCmd) - narozdil
od InitGui.py/Workbench.Initialize(), ktere se pro danou workbench
spusti/zavola az kdyz ji uzivatel poprve aktivuje v GUI.

DUVOD EXISTENCE TOHOTO SOUBORU (opraveny bug): Gui.Command objekty
(gl3_commands.py) a jejich Activated() metody si moduly gl3fc.gl3_library/
gl3_program/gl3_export importuji az "leniv(e" - teprve kdyz se prislusny
prikaz skutecne pouzije. Kdyby se pri otevirani .FCStd souboru s GL3Library/
GL3Program/GL3Export objekty tyhle tridy jeste nedaly naimportovat (protoze
uzivatel jeste nikdy neaktivoval NEG/GL3 workbench - FreeCAD si pamatuje a
pri startu automaticky nabizi naposledy pouzivanou workbench, treba
uplne jinou), Python by v okamziku obnovovani dokumentu tyhle tridy
neznal - jejich Proxy (a Proxy jejich ViewObjectu) by se nepodarilo
spravne "unpicklovat" a strom by se nesestavil spravne (chybejici
claimChildren() na GL3Program, chybejici onDocumentRestored(), atd.) -
presne pozorovany bug: "musim napred aktivovat doplnek a teprve potom
soubor otevrit".

Reseni: naimportovat tyhle 3 moduly (a tim registrovat jejich tridy v
sys.modules) uz TADY, coz FreeCAD spusti VZDY, bez ohledu na to, jestli
je NEG/GL3 prave aktivni workbench - tedy driv, nez ma uzivatel vubec
sanci nejaky dokument otevrit.

Import na teto urovni je bezpecny i bez realneho FreeCADu (syntax-check/
testy) - gl3_program.py/gl3_export.py maji vlastni try/except ImportError
kolem 'import FreeCAD as App' (gl3_library.py FreeCAD vubec nepotrebuje).

POZOR: FreeCAD tenhle soubor spousti pres exec() (ne normalni import),
takze __file__ NEMUSI byt k dispozici (viz gl3_wb_paths.py docstring) -
proto se cesta k doplnku zjistuje pres gl3_wb_paths (BEZNY importovany
modul, ma spolehlivy __file__) misto __file__ primo tady.
"""

import os
import sys

import gl3_wb_paths  # bezny import (ne exec) => spolehlivy __file__

# gl3fc balicek zije v <addon_root>/gl3/gl3fc/, takze na sys.path patri
# <addon_root>/gl3 (ne addon root samotny) - stejna konvence jako
# gl3_commands.py (_GL3_DIR).
_GL3_DIR = os.path.join(gl3_wb_paths.WB_DIR, "gl3")
if _GL3_DIR not in sys.path:
    sys.path.insert(0, _GL3_DIR)

import gl3fc.gl3_library  # noqa: F401 - viz modulovy docstring vyse
import gl3fc.gl3_program  # noqa: F401 - definuje i ViewProviderGL3Program
import gl3fc.gl3_export  # noqa: F401 - definuje i ViewProviderGL3Export
