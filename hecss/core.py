"""Generated from notebooks/core.py by build_package.py"""

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

class HECSS:
        '''
        Class encapsulating the sampling and weight generation
        for the HECSS algorithm.

        Create the HECSS sampling object. It is intendet to be a single object
        per crystal `cryst` used to run samplers for one or more temperatures.
        The object holds data common to all samplers (structure, calculator etc.).
        The other parameters are set per sampler. The set of samplers, indexed
        by temperature is hold inside the `samplers` dictionary.

        #### Arguments

        * cryst : crystal structure (ASE `Atoms` object)
        * calc  : calculator, must be re-usable, otherwise must be calculator generator
        * width : eta, displacement scaling parameter, approx 1.0
        * maxburn : max. number of initial burn-in samples
        * w_search : use width/eta searching algorithm (default True)
        * disp_dist : use different distribution instead of `stats.norm`
                       as the displacement distribution.
        * directory : basic calculation directory used by directory based calculators
        * pbar : show progress bar during calculations

        '''

        def __init__(self, cryst, calc, width=None, maxburn=20, w_search=True,
                     disp_dist='normal', directory=None, pbar=False):

            self.cryst = cryst
            self.calc = calc
            self.Ep0 = None
            self.maxburn = maxburn
            self.w_search = w_search
            if directory is None:
                self.directory = f'calc'
            else:
                self.directory = directory
            self._eta_list = []
            self._eta_samples = []
            self.w_scale = 1e-3  # Overall scale in w(T) function (Ang/sqrt(K))
            self.eta = width  # width = eta * w_scale sqrt(T)
            self.xscale_init = np.ones((len(self.cryst), 3))

            self.Q = stats.norm
            try:
                self.Q = _disp_dists[disp_dist]
            except KeyError:
                print(f'Warning: {disp_dist} displacement distribution not supported.\n'
                      'Keeping normal displacement distribution')

            self.pbar = None
            self._pbar = None
            if pbar is not None:
                self.pbar = pbar

            self.samplers = {}

        def smpl_print(self):
            return
            max_r = 15
            if pbar:
                if i == 0:
                    pbar.set_postfix(Sample='burn-in', n=k, w=w,
                                     dE=f'{(e_star - E_goal) / Es:+6.2f} sigma',
                                     xs=f'{sqrt(xscale.std()):6.3f}')
                else:
                    pbar.set_postfix(xs=f'{sqrt(xscale.std()):6.3f}', config=f'{i:04d}',
                                     w=w, w_bar=f'{np.mean([_[0] for _ in wl]) if wl else w:7.3f}')
            elif pbar is None:
                if i == 0:
                    print(f'Burn-in sample {sqrt(xscale.std()):6.3f}:{k}'
                          f'  w:{w:.4f}'
                          f'  dE:{(e_star - E_goal) / Es:+6.2f} sigma', end='\n')
                else:
                    print(f'Sample {sqrt(xscale.std()):6.3f}:{n:04d}'
                          f'w:{w:.4f}  <w>:{np.mean([_[0] for _ in wl]) if wl else w:.4f}', end='\n')
                sys.stdout.flush()
            else:
                pass

        def print_xs(self, c, s):
            return
            elmap = c.get_atomic_numbers()
            for el in sorted(set(elmap)):
                print(f'{chemical_symbols[el]:2}: {s[elmap == el, :].mean():8.4f}', end='  ')
            print()

__all__ = ["HECSS"]