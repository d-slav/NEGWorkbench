# -*- coding: utf-8 -*-
"""
Funkce FS51        n.p. Let Kunovice
Knihovna GL3E4                                     Listopad 1987

Ucel:    Definuje soustavu 4 nelinearnich rovnic pro nalezeni segmentu
         ekvidistantni krivky (S51) - viz gerlib/nlsolve.py.

Rozpoznano z FS51.FOR (A,B,C jsou standardni kubicke Hermitovy bazove
funkce, overeno rozepsanim):
    A = t^2*(2t-3)      =>  A+1 = h00(t) = 2t^3-3t^2+1
    B = t*(t*(t-2)+1)   =>  B    = h10(t) = t^3-2t^2+t
    C = t^2*(t-1)       =>  C    = h11(t) = t^3-t^2
    -A                  =>       = h01(t) = -2t^3+3t^2

FS51(X,4,K) pro K=1..4 pocita rezidual: hodnota FITOVANE Hermitovy
krivky (pocatek P0, konec P1 - PRESNE offset body; tecny = PUVODNI
smery na zacatku/konci segmentu, skalovane neznamymi X(3)=DD1,
X(4)=DD2) v parametru X(1) (K=1,2) nebo X(2) (K=3,4), minus cilovy bod
na SKUTECNE ekvidistante 'targets[K-1]'.
"""


def make_residual_fn(p0, p1, tangent0, tangent1, targets):
    """Sestavi rezidualni funkci pro nlsolve.solve() (n=4) - 1:1 podle
    FS51.FOR.

    p0, p1              - (x,y) presne offset krajni body segmentu
    tangent0, tangent1  - (x,y) PUVODNI (nescalovane) smerove vektory
                           na zacatku/konci segmentu
    targets             - (xe1, ye1, xe2, ye2) - dva cilove body na
                           skutecne ekvidistante, v parametrech X(1)
                           (xe1,ye1) a X(2) (xe2,ye2)
    """
    x1, y1 = p0
    x2, y2 = p1
    u1, v1 = tangent0
    u2, v2 = tangent1

    def func(x, n, k):
        j = (k + 1) // 2  # 1-based J, presne jako original
        i = 2 - (k % 2)   # 1-based I, presne jako original
        t = x[j - 1]
        a = t * t * (2.0 * t - 3.0)
        b = t * (t * (t - 2.0) + 1.0)
        c = t * t * (t - 1.0)
        d3, d4 = x[2], x[3]
        if i == 1:
            val = (a + 1.0) * x1 - a * x2 + b * u1 * d3 + c * u2 * d4
        else:
            val = (a + 1.0) * y1 - a * y2 + b * v1 * d3 + c * v2 * d4
        return val - targets[k - 1]

    return func
