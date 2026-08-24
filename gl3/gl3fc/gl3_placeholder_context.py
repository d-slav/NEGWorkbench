# -*- coding: utf-8 -*-
"""
gl3_placeholder_context.py - FreeCAD-znale zjistovani hodnot pro zastupne
texty ${workbench_path}/${fc_file_path} (viz gl3_placeholders.py -
mechanicke nahrazovani samotne, bez FreeCAD zavislosti, je tam;
${gl3_file_path} resi uz sam Interpreter, viz gl3_interpreter.py
_source_path_stack - neni ho treba zjistovat tady).

Pouzito z GL3Program.execute() (SourceFile) a GL3Library.build_registry()
(SearchPaths) - obe potrebuji stejne dve hodnoty, tak jsou pohromade
na jednom miste misto duplikovani v obou souborech.
"""

import os


def workbench_path():
    """Absolutni cesta k adresari, kde je nainstalovany cely doplnek
    (<doplnek>/) - stejny vypocet, jaky uz pouziva gl3_props.icon_path()
    a gl3_library._default_search_dirs()."""
    # tenhle soubor: <doplnek>/gl3/gl3fc/gl3_placeholder_context.py
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fc_file_path(obj):
    """Adresar, ve kterem je ulozeny FreeCAD dokument obsahujici 'obj'
    (GL3Program/GL3Library), nebo None, neni-li dokument (jeste) ulozeny
    na disk (FreeCAD.Document.FileName je v tom pripade prazdny retezec)
    - pouziti ${fc_file_path} pak vyhodi jasnou chybu (viz
    gl3_placeholders.substitute), ne tichou spatnou hodnotu."""
    doc = getattr(obj, "Document", None)
    filename = getattr(doc, "FileName", "") if doc is not None else ""
    if not filename:
        return None
    return os.path.dirname(os.path.abspath(filename))


def static_placeholders(obj):
    """Pohodlny pomocnik - {"workbench_path":..., "fc_file_path":...}
    pro predani primo do Interpreter(path_placeholders=...) i do
    gl3_placeholders.substitute() (SourceFile/SearchPaths, kde
    ${gl3_file_path} nedava smysl - viz volajici kod, ktery pro tenhle
    ucel jeste dopni "gl3_file_path": None)."""
    return {"workbench_path": workbench_path(), "fc_file_path": fc_file_path(obj)}
