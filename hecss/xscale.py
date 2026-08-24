"""Generated from notebooks/xscale.py by build.py"""

from __future__ import annotations

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
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset

def plot_virial_stat(cryst, smpl, normal=True):
        elems = cryst.get_chemical_symbols()
        elmap = cryst.get_atomic_numbers()
        vir = np.array([abs(s[2] * s[3]) for s in smpl])
        vir = vir / vir.mean(axis=(-1, -2))[:, None, None]
        nat = len(elems)
        xscale = np.ones(cryst.get_positions().shape)
        mi = 1
        ma = 1
        for n, el in enumerate(sorted(set(elems))):
            elmask = np.array(elems) == el
            m, s = plot_hist(1 / np.sqrt(vir[:, elmask, :].mean(axis=(-1, -2))), el, n + 1, normal=normal, df=3 * sum(elmask))
            if mi > m - 3 * s:
                mi = m - 3 * s
            if ma < m + 3 * s:
                ma = m + 3 * s
            xscale[elmask] = m
        plt.axvline(1, ls=':', color='C5', label='Equilibrium')
        plt.xlim(mi, ma)
        plt.legend()
        plt.title('Normalized Virial distribution in the sample')
        plt.ylabel('Probability density')
        plt.xlabel('Normalized Virial')
        return xscale


__all__ = ["plot_virial_stat"]