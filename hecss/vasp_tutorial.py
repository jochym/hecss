"""Generated from notebooks/vasp_tutorial.py by build.py"""

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

N = 4

N_1 = 10

T = 300

T_1 = 600

T_1000 = np.array([s[-1] for s in c_1000]).mean()

base_dir = f'example/VASP_3C-SiC/{supercell_2}/'

c_1000 = hecss.sample(1000, 50)

calc = Vasp(label='cryst', directory=f'{base_dir}/sc_{supercell_2}/', restart=True)

calc_dir = f'TMP/calc_{supercell_2}'

confs_600 = hecss.sample(T_1, 50)

cryst = calc.atoms.repeat(1)

distrib = hecss.generate(samples, T)

fit = np.polyfit(wm[1], y, 1)

hecss = HECSS(cryst, calc,
                  directory=f'{calc_dir}',
                  w_search=True,
                  pbar=True)

s_1000 = hecss.generate(c_1000, 2*T_1000/un.kB/3, border=True, debug=True)

samples = hecss.sample(T, N)

samples_1 = samples + hecss.sample(T, N_1, sentinel=show_stats, sentinel_args={'col': samples, 'Temp': T})

samples_2 = samples_1 + hecss.sample(T, N_1, sentinel=show_stats, sentinel_args={'col': samples_1, 'Temp': T})

supercell = '1x1x1'

supercell_1 = '2x2x2'

supercell_2 = '1x1x1'

wm = np.array(hecss._eta_list).T

x = np.linspace(0, 1.05*wm[1].max(), 2)

xsl = []

y = np.sqrt((3*wm[1]*un.kB)/(2*wm[2]))

def show_stats(s, sl, col=None, Temp=None):
        from matplotlib import pyplot as plt
        from IPython.display import clear_output
        from hecss.optimize import make_sampling
        plot_stats(make_sampling(sl if col is None else col + sl, Temp),
                   Temp, show=False)
        plt.axvline(s[-1], ls=':', label='Last sample')
        plt.legend()
        plt.show()
        clear_output(wait=True)
        return False
