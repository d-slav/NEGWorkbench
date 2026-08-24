# -*- coding: utf-8 -*-
"""
gl3_placeholders.py - nahrazovani zastupnych textu (placeholderu) tvaru
${jmeno} v retezcich pouzitych jako cesty k souborum/adresarum.

Zamerne bez jakekoli zavislosti na FreeCADu (na rozdil od gl3fc/*.py) -
pouziva ho primo interpret (gl3_interpreter.py, IDEV), i gl3fc moduly
(GL3Program.SourceFile, GL3Library.SearchPaths), ktere si samy zjisti
skutecne hodnoty (adresar workbenche, adresar FreeCAD dokumentu) a
predaji je sem.

Podporovane jmeno zastupneho textu urcuje VOLAJICI (dict 'values') - ne
tenhle modul; ten jen mechanicky nahradi ${jmeno} za values["jmeno"], a
jasne nahlasi:
  - neznamy zastupny text (jmeno vubec neni v 'values') - typicky
    preklep, nebo pouziti na miste, kde dany zastupny text vubec
    nedava smysl (napr. ${gl3_file_path} v GL3Library.SearchPaths).
  - znamy, ale v tomto kontextu nedostupny zastupny text (values[jmeno]
    je None) - typicky neulozeny FreeCAD dokument (${fc_file_path}).
"""

import re

_PLACEHOLDER_RE = re.compile(r"\$\{(\w+)\}")


def substitute(text, values):
    """Nahradi vsechny vyskyty ${jmeno} v 'text' za values['jmeno'].

    'text' - retezec (jina hodnota se vrati beze zmeny - vola se typicky
        na vysledek jiz vyhodnoceneho GL3 vyrazu, ktery nemusi byt
        retezec vubec, napr. IDEV s cislenym kanalem misto jmena).
    'values' - dict {jmeno: retezec nebo None}. None znamena "znamy
        zastupny text, ale v tomhle kontextu nema hodnotu" (jasna
        chyba, ne tichy prazdny retezec).

    Vraci 'text' beze zmeny, pokud neobsahuje zadne '${' (rychly
    vystup pro (naprostou vetsinu) retezcu bez zastupnych textu vubec).
    """
    if not isinstance(text, str) or "${" not in text:
        return text

    def _sub(match):
        name = match.group(1)
        if name not in values:
            raise ValueError(
                "Neznamy zastupny text '${%s}' (zname na tomto miste: %s)"
                % (name, ", ".join(sorted(values)) or "zadne")
            )
        value = values[name]
        if value is None:
            raise ValueError(
                "Zastupny text '${%s}' neni v tomto kontextu k dispozici "
                "(napr. ${fc_file_path} vyzaduje ulozeny FreeCAD dokument)"
                % (name,)
            )
        return value

    return _PLACEHOLDER_RE.sub(_sub, text)
