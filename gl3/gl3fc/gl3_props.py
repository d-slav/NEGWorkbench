# -*- coding: utf-8 -*-
"""
gl3_props.py - sdileny helper pro pridavani property na FeaturePython
objekty v GL3Library/GL3Program/GL3Export.

Duvod existence: v realnem FreeCADu se ukazalo, ze nove pridane property
(pres obj.addProperty(...)) nebyly v Property editoru videt, dokud
uzivatel nezapnul "Show hidden" - i kdyz addProperty() bylo volano se
standardnimi (nehidden) argumenty. Tahle funkce proto po pridani property
jeste explicitne zavola setPropertyStatus(name, "-Hidden"), aby se na
defaultu FreeCADu/verzi nemuselo spolehat.

DULEZITE: setPropertyStatus(-Hidden) se vola JEN PRI PRVNIM VYTVORENI
property (uvnitr "if not hasattr" vetve), NE pri kazdem volani teto
funkce - i kdyz se overenim na realnem FreeCADu ukazalo, ze tohle
SAMOTNE neresi hlavni pozorovany problem (viz nize), je to porad
spravnejsi chovani nez volat status-zmenu opakovane bezduvodne.

POZOR (aktualizovano po testu na realnem FreeCADu): puvodni teorie, ze
"GL3 In" property zbytecne zluta jen kvuli opakovanemu prepinani
"-Hidden" statusu pri kazdem execute(), se NEPOTVRDILA - i po opravene
(jen-jednou-volane) verzi se chovani nezmenilo. Skutecna prakticka
oprava byla jinde: prejit "GL3 Out" composite vystupy z
App::PropertyPythonObject (bez editoru -> nutne "Show all", vzdy
zluty fallback) na App::PropertyString drzici skutecny JSON text
(gerlib.serialize.dump_json()) + status ReadOnly - viz gl3_program.py.
Tim GL3 Out property maji vlastni editor (bezny textovy radek), jsou
videt vzdy (bez "Show all") a needitovatelne (sedive, ReadOnly), takze
uzivatel uz nikdy nepotrebuje zapinat "Show hidden" jen kvuli vystupum
- a tedy se ani nesetka s tim, ze by se "GL3 In" pri tom prepnuti
prekreslilo/zbarvilo (bez ohledu na to, co presne tenhle FreeCAD
UI jev zpusobovalo).

POZOR: property typy, ktere v Property View nemaji zadny editor
(napr. App::PropertyPythonObject, App::PropertyVectorList) - takove
property se nezobrazi vubec, dokud uzivatel nezapne "Show all", a i pak
jsou jen ke cteni, bez ohledu na "-Hidden" (viz FreeCAD PR #3535,
realthunder). Pro cokoliv, co ma byt v Property View editovatelne (nebo
alespon viditelne) hned po vytvoreni, pouzij typ s vestavenym editorem
(PropertyString, -Float, -Bool, -StringList, ...) - pripadne read_only=True
z teto funkce, pokud ma jit jen o needitovatelny vypis.
"""


def add_property(obj, type_name, name, group, doc, read_only=False):
    """Prida property (pokud jeste neexistuje) a zajisti, ze neni skryta.

    setPropertyStatus se vola jen pri prvnim vytvoreni property, ne pri
    kazdem opakovanem volani teto funkce (viz modulovy docstring vyse) -
    jinak by se stejna property pri kazdem execute()/recompute znovu a
    znovu prepinala mezi hidden/nehidden.

    read_only=True navic nastavi "ReadOnly" status (jen kosmeticky - v
    Property View se property zobrazi seda/needitovatelna; z Pythonu
    (napr. z execute()) se do ni pres setattr porad da normalne psat,
    ReadOnly omezuje jen GUI editaci). Hodi se pro vypocitane "out"
    property - uzivatel by je stejtak nemel rucne editovat."""
    if hasattr(obj, name):
        return obj

    obj.addProperty(type_name, name, group, doc)
    try:
        obj.setPropertyStatus(name, "-Hidden")
    except AttributeError:
        pass  # starsi FreeCAD bez setPropertyStatus - neni kriticke

    if read_only:
        try:
            obj.setPropertyStatus(name, "ReadOnly")
        except AttributeError:
            pass

    return obj
