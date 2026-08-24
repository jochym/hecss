"""Generated from notebooks/parwidth.py by build.py"""

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

CLEANUP = False

Ep0 = calc.get_potential_energy()

N = 10

base_dir = f'example/VASP_3C-SiC_calculated/{supercell_2}/'

calc = Vasp(label='cryst', directory=f'{base_dir}/sc/', restart=True)

calc_dir = TemporaryDirectory(dir='TMP')

cryst = calc.atoms.repeat(1)

fit = np.polyfit(wm[1], y, 1)

hecss = HECSS(cryst, calc,
                  directory=calc_dir.name,
                  w_search=True,
                  pbar=True)

rm = np.array([y_1[:l].mean() for l in range(1, len(y_1))])

rv = np.array([y_1[:l].std() for l in range(1, len(y_1))])

samples = defaultdict(lambda: [])

supercell = '1x1x1'

supercell_1 = '2x2x2'

supercell_2 = '1x1x1'

wm = np.array(hecss._eta_list).T

wm_1 = np.array(hecss._eta_list).T

x = np.linspace(0, 1.05 * wm[1].max(), 2)

xsl = []

y = np.sqrt(3 * wm[1] * un.kB / (2 * wm[2]))

y_1 = np.sqrt(3 * wm_1[1] * un.kB / (2 * wm_1[2]))


# Apply patches from @patch decorators
from fastcore.basics import patch as _patch
del _patch