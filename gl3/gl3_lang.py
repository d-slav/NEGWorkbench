# -*- coding: utf-8 -*-
"""
gl3_lang.py - lexer + parser pro podmnozinu jazyka GL3 (NEG).

Zamerne NEPODPORUJE obecny GOTO/navesti. Jediny idiom s navestim,
ktery se v realnych podprogramech objevuje (navesti + zpetny podmineny
skok na nej = "opakuj dokud"), se rozpozna uz na urovni predzpracovani
radku a preveden na strukturovany blok RepeatWhile. Jakykoli jiny skok
je chyba (parser jasne rekne, ze takovy tvar neumi - musel by se pri
portovani rucne prepsat).

Zadna geometricka semantika tu neni - to je vec gl3_ops.py.
Tenhle soubor jen preklada text programu na AST.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Tuple
import re


# ---------------------------------------------------------------------------
# AST uzly
# ---------------------------------------------------------------------------

@dataclass
class Num:
    value: float


@dataclass
class Str:
    """Retezcovy literal, napr. 'A' v IDEV,'A',1. Pouziva se jen tam, kde
    GL3 ocekava konstantni text (jmeno souboru u IDEV) - typ B ze shrnuti
    (skalar/retezec smi prijit zvenku jen jako konstanta, nikdy expression)."""
    value: str


@dataclass
class Var:
    name: str
    index: Optional[object] = None  # vyraz (Num/Var/BinOp/OpCall) nebo None


@dataclass
class BinOp:
    op: str  # '+', '-', '*', '/'
    left: object
    right: object


@dataclass
class UnaryMinus:
    operand: object


@dataclass
class OpCall:
    opcode: str
    args: List[object]


@dataclass
class Omitted:
    """Vynechany volitelny parametr uprostred (nebo na konci) seznamu
    argumentu OpCall - napr. DM=D28>E,,P2 vynechava P1 (prazdne misto
    mezi dvema carkami). Odlisne od proste chybejiciho koncoveho
    argumentu (D28>E,P1), coz GL3 take podporuje - tady jde navic o
    vynechani NEKDE UPROSTRED seznamu, ktere obycejny volitelny-
    parametr-na-konci vzor (Python *args) nedokaze vyjadrit.
    Vyhodnoti se na sentinel OMITTED (viz gl3_interpreter.eval_expr) -
    jednotlive opcody (v gl3_ops.py) uz rozhoduji, jakou vychozi
    hodnotu za vynechany parametr dosadit."""
    pass


class _OmittedSentinelType:
    """Sentinel hodnota vyhodnoceneho Omitted() uzlu - viz gl3_lang.Omitted.
    Zamerne ODLISNA od None (ktere v interpretu znamena 'predchozi
    operace nemela reseni' - viz eval_expr/OpCall a NoSolution)."""
    __slots__ = ()

    def __repr__(self):
        return "OMITTED"

    def __bool__(self):
        return False


OMITTED = _OmittedSentinelType()


@dataclass
class Compare:
    rel: str  # GT, LT, EQ, NE, GE, LE
    left: object
    right: object


@dataclass
class IsUndefined:
    """Test 'je X nedefinovane?' - vznikne z IFN/X/... (kde X neobsahuje
    zadnou relaci GT/LT/...). Typicky se objevi po cteni pole ze souboru
    pres READ/GET: po vycerpani zaznamu se do cile priradi None misto
    hodnoty a tenhle test detekuje konec dat (idiom IFN/PI(I)/THEN...).
    """
    expr: object


@dataclass
class IsDefined:
    """Test 'je X definovane?' - negace IsUndefined, vznikne z holeho
    IF/X/... (bez pismene za IF, na rozdil od IFN/IFI/IFD/... - viz
    gl3_keywords.json: 'IF' = 'Akce podminena definovanosti objektu',
    'IFN' = 'Akce podminena nedefinovanosti objektu' - obe puvodni,
    samostatna klicova slova)."""
    expr: object


# --- statementy ---

@dataclass
class Assign:
    target: str
    target_index: Optional[object]
    value: object


@dataclass
class CallStmt:
    name: str
    args: List[str]  # jmena promennych/vyrazu predanych podprogramu


@dataclass
class CommandStmt:
    """Obecny prikaz typu SCALE,... (neni to prirazeni ani CALL)."""
    name: str
    args: List[object]


@dataclass
class DimenStmt:
    entries: List[Tuple[str, int]]  # (jmeno, velikost)


@dataclass
class DataStmt:
    target_name: str
    target_index: Optional[object]  # vyraz (index v poli) nebo None (=> od 1)
    count: object  # vyraz "vi" - pocet objektu
    values: List[object]  # AST uzly (Num/Str/UnaryMinus) - syrove konstanty


@dataclass
class DoLoop:
    var: str
    start: object
    end: object
    body: List[object]
    step: Optional[object] = None  # vyraz "vi3" (krok) - None => implicitni 1


@dataclass
class BreakStmt:
    """Rozsireni nad ramec puvodniho GL-3 - predcasne ukonceni nejblizsiho
    obepinajiciho cyklu (DO/FOR nebo REPEATWHILE)."""
    pass


@dataclass
class ContinueStmt:
    """Rozsireni nad ramec puvodniho GL-3 - preskoci na dalsi iteraci
    nejblizsiho obepinajiciho cyklu (DO/FOR nebo REPEATWHILE). Nezamenovat
    s puvodnim GL-3 prikazem CONTIN (ten je jen no-op/zvyrazneni cteni)."""
    pass


@dataclass
class IfBlock:
    kind: str  # napr. "IFD"
    cond: Compare
    body: List[object]
    # Blok ELSE (viz G12.md, treti varianta akce THEN-ELSE-ENDIF) - None
    # znamena "zadny ELSE" (druha varianta akce, jen THEN-ENDIF, puvodni
    # chovani). Provede se, jestlize podminka NENI splnena.
    else_body: Optional[List[object]] = None


@dataclass
class IfShort:
    kind: str
    cond: Compare
    stmt: object


@dataclass
class RepeatWhile:
    """Preklad idiomu 'navesti + zpetny podmineny skok' ze zdrojoveho GL3."""
    kind: str
    cond: Compare
    body: List[object]


@dataclass
class IODevStmt:
    """IDEV,'jmeno'[,kanal] - otevre formatovany vstupni soubor na kanalu
    (0/1/2, default 0). IDEVB/ODEV/ODEVB zatim nepodporovano - az budou
    potreba."""
    command: str  # zatim vzdy "IDEV"
    filename: object  # vyraz (typicky Str) - vyhodnoti se na jmeno souboru
    channel: Optional[object]  # vyraz nebo None (=> kanal 0)


@dataclass
class IOTarget:
    """Jeden cil v GET/READ prikazu - promenna, pripadne indexovana."""
    name: str
    index: Optional[object] = None


@dataclass
class InputStmt:
    """GET/GET1/GET2/GETT nebo READ/READ1/READ2/READT s cilovymi
    promennymi. GETT/READT (terminal) parsuji se, ale interpret je
    v davkovem behu odmitne - nema odkud interaktivne cist."""
    command: str
    targets: List[IOTarget]


@dataclass
class OutputStmt:
    """PRINT/PRINT1/PRINT2/PRINTT/TRACE a WRITE/WRITE1/WRITE2/WRITET -
    vypis objektu na vystupni zarizeni. Dokud neni implementovano ODEV/
    ODEVB, chova se to spravne stejne jako v originale bez nastaveneho
    vystupniho zarizeni: vse jde na terminal (konzoli)."""
    command: str
    targets: List[IOTarget]


@dataclass
class TypeStmt:
    """TYPE/TYPE1/TYPE2/TYPET - viz G13.md 'PRIKAZY VYSTUPU TYPU TYPE'.
    Na rozdil od PRINT/WRITE (jeden zaznam/radek NA OBJEKT) TYPE spoji
    CELY seznam parametru (vyrazy, promenne I DOSLOVNE KONSTANTY) do
    JEDINEHO zaznamu/radku - viz gl3_interpreter._exec_type. Stejne jako
    OutputStmt vyse: dokud neni implementovano ODEV/ODEVB, jde vzdy na
    terminal."""
    command: str
    items: List[object]  # obecne vyrazy (Var/Str/Num/OpCall/BinOp/...)


@dataclass
class CreStmt:
    """CRE,pg - zahajeni vytvareni retezce (viz G10.md 'VYTVARENI
    RETEZCU POMOCI KRESLICICH PRIKAZU'). 'pg' je cil typu E (rovinny
    retezec) nebo H (prostorovy - zatim nepodporovano)."""
    target_name: str
    target_index: Optional[object]


@dataclass
class EndCreStmt:
    """ENDCRE - uzavreni retezce zahajeneho prikazem CRE."""
    pass


@dataclass
class IniStmt:
    """INI (bez parametru) - zahajeni kresleni do 'skryteho retezce'
    aktualne bezici SUBRO (viz zadani uzivatele - zjednodusena nahrada
    puvodniho INI/OPE...CLOSE do souboru CL2, ktery uz nepotrebujeme).
    Nasledujici prikazy MOVE az do CLOSE stavi body do tohoto skryteho
    retezce - stejnym zpusobem jako CRE...ENDCRE stavi pojmenovany
    retezec, jen bez explicitniho cile."""
    pass


@dataclass
class CloseStmt:
    """CLOSE - uzavreni kresleni zahajeneho prikazem INI. Nasbirane
    body se pripoji do skryteho retezce aktualni SUBRO (ktery se pri
    navratu z CALL pripoji do skryteho retezce volajiciho)."""
    pass


@dataclass
class MovePhrase:
    """Jedna fraze prikazu MOVE (viz G18.md 18.4) - 'pen' je 'up' (/,
    pero zvednuto) nebo 'down' (*, pero spusteno). 'sep' je oddelovac
    pouzity uvnitr fraze (None pro holou hodnotu, '#'/':'/',' jinak) -
    spolu s runtime typy vyhodnocenych 'values' urcuje az za behu
    (gerlib.move_geom), o jakou konkretni frazi jde (viz tamni
    dokumentace - stejny princip jako u D30/get_component)."""
    pen: str  # "up" | "down"
    sep: Optional[str]
    values: List[object]  # vyrazy (Num/Var/BinOp/OpCall/...)


@dataclass
class MoveStmt:
    """MOVE|fraze1|fraze2|... - viz G18.md 18.4."""
    phrases: List[MovePhrase]


@dataclass
class RetSub:
    pass


@dataclass
class SubroutineDef:
    name: str
    params: List[Tuple[str, Optional[int], str, Optional[str]]]  # (jmeno, velikost pole nebo None, "in"/"out", hint "file" nebo None)
    body: List[object]
    # Absolutni cesta k .GL3 souboru, ze ktereho tenhle SUBRO pochazi -
    # NENI soucasti parsovani (parse_program cestu vubec nezna), nastavuje
    # ji az volajici kod PO parsovani (Gl3FileRegistry.__getitem__ pro
    # SUBRO nactene pres CALL, GL3Program.execute() pro hlavni program).
    # Pouziva interpret pro zastupny text ${gl3_file_path} (viz
    # gl3_placeholders.py) - kazdemu bezicimu SUBRO (vc. vnorenych CALL)
    # tak odpovida adresar souboru, ve kterem je napsany, ne jen adresar
    # hlavniho programu.
    source_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Pomocne textove funkce (respektuji zavorky pri deleni na top-level casti)
# ---------------------------------------------------------------------------

_DATA_NUMBER_RE = re.compile(r"^[+-]?\d+\.?\d*([eE][+-]?\d+)?$")
_DATA_STRING_RE = re.compile(r"^'[^']*'$")


def _is_data_constants_line(line):
    """True, kdyz 'line' vypada jako cisty seznam konstant (cisla a/nebo
    retezcove literaly oddelene carkami) pro pokracovani prikazu DATA -
    pouziva se k rozpoznani, kolik nasledujicich radku jeste patri k
    DATA bloku (zadny jiny GL3 prikaz takhle nezacina - vzdy identifikator
    nebo klicove slovo, nikdy cislo/apostrof)."""
    if not line:
        return False
    parts = split_top_level(line, ",")
    if not parts:
        return False
    return all(_DATA_NUMBER_RE.match(p) or _DATA_STRING_RE.match(p) for p in parts)


def _split_move_phrases(rest):
    """'rest' je text prikazu MOVE PO odstraneni slova 'MOVE' (zacina
    perovym symbolem '/' nebo '*'). Vraci seznam (pen, phrase_text),
    kde pen je 'up' (/) nebo 'down' (*) - viz G18.md 18.4: '|' v
    obecnem zapisu prikazu je bud '/' (zvednute pero) nebo '*'
    (spustene pero). Respektuje zavorky (aritmeticky vyraz v zavorce
    smi obsahovat cokoliv, viz stejne pravidlo jako u split_top_level).
    """
    phrases = []
    depth = 0
    current = []
    pen = None
    for ch in rest:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif depth == 0 and ch in ("/", "*"):
            if pen is not None:
                phrases.append((pen, "".join(current).strip()))
            elif "".join(current).strip():
                raise SyntaxError(
                    "MOVE: text pred prvnim perovym symbolem (/ nebo *): %r" % (rest,)
                )
            pen = "up" if ch == "/" else "down"
            current = []
        else:
            current.append(ch)

    if pen is None:
        raise SyntaxError(
            "MOVE ocekava aspon jednu frazi uvozenou '/' (zvednute pero) "
            "nebo '*' (spustene pero): %r" % (rest,)
        )
    phrase_text = "".join(current).strip()
    if not phrase_text:
        raise SyntaxError("MOVE: prazdna fraze na konci prikazu: %r" % (rest,))
    phrases.append((pen, phrase_text))
    return phrases


def _split_move_phrase_fields(phrase_text):
    """Rozdeli text jedne fraze prikazu MOVE na (separator, [pole_textu]) -
    separator je prvni z '#', ':', ',' nalezeny na top-level (respektuje
    zavorky), nebo None, neni-li zadny pritomen (fraze je jedna holá
    hodnota). Viz G18.md 18.4: fraze pouziva vzdy jen JEDEN druh
    oddelovace ('vg', 'vg1:vg2', 'vg1#vg2', 'vg1,vg2,vg3[,vg4]')."""
    depth = 0
    sep_found = None
    for ch in phrase_text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch in ("#", ":", ","):
            sep_found = ch
            break
    if sep_found is None:
        return None, [phrase_text]
    return sep_found, split_top_level(phrase_text, sep_found)


def split_top_level(text, sep=","):
    parts = []
    depth = 0
    current = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p.strip() for p in parts]


# ---------------------------------------------------------------------------
# Lexer + expression parser
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"""
    (?P<STRING>'[^']*')
  | (?P<NUMBER>\d+\.\d*|\.\d+|\d+)
  | (?P<IDENT>[A-Za-z][A-Za-z0-9_]*)
  | (?P<OP>[+\-*/(),>])
""", re.VERBOSE)


def tokenize(text):
    tokens = []
    pos = 0
    text = text.strip()
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise SyntaxError("Neznamy znak v '%s' na pozici %d" % (text, pos))
        kind = m.lastgroup
        value = m.group()
        tokens.append((kind, value))
        pos = m.end()
    tokens.append(("EOF", None))
    return tokens


class ExprParser:
    """Rekurzivni sestup pro vyrazy vcetne OpCall(opcode>args) syntaxe."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect_op(self, value):
        kind, val = self.peek()
        if val != value:
            raise SyntaxError("Ocekavano '%s', nalezeno '%s'" % (value, val))
        return self.advance()

    # nejnizsi priorita: + -
    def parse_expr(self):
        node = self.parse_term()
        while self.peek()[1] in ("+", "-"):
            op = self.advance()[1]
            right = self.parse_term()
            node = BinOp(op, node, right)
        return node

    # vyssi priorita: * /
    def parse_term(self):
        node = self.parse_unary()
        while self.peek()[1] in ("*", "/"):
            op = self.advance()[1]
            right = self.parse_unary()
            node = BinOp(op, node, right)
        return node

    def parse_unary(self):
        if self.peek()[1] == "-":
            self.advance()
            return UnaryMinus(self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        kind, val = self.peek()

        if val == "(":
            self.advance()
            node = self.parse_expr()
            self.expect_op(")")
            return node

        if kind == "NUMBER":
            self.advance()
            return Num(float(val))

        if kind == "STRING":
            self.advance()
            return Str(val[1:-1])

        if kind == "IDENT":
            name = self.advance()[1]
            nxt = self.peek()[1]
            if nxt == "(":
                self.advance()
                index_expr = self.parse_expr()
                self.expect_op(")")
                return Var(name, index_expr)
            if nxt == ">":
                self.advance()
                args = self.parse_arg_list()
                return OpCall(name, args)
            return Var(name, None)

        raise SyntaxError("Neocekavany token: %r" % (val,))

    # Terminatory, ktere NEMOHOU zahajovat vyraz (viz parse_unary/
    # parse_primary - jedine povolene unarni predznamenani je '-', to
    # tedy NENI terminator) - pouzito k detekci vynechane pozice v
    # seznamu argumentu OpCall (viz Omitted, napr. "D28>E,,P2").
    _ARG_SLOT_TERMINATORS = (",", ")", "+", "*", "/")

    def _arg_slot_is_omitted(self):
        kind, val = self.peek()
        return kind == "EOF" or val in self._ARG_SLOT_TERMINATORS

    def parse_arg_list(self):
        args = [Omitted() if self._arg_slot_is_omitted() else self.parse_expr()]
        while self.peek()[1] == ",":
            self.advance()
            args.append(Omitted() if self._arg_slot_is_omitted() else self.parse_expr())
        return args


def parse_expr_text(text):
    parser = ExprParser(tokenize(text))
    node = parser.parse_expr()
    if parser.peek()[0] != "EOF":
        raise SyntaxError("Nespotrebovany zbytek vyrazu: %r" % (parser.peek(),))
    return node


def parse_expr_list_text(text):
    """Jako parse_expr_text, ale pro CELY carkami oddeleny seznam vyrazu
    (pouziva TypeStmt - viz G13.md 'PRIKAZY VYSTUPU TYPU TYPE'). Na
    rozdil od PRINT/WRITE/GET/READ (_parse_target_list - jen jmeno[(index)])
    TYPE explicitne povoluje i doslovne konstanty a obecne vyrazy v
    seznamu parametru, ne jen odkazy na promenne."""
    parser = ExprParser(tokenize(text))
    args = parser.parse_arg_list()
    if parser.peek()[0] != "EOF":
        raise SyntaxError("Nespotrebovany zbytek seznamu vyrazu: %r" % (parser.peek(),))
    return args


# ---------------------------------------------------------------------------
# Podminky (Compare) - dve moznosti zapisu: A.GT.B  nebo  A,GT,B
# ---------------------------------------------------------------------------

_DOT_REL_RE = re.compile(r"\.(GT|LT|EQ|NE|GE|LE)\.")
_RELS = ("GT", "LT", "EQ", "NE", "GE", "LE")


def parse_condition(text, if_kind=None):
    m = _DOT_REL_RE.search(text)
    if m:
        left_text = text[:m.start()]
        rel = m.group(1)
        right_text = text[m.end():]
        return Compare(rel, parse_expr_text(left_text), parse_expr_text(right_text))

    parts = split_top_level(text, ",")
    rel_idx = None
    for i, p in enumerate(parts):
        if p.strip() in _RELS:
            rel_idx = i
            break
    if rel_idx is None:
        # Zadna relace (GT/LT/...) - jde o unarni test definovanosti.
        # Hole 'IF/X/...' (if_kind == "") je 'je X DEFINOVANE?' (IsDefined),
        # kazde jine IFx/X/... (vc. IFN, ale i IFI/IFD/... bez ocekavane
        # relace) zustava 'je X NEdefinovane?' (IsUndefined) - puvodni
        # chovani beze zmeny, viz idiom IFN/PI(I)/THEN... pro detekci
        # konce dat po READ/GET za EOF (gl3_interpreter - READ/GET pri
        # vycerpani souboru priradi cili None misto vyjimky).
        if if_kind == "":
            return IsDefined(parse_expr_text(text))
        return IsUndefined(parse_expr_text(text))

    left_text = ",".join(parts[:rel_idx])
    rel = parts[rel_idx].strip()
    right_text = ",".join(parts[rel_idx + 1:])
    return Compare(rel, parse_expr_text(left_text), parse_expr_text(right_text))


# ---------------------------------------------------------------------------
# Predzpracovani radku: komentare, prazdne radky, navesti + zpetny skok
# ---------------------------------------------------------------------------

_LABEL_RE = re.compile(r"^(\d+):\s*(.*)$")
_GOTO_IFD_RE = re.compile(r"^IF([A-Z]?)/(.*)/(\d+)\s*$")


def _strip_trailing_comment(line):
    """Orizne koncovy komentar '< ...' - beznou soucast GL3 zdroje
    (viz priklady v dokumentaci: 'DIMEN,A(3)   < Definovani pole uhlu').
    '<' uvnitr retezcoveho literalu v uvozovkach se NEbere jako zacatek
    komentare."""
    in_quote = False
    for i, ch in enumerate(line):
        if ch == "'":
            in_quote = not in_quote
        elif ch == "<" and not in_quote:
            return line[:i]
    return line


def _strip_comments_and_blanks(raw_lines):
    out = []
    line_numbers = []
    for i, line in enumerate(raw_lines):
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped.lstrip().startswith("*"):
            continue
        stripped = _strip_trailing_comment(stripped)
        if stripped.strip() == "":
            continue
        out.append(stripped.strip())
        line_numbers.append(i + 1)  # 1-based cislo puvodniho radku
    return out, line_numbers


def preprocess_labels(lines, line_numbers):
    """Najde vzor 'navesti N: ... IFx/cond/N' (zpetny podmineny skok) a
    nahradi CELY tento usek (od navesti az po radek s GOTO, vcetne)
    jednou syntetickou strukturou ('REPEATWHILE', kind, cond, body_lines,
    body_line_numbers). Jakykoli jiny GOTO (dopredny skok, skok mimo
    tento vzor) zpusobi chybu az pri statement-parsovani (viz _parse_one).
    'line_numbers' je paralelni seznam (stejna delka jako 'lines') s
    puvodnimi cisly radku - pouziva se pro hlaseni chyb.
    """
    label_positions = {}
    for i, line in enumerate(lines):
        m = _LABEL_RE.match(line)
        if m:
            label_positions[m.group(1)] = i

    # najdi vsechny useky k nahrazeni: klic = index navesti (zacatek useku)
    spans_by_start = {}
    for j, line in enumerate(lines):
        m = _GOTO_IFD_RE.match(line)
        if not m:
            continue
        kind, cond_text, label = m.group(1), m.group(2), m.group(3)
        if label not in label_positions or label_positions[label] >= j:
            continue  # ne zpetny skok na znamou navesti - reseno jinde

        label_idx = label_positions[label]
        first_stmt = _LABEL_RE.match(lines[label_idx]).group(2)
        body_lines = ([first_stmt] if first_stmt else []) + list(lines[label_idx + 1:j])
        body_line_numbers = (
            ([line_numbers[label_idx]] if first_stmt else []) + list(line_numbers[label_idx + 1:j])
        )
        cond = parse_condition(cond_text, kind)
        spans_by_start[label_idx] = (j, "IF" + kind, cond, body_lines, body_line_numbers)

    if not spans_by_start:
        return lines, line_numbers

    out = []
    out_line_numbers = []
    i = 0
    while i < len(lines):
        if i in spans_by_start:
            goto_idx, kind, cond, body_lines, body_line_numbers = spans_by_start[i]
            out.append(("REPEATWHILE", kind, cond, body_lines, body_line_numbers))
            out_line_numbers.append(line_numbers[i])
            i = goto_idx + 1
            continue
        out.append(lines[i])
        out_line_numbers.append(line_numbers[i])
        i += 1
    return out, out_line_numbers


# ---------------------------------------------------------------------------
# Statement/block parser
# ---------------------------------------------------------------------------

class _Cursor:
    def __init__(self, lines, line_numbers=None):
        self.lines = lines
        self.line_numbers = line_numbers if line_numbers is not None else [None] * len(lines)
        self.i = 0

    def peek(self):
        return self.lines[self.i] if self.i < len(self.lines) else None

    def advance(self):
        item = self.lines[self.i]
        self.i += 1
        return item

    def current_line_no(self):
        """Cislo puvodniho zdrojoveho radku polozky, kterou vrati nejblizsi
        peek()/advance() (nebo None, pokud cursor nema cisla radku - napr.
        vnitrni pomocne pouziti, kde na tom nezalezi)."""
        return self.line_numbers[self.i] if self.i < len(self.line_numbers) else None

    def eof(self):
        return self.i >= len(self.lines)


def _attach_line_no(stmt_or_block, line_no):
    """Priradi cislo radku vysledku parsovani (pro pozdejsi chybova
    hlaseni) - nekteremu typu uzlu (napr. holy List z parse_block volane
    rekurzivne) se nedari priradit atribut, coz je v poradku."""
    try:
        stmt_or_block.line_no = line_no
    except Exception:
        pass


def parse_block(cursor, stop_words=()):
    """Parsuje statementy dokud nenarazi na jedno ze stop_words (napr. ENDDO)
    nebo konec vstupu."""
    stmts = []
    while not cursor.eof():
        item = cursor.peek()

        if isinstance(item, str) and item in stop_words:
            return stmts  # stop slovo NEKONZUMUJEME - odchyti ho volajici

        if isinstance(item, tuple) and item[0] == "REPEATWHILE":
            line_no = cursor.current_line_no()
            _, kind, cond, body_lines, body_line_numbers = cursor.advance()
            body_cursor = _Cursor(body_lines, body_line_numbers)
            body = parse_block(body_cursor)
            rw = RepeatWhile(kind, cond, body)
            _attach_line_no(rw, line_no)
            stmts.append(rw)
            continue

        line_no = cursor.current_line_no()
        line = cursor.advance()
        stmt_or_block = _parse_one(line, cursor)
        _attach_line_no(stmt_or_block, line_no)
        stmts.append(stmt_or_block)

    return stmts


def _parse_target_list(rest, cmd):
    """Rozparsuje seznam cilu (jmeno promenne, pripadne indexovane) pro
    GET/READ/PRINT/WRITE prikazy - napr. 'D1,I1,P(2)' -> [IOTarget('D1'),
    IOTarget('I1'), IOTarget('P', Num(2))]."""
    target_texts = split_top_level(rest, ",") if rest else []
    if not target_texts or target_texts[0] == "":
        raise SyntaxError("%s ocekava aspon jeden cil" % (cmd,))
    targets = []
    for t in target_texts:
        m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)(?:\((.+)\))?$", t.strip())
        if not m:
            raise SyntaxError("Nerozumim cili %r v prikazu %s" % (t, cmd))
        tname = m.group(1)
        tidx = parse_expr_text(m.group(2)) if m.group(2) else None
        targets.append(IOTarget(tname, tidx))
    return targets


def _parse_one(line, cursor):
    if line == "RETSUB":
        return RetSub()

    if line == "END":
        return RetSub()  # END na konci podprogramu - ekvivalent zavery

    if line.startswith("CALL/"):
        _, name, arglist = line.split("/", 2)
        args = split_top_level(arglist, ",")
        return CallStmt(name, args)

    if line.startswith("DIMEN,"):
        rest = line[len("DIMEN,"):]
        entries = []
        for part in split_top_level(rest, ","):
            m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\((\d+)\)$", part)
            if not m:
                raise SyntaxError("Nerozumim DIMEN polozce: %r" % (part,))
            entries.append((m.group(1), int(m.group(2))))
        return DimenStmt(entries)

    if line.startswith("DATA,"):
        rest = line[len("DATA,"):]
        target_text, count_text = split_top_level(rest, ",")

        m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)(?:\((.+)\))?$", target_text)
        if not m:
            raise SyntaxError("DATA: nerozumim cili %r" % (target_text,))
        target_name = m.group(1)
        target_index = parse_expr_text(m.group(2)) if m.group(2) else None
        count_expr = parse_expr_text(count_text)

        value_texts = []
        while True:
            nxt = cursor.peek()
            if nxt is None or not _is_data_constants_line(nxt):
                break
            value_texts.extend(split_top_level(cursor.advance(), ","))

        values = [parse_expr_text(v) for v in value_texts]
        return DataStmt(target_name, target_index, count_expr, values)

    if line == "BREAK":
        return BreakStmt()

    if line == "CONTINUE":
        return ContinueStmt()

    if line.startswith("DO,") or line.startswith("FOR,"):
        # DO/ENDDO a FOR/NEXT jsou v GL-3 plne rovnocenne synonyma (viz
        # dokumentace, kap. "PRIKAZ CYKLU") - parsuji se identicky a smi
        # se i kombinovat (zahajeni FOR ukoncene NEXT i ENDDO a naopak).
        prefix_len = len("DO,") if line.startswith("DO,") else len("FOR,")
        rest = line[prefix_len:]
        var_part, range_part = rest.split("=", 1)
        range_parts = split_top_level(range_part, ",")
        if len(range_parts) == 2:
            start_text, end_text = range_parts
            step_text = None
        elif len(range_parts) == 3:
            start_text, end_text, step_text = range_parts
        else:
            raise SyntaxError(
                "Nerozumim rozsahu cyklu %r (ocekavano pi=vi1,vi2[,vi3])" % (rest,)
            )
        body = parse_block(cursor, stop_words=("ENDDO", "NEXT"))
        cursor.advance()  # spotrebuj ENDDO/NEXT
        return DoLoop(
            var_part.strip(),
            parse_expr_text(start_text),
            parse_expr_text(end_text),
            body,
            parse_expr_text(step_text) if step_text else None,
        )

    m = re.match(r"^IF([A-Z]?)/(.*)/(THEN)$", line)
    if m:
        kind, cond_text = m.group(1), m.group(2)
        # Varianta 2 (jen THEN-ENDIF) i 3 (THEN-ELSE-ENDIF, viz G12.md) -
        # nejdriv se parsuje "THEN blok" az po prvni ze dvou moznych stop
        # slov, podle toho, ktere z nich to bylo, se pripadne parsuje
        # jeste "ELSE blok".
        then_body = parse_block(cursor, stop_words=("ELSE", "ENDIF"))
        stop_word = cursor.peek()  # jeste NEKONZUMOVANE - viz parse_block
        cursor.advance()  # spotrebuj ELSE nebo ENDIF
        else_body = None
        if stop_word == "ELSE":
            else_body = parse_block(cursor, stop_words=("ENDIF",))
            cursor.advance()  # spotrebuj ENDIF
        return IfBlock("IF" + kind, parse_condition(cond_text, kind), then_body, else_body)

    m = re.match(r"^IF([A-Z]?)/(.*)/(.*)$", line)
    if m:
        kind, cond_text, action_text = m.group(1), m.group(2), m.group(3)
        if action_text.strip().isdigit():
            raise SyntaxError(
                "Nepodporovany GOTO na navesti %s v radku: %r "
                "(mimo rozpoznany vzor 'opakuj dokud')" % (action_text, line)
            )
        action_stmt = _parse_one(action_text.strip(), cursor)
        return IfShort("IF" + kind, parse_condition(cond_text, kind), action_stmt)

    known_commands = ("SCALE", "DCOOS3", "TRA23")
    for cmd in known_commands:
        if line.startswith(cmd + ","):
            rest = line[len(cmd) + 1:]
            arg_texts = split_top_level(rest, ",")
            args = [parse_expr_text(a) for a in arg_texts]
            return CommandStmt(cmd, args)

    if line == "ACCUR" or line.startswith("ACCUR,"):
        rest = line[len("ACCUR"):]
        rest = rest[1:] if rest.startswith(",") else ""
        args = [parse_expr_text(rest)] if rest else []
        return CommandStmt("ACCUR", args)

    if line == "MESS" or line == "NOMESS":
        return CommandStmt(line, [])

    if line == "ABSOL" or line == "INCRE":
        return CommandStmt(line, [])

    if line.startswith("CRE,"):
        rest = line[len("CRE,"):]
        m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)(?:\((.+)\))?$", rest.strip())
        if not m:
            raise SyntaxError("CRE,pg: nerozumim cili %r" % (rest,))
        target_name = m.group(1)
        target_index = parse_expr_text(m.group(2)) if m.group(2) else None
        return CreStmt(target_name, target_index)

    if line == "ENDCRE":
        return EndCreStmt()

    if line == "INI":
        return IniStmt()

    if line == "CLOSE":
        return CloseStmt()

    if line == "MOVE" or line.startswith("MOVE/") or line.startswith("MOVE*"):
        rest = line[len("MOVE"):]
        raw_phrases = _split_move_phrases(rest)
        phrases = []
        for pen, phrase_text in raw_phrases:
            sep, field_texts = _split_move_phrase_fields(phrase_text)
            values = [parse_expr_text(t.strip()) for t in field_texts]
            phrases.append(MovePhrase(pen, sep, values))
        return MoveStmt(phrases)

    if line == "IDEV" or line.startswith("IDEV,"):
        rest = line[len("IDEV"):]
        rest = rest[1:] if rest.startswith(",") else ""
        parts = split_top_level(rest, ",") if rest else []
        if not parts or parts[0] == "":
            raise SyntaxError("IDEV ocekava aspon jmeno souboru, napr. IDEV,'A',1: %r" % (line,))
        filename_expr = parse_expr_text(parts[0])
        channel_expr = parse_expr_text(parts[1]) if len(parts) > 1 and parts[1] != "" else None
        return IODevStmt("IDEV", filename_expr, channel_expr)

    _IO_INPUT_COMMANDS = ("GET", "GET1", "GET2", "GETT", "READ", "READ1", "READ2", "READT")
    for cmd in _IO_INPUT_COMMANDS:
        if line == cmd or line.startswith(cmd + ","):
            rest = line[len(cmd):]
            rest = rest[1:] if rest.startswith(",") else ""
            targets = _parse_target_list(rest, cmd)
            return InputStmt(cmd, targets)

    _IO_OUTPUT_COMMANDS = (
        "PRINT", "PRINT1", "PRINT2", "PRINTT", "TRACE",
        "WRITE", "WRITE1", "WRITE2", "WRITET",
    )
    for cmd in _IO_OUTPUT_COMMANDS:
        if line == cmd or line.startswith(cmd + ","):
            rest = line[len(cmd):]
            rest = rest[1:] if rest.startswith(",") else ""
            targets = _parse_target_list(rest, cmd)
            return OutputStmt(cmd, targets)

    _TYPE_OUTPUT_COMMANDS = ("TYPE", "TYPE1", "TYPE2", "TYPET")
    for cmd in _TYPE_OUTPUT_COMMANDS:
        if line == cmd or line.startswith(cmd + ","):
            rest = line[len(cmd):]
            rest = rest[1:] if rest.startswith(",") else ""
            if not rest:
                raise SyntaxError("%s ocekava aspon jeden parametr" % (cmd,))
            items = parse_expr_list_text(rest)
            return TypeStmt(cmd, items)

    # jinak ocekavame prirazeni: TARGET[(index)] = vyraz
    if "=" in line:
        target_part, value_text = line.split("=", 1)
        target_part = target_part.strip()
        idx_match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\((.+)\)$", target_part)
        if idx_match:
            target_name = idx_match.group(1)
            target_index = parse_expr_text(idx_match.group(2))
        else:
            target_name = target_part
            target_index = None
        value = parse_expr_text(value_text.strip())
        return Assign(target_name, target_index, value)

    raise SyntaxError("Nerozpoznany radek: %r" % (line,))


# ---------------------------------------------------------------------------
# Parsovani hlavicky SUBRO a celeho souboru
# ---------------------------------------------------------------------------

_PARAM_RE = re.compile(
    r"^(in|out)(-f)?:([A-Za-z][A-Za-z0-9_]*)(?:\((\d+)\))?$", re.IGNORECASE
)


def parse_subro_header(line):
    """'SUBRO/SCARA/in:SP,out:SS,out:CNAB' ->
    ('SCARA', [('SP', None, 'in', None), ('SS', None, 'out', None), ('CNAB', None, 'out', None)])

    Smer (in:/out:) je POVINNY u kazdeho parametru - zamerne, aby se
    stare GL3 podprogramy nepredzavaly bez vedomeho rozhodnuti, co je
    vstup a co vystup (viz historicka nejednoznacnost u XPROC/P a K).
    Pro pomoc s anotovanim stareho zdroje bez teto syntaxe pouzij
    gl3_analysis.suggest_directions() - navrhne smery z pouziti v tele,
    ale porta si je musi rucne potvrdit/opravit primo v hlavicce.

    Volitelny '-f' hint (in-f:/out-f:, jen u B-parametru - jinak
    SyntaxError) rika "tenhle text je jmeno souboru" - pouziva ho jen
    GL3Program pri generovani FC property pro NEJVRCHNEJSI (hlavni)
    program, a jen pro in-f: (App::PropertyFile s hezkym file-browse
    tlacitkem misto App::PropertyString - viz gl3fc.gl3_program). U
    out-f:/out: se hint na FC property NIKDY nepromitne (vystupni
    "property = jmeno souboru" ve FreeCADu nedava smysl - jen pro
    vnitrni volani SUBRO, kde ma cistě dokumentacni hodnotu). NEJDE o
    tretí hodnotu 'direction' (ta zustava striste 'in'/'out') - je to
    ZCELA ODDELENY 4. prvek n-tice, aby zadne z existujicich
    porovnani 'direction == "in"/"out"' nikde v kodu nebylo treba
    menit."""
    _, name, params_text = line.split("/", 2)
    params = []
    for part in split_top_level(params_text, ","):
        m = _PARAM_RE.match(part.strip())
        if not m:
            raise SyntaxError(
                "Parametr %r v SUBRO/%s nema povinny prefix 'in:'/'out:' "
                "(pripadne 'in-f:'/'out-f:' u B-parametru) - napr. "
                "'in:SP', 'out:CNAB(11)', 'in-f:BJM'. Pouzij "
                "gl3_analysis.suggest_directions() pro navrh, pokud "
                "portujes stary zdroj bez teto anotace." % (part, name)
            )
        direction = m.group(1).lower()
        is_file_hint = m.group(2) is not None
        pname = m.group(3)
        size = int(m.group(4)) if m.group(4) else None
        if is_file_hint and not pname.upper().startswith("B"):
            raise SyntaxError(
                "Parametr %r v SUBRO/%s: hint '-f' (jmeno souboru) dava "
                "smysl jen u B-parametru (napr. 'in-f:BJM'), ne u %r"
                % (part, name, pname)
            )
        hint = "file" if is_file_hint else None
        params.append((pname, size, direction, hint))
    return name, params


def parse_program(raw_text):
    """Zparsuje cely obsah .GL3 souboru (jeden SUBRO) do SubroutineDef."""
    raw_lines = raw_text.splitlines()
    lines, line_numbers = _strip_comments_and_blanks(raw_lines)

    if not lines or not lines[0].startswith("SUBRO/"):
        raise SyntaxError("Ocekavan radek SUBRO/... na zacatku souboru")

    name, params = parse_subro_header(lines[0])
    body_lines, body_line_numbers = preprocess_labels(lines[1:], line_numbers[1:])

    cursor = _Cursor(body_lines, body_line_numbers)
    body = parse_block(cursor)

    return SubroutineDef(name, params, body)
