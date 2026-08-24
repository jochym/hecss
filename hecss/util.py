"""Generated from notebooks/util.py by build.py"""

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

flatten = itertools.chain.from_iterable

def calc_init_xscale(cryst, xsl, skip=None):
        '''
        Calculate initial xscale amplitude correction coefficients 
        from the history exported from the previous calculation 
        (with `xscale_list` argument). 

        INPUT
        -----
        cryst : ASE structure 
        xsl   : List of amplitude correction coefficients. The shape of 
                each element of the list must be `cryst.get_positions().shape`
        skip  : Number of samples to skip at the start of the xsl list

        OUTPUT
        ------
        Array amplitude correction coefficients with shape the same as
        `cryst.get_positions().shape`. May be directly plugged into 
        `xscale_init` argument of `HECSS_Sampler` or `HECSS`.
        '''
        from numpy import array, ones
        elmap = cryst.get_atomic_numbers()
        if skip is not None:
            skip = min(skip, len(xsl)//2)
        xs = array(xsl)[skip:]
        xscale = ones(xs[0].shape)
        for i, el in enumerate(set(elmap)):
            xscale[elmap==el] = xs[:, elmap==el, :].mean()
        return xscale

def create_asap_calculator(model):    
        import asap3
        return asap3.OpenKIMcalculator(model)

def get_cell_data(cell):
        '''
        Create new spglib style of cell data from ase cell.
        '''

        lattice = array(cell.get_cell().T, dtype="double", order="C")
        positions = array(cell.get_scaled_positions(), dtype="double", order="C")
        numbers = array(cell.get_atomic_numbers(), dtype="intc")

        return (lattice, positions, numbers)

def get_dfset_len(fn):
        try:
            with open(fn) as dfset:
                return len([l for l in dfset if 'set:' in l])
        except FileNotFoundError:
            return 0

def load_dfset(fn):
        '''
        Load contents of the DFSET file and return dfset array
        '''
        N = get_dfset_len(fn)
        dfset = loadtxt(fn).reshape(N, -1, 6)
        nat = dfset.shape[1]

        confs = []
        sets = []
        es = []
        n = 0
        with open(fn) as dff:
            for l in dff:
                if 'set:' not in l:
                    continue
                s, _, c, _, e = l.split()[2:7]
                s = int(s)
                c = int(c)
                e = float(e)
                confs.append((n, c, 
                              dfset[n, :, :3]*un.Bohr, 
                              dfset[n, :, 3:]*un.Ry/un.Bohr, e))
                n += 1

        return confs

def normalize_conf(c, base):
        '''
        Normalize the configuration `c` relative to the basic structure `base`.
        Normalization is performed by "unwrapping" the displacements of atoms
        when they cross the periodic boundary conditions in such a way that the
        atoms are not "jumping" from one side of the cell to the other. 

        E.g. if the atom at r=(0,0,0) goes to the relative position (-0.01, 0, 0)
        it is "wrapped" by PBC to the r=(0.99, 0, 0). Thus if we naively calculate
        the displacement we will get a large positive displacement (0.99 of the cell 
        vector) instead of a small negative one. 

        This function reverses that process making the positions suitable for 
        differentiation. The positions may be part of a continuous trajectory or
        just independent configurations. This makes it impossible for described 
        procedure to work if the displacements are above 1/2 of the unit cell.
        For safety this implementation is limited to displacements < 1/3 of the 
        unit cell. If any coordinate changes by more then 1/3 the function
        will raise an AssertionError exception.

        This implementation is not suitable for tracking positions in the system
        with systematic drift (e.g. long MD trajectory with non-perfect momentum
        conservation). For stronger implementation suitable for such cases look
        at dxutils package.
        '''
        cell = base.get_cell()
        spos = c.get_scaled_positions()
        bspos = base.get_scaled_positions()

        # Unwrap the displacement relative to base
        sdx = spos - bspos
        sht = (sdx < -0.5)*1 - (sdx > 0.5)*1
        sdx += sht

        # Check if fractional displacements are below 1/3
        assert (abs(sdx) < 1/3).all()

        # Calculate unwrapped spos
        spos = bspos + sdx

        # Return cartesian positions, fractional positions
        return dot(spos, cell), spos

def select_asap_model(comp='SiC'):
        '''
        This simple function selects the latest *working* OpenKIM model
        containing `comp` in the name. Required since some models are 
        not loading properly and the names are not stable.
        OUTPUT
        ------
        Name of the model. If nothing is found returns None.
        '''
        import asap3
        models = []
        for pot in [pot for pot in asap3.OpenKIMavailable() if comp in pot]:
            try:
                calc = asap3.OpenKIMcalculator(pot)
                models.append(pot)
            except asap3.AsapError:
                pass
        if models:
            model = sorted(models, key=lambda m: m.split('_')[3])[-1]
        else:
            model = None
        return model

def write_dfset(fn, c, comment=''):
        '''
        Append displacement-force data from the conf to the fn file.
        The format is suitable for use as ALAMODE DFSET file.
        Optionally you can provide configuration number in n.
        File need not exist prior to first call. 
        If it does not it will be created.
        '''
        n, i, x, f, e = c
        with open(fn, 'at') as dfset:
            if comment:
                print('##', comment, file=dfset)
            print(f'# set: {n:04d} config: {i:04d}  energy: {e:8e} eV/at', file=dfset)
            for ui, fi in zip(x, f):
                print((3*'%15.7f ' + '     ' + 3*'%15.8e ') % 
                            (tuple(ui/un.Bohr) + tuple(fi*un.Bohr/un.Ry)), 
                            file=dfset)


__all__ = ["select_asap_model", "create_asap_calculator", "normalize_conf", "load_dfset", "get_dfset_len", "write_dfset", "calc_init_xscale", "get_cell_data", "flatten"]