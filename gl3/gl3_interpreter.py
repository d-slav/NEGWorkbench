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
import sys
import re

try:
    import FreeCAD as App
except ImportError:  # offline beh (testy, CLI) - beze zmeny, prosty text
    App = None

from gl3_lang import (
    Var, Num, Str, BinOp, UnaryMinus, OpCall,
    Assign, CallStmt, CommandStmt, DimenStmt, DataStmt,
    DoLoop, IfBlock, IfShort, RepeatWhile, RetSub,
    BreakStmt, ContinueStmt,
    IODevStmt, IOTarget, InputStmt, OutputStmt, TypeStmt, IsUndefined, IsDefined,
    CreStmt, EndCreStmt, MoveStmt, Omitted, OMITTED,
    IniStmt, CloseStmt,
    parse_expr_text,
)
from gl3_ops import (
    OPERATIONS, COMMANDS, Point, Vector, Line, Circle, Plane, Curve, classify,
    NotYetImplemented, NoSolution, ARRAY_REF_OPS, DATA_CONSTANTS_PER_OBJECT,
    builtin_constants, format_components,
)
from geplib import define_coord_system3, transform3
from gl3_analysis import get_param_directions, _is_identifier
import gerlib.accur as _gerlib_accur
import gl3_placeholders
from gerlib import (
    make_chain as _gerlib_make_chain,
    make_chain_with_gaps as _gerlib_make_chain_with_gaps,
)
from gerlib.move_geom import (
    evaluate_move_phrase as _gerlib_evaluate_move_phrase,
    MovePhraseError, MovePhraseNotYetImplemented,
)


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


class BreakSignal(Exception):
    """Rizeni behu (rozsireni nad ramec puvodniho GL-3) - predcasne
    ukonceni nejblizsiho obepinajiciho cyklu (BREAK). Zachyti se primo
    v obsluze DoLoop/RepeatWhile - pokud unikne az na uroven podprogramu,
    znamena to pouziti BREAK mimo cyklus."""
    pass


class ContinueSignal(Exception):
    """Rizeni behu (rozsireni nad ramec puvodniho GL-3) - preskok na
    dalsi iteraci nejblizsiho obepinajiciho cyklu (CONTINUE). Zachyti se
    primo v obsluze DoLoop/RepeatWhile."""
    pass


class GL3RuntimeError(Exception):
    """Kategorie 2 - chyba v GL3 programu (ne bug v Pythonu, ne kategorie
    3 varovani). Napr. neexistujici promenna, neznamy opcode, promenna
    v undefined stavu pouzita ve vypoctu. Zprava uz obsahuje kompletni
    kontext ('[Error] program/radek/operace: text') sestaveny IHNED pri
    vyhozeni - behem odvijeni vyjimky by uz self._program_name_stack/
    current_line_no mohly ukazovat jinam (viz _exec_call - finally: pop
    probehne pri odvijeni driv, nez se vyjimka dostane nahoru)."""
    pass


_REL_FUNCS = {
    "GT": lambda a, b: a > b,
    "LT": lambda a, b: a < b,
    "GE": lambda a, b: a >= b,
    "LE": lambda a, b: a <= b,
    "EQ": lambda a, b: a == b,
    "NE": lambda a, b: a != b,
}


def _build_data_object(prefix, chunk):
    """Sestavi jeden objekt prikazu DATA z 'chunk' (seznam konstant, jiz
    vyhodnocenych na cisla/retezce) podle typu urceneho 'prefix' (prvni
    pismeno jmena cile) - viz gl3_ops.DATA_CONSTANTS_PER_OBJECT pro
    pocet konstant na typ a G06.md pro presny vyznam/poradi kazde
    slozky (autoritativni zdroj, DATA jen doslovne prevadi cisla na
    pole objektu - zadna geometricka odvozovaci logika, ta uz je hotova
    v prislusnych opcodech).

    Podporovany jsou vsechny "jednoduche" (pevny pocet slozek) objekty:
    A/D (skalar), I/J/K (celociselny skalar), B (text), P/V/C/L (2D),
    Q/U/R/M/G (3D). "Slozene" objekty (S/E/T/H - retezec/krivka
    promenne delky, F - plocha) DATA vyslovne NEPODPORUJE - to neni
    mezera/"zatim neimplementovano", G06.md je oznacuje jako jiny druh
    objektu (data promenne delky "ve vnejsi pameti"), pro ktery jsou
    DATA/READ/GET/PRINT/WRITE/TYPE v originale vyslovne nedefinovane -
    ty se sestavuji pres CRE/MOVE nebo prislusne opcody (E01/S01/...)."""
    if prefix in ("D", "A"):
        return float(chunk[0])
    if prefix in ("I", "J", "K"):
        return int(round(chunk[0]))
    if prefix == "B":
        return str(chunk[0])
    if prefix == "P":
        return Point(chunk[0], chunk[1], 0.0)
    if prefix == "V":
        return Vector(chunk[0], chunk[1], 0.0)
    if prefix == "C":
        return Circle(Point(chunk[0], chunk[1], 0.0), chunk[2])
    if prefix == "L":
        return Line(Point(chunk[0], chunk[1], 0.0), Vector(chunk[2], chunk[3], 0.0))
    if prefix == "Q":
        return Point(chunk[0], chunk[1], chunk[2])
    if prefix == "U":
        return Vector(chunk[0], chunk[1], chunk[2])
    if prefix == "R":
        # {ux,uy,uz,d} podle G06.md - d je vzdalenost roviny od pocatku
        # PODEL normaly (ne bod na rovine primo) - gerlib.types.Plane
        # ale uklada origin (bod), takze se dopocita jako d*normala
        # (viz i format_components() - opacny smer stejneho vztahu).
        ux, uy, uz, d = chunk[0], chunk[1], chunk[2], chunk[3]
        return Plane(Point(d * ux, d * uy, d * uz), Vector(ux, uy, uz))
    if prefix == "M":
        return Line(
            Point(chunk[0], chunk[1], chunk[2]),
            Vector(chunk[3], chunk[4], chunk[5]),
        )
    if prefix == "G":
        return Circle(
            Point(chunk[0], chunk[1], chunk[2]),
            chunk[6],
            Vector(chunk[3], chunk[4], chunk[5]),
        )
    raise NotYetImplemented("DATA: sestaveni objektu typu '%s' neni podporovano" % prefix)


class Interpreter:
    def __init__(self, registry=None, operations=None, commands=None, io_base_dir=".",
                 path_placeholders=None):
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
        path_placeholders - dict {jmeno: retezec nebo None} s hodnotami
                     zastupnych textu ${workbench_path}/${fc_file_path}
                     (viz gl3_placeholders.py) - pro cely beh KONSTANTNI
                     (na rozdil od ${gl3_file_path}, ktery se dopocitava
                     dynamicky podle prave bezici SUBRO, viz
                     _source_path_stack/run()/_exec_call). Typicky je
                     dodava GL3Program.execute() (workbench_path =
                     adresar doplnku, fc_file_path = adresar otevreneho
                     FreeCAD dokumentu) - bez FreeCADu (napr. v testech)
                     zustavaji nedostupne (pouziti vyhodi jasnou chybu,
                     ne tichou spatnou hodnotu).
        """
        self.registry = registry or {}
        self.operations = operations if operations is not None else OPERATIONS
        self.commands = commands if commands is not None else COMMANDS
        self.io_base_dir = io_base_dir
        self._static_placeholders = dict(path_placeholders or {})
        self.io_channels = {}  # {0/1/2: {"file": fh, "path": str}} - nastaveno IDEV
        self._directions_cache = {}
        # Souradnicove soustavy definovane DCOOS3 (viz gerlib.dcoos3) -
        # {1..10: CoordSystem3}. Sdilene pres cely beh (vc. vnorenych CALL -
        # jeden Interpreter = jeden beh hlavniho SUBRO), ale IZOLOVANE per
        # beh - novy Interpreter() (= novy GL3Program.execute()) zacina
        # vzdy s prazdnou sadou.
        self.coordinate_systems = {}
        # Jmena 'in:' vstupnich parametru pro kazdy aktivni env (id(env) ->
        # set jmen) - pouzito jen k tomu, aby DIMEN nemohl tise prepsat
        # jiz svazany vstupni parametr (typicky composite in:P(N)) na
        # prazdne pole. Klicovano podle id(env), aby to spravne fungovalo
        # i pres vnorene CALL (kazdy ma svuj vlastni lokalni env) - viz
        # _exec_call.
        self._input_names_by_env = {}
        # ACCUR (presnost pro E45/H45/H96) - izolovana na tento beh:
        # kazdy novy Interpreter zacina na vychozich 0.01, predchozi
        # beh/test ji nemuze ovlivnit (viz gerlib.accur).
        _gerlib_accur.reset_accuracy()
        # Varovani (kategorie 3 - NoSolution, viz gerlib.errors) -
        # izolovano per beh, presne jako ACCUR. MESS/NOMESS prepina.
        self.disp_warning = True
        # Rezim kresleni (ABSOL/INCRE, viz G17.md 17.6.1) - globalni pro
        # cely beh (vc. vnorenych CALL), izolovano per beh jako ACCUR.
        # Ovlivnuje jen fraze MOVE s "promenlivym rezimem" (D#A, D1:D2) -
        # viz gerlib.move_geom.
        self.draw_mode = "ABSOL"
        # Rozpracovany blok CRE...ENDCRE (viz G10.md "VYTVARENI RETEZCU
        # POMOCI KRESLICICH PRIKAZU") - None mimo blok. Vnorene bloky
        # CRE zatim nejsou podporovany (viz _exec_cre).
        self._chain_builder = None
        # Kolik bloku INI...CLOSE je prave otevrenych KDEKOLIV v
        # zasobniku volani (viz _hidden_chain_stack nize) - pouzito jen
        # pro rychlou vzajemnou kontrolu s CRE (nesmi bezet soucasne,
        # viz G10.md "CRE, ENDCRE uvnitr otevrene kresby... neni
        # pripustne").
        self._open_ini_count = 0
        # Zasobnik "skrytych retezcu" - jeden zaznam na kazde aktivni
        # volani SUBRO (vc. hlavniho programu), viz zadani uzivatele:
        # kazdy GL3 program ma skryty retezec, ktery vznika bloky
        # INI...CLOSE (stejnou MOVE frazovou logikou jako CRE...ENDCRE,
        # viz _active_move_builder). Pri navratu z CALL se hotovy
        # skryty retezec volane SUBRO pripoji (konkatenuje) do
        # skryteho retezce volajiciho - viz _push_hidden_chain_frame/
        # _pop_hidden_chain_frame.
        #   frame = {"points": [...], "ini_builder": None nebo
        #            {"points": [...], "current_point": ..., "last_direction": ...}}
        self._hidden_chain_stack = []
        # Vysledny skryty retezec CELEHO behu (Curve, nebo None, nebylo-
        # li nikdy nic nakresleno) - viz run(). K dispozici az PO
        # run() dobehne.
        self.hidden_chain = None
        # Zasobnik jmen aktualne bezicich SUBRO (kvuli vnorenym CALL) -
        # pro hlaseni "[Warning] jmeno_programu/cislo_radku/operace: ...".
        self._program_name_stack = []
        # Zasobnik cest k .GL3 souborum aktualne bezicich SUBRO (soubezne
        # s _program_name_stack, stejny zivotni cyklus - viz run()/
        # _exec_call) - vrchol udava adresar pro zastupny text
        # ${gl3_file_path} (viz gl3_placeholders.py a _resolve_path()
        # nize). Prvek muze byt None (SUBRO bez zname puvodni cesty -
        # napr. testy volajici run()/registry primo bez nastaveni
        # SubroutineDef.source_path) - pak pouziti ${gl3_file_path}
        # vyhodi jasnou chybu, ne tichou spatnou hodnotu.
        self._source_path_stack = []
        # Cislo radku prave provadeneho statementu (pro totez hlaseni) -
        # nastavuje se v _exec_stmt pred vyhodnocenim, cte se pri
        # zachyceni NoSolution v eval_expr.
        self.current_line_no = None

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

        Po dobehnuti je vysledny "skryty retezec" (viz zadani uzivatele
        - INI...CLOSE, sbira i skryte retezce vsech vnorenych CALL) k
        dispozici v self.hidden_chain (Curve, nebo None, nebylo-li nic
        nakresleno).
        """
        env = builtin_constants()
        env.update(inputs)
        self._input_names_by_env[id(env)] = set(inputs.keys())
        self.io_channels = {}
        self._program_name_stack.append(subdef.name)
        self._source_path_stack.append(getattr(subdef, "source_path", None))
        self._push_hidden_chain_frame()
        try:
            self._exec_block(subdef.body, env)
        except RetSubSignal:
            pass
        except (BreakSignal, ContinueSignal) as exc:
            kw = "BREAK" if isinstance(exc, BreakSignal) else "CONTINUE"
            raise GL3RuntimeError(
                "%s pouzit mimo cyklus (DO/FOR nebo REPEATWHILE)" % (kw,)
            )
        finally:
            self._program_name_stack.pop()
            self._source_path_stack.pop()
            had_error = sys.exc_info()[0] is not None
            top_level_points = self._pop_hidden_chain_frame(
                parent_frame=None, suppress_dangling_check=had_error
            )
            self.hidden_chain = (
                _gerlib_make_chain_with_gaps(top_level_points) if top_level_points else None
            )
            for state in self.io_channels.values():
                try:
                    state["file"].close()
                except Exception:
                    pass
        return env

    # ------------------------------------------------------------------
    # "skryty retezec" (INI...CLOSE) - viz zadani uzivatele
    # ------------------------------------------------------------------

    def _push_hidden_chain_frame(self):
        """Otevre novy zaznam skryteho retezce pro prave zacinajici
        volani SUBRO (hlavni program i kazdy vnoreny CALL) - viz
        _hidden_chain_stack.

        'starts_with_gap' - True, pokud UPLNE PRVNI nakreslena cast
        teto SUBRO (prvni INI...CLOSE blok) zacala pohybem se zdviženym
        perem (/) - viz _exec_close. Pouziva se pri navratu z CALL
        (_pop_hidden_chain_frame) k rozhodnuti, jestli se spojeni s uz
        nakreslenou casti volajiciho ma kreslit jako viditelna usecka
        (default, zakladajici pohyb '*'), nebo jako mezera/nespojitost
        (zakladajici pohyb '/') - viz zadani uzivatele: 'kdyz SUBRO
        zacina lomítkem, tak prvni pohyb k nemu bude neviditelny'."""
        self._hidden_chain_stack.append(
            {"points": [], "ini_builder": None, "starts_with_gap": False}
        )

    def _pop_hidden_chain_frame(self, parent_frame, suppress_dangling_check=False):
        """Uzavre zaznam skryteho retezce prave koncici SUBRO a vrati
        jeho nasbirane body. 'parent_frame' je zaznam volajiciho (nebo
        None na urovni hlavniho programu) - je-li zadan a tato SUBRO
        neco nakreslila, jeji body se do nej rovnou pripoji (viz zadani
        uzivatele: "skryty retezec [volane SUBRO] bude pripojeny k
        vlastnimu skrytemu retezci [volajiciho]") - pripadne pres
        mezeru (None), zacinala-li tato SUBRO pohybem se zdviženym
        perem (viz frame['starts_with_gap'] / _push_hidden_chain_frame).

        Chyba, byl-li blok INI ponechany otevreny bez CLOSE (obdoba
        existujici kontroly u CRE/ENDCRE) - POKUD 'suppress_dangling_check'
        neni True (nastavuje volajici, kdyz uz stejne probiha jina
        vyjimka - jinak by tato kontrola tu puvodni, dulezitejsi chybu
        nezadouci prekryla)."""
        frame = self._hidden_chain_stack.pop()
        if frame["ini_builder"] is not None and not suppress_dangling_check:
            raise GL3RuntimeError(
                "INI bez odpovidajiciho CLOSE pred koncem SUBRO "
                "(skryty retezec zustal otevreny)"
            )
        points = frame["points"]
        if parent_frame is not None and points:
            if parent_frame["points"] and frame["starts_with_gap"]:
                parent_frame["points"].append(None)
            parent_frame["points"].extend(points)
        return points

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
                self._raise_gl3_error(node.name, "promenna nebyla pred pouzitim nastavena")
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

        if isinstance(node, Omitted):
            # Vynechany volitelny parametr uprostred seznamu argumentu
            # OpCall (napr. DM=D28>E,,P2) - viz gl3_lang.Omitted. Sentinel
            # OMITTED je zamerne odlisny od None (to znamena "predchozi
            # operace nemela reseni", viz nize) - jednotlive opcody v
            # gl3_ops.py rozhoduji, jakou vychozi hodnotu za nej dosadit.
            return OMITTED

        if isinstance(node, OpCall):
            fn = self.operations.get(node.opcode)
            if fn is None:
                self._raise_gl3_error(
                    node.opcode,
                    "neznamy opcode - neni v registru OPERATIONS vubec zavedeny "
                    "(ani jako stub)",
                )
            array_ref_positions = ARRAY_REF_OPS.get(node.opcode, ())
            args = []
            for i, a in enumerate(node.args):
                if i in array_ref_positions:
                    args.append(self._eval_array_ref(a, env))
                else:
                    args.append(self.eval_expr(a, env))
            for i, v in enumerate(args):
                if i not in array_ref_positions and v is None:
                    self._raise_gl3_error(
                        node.opcode,
                        "%d. argument je undefined (predchozi operace nemela "
                        "reseni) - nelze s nim dale pocitat" % (i + 1),
                    )
            try:
                return fn(*args)
            except NoSolution as exc:
                self._report_warning(node.opcode, str(exc))
                return None

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
                if node.index is not None:
                    raise TypeError(
                        "'%s' se pouziva jako pole bodu (P(1),N) s indexem, ale "
                        "neni to pole" % (node.name,)
                    )
                # Fortranovska konvence: i "obycejnou" (nepolovou) promennou
                # lze adresovat jako pole o jednom prvku (scalar-as-array-of-1)
                # - typicky SCALE volany na jediny objekt (ne pole), napr.
                # "SCALE,S,SP,1000/DH,1" kde SP je jeden Spline.
                return [value]
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
        if isinstance(cond, IsDefined):
            return self.eval_expr(cond.expr, env) is not None
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
        line_no = getattr(stmt, "line_no", None)
        if line_no is not None:
            self.current_line_no = line_no

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
            input_names = self._input_names_by_env.get(id(env), ())
            for name, size in stmt.entries:
                if name in input_names:
                    raise ValueError(
                        "DIMEN,%s(...): '%s' uz je vstupni parametr (in:) "
                        "teto subrutiny - DIMEN by tise prepsal jeho "
                        "hodnotu na prazdne pole. Vstupni composite pole "
                        "(napr. in:P(N)) netreba znovu deklarovat pres "
                        "DIMEN, je uz k dispozici primo." % (name, name)
                    )
                env[name] = [None] * size
            return

        if isinstance(stmt, DataStmt):
            self._exec_data(stmt, env)
            return

        if isinstance(stmt, CommandStmt):
            self._exec_command(stmt, env)
            return

        if isinstance(stmt, CreStmt):
            self._exec_cre(stmt, env)
            return

        if isinstance(stmt, EndCreStmt):
            self._exec_endcre(stmt, env)
            return

        if isinstance(stmt, MoveStmt):
            self._exec_move(stmt, env)
            return

        if isinstance(stmt, IniStmt):
            self._exec_ini(stmt, env)
            return

        if isinstance(stmt, CloseStmt):
            self._exec_close(stmt, env)
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

        if isinstance(stmt, TypeStmt):
            self._exec_type(stmt, env)
            return

        if isinstance(stmt, CallStmt):
            self._exec_call(stmt, env)
            return

        if isinstance(stmt, DoLoop):
            start = int(round(self.eval_expr(stmt.start, env)))
            end = int(round(self.eval_expr(stmt.end, env)))
            step = int(round(self.eval_expr(stmt.step, env))) if stmt.step is not None else 1
            if step == 0:
                raise GL3RuntimeError(
                    "DO/FOR: krok (vi3) nesmi byt 0 (promenna %r)" % (stmt.var,)
                )
            i = start
            while (i <= end) if step > 0 else (i >= end):
                env[stmt.var] = i
                try:
                    self._exec_block(stmt.body, env)
                except ContinueSignal:
                    pass
                except BreakSignal:
                    break
                # Cetba aktualni hodnoty citace AZ PO tele - podporuje bezny
                # idiom starych GL3 programu, kdy se citac uvnitr tela
                # nastavi rovnou na koncovou hodnotu, aby se smycka po
                # tomto pruchodu ukoncila drive (viz TEHLO.gl3: I=100).
                i = int(round(self.eval_expr(Var(stmt.var, None), env))) + step
            return

        if isinstance(stmt, IfBlock):
            if self.eval_cond(stmt.cond, env):
                self._exec_block(stmt.body, env)
            elif stmt.else_body is not None:
                self._exec_block(stmt.else_body, env)
            return

        if isinstance(stmt, IfShort):
            if self.eval_cond(stmt.cond, env):
                self._exec_stmt(stmt.stmt, env)
            return

        if isinstance(stmt, RepeatWhile):
            # preklad "navesti + zpetny skok, dokud plati cond"
            while True:
                try:
                    self._exec_block(stmt.body, env)
                except ContinueSignal:
                    pass
                except BreakSignal:
                    break
                if not self.eval_cond(stmt.cond, env):
                    break
            return

        if isinstance(stmt, BreakStmt):
            raise BreakSignal()

        if isinstance(stmt, ContinueStmt):
            raise ContinueSignal()

        if isinstance(stmt, RetSub):
            raise RetSubSignal()

        raise TypeError("Neznamy typ statementu: %r" % (stmt,))

    def _format_report(self, kind, operation, message):
        """Sestavi hlasku '[Warning|Error] jmeno_programu/cislo_radku/
        operace: text' - viz konverzace o rozdeleni chyb do kategorii."""
        program = self._program_name_stack[-1] if self._program_name_stack else "?"
        line = self.current_line_no if self.current_line_no is not None else "?"
        op = operation if operation else "-"
        return "[%s] %s/%s/%s: %s" % (kind, program, line, op, message)

    def _report_warning(self, operation, message):
        """Kategorie 3 (viz gerlib.errors.NoSolution) - vypis (pokud
        disp_warning) a beh programu pokracuje dal beze zmeny."""
        if not self.disp_warning:
            return
        text = self._format_report("Warning", operation, message)
        if App is not None:
            App.Console.PrintWarning(text + "\n")
        else:
            print(text)

    def _raise_gl3_error(self, operation, message):
        """Kategorie 2 (chyba v GL3 programu) - vzdy tvrde zastavi beh."""
        raise GL3RuntimeError(self._format_report("Error", operation, message))

    def _exec_data(self, stmt, env):
        """DATA,p,vi - viz manual (dodano v konverzaci) + G06.md. 'p'
        urcuje prvek pole/mnoziny (jiz drive deklarovane pres DIMEN),
        pocinaje kterym se prirazuji objekty; typ objektu se odvodi z
        prefixu jmena 'p' (viz gl3_ops.classify/DATA_CONSTANTS_PER_OBJECT).
        Podporovany jsou vsechny "jednoduche" (pevny pocet slozek)
        objekty - skalary (A/D/I/J/K), text (B), 2D (P/V/C/L) i 3D
        (Q/U/R/M/G). "Slozene" objekty promenne delky (S/E/T/H, F) DATA
        nepodporuje vubec - to je spravne portovane omezeni original
        jazyka (viz G06.md a komentar u DATA_CONSTANTS_PER_OBJECT), ne
        mezera k dodelani."""
        count = int(round(self.eval_expr(stmt.count, env)))
        if count < 0:
            raise ValueError("DATA,%s,...: pocet objektu (vi) nesmi byt zaporny" % stmt.target_name)

        prefix = stmt.target_name[0].upper()
        per_object = DATA_CONSTANTS_PER_OBJECT.get(prefix)
        if per_object is None:
            raise NotYetImplemented(
                "DATA,%s: typ s prefixem '%s' neni podporovan - DATA jde "
                "jen pro 'jednoduche' objekty s pevnym poctem slozek "
                "(A,D,I,J,K,B,P,V,C,L,Q,U,R,M,G); retezec/krivka (S,E,T,H) "
                "a plocha (F) maji promennou delku dat a DATA/READ/GET/"
                "PRINT/WRITE/TYPE pro ne nejsou v originale definovane"
                % (stmt.target_name, prefix)
            )

        values = [self.eval_expr(v, env) for v in stmt.values]
        expected = count * per_object
        if len(values) != expected:
            raise ValueError(
                "DATA,%s,%d: ocekavano %d konstant (%d objekt(u) x %d na typ "
                "'%s'), nalezeno %d"
                % (stmt.target_name, count, expected, count, per_object, prefix, len(values))
            )

        if stmt.target_name not in env or not isinstance(env[stmt.target_name], list):
            raise NameError(
                "DATA,%s: pole '%s' nebylo deklarovano (DIMEN) pred pouzitim"
                % (stmt.target_name, stmt.target_name)
            )
        target_array = env[stmt.target_name]

        start_idx = 1
        if stmt.target_index is not None:
            start_idx = int(round(self.eval_expr(stmt.target_index, env)))

        for i in range(count):
            chunk = values[i * per_object:(i + 1) * per_object]
            obj = _build_data_object(prefix, chunk)
            self._set_indexed(target_array, start_idx + i, obj)

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
            target_array = env.get(target_node.name)
            if isinstance(target_array, list):
                for k in range(count):
                    if k >= len(source_ref) or source_ref[k] is None:
                        raise ValueError("SCALE: zdrojovy prvek c. %d neni definovan" % (k + 1))
                    result = fn(self, source_ref[k], factor)
                    self._set_indexed(target_array, target_start + k + 1, result)
                return

            # Cil neni (zatim) pole - Fortranovska konvence dovoluje zapsat
            # i do "obycejne" promenne, pokud jde jen o JEDEN (neindexovany)
            # vysledek, typicky "SCALE,S,SP,1000/DH,1" kde S ma vzniknout
            # jako novy skalar (Spline), ne prvek pole.
            if target_node.index is not None or count != 1:
                raise TypeError(
                    "SCALE: cil '%s' neni pole (DIMEN) - takhle lze zapsat "
                    "jen jeden neindexovany vysledek" % target_node.name
                )
            if not source_ref or source_ref[0] is None:
                raise ValueError("SCALE: zdrojovy prvek c. 1 neni definovan")
            env[target_node.name] = fn(self, source_ref[0], factor)
            return

        if stmt.name == "DCOOS3":
            self._exec_dcoos3(stmt, env)
            return

        if stmt.name == "TRA23":
            self._exec_tra23(stmt, env)
            return

        if stmt.name == "ACCUR":
            # ACCUR[,vr] - nastavi globalni presnost pro E45/H45/H96
            # (viz gerlib.accur). Bez argumentu = reset na vychozich 0.01.
            value = self.eval_expr(stmt.args[0], env) if stmt.args else None
            fn = self.commands.get("ACCUR")
            if fn is None:
                raise KeyError("Prikaz 'ACCUR' neni v registru COMMANDS")
            fn(self, value)
            return

        if stmt.name == "MESS":
            # MESS - zapne vypis varovani (kategorie 3 - NoSolution),
            # vychozi stav. Izolovano per beh (viz __init__).
            self.disp_warning = True
            return

        if stmt.name == "NOMESS":
            # NOMESS - vypne vypis varovani ([Warning] hlasky se
            # potlaci, ale cilova promenna se PRESTO priradi None
            # beze zmeny - jen se to nevypise).
            self.disp_warning = False
            return

        if stmt.name == "ABSOL":
            # ABSOL - absolutni rezim kresleni (viz G17.md 17.6.1),
            # vychozi. Ovlivnuje jen fraze MOVE s "promenlivym rezimem"
            # (D#A, D1:D2).
            self.draw_mode = "ABSOL"
            return

        if stmt.name == "INCRE":
            # INCRE - prirustkovy rezim kresleni (viz G17.md 17.6.1).
            self.draw_mode = "INCRE"
            return

        raise KeyError("Neznamy prikaz '%s'" % stmt.name)

    def _assign_result(self, target_name, target_index, value, env):
        """Zapise 'value' do 'target_name' (pripadne indexovane pole) v
        'env' - stejna logika jako u _exec_stmt(Assign, ...), sdilena i
        pro cil prikazu CRE...ENDCRE (viz _exec_endcre)."""
        if target_index is None:
            env[target_name] = value
            return
        idx = int(round(self.eval_expr(target_index, env)))
        if target_name not in env:
            raise NameError(
                "Pole '%s' nebylo deklarovano (DIMEN) pred zapisem" % target_name
            )
        self._set_indexed(env[target_name], idx, value)

    def _exec_cre(self, stmt, env):
        """CRE,pg - zahajeni vytvareni retezce (viz G10.md 'VYTVARENI
        RETEZCU POMOCI KRESLICICH PRIKAZU'). Nasledujici prikazy MOVE az
        do ENDCRE budujici body retezce 'pg' - viz _exec_move."""
        if self._chain_builder is not None:
            raise GL3RuntimeError(
                "CRE,%s: vnorene bloky CRE...ENDCRE nejsou (zatim) "
                "podporovany (predchozi blok jeste neni uzavren ENDCRE)"
                % stmt.target_name
            )
        if self._open_ini_count > 0:
            raise GL3RuntimeError(
                "CRE,%s: nelze zahajit uvnitr otevreneho bloku INI...CLOSE "
                "(kresleni se nesmi prolinat, viz G10.md)" % stmt.target_name
            )
        self._chain_builder = {
            "target_name": stmt.target_name,
            "target_index": stmt.target_index,
            "env": env,
            "points": [],
            "current_point": None,
            "last_direction": None,
            "founding_pen": None,
        }

    def _exec_endcre(self, stmt, env):
        """ENDCRE - uzavreni retezce zahajeneho prikazem CRE. Body
        nasbirane prikazy MOVE (viz _exec_move) se ulozi jako retezec
        (Curve) do cile zadaneho v CRE. Mid-block pohyby se zdviženym
        perem (/) v mezicase vytvorily v 'points' mezery (None) - viz
        _exec_move a gerlib.e01.make_chain_with_gaps."""
        builder = self._chain_builder
        if builder is None:
            raise GL3RuntimeError("ENDCRE bez odpovidajiciho predchoziho CRE")
        defined_count = sum(1 for p in builder["points"] if p is not None)
        if defined_count < 2:
            raise GL3RuntimeError(
                "CRE,%s...ENDCRE: retezec ma min nez 2 definovane (viditelne) "
                "body - je potreba aspon jeden pohyb MOVE 'se spustenym "
                "perem' (*) za zakladajicim pohybem 'se zdviženym perem' (/)"
                % builder["target_name"]
            )
        chain = _gerlib_make_chain_with_gaps(builder["points"])
        self._assign_result(builder["target_name"], builder["target_index"], chain, builder["env"])
        self._chain_builder = None

    def _exec_ini(self, stmt, env):
        """INI (bez parametru) - zahajeni kresleni do 'skryteho
        retezce' aktualne bezici SUBRO (viz zadani uzivatele -
        zjednodusena nahrada puvodniho INI/OPE...CLOSE do souboru CL2).
        Nasledujici prikazy MOVE az do CLOSE stavi body stejnym
        zpusobem jako CRE...ENDCRE - viz _exec_move/_active_move_builder."""
        frame = self._hidden_chain_stack[-1]
        if frame["ini_builder"] is not None:
            raise GL3RuntimeError(
                "INI: vnorene bloky INI...CLOSE (v ramci jedne SUBRO) "
                "nejsou podporovany (predchozi blok jeste neni uzavren "
                "CLOSE) - kazda volana SUBRO ma ale svuj VLASTNI skryty "
                "retezec, viz CALL"
            )
        if self._chain_builder is not None:
            raise GL3RuntimeError(
                "INI: nelze zahajit uvnitr otevreneho bloku CRE...ENDCRE "
                "(kresleni se nesmi prolinat, viz G10.md)"
            )
        frame["ini_builder"] = {
            "points": [], "current_point": None, "last_direction": None, "founding_pen": None,
        }
        self._open_ini_count += 1

    def _exec_close(self, stmt, env):
        """CLOSE - uzavreni kresleni zahajeneho prikazem INI. Nasbirane
        body (mohou obsahovat mezery/None - viz _exec_move) se pripoji
        do skryteho retezce aktualni SUBRO (viz _push_hidden_chain_frame/
        _pop_hidden_chain_frame pro pripojeni pri navratu z CALL).

        Je-li tohle UPLNE PRVNI nakreslena cast teto SUBRO, jeji
        zakladajici pohyb (viz builder['founding_pen']) urcuje
        frame['starts_with_gap'] pro pozdejsi spojeni s volajicim.
        Je-li to DALSI INI...CLOSE blok VE STEJNE SUBRO, stejne pravidlo
        (zakladajici pohyb '/' => mezera) plati uz TADY, pro spojeni
        s jiz nakreslenou casti teto SUBRO."""
        frame = self._hidden_chain_stack[-1]
        builder = frame["ini_builder"]
        if builder is None:
            raise GL3RuntimeError("CLOSE bez odpovidajiciho predchoziho INI")
        defined_count = sum(1 for p in builder["points"] if p is not None)
        if defined_count < 2:
            raise GL3RuntimeError(
                "INI...CLOSE: nakreslena cast ma min nez 2 definovane "
                "(viditelne) body - je potreba aspon jeden pohyb MOVE "
                "'se spustenym perem' (*) za zakladajicim pohybem 'se "
                "zdviženym perem' (/)"
            )
        if not frame["points"]:
            frame["starts_with_gap"] = (builder["founding_pen"] == "up")
            frame["points"].extend(builder["points"])
        else:
            if builder["founding_pen"] == "up":
                frame["points"].append(None)
            frame["points"].extend(builder["points"])
        frame["ini_builder"] = None
        self._open_ini_count -= 1

    def _active_move_builder(self):
        """Vrati builder (dict s 'points'/'current_point'/'last_direction'),
        do ktereho ma MOVE prave prispivat - bud rozpracovany CRE, nebo
        rozpracovany INI aktualniho ramce (viz _exec_cre/_exec_ini - jsou
        navzajem vylucne, nemuzou byt aktivni soucasne). None, neni-li
        aktivni zadny z nich."""
        if self._chain_builder is not None:
            return self._chain_builder
        return self._hidden_chain_stack[-1]["ini_builder"]

    def _exec_move(self, stmt, env):
        """MOVE|fraze1|fraze2|... (viz G18.md 18.4) - podporovano uvnitr
        bloku CRE...ENDCRE (vytvareni pojmenovaneho retezce, viz
        _exec_cre/_exec_endcre) NEBO uvnitr bloku INI...CLOSE
        (vytvareni 'skryteho retezce' aktualni SUBRO, viz _exec_ini/
        _exec_close) - stejna frazova logika pro oba pripady."""
        builder = self._active_move_builder()
        if builder is None:
            raise GL3RuntimeError(
                "MOVE: podporovano jen uvnitr bloku CRE...ENDCRE (retezec) "
                "nebo INI...CLOSE (skryty retezec)"
            )

        for phrase in stmt.phrases:
            values = [self.eval_expr(v, env) for v in phrase.values]

            if builder["current_point"] is None:
                # Uplne prvni fraze bloku - zakladajici bod retezce. Nema
                # jeste zadny "aktualni bod", pouzijeme pocatek souradnic
                # - useckove fraze zavisle na predchozim bode (*D, *D:V
                # v INCRE rezimu apod.) tu davaji smysl jen vyjimecne,
                # spravny zapis je vzdy absolutni bod (*P) nebo
                # souradnice (*D1:D2 v rezimu ABSOL).
                try:
                    points, direction = _gerlib_evaluate_move_phrase(
                        Point(0.0, 0.0, 0.0), None, self.draw_mode, phrase.sep, values,
                        founding=True,
                    )
                except MovePhraseNotYetImplemented as exc:
                    raise NotYetImplemented(str(exc))
                except MovePhraseError as exc:
                    raise GL3RuntimeError("MOVE (zakladajici fraze): %s" % exc)
                if phrase.pen == "down":
                    # Zakladajici fraze 'se spustenym perem' - retezcove/
                    # obloukove/krivkove fraze (napr. cely retezec *E nebo
                    # cela krivka *S) vraceji VICE bodu; vsechny jsou soucasti
                    # kreslene cesty (neni pred nimi zadny predchozi bod, ktery
                    # by mel byt "od nej" viditelny/neviditelny - fraze sama
                    # svym perem urcuje viditelnost cele sve delky).
                    builder["points"].extend(points)
                else:
                    # 'se zdviženym perem' - jen pozice, bez kresleni (i kdyby
                    # fraze vracela vic bodu - napr. /E:0 pohyb na zacatek
                    # retezce E - zajima nas jen VYSLEDNA pozice).
                    builder["points"].append(points[-1])
                builder["current_point"] = points[-1]
                builder["last_direction"] = direction
                builder["founding_pen"] = phrase.pen
                continue

            try:
                points, direction = _gerlib_evaluate_move_phrase(
                    builder["current_point"], builder["last_direction"], self.draw_mode,
                    phrase.sep, values
                )
            except MovePhraseNotYetImplemented as exc:
                raise NotYetImplemented(str(exc))
            except MovePhraseError as exc:
                raise GL3RuntimeError("MOVE: %s" % exc)

            if phrase.pen == "down":
                builder["points"].extend(points)
            else:
                # Pohyb "se zdviženym perem" (/) uprostred bloku -
                # neviditelny pohyb (viz G18.md "MOVE"): jen posune
                # aktualni bod, ale VYTVORI MEZERU (nespojitost) v
                # kresleni. Zaznamenava se jako None v builder["points"]
                # (pouzivano uz jinde jako "nedefinovana polozka pole" -
                # gl3fc.gl3_export._build_curve mezi sousedy s None
                # prosta preskoci hranu, viz gerlib.e01.make_chain_with_gaps),
                # nasledovana skutecnym bodem doskoku (aby mel dalsi
                # viditelny usek od ceho navazat).
                builder["points"].append(None)
                builder["points"].append(points[-1])

            builder["current_point"] = points[-1]
            builder["last_direction"] = direction

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
        local_input_names = set()
        for i, (formal_name, dim, _dir, _hint) in enumerate(callee_params):
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
            local_input_names.add(formal_name)

        self._input_names_by_env[id(local_env)] = local_input_names

        self._program_name_stack.append(stmt.name)
        self._source_path_stack.append(getattr(callee, "source_path", None))
        saved_line_no = self.current_line_no
        self._push_hidden_chain_frame()
        try:
            self._exec_block(callee.body, local_env)
        except RetSubSignal:
            pass
        except (BreakSignal, ContinueSignal) as exc:
            kw = "BREAK" if isinstance(exc, BreakSignal) else "CONTINUE"
            raise GL3RuntimeError(
                "%s pouzit mimo cyklus (DO/FOR nebo REPEATWHILE) v podprogramu %r"
                % (kw, stmt.name)
            )
        finally:
            self._program_name_stack.pop()
            self._source_path_stack.pop()
            self.current_line_no = saved_line_no
            # stack je [..., parent_frame, callee_frame] - callee_frame
            # (prave dobehnuvsi) je na vrcholu, parent_frame je pod nim.
            parent_frame = self._hidden_chain_stack[-2]
            had_error = sys.exc_info()[0] is not None
            self._pop_hidden_chain_frame(parent_frame=parent_frame, suppress_dangling_check=had_error)

        for i, (formal_name, _dim, _dir, _hint) in enumerate(callee_params):
            if i >= len(stmt.args):
                continue
            actual_text = stmt.args[i]
            if directions.get(formal_name) == "out":
                if _is_identifier(actual_text):
                    env[actual_text] = local_env.get(formal_name)
                # jinak (literal na miste vystupu) - neni kam zapsat, ignoruj

    # ------------------------------------------------------------------
    # Zastupne texty v cestach (${workbench_path}/${fc_file_path}/
    # ${gl3_file_path}) - viz gl3_placeholders.py.
    # ------------------------------------------------------------------

    def _resolve_path(self, text):
        """Nahradi zastupne texty v 'text' (viz gl3_placeholders.substitute)
        - ${workbench_path}/${fc_file_path} jsou konstantni pro cely beh
        (self._static_placeholders, viz __init__), ${gl3_file_path}/
        ${gl3_file_name} jsou adresar/jmeno souboru (vc. pripony) .GL3
        souboru PRAVE BEZICI SUBRO (vrchol _source_path_stack - meni se
        pres vnorene CALL, viz run()/_exec_call)."""
        values = dict(self._static_placeholders)
        current_source = self._source_path_stack[-1] if self._source_path_stack else None
        values["gl3_file_path"] = os.path.dirname(current_source) if current_source else None
        values["gl3_file_name"] = os.path.basename(current_source) if current_source else None
        return gl3_placeholders.substitute(text, values)

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
        filename = self._resolve_path(filename)
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
        """PRINT/WRITE - JEDEN zaznam (radek) na objekt: 'jmeno(index)'
        nasledovane jeho naformatovanymi slozkami (viz
        gl3_ops.format_components - pocet/vyznam slozek zavisi na prvnim
        pismenu 'name', ne na typu 'value' - napr. Point u P (2D) da 2
        cisla, u Q (3D) 3)."""
        label = "%s(%d)" % (name, idx)
        prefix = name[0].upper()
        parts = format_components(prefix, value)
        print("%-10s%s" % (label, "".join("%12s" % p for p in parts)))

    def _exec_type(self, stmt, env):
        """TYPE/TYPE1/TYPE2/TYPET - viz G13.md 'PRIKAZY VYSTUPU TYPU
        TYPE': na rozdil od PRINT/WRITE (jeden zaznam/radek NA OBJEKT)
        spoji CELY seznam parametru (vyrazy, promenne i doslovne
        konstanty) do JEDINEHO zaznamu/radku - zadne label 'jmeno(index)'
        jako u PRINT/WRITE, jen slozky za sebou oddelene mezerou (viz
        priklad v G13.md: "BOD Q 50.000 23.500 0.000 LEZI NA KRIVCE T").

        Prefix pro format_components() se u obecneho vyrazu (ne holeho
        odkazu na promennou) bere jako 'D' (skalar) - v puvodnim jazyce
        by takovy vyraz beztak vzdy byl cislo (retezcovy literal je
        Str primo, ne vypocet, a ten se resi zvlast nize)."""
        parts = []
        for item in stmt.items:
            if isinstance(item, Str):
                parts.append(item.value)
                continue
            value = self.eval_expr(item, env)
            prefix = item.name[0].upper() if isinstance(item, Var) else "D"
            parts.extend(format_components(prefix, value))
        print(" ".join(parts))

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
