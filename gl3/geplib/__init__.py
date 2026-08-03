# -*- coding: utf-8 -*-
"""
geplib - GEometrie Prostorova LIBrary.

Prostorove (3D) GL3 prikazy/operace, ktere nejsou soucasti puvodni
Fortran GERLIBPC knihovny (ta byla čistě rovinna) - DCOOS3, TRA23, Q00,
U00, a dalsi prostorove operace, jak pribudou.

Vyuziva zakladni geometricke typy (Point/Vector/Line/Spline) primo z
gerlib.types - ty zustavaji JEDNOTNE sdilene pro 2D i 3D pouziti (viz
gerlib/__init__.py docstring - Point/Vector uz vzdy nesou x,y,z, rozdil
mezi 2D (P/V) a 3D (Q/U) je jen jazykova konvence GL3 prefixu jmena
promenne, ne rozdilny Python typ).

Kazda operace ma svuj vlastni soubor pojmenovany podle GL3 prikazu/
opcode (dcoos3.py, tra23.py, q00.py, u00.py, ...) - stejna konvence
jako gerlib.

Pouziti:
    from geplib import define_coord_system3, transform3, make_point3, make_vector3
"""

from .dcoos3 import CoordSystem3, define_coord_system3
from .tra23 import (
    transform3, transform_point3, transform_vector3, transform_spline3, transform_curve3,
)
from .q00 import make_point3
from .u00 import make_vector3

__all__ = [
    "CoordSystem3", "define_coord_system3",
    "transform3", "transform_point3", "transform_vector3", "transform_spline3",
    "transform_curve3",
    "make_point3", "make_vector3",
]
