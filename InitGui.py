# -*- coding: utf-8 -*-
"""
InitGui.py - vstupni bod FreeCAD GUI doplnku NEGWorkbench.

FreeCAD tenhle soubor automaticky najde a nacte pri startu, POKUD je
tahle slozka primo pod uzivatelskym Mod/ adresarem (napr.
%APPDATA%\\FreeCAD\\Mod\\NEGWorkbench\\InitGui.py na Windows,
~/.local/share/FreeCAD/Mod/NEGWorkbench/InitGui.py na Linuxu) - staci
zkopirovat/naklonovat cely tenhle repozitar tam a restartovat FreeCAD.

Zatim jen jeden prikaz (vytvoreni GL3Library) - dalsi (GL3Program,
GL3Export, editace Library, ...) pribudou postupne, az bude tenhle
zakladni krok spolehlive fungovat - viz README.md a docs/cs/.
"""

"""
InitGui.py - vstupni bod FreeCAD GUI doplnku NEGWorkbench.

FreeCAD tenhle soubor automaticky najde a nacte pri startu, POKUD je
tahle slozka primo pod uzivatelskym Mod/ adresarem (napr.
%APPDATA%\\FreeCAD\\Mod\\NEGWorkbench\\InitGui.py na Windows,
~/.local/share/FreeCAD/Mod/NEGWorkbench/InitGui.py na Linuxu) - staci
zkopirovat/naklonovat cely tenhle repozitar tam a restartovat FreeCAD.

DULEZITA POZNAMKA K TOMU, JAK FREECAD TENHLE SOUBOR SPOUSTI:
FreeCAD InitGui.py/Init.py nenacita jako normalni Python modul (import),
ale spousti primo pres `exec(compile(obsah_souboru))` UVNITR SVE VLASTNI
FUNKCE (RunInitGuiPy ve FreeCADGuiInit.py). Protoze je exec() zavolany
BEZ explicitnich globals/locals uvnitr funkce, Python pouzije pro tenhle
exec DVE ODDELENE veci: skutecne globals (vnitrni modul FreeCADu) a
locals te funkce (jako by nas kod byl proste vlozeny primo doprostred
teto funkce). Dusledek: cokoliv, co si NA NEJVYSSI UROVNI TOHOTO SOUBORU
prirsadime (_WB_DIR = ..., import os, def QT_TRANSLATE_NOOP...), skonci
v teto specialni "locals" dict - NE ve skutecnych globals. Trida
(NEGWorkbench) a jeji metody ale pri hledani jmen, ktera sami nemaji
definovana, koukaji JEN do skutecnych globals (ne do teto "locals" dict)
- takze cokoliv definovane na teto (souborove) urovni NENI VIDET ZEVNITR
TRIDY/METOD (odtud presne hlaska "name '_WB_DIR' is not defined").

Reseni: trida i kazda jeji metoda si musi VSECHNO, co potrebuji, znovu
naimportovat/spocitat PRIMO VE SVEM VLASTNIM TELE - nespolehat na nic
z vrcholu souboru. Proto tu vidite "import os"/"import gl3_wb_paths"
opakovane na nekolika mistech - neni to preklep, je to nutne.

Zatim jen jeden prikaz (vytvoreni GL3Library) - dalsi (GL3Program,
GL3Export, editace Library, ...) pribudou postupne, az bude tenhle
zakladni krok spolehlive fungovat - viz README.md a docs/cs/.
"""

import FreeCADGui as Gui


class NEGWorkbench(Gui.Workbench):
    # DULEZITE: import primo tady, v tele tridy - ne na vrcholu souboru
    # (viz vysvetleni v modulovem docstringu vyse). Kazde jmeno pouzite
    # v tomhle tele tridy musi byt definovane bud tady, nebo byt
    # skutecny Python builtin.
    import os as _os
    import gl3_wb_paths as _wb_paths

    MenuText = "NEG/GL3"
    ToolTip = (
        "NEG/GL3 - integrace historickeho geometrickeho jazyka "
        "(LET Kunovice / Aircraft Industries a.s.) do FreeCADu"
    )
    Icon = _os.path.join(_wb_paths.WB_DIR, "Resources", "icons", "neg_workbench.svg")

    def Initialize(self):
        # Znovu import VSEHO potrebneho - viz vysvetleni na vrcholu
        # souboru. Nelze spolehat na nic z vrcholu souboru ani z tela
        # tridy (jina metoda = jiny scope, stejny problem).
        import os
        import sys
        import gl3_wb_paths
        import FreeCADGui as Gui

        def qt_translate_noop(context, text):
            """Neni skutecny preklad (zadny .ts/.qm zatim neexistuje) -
            jen oznaceni textu pro pripadny budouci 'lupdate' extract,
            aby se lokalizace dala pridat pozdeji jako .ts/.qm soubor
            bez zasahu do kodu. Viz
            https://wiki.freecad.org/Translating_an_external_workbench
            """
            return text

        wb_dir = gl3_wb_paths.WB_DIR
        if wb_dir not in sys.path:
            sys.path.insert(0, wb_dir)

        # Az budou nejake .qm soubory, budou se hledat tady (zatim
        # prazdna slozka staci zaregistrovat uz ted, at se pozdejsi
        # pridani prekladu obejde bez dalsi zmeny kodu).
        Gui.addLanguagePath(os.path.join(wb_dir, "translations"))
        Gui.updateLocale()

        import gl3_commands  # noqa: F401 - registruje Gui.Command objekty

        self.command_list = ["NEG_CreateLibrary"]
        # Kontext "Workbench" je FreeCAD konvence pro appendMenu/appendToolbar
        # nazvy (viz Translating_an_external_workbench) - jednotlivé
        # prikazy maji svuj vlastni kontext (jmeno prikazu), viz
        # gl3_commands.py.
        self.appendToolbar(qt_translate_noop("Workbench", "NEG/GL3"), self.command_list)
        self.appendMenu(qt_translate_noop("Workbench", "NEG/GL3"), self.command_list)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(NEGWorkbench())
