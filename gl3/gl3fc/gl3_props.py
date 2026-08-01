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

---

Reference format "JmenoObjektu.JmenoVystupu" nebo
"JmenoObjektu.JmenoVystupu(Index)" (GL3Export.Input, GL3Program
composite in: parametry) - viz parse_ref()/add_hidden_link(). Index v
zavorce (1 = prvni prvek) vybere JEDEN prvek z Array vystupu (napr.
'TEHLO002.PO(10)') - hodi se, kdyz vstup/export ocekava jednotlivy
composite prvek (napr. Point), ale zdrojovy vystup je cele pole. Bez
zavorky se pouzije cely vystup tak, jak je (Array i jinak).

Uzivatel vidi a edituje JEDNU textovou property (citelna, da se vlozit
odkudkoli). Pod kapotou se ale drzi SKUTECNA App::PropertyLink na
vyresolvovany objekt - DUVOD: FreeCAD si poradi recompute (kdo se ma
prepocitat driv) pocita z vlastnich Link/LinkSub/... property v grafu
zavislosti; holy text by v tomhle grafu vubec nebyl videt, takze by
recompute poradi prestalo byt garantovane (hrozily by zastarala data).
Tenhle skryty Link se drzi synchronizovany s textovou property pres
onChanged() (viz gl3_export.py/gl3_program.py) - FreeCAD onChanged()
se vola SYNCHRONNE hned pri zmene property (i programove, ne jen z
GUI), tedy jeste PRED tim, nez se vubec sestavi poradi pro dalsi
recompute - zadne zpozdeni o cyklus."""

import os
import re

_REF_RE = re.compile(r"^(?P<obj>[^.()]+)\.(?P<prop>[^.()]+)(?:\((?P<index>\d+)\))?$")


def parse_ref(text):
    """'JmenoObjektu.JmenoVystupu' nebo 'JmenoObjektu.JmenoVystupu(Index)'
    -> (jmeno_objektu, jmeno_vystupu, index), kde index je bud kladne
    cele cislo (1 = prvni prvek, tak jak ho zada uzivatel - odecteni na
    0-based index si dela az volajici) nebo None, pokud zavorka nebyla
    v textu vubec pouzita.

    Vraci (None, None, None) pro prazdny retezec nebo cokoliv, co
    neodpovida ocekavanemu formatu (chybejici tecka, prazdne jmeno
    objektu/vystupu po ostripovani, neplatny obsah zavorky - ...)."""
    if not text:
        return None, None, None
    m = _REF_RE.match(text.strip())
    if not m:
        return None, None, None
    obj_name = m.group("obj").strip()
    prop_name = m.group("prop").strip()
    if not obj_name or not prop_name:
        return None, None, None
    index_text = m.group("index")
    index = int(index_text) if index_text is not None else None
    return obj_name, prop_name, index


def add_hidden_link(obj, name, group, doc):
    """Prida (pokud jeste neexistuje) SKUTECNE skrytou App::PropertyLink -
    na rozdil od add_property() vyse tahle NEMA byt v Property View videt
    vubec (interni bookkeeping, viz modulovy docstring - "reference
    format"), proto NEVOLA setPropertyStatus("-Hidden") (presny opak
    add_property() - tady chceme Hidden flag ZACHOVAT/NASTAVIT, ne
    smazat)."""
    if hasattr(obj, name):
        return obj
    type_name = "App::PropertyLink"
    try:
        # attr=0, ro=False, hidden=True (pozicni argumenty za "doc" -
        # dostupne v beznych FreeCAD verzich; viz FreeCAD DocumentObjectPy
        # addProperty() signatura)
        obj.addProperty(type_name, name, group, doc, 0, False, True)
    except TypeError:
        # starsi/jina FreeCAD signatura addProperty() bez pozicnich
        # attr/ro/hidden argumentu - pridat aspon bez nich a skryt
        # dodatecne pres setPropertyStatus.
        obj.addProperty(type_name, name, group, doc)
        try:
            obj.setPropertyStatus(name, "Hidden")
        except AttributeError:
            pass
    return obj


def icon_path(filename):
    """Absolutni cesta k <doplnek>/Resources/icons/<filename> - pro
    ViewProvider.getIcon(), at se ve stromu zobrazuji stejne ikony jako
    v toolbaru/menu (viz gl3_commands.py), misto vychozi FreeCAD ikony.
    FreeCAD's getIcon() bezne akceptuje primo cestu k souboru na disku
    (svg/png), zadna registrace jako Qt resource neni potreba."""
    # tenhle soubor: <doplnek>/gl3/gl3fc/gl3_props.py
    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(addon_dir, "Resources", "icons", filename)


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
