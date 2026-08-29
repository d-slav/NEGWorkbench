# -*- coding: utf-8 -*-
"""
gl3_analysis.py

Smer (in/out) parametru se ted cte PRIMO z povinne anotace v hlavicce
SUBRO (viz gl3_lang.parse_subro_header) - zadne hadani za behu.

get_param_directions() je triviální - jen prevede SubroutineDef.params
na dict {jmeno: 'in'/'out'}.

suggest_directions() je puvodni heuristika (odvozeni z poradi cteni/
zapisu v tele) - ZUSTAVA jen jako pomocny navrh pro rucni anotovani
stareho zdroje bez in:/out: prefixu. Nikdy se nepouziva automaticky
pri behu interpretu - jen ji zavolas rucne, kdyz portujes stary
podprogram a chces navrh, co asi je vstup a co vystup, ktery si pak
sam potvrdis/opravis primo v hlavicce.
"""

import re

from gl3_lang import (
    Var, Num, BinOp, UnaryMinus, OpCall,
    Assign, CallStmt, CommandStmt, DimenStmt, DataStmt,
    DoLoop, IfBlock, IfShort, RepeatWhile, RetSub,
)

_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _is_identifier(text):
    return bool(_IDENT_RE.match(text.strip()))


def get_param_directions(subdef):
    """Vraci dict {param_jmeno: 'in'/'out'} PRIMO z povinne anotace
    v SUBRO hlavicce (subdef.params je (jmeno, velikost, smer, hint))."""
    return {name: direction for name, _size, direction, _hint in subdef.params}


# ---------------------------------------------------------------------------
# Pomocny navrh pro anotovani stareho (jeste needitovaneho) zdroje.
# ---------------------------------------------------------------------------

# Docasna zaloha pro rutiny volane pres CALL, jejichz GL3 zdroj JESTE
# nemame v registru (typicky HLO, nez ho dodas). Klic = jmeno rutiny,
# hodnota = mnozina POZIC (0-indexovanych) argumentu, ktere jsou VYSTUPNI.
# Jakmile bude HLO.GL3 nactena a v registru, tahle polozka se uz vubec
# nepouzije (skutecna anotace v jeji hlavicce ma prednost).
MANUAL_HINTS = {
    "HLO": {"outputs": {0, 2}},
}


def suggest_directions(param_names, body, registry_directions=None, manual_hints=None):
    """
    param_names - list jmen parametru (bez anotace, jen hola jmena)
    body        - seznam jiz zparsovanych statementu tela podprogramu
    registry_directions - dict {podprogram_jmeno: {param: 'in'/'out'}}
                  jiz anotovanych/znamych podprogramu volanych pres CALL

    Vraci dict {jmeno: 'in'/'out'} jako NAVRH - potvrd/oprav rucne pri
    zapisu do skutecne SUBRO hlavicky (in:/out: je povinne).
    """
    manual_hints = manual_hints if manual_hints is not None else MANUAL_HINTS
    registry_directions = registry_directions or {}

    order = []

    def note(name, kind):
        order.append((name, kind))

    def visit_expr(node):
        if node is None:
            return
        if isinstance(node, Var):
            note(node.name, "read")
            visit_expr(node.index)
        elif isinstance(node, BinOp):
            visit_expr(node.left)
            visit_expr(node.right)
        elif isinstance(node, UnaryMinus):
            visit_expr(node.operand)
        elif isinstance(node, OpCall):
            for a in node.args:
                visit_expr(a)

    def visit_cond(cond):
        visit_expr(cond.left)
        visit_expr(cond.right)

    def visit_stmt(s):
        if isinstance(s, Assign):
            visit_expr(s.value)
            visit_expr(s.target_index)
            note(s.target, "write")
        elif isinstance(s, CallStmt):
            callee_dirs = registry_directions.get(s.name)
            hints = manual_hints.get(s.name)
            if callee_dirs is not None:
                callee_param_names = list(callee_dirs.keys())
                for i, arg in enumerate(s.args):
                    if not _is_identifier(arg):
                        continue
                    pname = callee_param_names[i] if i < len(callee_param_names) else None
                    direction = callee_dirs.get(pname, "in")
                    note(arg, "write" if direction == "out" else "read")
            elif hints is not None:
                out_positions = hints.get("outputs", set())
                for i, arg in enumerate(s.args):
                    if not _is_identifier(arg):
                        continue
                    note(arg, "write" if i in out_positions else "read")
            else:
                for arg in s.args:
                    if _is_identifier(arg):
                        note(arg, "read")
                        note(arg, "write")
        elif isinstance(s, CommandStmt):
            for a in s.args:
                visit_expr(a)
        elif isinstance(s, DimenStmt):
            for name, _size in s.entries:
                note(name, "write")
        elif isinstance(s, DataStmt):
            note(s.array_name, "write")
        elif isinstance(s, DoLoop):
            visit_expr(s.start)
            visit_expr(s.end)
            note(s.var, "write")
            for st in s.body:
                visit_stmt(st)
        elif isinstance(s, (IfBlock, RepeatWhile)):
            visit_cond(s.cond)
            for st in s.body:
                visit_stmt(st)
        elif isinstance(s, IfShort):
            visit_cond(s.cond)
            visit_stmt(s.stmt)
        elif isinstance(s, RetSub):
            pass

    for stmt in body:
        visit_stmt(stmt)

    first_seen = {}
    ever_write = set()
    ever_read = set()
    for name, kind in order:
        first_seen.setdefault(name, kind)
        if kind == "write":
            ever_write.add(name)
        else:
            ever_read.add(name)

    result = {}
    for pname in param_names:
        if pname in ever_write and pname in ever_read:
            result[pname] = "in" if first_seen[pname] == "read" else "out"
        elif pname in ever_write:
            result[pname] = "out"
        elif pname in ever_read:
            result[pname] = "in"
        else:
            result[pname] = "in"
    return result
