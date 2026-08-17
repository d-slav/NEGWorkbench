# -*- coding: utf-8 -*-
"""
test_omitted_args.py - Obecna podpora vynechanych pozic v seznamu
argumentu OpCall (napr. "D28>E,,P2" - vynechany prvni volitelny
parametr uprostred seznamu). Viz gl3_lang.Omitted/OMITTED a
gl3_interpreter.eval_expr.

Testuje mechanismus samotny (parser + eval_expr sentinel), nezavisle
na konkretnim opcode, ktery ho pouziva (D28 ma svuj vlastni test v
gerlib/test_d28.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gl3_lang import parse_expr_text, Omitted, OMITTED, Var, UnaryMinus
from gl3_interpreter import Interpreter


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print("%s %s" % (status, msg))
    assert cond, msg


def test_parser_recognizes_omitted_slots():
    # Vynechany prostredni argument
    n = parse_expr_text("D28>E,,P2")
    kinds = [type(a).__name__ for a in n.args]
    check(kinds == ["Var", "Omitted", "Var"], "prostredni vynechany argument (E,,P2)")

    # Vynechany posledni argument (trailing carka)
    n2 = parse_expr_text("D28>E,P1,")
    kinds2 = [type(a).__name__ for a in n2.args]
    check(kinds2 == ["Var", "Var", "Omitted"], "koncovy vynechany argument (E,P1,)")

    # Zadny vynechany argument
    n3 = parse_expr_text("D28>E,P1,P2")
    kinds3 = [type(a).__name__ for a in n3.args]
    check(kinds3 == ["Var", "Var", "Var"], "zadny vynechany argument")

    # Bez zadneho volitelneho argumentu vubec
    n4 = parse_expr_text("D28>E")
    kinds4 = [type(a).__name__ for a in n4.args]
    check(kinds4 == ["Var"], "jediny (povinny) argument")

    # DULEZITE: zaporne cislo za carkou NENI vynechany argument
    n5 = parse_expr_text("D28>E,-5,P2")
    kinds5 = [type(a).__name__ for a in n5.args]
    check(kinds5 == ["Var", "UnaryMinus", "Var"],
          "zaporne cislo (unarni minus) se NEPLETE s vynechanym argumentem")

    print("test_parser_recognizes_omitted_slots(): OK")


def test_eval_expr_returns_sentinel():
    interp = Interpreter()
    value = interp.eval_expr(Omitted(), {})
    check(value is OMITTED, "Omitted() se vyhodnoti na sentinel OMITTED")
    check(bool(OMITTED) is False, "OMITTED je 'falsy' (pro pripadne pohodlne if not opt: ...)")
    check(OMITTED is not None, "OMITTED je odlisny objekt od None (jiny vyznam - viz NoSolution)")

    print("test_eval_expr_returns_sentinel(): OK")


def main():
    test_parser_recognizes_omitted_slots()
    test_eval_expr_returns_sentinel()
    print("\nVSE OK - obecna podpora vynechanych argumentu (,,) funguje.")


if __name__ == "__main__":
    main()
