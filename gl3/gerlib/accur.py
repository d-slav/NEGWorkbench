# -*- coding: utf-8 -*-
"""
Prikaz ACCUR (dle dodane dokumentace GL3E)

Ucel:    Nastaveni presnosti aproximace krivek a prostorovych kruznic
         retezcem - pouzivaji E45, H45, H96 a kresleni krivek/kruznic.

Uziti:   ACCUR[,vr]

Neni-li 'vr' uvedeno (holy prikaz ACCUR), NEBO neni-li ACCUR v
programu vubec pouzit, systemova hodnota presnosti je 0.01.

Implementace: jednoducha modulova promenna - podle domluvy "izolovana
na jeden gl3_program". Interpreter.__init__ vola reset_accuracy() na
zacatku kazdeho behu, takze predchozi beh (nebo predchozi test) nemuze
ovlivnit ten dalsi. E45 (a pozdeji H45/H96) zustavaji normalni
bezstavove OPERATIONS funkce - presnost si cti primo pres
get_accuracy() v okamziku sveho volani, presne jak se v puvodnim GL3E
chovala jako "aktualne nastavena globalni hodnota" spolecna pro celý
beh programu.
"""

_DEFAULT_ACCURACY = 0.01
_current_accuracy = _DEFAULT_ACCURACY


def set_accuracy(value=None):
    """ACCUR[,vr] - nastavi aktualni presnost. value=None (holy prikaz
    ACCUR, nebo reset na zacatku noveho behu) vrati presnost na vychozich
    0.01."""
    global _current_accuracy
    _current_accuracy = _DEFAULT_ACCURACY if value is None else float(value)


def get_accuracy():
    """Aktualne nastavena presnost (0.01, pokud ACCUR jeste v tomto behu
    nebyl pouzit)."""
    return _current_accuracy


def reset_accuracy():
    """Navrat na vychozi hodnotu - vola se na zacatku kazdeho noveho behu
    Interpreteru (viz Interpreter.__init__)."""
    set_accuracy(None)
