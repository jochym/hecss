"""Generated from notebooks/monitor_bands.py by build.py"""

"Generated from notebooks/monitor_bands.py by build.py"

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.units import _hplanck, J
THz = 1e12 * _hplanck * J  # THz in eV
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
from numpy import loadtxt


def plot_band_set(bnd, units=THz, lbl=None, **kwargs):
        if lbl is None:
            lbl=''
        kwa = {k:v for k, v in kwargs.items() if k not in ('color',)}
        plt=plot(bnd[0], un.invcm * bnd[1] / units, label=lbl, **kwargs)
        for b in bnd[2:]:
            plot(bnd[0], un.invcm * b / units, color=plt[0].get_color(), **kwa)

def plot_bands(bnd, kpnts, units=THz, decorate=True, lbl=None, **kwargs):
        plot_band_set(bnd, units, lbl, **kwargs)

        lbls, pnts = kpnts

        if decorate:
            xticks(pnts, lbls)
            xlim(min(pnts), max(pnts))
            axhline(0,ls=':', lw=1, alpha=0.5)
            for p in sorted(pnts)[1:-1]:
                axvline(p, ls=':', lw=1, alpha=0.5)
            xlabel('Wave vector')
            ylabel('Frequency (THz)')

def plot_bands_file(fn, units=THz, decorate=True, lbl=None, **kwargs):
        bnd = loadtxt(fn).T

        with open(fn) as f:
            p_lbl = [l if l!='G' else '$\\Gamma$' for l in f.readline().split()[1:]]
            p_pnt = [float(v) for v in f.readline().split()[1:]]
        kpnts = (p_lbl, p_pnt)

        if lbl is None:
            lbl=fn

        plot_bands(bnd, kpnts, units, decorate, lbl, **kwargs)


__all__ = ["plot_band_set", "plot_bands", "plot_bands_file"]