"""Generated from notebooks/vasp_workflow.py by build.py"""

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

N = 5

N_1 = 30

T_list = (100, 200, 300)

base_dir = f'example/VASP_3C-SiC/{supercell_2}/'

calc = Vasp(label='cryst', directory=f'{base_dir}/sc_{supercell_2}/', restart=True)

calc_dir = TemporaryDirectory(dir='TMP')

cryst = calc.atoms.repeat(1)

fit = np.polyfit(wm[1], y, 1)

hecss = HECSS(cryst, calc,
                  directory=calc_dir.name,
                  w_search=True,
                  pbar=True)

samples = defaultdict(lambda: [])

supercell = '1x1x1'

supercell_1 = '2x2x2'

supercell_2 = '1x1x1'

wm = np.array(hecss._eta_list).T

x = np.linspace(0, 1.05*wm[1].max(), 2)

xsl = []

y = np.sqrt((3*wm[1]*un.kB)/(2*wm[2]))
