# -*- coding: utf-8 -*-
"""
Prototyp: prevod gerlib.types.Spline (kubicky Hermitovsky splajn, S03)
na sekvenci kubickych Bezierovych segmentu - presne, bez FreeCADu.

Pouzita identita Hermite -> Bezier pro segment P_i -> P_{i+1} s tecnymi
vektory T_i, T_{i+1} (parametrizace t na [0,1]):

    B0 = P_i
    B1 = P_i + T_i / 3
    B2 = P_{i+1} - T_{i+1} / 3
    B3 = P_{i+1}

Overeni: H(t) (primy vypocet Hermitovske baze) vs Bezier(t) (Bernsteinova
baze z B0..B3) musi byt bodove totozne pro kazdy segment a kazde t.
"""
import sys
sys.path.insert(0, ".")

from gl3_lang import parse_program
from gl3_interpreter import Interpreter


def load(name):
    with open("examples/%s" % name, "r", encoding="utf-8", errors="replace") as f:
        return parse_program(f.read())


def hermite_point(p0, p1, t0, t1, t):
    h00 = 2 * t**3 - 3 * t**2 + 1
    h10 = t**3 - 2 * t**2 + t
    h01 = -2 * t**3 + 3 * t**2
    h11 = t**3 - t**2
    x = h00 * p0.x + h10 * t0.x + h01 * p1.x + h11 * t1.x
    y = h00 * p0.y + h10 * t0.y + h01 * p1.y + h11 * t1.y
    return x, y


def hermite_to_bezier_controls(p0, p1, t0, t1):
    b0 = (p0.x, p0.y)
    b1 = (p0.x + t0.x / 3.0, p0.y + t0.y / 3.0)
    b2 = (p1.x - t1.x / 3.0, p1.y - t1.y / 3.0)
    b3 = (p1.x, p1.y)
    return b0, b1, b2, b3


def bezier_point(b0, b1, b2, b3, t):
    mt = 1 - t
    x = (mt**3) * b0[0] + 3 * (mt**2) * t * b1[0] + 3 * mt * (t**2) * b2[0] + (t**3) * b3[0]
    y = (mt**3) * b0[1] + 3 * (mt**2) * t * b1[1] + 3 * mt * (t**2) * b2[1] + (t**3) * b3[1]
    return x, y


def main():
    tehlo = load("TEHLO.GL3")
    hlo = load("HLO.GL3")
    interp = Interpreter(registry={"TEHLO": tehlo, "HLO": hlo})
    result = interp.run(tehlo, inputs={"BJM": "examples/E374.TXT", "DH": 15.2})
    spline = result["S"]

    pts = spline.points
    tans = spline.tangents
    n = len(pts)

    max_err = 0.0
    all_bezier_ctrl = []
    for i in range(n - 1):
        p0, p1 = pts[i], pts[i + 1]
        t0, t1 = tans[i], tans[i + 1]
        b0, b1, b2, b3 = hermite_to_bezier_controls(p0, p1, t0, t1)
        all_bezier_ctrl.append((b0, b1, b2, b3))

        for k in range(11):
            t = k / 10.0
            hx, hy = hermite_point(p0, p1, t0, t1, t)
            bx, by = bezier_point(b0, b1, b2, b3, t)
            err = ((hx - bx) ** 2 + (hy - by) ** 2) ** 0.5
            max_err = max(max_err, err)

    print("segmentu:", n - 1)
    print("max. odchylka Hermite vs Bezier (mm):", max_err)
    assert max_err < 1e-9, "Hermite->Bezier prevod NENI presny!"
    print("OK - prevod je bodove presny (identita, ne aproximace)")

    # vizualni kontrola: vykresli Bezier segmenty (jemne vzorkovane) + kontrolni polygon
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4))
    for (b0, b1, b2, b3) in all_bezier_ctrl:
        xs, ys = [], []
        for k in range(41):
            t = k / 40.0
            x, y = bezier_point(b0, b1, b2, b3, t)
            xs.append(x)
            ys.append(y)
        ax.plot(xs, ys, color="tab:blue", linewidth=1.5)
        # kontrolni polygon kazdeho segmentu (tence, pro kontrolu tvaru tecen)
        cx = [b0[0], b1[0], b2[0], b3[0]]
        cy = [b0[1], b1[1], b2[1], b3[1]]
        ax.plot(cx, cy, color="lightgray", linewidth=0.5, linestyle="--")

    node_x = [p.x for p in pts]
    node_y = [p.y for p in pts]
    ax.scatter(node_x, node_y, color="red", s=10, zorder=5, label="uzlove body (PO)")

    ax.set_aspect("equal")
    ax.set_title("TEHLO / E374 - S03 Hermite spline jako retezec Bezier segmentu")
    ax.legend()
    fig.tight_layout()
    fig.savefig("/home/claude/proto_bezier_export.png", dpi=150)
    print("Ulozen obrazek: /home/claude/proto_bezier_export.png")


if __name__ == "__main__":
    main()
