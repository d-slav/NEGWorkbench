# -*- coding: utf-8 -*-
"""
Vyjimky pro rozliseni "geometricka konstrukce nema reseni" (varovani,
GL3 program pokracuje s vysledkem undefined) od ostatnich chyb
(spatne argumenty, chybna geometrie na vstupu, bug apod. - ty zustavaji
jako obycejny ValueError/TypeError a jsou tvrde chyby nebo bugy).

Pouziti v gerlib: kde operace nema jednoznacny numericky bug, ale proste
"neexistuje reseni pro tento vstup" (rovnobezne primky u pruseciku,
neprotinajici se kruznice, K-ty prvek kdyz existuje min nez K reseni...),
se ma vyhodit NoSolution misto obecneho ValueError. Interpret (gl3_
interpreter.py) NoSolution odchyti na urovni vyhodnoceni OpCall, vypise
varovani (pokud disp_warning) a cilove promenne priradi None (existujici
mechanismus IFN/undefined - viz gl3_lang.IsUndefined) - beh programu
pokracuje dal.

Zavadi se POSTUPNE (dohodnuto v konverzaci) - pilotne u tecnych kruznic
(C32/C33/C34, gerlib/circle_geom.py), zbytek gerlib prochazi puvodni
ValueError beze zmeny, dokud nebude prepracovan.
"""


class NoSolution(ValueError):
    """Geometricka konstrukce nema pro dany vstup reseni - NENI to bug
    ani chyba pouziti, jen legitimni vysledek (napr. rovnobezne primky
    nemaji prusecik). Podtrida ValueError, takze stavajici 'except
    ValueError' kod (testy, starsi volajici) dal funguje beze zmeny -
    jen interpret ji muze rozeznat specialne."""
    pass
