# -*- coding: utf-8 -*-
"""
gl3_ops.py - registr operaci pouzitych v GL3 programech.

Samotna geometrie (Point/Vector/Line/.../make_chain/tangent_line/...) zije
v samostatnem, na GL3 nezavislem balicku gerlib/ (viz gerlib/__init__.py) -
tenhle modul je jen tenka adapterova vrstva, ktera:
  - registruje kazdou operaci pod jejim GL3 kodem (D10, P48, C02, E01, ...)
    v OPERATIONS/COMMANDS - vetsina je zatim STUB (NotYetImplemented), dokud
    nedodas Fortran zdrojak a nenahradis telo skutecnym vypoctem v gerlib,
  - rika interpretru, jak z prvniho pismene nazvu promenne poznat typ
    (TYPE_PREFIX_INFO/classify) - pro pripadne pozdejsi generovani FreeCAD
    properties,
  - rika interpretru, ktere opcody ocekavaji "adresu prvniho prvku pole"
    (ARRAY_REF_OPS, Fortran konvence 'P(1),N').

Interpret (gl3_interpreter.py) vola operace takto:
    OPERATIONS["D10"](arg1, arg2)   # vraci skalar
kde arg1/arg2 uz jsou vyhodnocene Python hodnoty (float, nebo gerlib.Point/
Vector/Circle/Line/Plane/Curve).
"""

from gerlib import (
    Point, Vector, Line, Circle, Plane, Curve, Spline,
    make_chain, tangent_point, tangent_point_from_line, tangent_line,
    sum_or_diff, product_or_quotient,
    point_point, point_line, vector_magnitude,
    line_intersection,
    line_through_point as _gerlib_line_through_point,
    copy_point as _gerlib_copy_point,
    copy_circle as _gerlib_copy_circle,
    circle_center as _gerlib_circle_center,
    circle_from_3_points as _gerlib_circle_from_3_points,
    parallel_line as _gerlib_parallel_line,
    point_count as _gerlib_point_count,
    curve_node as _gerlib_curve_node,
    nearest_point as _gerlib_nearest_point,
    radius_of_curvature as _gerlib_radius_of_curvature,
    line_curve_intersection as _gerlib_line_curve_intersection,
    triangle_area, triangle_area_signed, triangle_area_from_lines, circle_area,
    scale as _gerlib_scale,
    get_component as _gerlib_get_component,
    index_parameter as _gerlib_index_parameter,
    offset_point as _gerlib_offset_point,
    interpolate_point as _gerlib_interpolate_point,
    make_spline as _gerlib_make_spline,
    make_spline1 as _gerlib_make_spline1,
    builtin_constants as _gerlib_builtin_constants,
)
from geplib import (
    make_point3 as _geplib_make_point3,
    make_vector3 as _geplib_make_vector3,
)


def builtin_constants():
    return _gerlib_builtin_constants()


# ---------------------------------------------------------------------------
# Typovy system pro generovani FreeCAD properties (viz diskuze s uzivatelem)
# ---------------------------------------------------------------------------

# prefix -> ("scalar" | "composite" | "string", nativni FC typ nebo None)
#
# Presne podle zadani uzivatele:
#   Skalarni:              D, A (delka, uhel, plocha, ...)
#   Rovinne (2D) objekty:  P bod, V vektor, C kruznice, L primka, S krivka,
#                          E retezec
#   Prostorove (3D):       Q bod, U vektor, R rovina, M primka, G kruznice,
#                          T krivka, H retezec, F plocha
#   Celociselne:           I, J, K (jen tyto tri - NE M/N, jak jsem drive
#                          mylne predpokladal; M je 3D primka)
#   Textove:               B
# Cokoliv jineho (neznamy/nerezervovany prefix) je bezny skalar (float).
TYPE_PREFIX_INFO = {
    "D": ("scalar", "App::PropertyFloat"),
    "A": ("scalar", "App::PropertyFloat"),
    "I": ("scalar", "App::PropertyInteger"),
    "J": ("scalar", "App::PropertyInteger"),
    "K": ("scalar", "App::PropertyInteger"),
    "B": ("string", "App::PropertyFile"),
    # 2D
    "P": ("composite", None),   # bod 2D
    "V": ("composite", None),   # vektor 2D
    "C": ("composite", None),   # kruznice 2D
    "L": ("composite", None),   # primka 2D
    "S": ("composite", None),   # krivka 2D
    "E": ("composite", None),   # retezec 2D
    # 3D
    "Q": ("composite", None),   # bod 3D
    "U": ("composite", None),   # vektor 3D
    "R": ("composite", None),   # rovina
    "M": ("composite", None),   # primka 3D
    "G": ("composite", None),   # kruznice 3D
    "T": ("composite", None),   # krivka 3D
    "H": ("composite", None),   # retezec 3D
    "F": ("composite", None),   # plocha
}


def classify(var_name):
    """Vrati (kind, native_fc_type) podle prvniho pismene jmena promenne.
    Neznamy/nerezervovany prefix (napr. J, jak ho pouziva TEHLO.gl3 jako
    obycejny scitaci skalar) se bere jako scalar/float - ne jako composite,
    protoze composite geometricke typy maji sve vlastni vyhrazene prefixy
    a vsechno ostatni je v realnych GL3 programech bezny skalar."""
    prefix = var_name[0].upper()
    return TYPE_PREFIX_INFO.get(prefix, ("scalar", "App::PropertyFloat"))


# ---------------------------------------------------------------------------
# Pomocna trida pro pahyly - drzi si i informaci "kde se pouziva", aby
# chybova hlaska byla k necemu uzitecna pri postupnem doplnovani.
# ---------------------------------------------------------------------------

class NotYetImplemented(NotImplementedError):
    pass


def _stub(code, description):
    def fn(*args):
        raise NotYetImplemented(
            "Operace '%s' (%s) jeste neni implementovana - "
            "potrebuje Fortran zdrojak k prevodu. Volano s argumenty: %r"
            % (code, description, args)
        )
    fn.__name__ = "stub_" + code
    return fn


# ---------------------------------------------------------------------------
# Adaptery na gerlib - prevadeji GL3 pozicni argumenty (OPCODE>args) na
# volani gerlib funkci a hlidaji jejich vlastni GL3-specificke drobnosti
# (napr. E01 dostava "podpole" misto jednoho bodu - viz ARRAY_REF_OPS).
# ---------------------------------------------------------------------------

def _op_e01(points_ref, n):
    """E01: EM=E01>P,N - viz gerlib.make_chain."""
    return make_chain(points_ref, n)


def _op_p85(direction_vec, curve, k):
    """P85: PM=P85>V,E,K - viz gerlib.tangent_point."""
    return tangent_point(direction_vec, curve, k)


def _op_p86(line, curve, k):
    """P86: PM=P86>L,E,K - viz gerlib.tangent_point_from_line."""
    return tangent_point_from_line(line, curve, k)


def _op_l46(line, curve, k):
    """L46: LM=L46>L,E,K - viz gerlib.tangent_line."""
    return tangent_line(line, curve, k)


def _op_l02(point, direction):
    """L02: LM=L02>P,V - viz gerlib.line_through_point (L302.FOR)."""
    return _gerlib_line_through_point(point, direction)


def _op_p49(point):
    """P49: PM=P49>>P< - viz gerlib.copy_point (hodnotova kopie bodu)."""
    return _gerlib_copy_point(point)


def _op_c49(circle):
    """C49: CM=C49>>C< - viz gerlib.copy_circle (hodnotova kopie kruznice)."""
    return _gerlib_copy_circle(circle)


def _op_p47(circle):
    """P47: PM=P47>C - viz gerlib.circle_center (stred kruznice)."""
    return _gerlib_circle_center(circle)


def _op_c02(p1, p2, p3):
    """C02: CM=C02>>P1,P2,P3< - viz gerlib.circle_from_3_points (C402.FOR)."""
    return _gerlib_circle_from_3_points(p1, p2, p3)


def _op_l20(line, distance, k=0):
    """L20: LM=L20>>L,D[,K]< - viz gerlib.parallel_line (L320.FOR)."""
    return _gerlib_parallel_line(line, distance, k)


def _op_npo(curve_or_chain):
    """NPO: pi=NPO>vg(S,E,T,H) - viz gerlib.point_count."""
    return _gerlib_point_count(curve_or_chain)


def _op_p48(curve_or_chain, k):
    """P48: PM=P48>pg,K< - viz gerlib.curve_node (P48/P48E/P48S)."""
    return _gerlib_curve_node(curve_or_chain, int(round(k)))


def _op_p42(point, spline, k):
    """P42: PM=P42>P,S,K< - viz gerlib.nearest_point (paty kolmic na krivku)."""
    return _gerlib_nearest_point(spline, point, k)


def _op_d50(spline, point):
    """D50: DM=D50>S,P< - viz gerlib.radius_of_curvature (RKSEG.FOR, bez GLPAT)."""
    return _gerlib_radius_of_curvature(spline, point)


def _op_p22(line, spline, k):
    """P22: PM=P22>L,S,K< - viz gerlib.line_curve_intersection (GLPRU.FOR)."""
    return _gerlib_line_curve_intersection(spline, line, k)


def _op_d01(x1, x2, k):
    """D01 (interne D601): soucet/rozdil dvou skalaru."""
    return sum_or_diff(x1, x2, int(round(k)))


def _op_d02(x1, x2, k):
    """D02 (interne D602): soucin/podil dvou skalaru."""
    return product_or_quotient(x1, x2, int(round(k)))


def _op_d10(p1, p2):
    """D10 (interne D610): vzdalenost bod-bod."""
    return point_point(p1, p2)


def _op_d11(point, line):
    """D11 (interne D611): vzdalenost bodu od primky."""
    return point_line(point, line)


def _op_d20(vec):
    """D20 (interne D620): velikost vektoru."""
    return vector_magnitude(vec)


def _op_d40(p1, p2, p3):
    """D40 (interne D640): obsah trojuhelniku (vzdy kladny)."""
    return triangle_area(p1, p2, p3)


def _op_d42(p1, p2, p3):
    """D42 (interne D642): obsah trojuhelniku se znamenkem (CW+/CCW-)."""
    return triangle_area_signed(p1, p2, p3)


def _op_d43(circle):
    """D43 (interne D643): obsah kruhu."""
    return circle_area(circle)


def _op_d30(pg, k):
    """D30: DM=D30>pg,K - vytazena slozka geometrickeho objektu (podle
    dokumentace uzivatele - viz gerlib.get_component pro presne cislovani
    a upozorneni na 2D/3D nejednoznacnost primky a kruznice)."""
    return _gerlib_get_component(pg, k)


def _op_d31(curve_or_spline, point):
    """D31: DM=D31>E,P / DM=D31>S,P - indexparametr bodu na retezci/krivce."""
    return _gerlib_index_parameter(curve_or_spline, point)


def _op_p20(line1, line2):
    """P20 (interne P120): prusecik dvou primek."""
    return line_intersection(line1, line2)


def _op_d41(line1, line2, line3):
    """D41 (interne D641): obsah trojuhelniku vymezeneho tremi primkami."""
    return triangle_area_from_lines(line1, line2, line3)


def _op_p10(point, dx, dy):
    """P10 (interne P110): bod posunuty o prirustky (dx, dy)."""
    return _gerlib_offset_point(point, dx, dy)


def _op_p13(p1, p2, t):
    """P13 (interne P113): bod deli usecku v danem pomeru t (0..1)."""
    return _gerlib_interpolate_point(p1, p2, t)


def _op_s01(points_ref, k, *rest):
    """S01: SM=S01>P(I),K[,[V1],[VK]] - krivka (Spline) K body, chordalni
    (chord-length) parametrizace, viz gerlib.make_spline1. Na rozdil od
    S03 nema volitelny krok N (viz signatura v zadani)."""
    v1 = rest[0] if len(rest) >= 1 else None
    vk = rest[1] if len(rest) >= 2 else None
    return _gerlib_make_spline1(points_ref, k, v1, vk)


def _op_s03(points_ref, k, *rest):
    """S03: SM=S03>P(I),K[,[V1],[VK][,N]] - krivka (Spline) K body se
    dvema okrajovymi tecnymi vektory, viz gerlib.make_spline."""
    v1 = rest[0] if len(rest) >= 1 else None
    vk = rest[1] if len(rest) >= 2 else None
    n = rest[2] if len(rest) >= 3 else None
    return _gerlib_make_spline(points_ref, k, v1, vk, n)


def _op_q00(d1, d2, d3):
    """Q00: QM=Q00>D1,D2,D3 - bod tremi souradnicemi, viz geplib.q00."""
    return _geplib_make_point3(d1, d2, d3)


def _op_u00(d1, d2, d3):
    """U00: UM=U00>D1,D2,D3 - vektor tremi slozkami, viz geplib.u00."""
    return _geplib_make_vector3(d1, d2, d3)


# Opcody, ktere v puvodnim Fortranu ocekavaji "adresu prvniho prvku pole"
# (zapis 'P(1),N' = precti N prvku pole P pocinaje P(1)) - interpret jim
# proto misto jednoho vyhodnoceneho bodu preda cele podpole (viz
# gl3_interpreter._eval_array_ref). Pozice v mnozine je 0-based index
# argumentu v seznamu OPCODE>args.
ARRAY_REF_OPS = {
    "E01": {0},
    "S01": {0},
    "S03": {0},
}


# ---------------------------------------------------------------------------
# Registr - jeden radek na kazdy kod pouzity v XPROC.GL3 / SCARA.GL3 / HLO.GL3
# ---------------------------------------------------------------------------

OPERATIONS = {
    # --- skalary ---
    "D01": _op_d01,
    "D02": _op_d02,

    # --- vzdalenosti / velikosti / obsahy ---
    "D10": _op_d10,
    "D11": _op_d11,
    "D20": _op_d20,
    "D27": _stub("D27", "delka kruhoveho oblouku - potrebuje jeste A512.FOR (D627.FOR ho vola)"),
    "D30": _op_d30,
    "D31": _op_d31,
    "D40": _op_d40,
    "D41": _op_d41,
    "D42": _op_d42,
    "D43": _op_d43,
    "D50": _op_d50,

    # --- body ---
    "P10": _op_p10,
    "P13": _op_p13,
    "P22": _op_p22,
    "P42": _op_p42,
    "P44": _stub("P44", "odpovidajici bod na jine krivce (projekce?)"),
    "P47": _op_p47,
    "P48": _op_p48,
    "P49": _op_p49,
    "P85": _op_p85,
    "P86": _op_p86,

    # --- primky ---
    "L02": _op_l02,
    "L20": _op_l20,
    "L45": _stub("L45", "primka kolma na neco (?) - pouzito pri vypoctu delky tetivy"),
    "L46": _op_l46,
    "P20": _op_p20,  # prusecik dvou primek - vraci bod, ale nazev je P20 (viz uzivatelovo vysvetleni P20->P120)

    # --- kruznice ---
    "C02": _op_c02,
    "C49": _op_c49,

    # --- krivky / retezce ---
    "S01": _op_s01,
    "S03": _op_s03,
    "E01": _op_e01,
    "E45": _stub("E45", "diskretizace krivky na retezec s danou presnosti / vyrez segmentu"),
    "NPO": _op_npo,

    # --- prostorove (3D) - viz geplib ---
    "Q00": _op_q00,
    "U00": _op_u00,

    # --- ostatni ---
    "ABS": lambda x: abs(x),  # obycejna absolutni hodnota - neni potreba Fortran
}


# ---------------------------------------------------------------------------
# "Prikazy" (ne funkce vracejici hodnotu, ale prikazy menici stav) -
# SCALE, pripadne dalsi z NEG, az je budes potrebovat.
# ---------------------------------------------------------------------------

def cmd_scale(interpreter, source_value, factor):
    """SCALE,pg1,pg2,vr,vi - meritkova transformace (SCALEX.FOR). Interpret
    (gl3_interpreter._exec_command) uz obstaral smycku pres 'vi' objektu
    a indexovani cilove/zdrojove pole (Fortran konvence P(1),N) - tady se
    resi jen transformace JEDNOHO objektu."""
    return _gerlib_scale(source_value, factor)


COMMANDS = {
    "SCALE": cmd_scale,
}
