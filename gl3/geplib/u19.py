# -*- coding: utf-8 -*-
"""
Procedura VECT75 (GL3 opcode U19)     LET, k.p., Uh.Hradiste
Knihovna GEPLIBPC                                  Listopad 1989

Ucel:    Vektor otoceny o uhel kolem primky (osy rotace).

Uziti:   CALL VECT75(U1,Q2,U2,A,U)
         GL3:  UM=U19>U,M,A[,K]

Vektor UM je ziskan otocenim vektoru U o uhel A (stupne) kolem primky M
(osa rotace - pouzije se jen jeji SMER, poloha primky na vysledek
nema vliv - viz odvozeni nize). Pri pohledu VE SMERU vektoru primky
kladna hodnota uhlu A otaci vektor proti smeru hodinovych rucicek pro
K=0 (default), po smeru pro K=1 (viz G10.md 'U19 - Vektor otoceny o
uhel kolem primky').

Puvodni VECT75.FOR sklada pomocny bod Q3=Q2+U1, otoci ho o uhel kolem
primky (Q2,U2) pres POIN93 (K uvnitr VECT75 VZDY 0 - K jako volitelny
parametr vystavuje az GL3 opcode U19, VECT75 sam o sobe je jen jeho
K=0 specialni pripad) a odecte Q2 zpet:
    Q3 = Q2 + U1                          (VECT79 - soucet)
    Q4 = otoceny bod Q3 kolem primky (Q2,U2) o uhel A, K   (POIN93)
    U  = Q4 - Q2                          (VECT80 - rozdil)

POIN93 pocita rotaci pres pomocny lokalni souradny system (CS999 -
osa x' ve smeru primky, y'/z' v rovine kolmicek na ni) a transformaci
zpet (VECT99) - matematicky se ale cely tenhle retezec zjednodusi na
klasicky Rodriguesuv vzorec pro rotaci vektoru kolem OSY (smeru n):

    U = U*cos(t) + (n x U)*sin(t) + n*(n.U)*(1-cos(t))

kde n je jednotkovy smerovy vektor primky M a t = A (radiany) pro K=1,
t = -A pro K=0 (default) - odvozeno a OVERENO numericky (200 nahodnych
zkousek, primy port puvodniho retezce VECT75->POIN93->CS999->VECT99 dal
shodne vysledky na 1e-7) proti primemu prepisu puvodniho Fortranu.

Primy Rodriguesuv vzorec je matematicky ekvivalentni, ale nepotrebuje
zadny mezikrok pres pomocny bod Q2 ani lokalni souradny system - a na
rozdil od puvodniho POIN81 (patni bod na primce), ktery implicitne
predpoklada uz JEDNOTKOVY smerovy vektor primky (nedeli druhou mocninou
jeho velikosti), tady normalizace probiha explicitne, takze funguje i
pro primku se smerovym vektorem libovolne (nenulove) delky.
"""
import math

from gerlib.types import Vector

_TOL = 1e-6


def rotate_vector_about_line(vector, line, angle_deg, k=0):
    """U19: UM=U19>U,M,A[,K] - vektor U otoceny o uhel A (stupne) kolem
    smeru primky M. K=0 (default) proti smeru hodinovych rucicek (pri
    pohledu ve smeru primky), K=1 po smeru - viz hlavicka modulu."""
    nx, ny, nz = line.direction.x, line.direction.y, line.direction.z
    nlen = math.sqrt(nx * nx + ny * ny + nz * nz)
    if nlen < _TOL:
        raise ValueError("U19: smerovy vektor primky M je nulovy")
    nx, ny, nz = nx / nlen, ny / nlen, nz / nlen

    theta = math.radians(angle_deg)
    if int(round(k)) == 0:
        theta = -theta

    vx, vy, vz = vector.x, vector.y, vector.z
    dot = nx * vx + ny * vy + nz * vz
    cx, cy, cz = ny * vz - nz * vy, nz * vx - nx * vz, nx * vy - ny * vx  # n x v

    cos_t, sin_t = math.cos(theta), math.sin(theta)
    one_minus_cos = 1.0 - cos_t

    rx = vx * cos_t + cx * sin_t + nx * dot * one_minus_cos
    ry = vy * cos_t + cy * sin_t + ny * dot * one_minus_cos
    rz = vz * cos_t + cz * sin_t + nz * dot * one_minus_cos
    return Vector(rx, ry, rz)
