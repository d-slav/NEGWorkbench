# -*- coding: utf-8 -*-
"""
Procedura VNORM     LET n.p. Uh.Hradiste
Knihovna CURLIB32                      Unor 1980

Ucel:    Normalizace vektoru o N slozkach.

Uziti:   CALL VNORM(A,N,NON)

Parametry: A(N)  R*4  Slozky vektoru (in/out - normalizuje na miste)
           NON   I*2  NON=0 vektor byl normalizovan, NON=1 vektor je nulovy
"""


def is_zero_vector(components, eps=1e-10):
    """VNORM - jen cast 'detekce nuloveho vektoru' (presna hodnota
    normalizovaneho vektoru se v DSN/DSPN/DSPP dal nepouziva, jen tenhle
    priznak)."""
    return sum(c * c for c in components) <= eps
