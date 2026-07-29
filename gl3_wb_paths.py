# -*- coding: utf-8 -*-
"""
gl3_wb_paths.py - pomocny modul jen pro spolehlive zjisteni cesty ke
slozce workbenche.

InitGui.py/Init.py FreeCAD spousti primo (execfile-like mechanismus, ne
pres normalni import), takze v nich NEMUSI byt k dispozici __file__ -
znamy dlouhodoby limit FreeCADu (viz napr.
forum.freecad.org/viewtopic.php?t=646 a
wiki.freecad.org/Translating_an_external_workbench, sekce o hledani
cesty k translations/ slozce).

Tenhle soubor je ale BEZNE IMPORTOVANY modul (ne exec'd primo), takze
jeho __file__ je vzdy spolehlivy - pouziva se proto jako obchvat.
"""
import os

WB_DIR = os.path.dirname(os.path.abspath(__file__))
