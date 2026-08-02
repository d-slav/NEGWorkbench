# -*- coding: utf-8 -*-
"""
gl3_interpreter.py - provede AST (SubroutineDef.body) vyprodukovany
gl3_lang.parse_program proti:
  - OPERATIONS  (gl3_ops.py) - operace volane syntaxi OPCODE>args
  - COMMANDS    (gl3_ops.py) - prikazy jako SCALE
  - registru dalsich SubroutineDef (CALL/name/args) - vnorene podprogramy
    vcetne HLO, az ho dodas jako HLO.GL3

Semantika CALL je "kopie pri volani, kopie pri navratu" (viz diskuze
o referencnich parametrech) - zadne sdileni pameti mezi bezicimi
podprogramy, jen vstupni hodnoty se zkopiruji dovnitr a vystupni
hodnoty se po dobehnuti zkopiruji zpatky do volajiciho prostredi.
"""

import os
import re

from gl3_lang import (
    Var, Num, Str, BinOp, UnaryMinus, OpCall,
    Assign, CallStmt, CommandStmt, DimenStmt, DataStmt,
    DoLoop, IfBlock, IfShort, RepeatWhile, RetSub,
    IODevStmt, IOTarget, InputStmt, OutputStmt, IsUndefined,
    parse_expr_text,
)
from gl3_ops import (
    OPERATIONS, COMMANDS, Point, Curve, classify, NotYetImplemented,
    ARRAY_REF_OPS, builtin_constants,
)
from gerlib import define_coord_system3, transform3
from gl3_analysis import get_param_directions, _is_identifier


# ---------------------------------------------------------------------------
# Cislo kanalu podle jmena prikazu (GET/READ = 0, GET1/READ1 = 1, ...,
# GETT/READT = "T" pro terminal - v davkovem behu nepodporovano).
# ---------------------------------------------------------------------------

_CHANNEL_BY_COMMAND = {
    "GET": 0, "READ": 0,
    "GET1": 1, "READ1": 1,
    "GET2": 2, "READ2": 2,
    "GETT": "T", "READT": "T",
}


class RetSubSignal(Exception):
    """Rizeni behu - ukonci provadeni aktualniho podprogramu (RETSUB/END)."""
    pass


_REL_FUNCS = {
    "GT": lambda a, b: a > b,
    "LT": lambda a, b: a < b,
    "GE": lambda a, b: a >= b,
    "LE": lambda a, b: a <= b,
    "EQ": lambda a, b: a == b,
    "NE": lambda a, b: a != b,
}


class Interpreter:
    def __init__(self, registry=None, operations=None, commands=None, io_base_dir="."):
        """
        registry   - dict {jmeno_podprogramu: SubroutineDef}, vcetne HLO
                     az ji dodas (bez ni CALL/HLO/... vyhodi jasnou chybu,
                     ne tichou spatnou hodnotu).
        operations - registr OPCODE>args funkci (vychozi OPERATIONS)
        commands   - registr prikazu jako SCALE (vychozi COMMANDS)
        io_base_dir - adresar, vuci kteremu se hleda relativni jmeno
                     souboru z IDEV (puvodni VMS konvence s automatickym
                     pripojenim pripony napr. '.RDT' zamerne NEreplikujeme -
                     jmeno souboru z IDEV se pouzije doslovne).
        """
        self.registry = registry or {}
        self.operations = operations if operations is not None else OPERATIONS
        self.commands = commands if commands is not None else COMMANDS
        self.io_base_dir = io_base_dir
        self.io_channels = {}  # {0/1/2: {"file": fh, "path": str}} - nastaveno IDEV
        self._directions_cache = {}
        # Souradnicove soustavy definovane DCOOS3 (viz gerlib.dcoos3) -
        # {1..10: CoordSystem3}. Sdilene pres cely beh (vc. vnorenych CALL -
        # jeden Interpreter = jeden beh hlavniho SUBRO), ale IZOLOVANE per
        # beh - novy Interpreter() (= novy GL3Program.execute()) zacina
        # vzdy s prazdnou sadou.
        self.coordinate_systems = {}

    # ------------------------------------------------------------------
    # verejne API
    # ------------------------------------------------------------------

    def run(self, subdef, inputs):
        """Spusti podprogram s danymi vstupnimi hodnotami (dict jmeno->hodnota
        pro vstupni formalni parametry). Vraci cely lokalni environment
        (vcetne vystupu) - uzitecne pro testovani/debug.

        I/O kanaly (IDEV) jsou globalni pro cely beh programu (sdilene i
        pres vnorene CALL) a resetuji/zaviraji se na zacatku a konci
        kazdeho volani run() - odpovida tomu, ze jde o novy beh programu.
        """
        env = builtin_constants()
        env.update(inputs)
        self.io_channels = {}
        try:
            self._exec_block(subdef.body, env)
        except RetSubSignal:
            pass
        finally:
            for state in self.io_channels.values():
                try:
                    state["file"].close()
                except Exception:
                    pass
        return env

    # ------------------------------------------------------------------
    # vyhodnoceni vyrazu
    # ------------------------------------------------------------------

    def eval_expr(self, node, env):
        if isinstance(node, Num):
            return node.value

        if isinstance(node, Str):
            return node.value

        if isinstance(node, Var):
            if node.name not in env:
                raise NameError(
                    "Promenna '%s' nebyla pred pouzitim nastavena" % node.name
                )
            value = env[node.name]
            if node.index is not None:
                idx = int(round(self.eval_expr(node.index, env)))
                return value[idx - 1]
            return value

        if isinstance(node, BinOp):
            left = self.eval_expr(node.left, env)
            right = self.eval_expr(node.right, env)
            if node.op == "+":
                return left + right
            if node.op == "-":
                return left - right
            if node.op == "*":
                return left * right
            if node.op == "/":
                return left / right
            raise ValueError("Neznamy operator %r" % node.op)

        if isinstance(node, UnaryMinus):
            return -self.eval_expr(node.operand, env)

        if isinstance(node, OpCall):
            fn = self.operations.get(node.opcode)
            if fn is None:
                raise KeyError(
                    "Operace '%s' neni v registru OPERATIONS vubec zavedena "
                    "(ani jako stub) - zkontroluj gl3_ops.py" % node.opcode
                )
            array_ref_positions = ARRAY_REF_OPS.get(node.opcode, ())
            args = []
            for i, a in enumerate(node.args):
                if i in array_ref_positions:
                    args.append(self._eval_array_ref(a, env))
                else:
                    args.append(self.eval_expr(a, env))
            return fn(*args)

        raise TypeError("Neznamy typ uzlu vyrazu: %r" % (node,))

    def _eval_array_ref(self, node, env):
        """Pro operace jako E01 (a pozdeji S01), ktere v puvodnim Fortranu
        ocekavaji 'adresu prvniho prvku pole + pocet' (zapis 'P(1),N' -
        precti N prvku pole P pocinaje P(1)): vrati podpole (list) zacinajici
        na danem indexu, ne jen jeden vyhodnoceny prvek."""
        if isinstance(node, Var):
            if node.name not in env:
                raise NameError("Promenna '%s' nebyla pred pouzitim nastavena" % (node.name,))
            value = env[node.name]
            if not isinstance(value, list):
                raise TypeError(
                    "'%s' se pouziva jako pole bodu (P(1),N), ale neni to pole"
                    % (node.name,)
                )
            if node.index is None:
                return value
            idx = int(round(self.eval_expr(node.index, env)))
            return value[idx - 1:]
        raise TypeError(
            "Ocekavano jmeno pole (napr. P nebo P(1)), dostal jiny vyraz: %r" % (node,)
        )

    def _set_indexed(self, array, idx1, value):
        """Zapise 'value' na 1-based index 'idx1' do 'array'. Pokud je index
        za soucasnou delkou pole, pole se automaticky dopadne None - hlavicky
        SUBRO typu 'out:PO(2)' jsou v realnych GL3 programech casto jen
        orientacni/zastarale (viz HLO.GL3: PI(2)/PO(2), ale skutecne se
        pouzivaji desitky bodu), takze davat tvrdou chybu na 'prilis male
        pole' by bylo v rozporu s tim, jak se puvodni jazyk skutecne
        pouzival."""
        if idx1 < 1:
            raise IndexError("index musi byt >= 1 (dostal %d)" % (idx1,))
        if idx1 > len(array):
            array.extend([None] * (idx1 - len(array)))
        array[idx1 - 1] = value

    def eval_cond(self, cond, env):
        if isinstance(cond, IsUndefined):
            return self.eval_expr(cond.expr, env) is None
        left = self.eval_expr(cond.left, env)
        right = self.eval_expr(cond.right, env)
        fn = _REL_FUNCS.get(cond.rel)
        if fn is None:
            raise ValueError("Neznama relace %r" % cond.rel)
        return fn(left, right)

    # ------------------------------------------------------------------
    # provadeni statementu
    # ------------------------------------------------------------------

    def _exec_block(self, stmts, env):
        for stmt in stmts:
            self._exec_stmt(stmt, env)

    def _exec_stmt(self, stmt, env):
        if isinstance(stmt, Assign):
            value = self.eval_expr(stmt.value, env)
            if stmt.target_index is None:
                env[stmt.target] = value
            else:
                idx = int(round(self.eval_expr(stmt.target_index, env)))
                if stmt.target not in env:
                    raise NameError(
                        "Pole '%s' nebylo deklarovano (DIMEN) pred zapisem"
                        % stmt.target
                    )
                self._set_indexed(env[stmt.target], idx, value)
            return

        if isinstance(stmt, DimenStmt):
            for name, size in stmt.entries:
                env[name] = [None] * size
            return

        if isinstance(stmt, DataStmt):
            env[stmt.array_name] = list(stmt.values)
            return

        if isinstance(stmt, CommandStmt):
            self._exec_command(stmt, env)
            return

        if isinstance(stmt, IODevStmt):
            self._exec_idev(stmt, env)
            return

        if isinstance(stmt, InputStmt):
            self._exec_input(stmt, env)
            return

        if isinstance(stmt, OutputStmt):
            self._exec_output(stmt, env)
            return

        if isinstance(stmt, CallStmt):
            self._exec_call(stmt, env)
            return

        if isinstance(stmt, DoLoop):
            start = int(round(self.eval_expr(stmt.start, env)))
            end = int(round(self.eval_expr(stmt.end, env)))
            i = start
            while i <= end:
                env[stmt.var] = i
                self._exec_block(stmt.body, env)
                # Cetba aktualni hodnoty citace AZ PO tele - podporuje bezny
                # idiom starych GL3 programu, kdy se citac uvnitr tela
                # nastavi rovnou na koncovou hodnotu, aby se smycka po
                # tomto pruchodu ukoncila drive (viz TEHLO.gl3: I=100).
                i = int(round(self.eval_expr(Var(stmt.var, None), env))) + 1
            return

        if isinstance(stmt, IfBlock):
            if self.eval_cond(stmt.cond, env):
                self._exec_block(stmt.body, env)
            return

        if isinstance(stmt, IfShort):
            if self.eval_cond(stmt.cond, env):
                self._exec_stmt(stmt.stmt, env)
            return

        if isinstance(stmt, RepeatWhile):
            # preklad "navesti + zpetny skok, dokud plati cond"
            while True:
                self._exec_block(stmt.body, env)
                if not self.eval_cond(stmt.cond, env):
                    break
            return

        if isinstance(stmt, RetSub):
            raise RetSubSignal()

        raise TypeError("Neznamy typ statementu: %r" % (stmt,))

    def _exec_command(self, stmt, env):
        if stmt.name == "SCALE":
            # SCALE,pg1,pg2,vr,vi - meritkova transformace 'vi' objektu
            # (SCALEX.FOR): pg1/pg2 jsou "adresy prvniho prvku pole" stejne
            # jako u E01 (Fortran konvence 'P(1),N'), vr je meritko, vi
            # pocet transformovanych objektu.
            target_node, source_node, factor_node, count_node = stmt.args
            if not isinstance(target_node, Var):
                raise SyntaxError(
                    "SCALE ocekava jako 1. argument jmeno pole/promenne (pripadne indexovane)"
                )
            if not isinstance(source_node, Var):
                raise SyntaxError(
                    "SCALE ocekava jako 2. argument jmeno pole/promenne (pripadne indexovane)"
                )

            source_ref = self._eval_array_ref(source_node, env)
            factor = self.eval_expr(factor_node, env)
            count = int(round(self.eval_expr(count_node, env)))

            fn = self.commands.get("SCALE")
            if fn is None:
                raise KeyError("Prikaz 'SCALE' neni v registru COMMANDS")

            target_start = (
                0 if target_node.index is None
                else int(round(self.eval_expr(target_node.index, env))) - 1
            )
            if target_node.name not in env:
                raise NameError(
                    "Pole '%s' nebylo deklarovano (DIMEN) pred zapisem" % target_node.name
                )
            target_array = env[target_node.name]
            if not isinstance(target_array, list):
                raise TypeError("SCALE: cil '%s' neni pole" % target_node.name)

            for k in range(count):
                if k >= len(source_ref) or source_ref[k] is None:
                    raise ValueError("SCALE: zdrojovy prvek c. %d neni definovan" % (k + 1))
                result = fn(self, source_ref[k], factor)
                self._set_indexed(target_array, target_start + k + 1, result)
            return

        if stmt.name == "DCOOS3":
            self._exec_dcoos3(stmt, env)
            return

        if stmt.name == "TRA23":
            self._exec_tra23(stmt, env)
            return

        raise KeyError("Neznamy prikaz '%s'" % stmt.name)

    def _exec_dcoos3(self, stmt, env):
        """DCOOS3,vi,vg1,vg2,vg3 - definice prostorove souradnicove
        soustavy c. vi (1..10), viz gerlib.dcoos3.define_coord_system3()
        pro vyznam vg1(pocatek)/vg2(smer x')/vg3(napoveda pro y')."""
        if len(stmt.args) != 4:
            raise SyntaxError(
                "DCOOS3 ocekava presne 4 argumenty (vi,vg1,vg2,vg3), dostal %d"
                % len(stmt.args)
            )
        vi_node, vg1_node, vg2_node, vg3_node = stmt.args

        vi = int(round(self.eval_expr(vi_node, env)))
        if not (1 <= vi <= 10):
            raise ValueError(
                "DCOOS3: cislo souradnicove soustavy musi byt v rozsahu "
                "1..10, je %d" % vi
            )

        origin = self.eval_expr(vg1_node, env)
        x_ref = self.eval_expr(vg2_node, env)
        y_ref = self.eval_expr(vg3_node, env)

        self.coordinate_systems[vi] = define_coord_system3(origin, x_ref, y_ref)

    def _exec_tra23(self, stmt, env):
        """TRA23,pg1,pg2,vi1,vi2 - transformace z roviny do prostoru pomoci
        souradnicove soustavy vi2 (definovane driv prikazem DCOOS3).

        Rozliseni pole (P(1),N -> Q(1), Fortran konvence jako SCALE/E01)
        vs. jednotlivy objekt (cela Spline S -> T, vi1 se v tomhle
        pripade netyka - viz specifikace 'Plati pouze pro pole') se
        dela AZ ZA BEHU podle skutecne hodnoty pg2 (list, nebo ne),
        protoze GL3 jazyk sam typ staticky nerozlisuje."""
        if len(stmt.args) != 4:
            raise SyntaxError(
                "TRA23 ocekava presne 4 argumenty (pg1,pg2,vi1,vi2), dostal %d"
                % len(stmt.args)
            )
        target_node, source_node, count_node, coord_id_node = stmt.args

        if not isinstance(target_node, Var):
            raise SyntaxError(
                "TRA23 ocekava jako 1. argument jmeno pole/promenne (pripadne indexovane)"
            )
        if not isinstance(source_node, Var):
            raise SyntaxError(
                "TRA23 ocekava jako 2. argument jmeno pole/promenne (pripadne indexovane)"
            )

        coord_id = int(round(self.eval_expr(coord_id_node, env)))
        coord_system = self.coordinate_systems.get(coord_id)
        if coord_system is None:
            raise ValueError(
                "TRA23: souradnicova soustava c. %d nebyla definovana "
                "(DCOOS3)" % coord_id
            )

        if source_node.name not in env:
            raise NameError(
                "Promenna '%s' nebyla pred pouzitim nastavena" % (source_node.name,)
            )
        source_value = env[source_node.name]

        if isinstance(source_value, list):
            # Pole (napr. P(1),N -> Q(1)) - stejna smycka jako SCALE.
            count = int(round(self.eval_expr(count_node, env)))
            source_ref = self._eval_array_ref(source_node, env)

            if target_node.name not in env:
                raise NameError(
                    "Pole '%s' nebylo deklarovano (DIMEN) pred zapisem"
                    % (target_node.name,)
                )
            target_array = env[target_node.name]
            if not isinstance(target_array, list):
                raise TypeError("TRA23: cil '%s' neni pole" % (target_node.name,))

            target_start = (
                0 if target_node.index is None
                else int(round(self.eval_expr(target_node.index, env))) - 1
            )
            for k in range(count):
                if k >= len(source_ref) or source_ref[k] is None:
                    raise ValueError("TRA23: zdrojovy prvek c. %d neni definovan" % (k + 1))
                result = transform3(source_ref[k], coord_system)
                self._set_indexed(target_array, target_start + k + 1, result)
            return

        # Jednotlivy objekt (napr. cela Spline S -> T) - vi1 (count) se
        # netyka, viz specifikace "Plati pouze pro pole".
        if source_value is None:
            raise ValueError(
                "TRA23: zdrojova promenna '%s' neni definovana" % (source_node.name,)
            )
        result = transform3(source_value, coord_system)
        if target_node.index is None:
            env[target_node.name] = result
        else:
            if target_node.name not in env:
                raise NameError(
                    "Pole '%s' nebylo deklarovano (DIMEN) pred zapisem"
                    % (target_node.name,)
                )
            idx = int(round(self.eval_expr(target_node.index, env)))
            self._set_indexed(env[target_node.name], idx, result)

    def _exec_call(self, stmt, env):
        if stmt.name not in self.registry:
            raise KeyError(
                "CALL na '%s' - tento podprogram jeste neni v registru "
                "(dodej jeho .GL3 zdroj a pridej do registry pred spustenim)"
                % stmt.name
            )

        callee = self.registry[stmt.name]
        directions = get_param_directions(callee)
        callee_params = callee.params

        local_env = builtin_constants()
        for i, (formal_name, dim, _dir) in enumerate(callee_params):
            if i >= len(stmt.args):
                continue
            if directions.get(formal_name) == "out":
                # 'out' pole se alokuje rovnou podle velikosti deklarovane
                # v hlavicce (napr. out:PO(2)) - telo podprogramu ho pak
                # nemusi znovu deklarovat vlastnim DIMEN.
                if dim is not None:
                    local_env[formal_name] = [None] * dim
                continue
            actual_text = stmt.args[i]
            value = self._resolve_actual(actual_text, env)
            if isinstance(value, list):
                value = list(value)  # kopie pole - zadne sdileni pameti s volajicim
            local_env[formal_name] = value

        try:
            self._exec_block(callee.body, local_env)
        except RetSubSignal:
            pass

        for i, (formal_name, _dim, _dir) in enumerate(callee_params):
            if i >= len(stmt.args):
                continue
            actual_text = stmt.args[i]
            if directions.get(formal_name) == "out":
                if _is_identifier(actual_text):
                    env[actual_text] = local_env.get(formal_name)
                # jinak (literal na miste vystupu) - neni kam zapsat, ignoruj

    # ------------------------------------------------------------------
    # IDEV + GET/READ - vstup ze souboru
    # ------------------------------------------------------------------

    def _exec_idev(self, stmt, env):
        filename = self.eval_expr(stmt.filename, env)
        if not isinstance(filename, str):
            raise TypeError(
                "IDEV ocekava jmeno souboru jako retezec (napr. 'A'), "
                "dostal: %r" % (filename,)
            )
        channel = (
            int(round(self.eval_expr(stmt.channel, env)))
            if stmt.channel is not None else 0
        )
        if channel not in (0, 1, 2):
            raise ValueError("IDEV: kanal musi byt 0, 1 nebo 2 (dostal %r)" % (channel,))

        old = self.io_channels.get(channel)
        if old is not None:
            try:
                old["file"].close()
            except Exception:
                pass

        path = filename
        if not os.path.isabs(path) and os.sep not in path:
            path = os.path.join(self.io_base_dir, path)
        try:
            f = open(path, "r", encoding="utf-8")
        except OSError as e:
            raise OSError("IDEV: nepodarilo se otevrit soubor '%s' (kanal %d): %s" % (path, channel, e))
        self.io_channels[channel] = {"file": f, "path": path}

    def _next_raw_line(self, channel):
        """Vrati dalsi neprazdny radek z kanalu (jako text, komentar '< ...'
        orezan - stejna konvence jako ve zdrojovem kodu, viz E374.TXT),
        nebo None pri konci souboru (misto vyjimky - umoznuje test IFN)."""
        if channel == "T":
            raise NotYetImplemented(
                "Cteni z terminalu (GETT/READT) neni v davkovem interpretru "
                "podporovano - pouzij IDEV a kanal 0/1/2."
            )
        state = self.io_channels.get(channel)
        if state is None:
            raise ValueError(
                "Kanal %d neni otevren - chybi IDEV pred ctenim z tohoto "
                "kanalu (cteni z terminalu neni v davkovem interpretru "
                "podporovano)" % (channel,)
            )
        f = state["file"]
        while True:
            line = f.readline()
            if line == "":
                return None
            line = line.split("<", 1)[0].strip()
            if line == "":
                continue
            return line

    def _next_record(self, channel):
        """Vrati dalsi zaznam jako list textovych tokenu (cisla oddelena
        carkou/mezerou/tabulatorem), nebo None na konci souboru."""
        line = self._next_raw_line(channel)
        if line is None:
            return None
        return re.split(r"[,\s]+", line)

    def _component_count(self, name):
        """Kolik cisel v zaznamu zabira jeden cil daneho jmena. Zatim jen
        skalary (1 cislo) a 2D body prefixu P (2 cisla: X, Y) - ostatni
        slozene typy pri cteni jeste nejsou podporovany."""
        kind, _ = classify(name)
        if kind == "scalar":
            return 1
        if kind == "string":
            raise NotYetImplemented(
                "Cteni textove promenne '%s' prikazem GET neni podporovano "
                "- pouzij READ (cte cely radek jako text)." % (name,)
            )
        prefix = name[0].upper()
        if prefix == "P":
            return 2
        raise NotYetImplemented(
            "Cteni typu '%s' (promenna %s) zatim v GET/READ neni podporovano "
            "- zatim jen skalary (D/K/I) a 2D body (P)." % (prefix, name)
        )

    def _make_value(self, name, tokens):
        kind, fc_type = classify(name)
        if kind == "scalar":
            raw = float(tokens[0])
            if fc_type == "App::PropertyInteger":
                return int(round(raw))
            return raw
        prefix = name[0].upper()
        if prefix == "P":
            return Point(float(tokens[0]), float(tokens[1]))
        raise NotYetImplemented("Cteni typu '%s' neni podporovano" % (prefix,))

    def _assign_target(self, target, value, env):
        if target.index is None:
            env[target.name] = value
            return
        idx = int(round(self.eval_expr(target.index, env)))
        if target.name not in env:
            raise NameError(
                "Pole '%s' nebylo deklarovano (DIMEN) pred zapisem" % (target.name,)
            )
        self._set_indexed(env[target.name], idx, value)

    def _exec_input(self, stmt, env):
        channel = _CHANNEL_BY_COMMAND[stmt.command]
        is_get = stmt.command.startswith("GET")

        if is_get:
            # GET: presne jeden zaznam, rozdeleny mezi vsechny cile podle
            # souctu poctu jejich slozek. Na konci souboru -> vsem cilum None.
            needed = sum(self._component_count(t.name) for t in stmt.targets)
            tokens = self._next_record(channel)
            if tokens is None:
                for t in stmt.targets:
                    self._assign_target(t, None, env)
                return
            if len(tokens) < needed:
                raise ValueError(
                    "%s: zaznam obsahuje %d cislo/cisla, ale je potreba %d"
                    % (stmt.command, len(tokens), needed)
                )
            pos = 0
            for t in stmt.targets:
                n = self._component_count(t.name)
                value = self._make_value(t.name, tokens[pos:pos + n])
                pos += n
                self._assign_target(t, value, env)
        else:
            # READ: kazdy cil ze sveho vlastniho (noveho) zaznamu; pripadna
            # nadbytecna cisla v zaznamu se ignoruji. Textove promenne (B)
            # cetou cely radek jako text. Na konci souboru -> cili None.
            for t in stmt.targets:
                kind, _ = classify(t.name)
                if kind == "string":
                    line = self._next_raw_line(channel)
                    self._assign_target(t, line, env)
                    continue
                n = self._component_count(t.name)
                tokens = self._next_record(channel)
                if tokens is None:
                    self._assign_target(t, None, env)
                    continue
                if len(tokens) < n:
                    raise ValueError(
                        "%s,%s: zaznam obsahuje %d cislo/cisla, ale je "
                        "potreba %d" % (stmt.command, t.name, len(tokens), n)
                    )
                value = self._make_value(t.name, tokens[:n])
                self._assign_target(t, value, env)

    # ------------------------------------------------------------------
    # PRINT/WRITE (vystup na konzoli - ODEV/ODEVB jeste neni implementovano,
    # takze se stejne jako v originale bez nastaveneho vystupniho zarizeni
    # vypisuje na terminal)
    # ------------------------------------------------------------------

    def _print_one(self, name, idx, value):
        label = "%s(%d)" % (name, idx)
        _kind, fc_type = classify(name)
        if isinstance(value, Point):
            text = "%-10s%12.3f%12.3f" % (label, value.x, value.y)
        elif fc_type == "App::PropertyInteger":
            text = "%-10s%12d" % (label, int(round(value)))
        else:
            text = "%-10s%12.3f" % (label, float(value))
        print(text)

    def _exec_output(self, stmt, env):
        is_write = stmt.command.startswith("WRITE")

        for t in stmt.targets:
            name = t.name

            if name.endswith("@"):
                raise NotYetImplemented(
                    "'%s' (vsechny definovane objekty daneho typu) jeste "
                    "neni v %s podporovano." % (name, stmt.command)
                )

            if name not in env:
                if is_write:
                    continue
                raise NameError("Prikaz %s: objekt '%s' neni definovan" % (stmt.command, name))
            raw = env[name]

            if t.index is not None:
                idx = int(round(self.eval_expr(t.index, env)))
                if not isinstance(raw, list):
                    raise TypeError("'%s' neni pole, nelze indexovat" % (name,))
                value = raw[idx - 1] if 0 <= idx - 1 < len(raw) else None
                if value is None:
                    if is_write:
                        continue
                    raise ValueError("Prikaz %s: '%s(%d)' neni definovan" % (stmt.command, name, idx))
                self._print_one(name, idx, value)
                continue

            if isinstance(raw, list):
                if is_write:
                    for i, value in enumerate(raw):
                        if value is not None:
                            self._print_one(name, i + 1, value)
                else:
                    value = raw[0] if raw else None
                    if value is None:
                        raise ValueError("Prikaz %s: '%s(1)' neni definovan" % (stmt.command, name))
                    self._print_one(name, 1, value)
            else:
                if raw is None:
                    if is_write:
                        continue
                    raise ValueError("Prikaz %s: '%s' neni definovan" % (stmt.command, name))
                self._print_one(name, 1, raw)

    def _resolve_actual(self, actual_text, env):
        actual_text = actual_text.strip()
        if _is_identifier(actual_text) and actual_text in env:
            return env[actual_text]
        # literal nebo slozitejsi vyraz (napr. konstanta '1000.')
        return self.eval_expr(parse_expr_text(actual_text), env)
