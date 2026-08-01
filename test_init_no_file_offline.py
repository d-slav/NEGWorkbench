# -*- coding: utf-8 -*-
"""
test_init_no_file_offline.py - overuje, ze Init.py (App-level, viz jeho
modulovy docstring pro duvod existence) po spusteni zaregistruje moduly
gl3fc.gl3_library/gl3_program/gl3_export v sys.modules - TOTO MUSI JIT
BEZ OHLEDU NA TO, JESTLI BYLA NEG/GL3 WORKBENCH NEKDY AKTIVOVANA V GUI
(na rozdil od InitGui.py/Workbench.Initialize(), ktere se vola az pri
prvni aktivaci - viz test_initgui_no_file_offline.py).

Simuluje FreeCAD skutecny zpusob spousteni (exec() uvnitr funkce, s
oddelenymi globals/locals) stejne verne jako
test_initgui_no_file_offline.py - viz tam podrobne vysvetleni.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)


def main():
    # Cistá sada sys.modules pro gl3fc.* - abychom fakt overili, ze je
    # Init.py sam DOKAZE naimportovat (a ne ze uz tam nahodou jsou z
    # nejakeho drivejsiho importu v tomhle testovacim procesu).
    for mod_name in list(sys.modules):
        if mod_name == "gl3fc" or mod_name.startswith("gl3fc."):
            del sys.modules[mod_name]

    init_path = os.path.join(_HERE, "Init.py")

    # --- simulace FreeCADu jako samostatneho "modulu" (fake globals dict),
    # presne jako u InitGui.py v test_initgui_no_file_offline.py ---
    fake_freecad_init_module = {"os": os, "__name__": "FreeCADInit_sim"}

    exec(
        "def RunInitPy(path):\n"
        "    with open(path, 'r', encoding='utf-8') as f:\n"
        "        src = f.read()\n"
        "    code = compile(src, path, 'exec')\n"
        "    exec(code)\n",
        fake_freecad_init_module,
    )
    run_init_py = fake_freecad_init_module["RunInitPy"]

    # Tohle musi projit BEZ vyjimky - i BEZ ohledu na to, ze zadna GUI
    # workbench (natoz NASE) v tomhle testu nebyla nikdy "aktivovana".
    run_init_py(init_path)

    print("Init.py se nactl pod VERNOU simulaci FreeCAD exec() (oddelene")
    print("globals/locals uvnitr funkce) - bez vyjimky.")

    for mod_name in ("gl3fc.gl3_library", "gl3fc.gl3_program", "gl3fc.gl3_export"):
        assert mod_name in sys.modules, (
            "%s musi byt v sys.modules PO Init.py - jinak by se otevreni "
            ".FCStd souboru s GL3Library/GL3Program/GL3Export objekty "
            "nezdarilo, dokud by uzivatel nejdriv rucne neaktivoval "
            "NEG/GL3 workbench (presne pozorovany bug)" % mod_name
        )
    print("sys.modules obsahuje gl3fc.gl3_library/gl3_program/gl3_export: OK")

    assert hasattr(sys.modules["gl3fc.gl3_program"], "GL3Program")
    assert hasattr(sys.modules["gl3fc.gl3_program"], "ViewProviderGL3Program")
    assert hasattr(sys.modules["gl3fc.gl3_export"], "GL3Export")
    assert hasattr(sys.modules["gl3fc.gl3_export"], "ViewProviderGL3Export")
    assert hasattr(sys.modules["gl3fc.gl3_library"], "GL3Library")
    print("Vsechny potrebne tridy (GL3Library/GL3Program/GL3Export + ViewProvidery): OK")

    print()
    print("VSE OK - Init.py zaregistruje proxy tridy uz pri startu FreeCADu,")
    print("bez ohledu na to, jestli byla NEG/GL3 workbench nekdy aktivovana.")


if __name__ == "__main__":
    main()
