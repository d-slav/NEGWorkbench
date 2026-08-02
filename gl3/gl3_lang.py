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
class Compare:
    rel: str  # GT, LT, EQ, NE, GE, LE
    left: object
    right: object


@dataclass
class IsUndefined:
    """Test 'je X nedefinovane?' - vznikne z IFx/X/... kde X neobsahuje
    zadnou relaci (GT/LT/...). Typicky se objevi po cteni pole ze souboru
    pres READ/GET: po vycerpani zaznamu se do cile priradi None misto
    hodnoty a tenhle test detekuje konec dat (idiom IFN/PI(I)/THEN...).
    """
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
    array_name: str
    size: int
    values: List[float]


@dataclass
class DoLoop:
    var: str
    start: object
    end: object
    body: List[object]


@dataclass
class IfBlock:
    kind: str  # napr. "IFD"
    cond: Compare
    body: List[object]


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
class RetSub:
    pass


@dataclass
class SubroutineDef:
    name: str
    params: List[Tuple[str, Optional[int], str]]  # (jmeno, velikost pole nebo None, "in"/"out")
    body: List[object]


# ---------------------------------------------------------------------------
# Pomocne textove funkce (respektuji zavorky pri deleni na top-level casti)
# ---------------------------------------------------------------------------

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

import re

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

    def parse_arg_list(self):
        args = [self.parse_expr()]
        while self.peek()[1] == ",":
            self.advance()
            args.append(self.parse_expr())
        return args


def parse_expr_text(text):
    parser = ExprParser(tokenize(text))
    node = parser.parse_expr()
    if parser.peek()[0] != "EOF":
        raise SyntaxError("Nespotrebovany zbytek vyrazu: %r" % (parser.peek(),))
    return node


# ---------------------------------------------------------------------------
# Podminky (Compare) - dve moznosti zapisu: A.GT.B  nebo  A,GT,B
# ---------------------------------------------------------------------------

_DOT_REL_RE = re.compile(r"\.(GT|LT|EQ|NE|GE|LE)\.")
_RELS = ("GT", "LT", "EQ", "NE", "GE", "LE")


def parse_condition(text):
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
        # Zadna relace (GT/LT/...) - jde o unarni test "je X nedefinovane?"
        # (idiom IFN/X/THEN... pro detekci konce dat po READ/GET za EOF -
        # viz gl3_interpreter, kde READ/GET pri vycerpani souboru priradi
        # cili None misto vyjimky).
        return IsUndefined(parse_expr_text(text))

    left_text = ",".join(parts[:rel_idx])
    rel = parts[rel_idx].strip()
    right_text = ",".join(parts[rel_idx + 1:])
    return Compare(rel, parse_expr_text(left_text), parse_expr_text(right_text))


# ---------------------------------------------------------------------------
# Predzpracovani radku: komentare, prazdne radky, navesti + zpetny skok
# ---------------------------------------------------------------------------

_LABEL_RE = re.compile(r"^(\d+):\s*(.*)$")
_GOTO_IFD_RE = re.compile(r"^IF([A-Z])/(.*)/(\d+)\s*$")


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
    for line in raw_lines:
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped.lstrip().startswith("*"):
            continue
        stripped = _strip_trailing_comment(stripped)
        if stripped.strip() == "":
            continue
        out.append(stripped.strip())
    return out


def preprocess_labels(lines):
    """Najde vzor 'navesti N: ... IFx/cond/N' (zpetny podmineny skok) a
    nahradi CELY tento usek (od navesti az po radek s GOTO, vcetne)
    jednou syntetickou strukturou ('REPEATWHILE', kind, cond, body_lines).
    Jakykoli jiny GOTO (dopredny skok, skok mimo tento vzor) zpusobi chybu
    az pri statement-parsovani (viz _parse_one).
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
        cond = parse_condition(cond_text)
        spans_by_start[label_idx] = (j, "IF" + kind, cond, body_lines)

    if not spans_by_start:
        return lines

    out = []
    i = 0
    while i < len(lines):
        if i in spans_by_start:
            goto_idx, kind, cond, body_lines = spans_by_start[i]
            out.append(("REPEATWHILE", kind, cond, body_lines))
            i = goto_idx + 1
            continue
        out.append(lines[i])
        i += 1
    return out


# ---------------------------------------------------------------------------
# Statement/block parser
# ---------------------------------------------------------------------------

class _Cursor:
    def __init__(self, lines):
        self.lines = lines
        self.i = 0

    def peek(self):
        return self.lines[self.i] if self.i < len(self.lines) else None

    def advance(self):
        item = self.lines[self.i]
        self.i += 1
        return item

    def eof(self):
        return self.i >= len(self.lines)


def parse_block(cursor, stop_words=()):
    """Parsuje statementy dokud nenarazi na jedno ze stop_words (napr. ENDDO)
    nebo konec vstupu."""
    stmts = []
    while not cursor.eof():
        item = cursor.peek()

        if isinstance(item, str) and item in stop_words:
            return stmts  # stop slovo NEKONZUMUJEME - odchyti ho volajici

        if isinstance(item, tuple) and item[0] == "REPEATWHILE":
            _, kind, cond, body_lines = cursor.advance()
            body_cursor = _Cursor(body_lines)
            body = parse_block(body_cursor)
            stmts.append(RepeatWhile(kind, cond, body))
            continue

        line = cursor.advance()
        stmt_or_block = _parse_one(line, cursor)
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
        name, size_text = split_top_level(rest, ",")
        size = int(size_text)
        values_line = cursor.advance()
        values = [float(v) for v in split_top_level(values_line, ",")]
        if len(values) != size:
            raise SyntaxError(
                "DATA %s: ocekavano %d hodnot, nalezeno %d"
                % (name, size, len(values))
            )
        return DataStmt(name, size, values)

    if line.startswith("DO,"):
        rest = line[len("DO,"):]
        var_part, range_part = rest.split("=", 1)
        start_text, end_text = split_top_level(range_part, ",")
        body = parse_block(cursor, stop_words=("ENDDO",))
        cursor.advance()  # spotrebuj ENDDO
        return DoLoop(
            var_part.strip(),
            parse_expr_text(start_text),
            parse_expr_text(end_text),
            body,
        )

    m = re.match(r"^IF([A-Z])/(.*)/(THEN)$", line)
    if m:
        kind, cond_text = m.group(1), m.group(2)
        body = parse_block(cursor, stop_words=("ENDIF",))
        cursor.advance()  # spotrebuj ENDIF
        return IfBlock("IF" + kind, parse_condition(cond_text), body)

    m = re.match(r"^IF([A-Z])/(.*)/(.*)$", line)
    if m:
        kind, cond_text, action_text = m.group(1), m.group(2), m.group(3)
        if action_text.strip().isdigit():
            raise SyntaxError(
                "Nepodporovany GOTO na navesti %s v radku: %r "
                "(mimo rozpoznany vzor 'opakuj dokud')" % (action_text, line)
            )
        action_stmt = _parse_one(action_text.strip(), cursor)
        return IfShort("IF" + kind, parse_condition(cond_text), action_stmt)

    known_commands = ("SCALE", "DCOOS3", "TRA23")
    for cmd in known_commands:
        if line.startswith(cmd + ","):
            rest = line[len(cmd) + 1:]
            arg_texts = split_top_level(rest, ",")
            args = [parse_expr_text(a) for a in arg_texts]
            return CommandStmt(cmd, args)

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
    r"^(in|out):([A-Za-z][A-Za-z0-9_]*)(?:\((\d+)\))?$", re.IGNORECASE
)


def parse_subro_header(line):
    """'SUBRO/SCARA/in:SP,out:SS,out:CNAB' ->
    ('SCARA', [('SP', None, 'in'), ('SS', None, 'out'), ('CNAB', None, 'out')])

    Smer (in:/out:) je POVINNY u kazdeho parametru - zamerne, aby se
    stare GL3 podprogramy nepredzavaly bez vedomeho rozhodnuti, co je
    vstup a co vystup (viz historicka nejednoznacnost u XPROC/P a K).
    Pro pomoc s anotovanim stareho zdroje bez teto syntaxe pouzij
    gl3_analysis.suggest_directions() - navrhne smery z pouziti v tele,
    ale porta si je musi rucne potvrdit/opravit primo v hlavicce.
    """
    _, name, params_text = line.split("/", 2)
    params = []
    for part in split_top_level(params_text, ","):
        m = _PARAM_RE.match(part.strip())
        if not m:
            raise SyntaxError(
                "Parametr %r v SUBRO/%s nema povinny prefix 'in:' nebo "
                "'out:' (napr. 'in:SP', 'out:CNAB(11)'). Pouzij "
                "gl3_analysis.suggest_directions() pro navrh, pokud "
                "portujes stary zdroj bez teto anotace." % (part, name)
            )
        direction = m.group(1).lower()
        pname = m.group(2)
        size = int(m.group(3)) if m.group(3) else None
        params.append((pname, size, direction))
    return name, params


def parse_program(raw_text):
    """Zparsuje cely obsah .GL3 souboru (jeden SUBRO) do SubroutineDef."""
    raw_lines = raw_text.splitlines()
    lines = _strip_comments_and_blanks(raw_lines)

    if not lines or not lines[0].startswith("SUBRO/"):
        raise SyntaxError("Ocekavan radek SUBRO/... na zacatku souboru")

    name, params = parse_subro_header(lines[0])
    body_lines = preprocess_labels(lines[1:])

    cursor = _Cursor(body_lines)
    body = parse_block(cursor)

    return SubroutineDef(name, params, body)
