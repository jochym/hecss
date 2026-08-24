"""Generated from notebooks/core.py by build.py"""

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

_disp_dists = {
        'normal': stats.norm,
        'logistic': stats.logistic,
        'hypsecant': stats.hypsecant,
        'laplace': stats.laplace,
        'cauchy': stats.cauchy,
    }

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


# Apply patches from @patch decorators
from fastcore.basics import patch as _patch
@patch
def __get_calculator(self: HECSS):
    '''
    Produce a new calculator each time it is called.
    If constructor produces new calculator, just call it.
    Otherwise pass the calc attribute.
    '''
    return self.calc() if callable(self.calc) else self.calc


HECSS.__get_calculator = _patch(__get_calculator)
@patch
def _estimate_width_scale_ser(self: HECSS, n=1, Tmin=0, Tmax=600, set_scale=True, pbar=None):
    '''
    Serial version of w-estimator.
    Estimate coefficient between temperature and displacement scale (eta).
    '''
    from hecss.util import get_cell_data

    nat = len(self.cryst)
    dim = (nat, 3)

    cr = Atoms(self.cryst.get_atomic_numbers(),
               cell=self.cryst.get_cell(),
               scaled_positions=self.cryst.get_scaled_positions(),
               pbc=True,
               calculator=self.__get_calculator())

    while len(self._eta_list) < n:
        T = stats.uniform.rvs(Tmin, Tmax - Tmin)
        if not T:
            continue
        w = self.w_scale * np.sqrt(T)
        dx = self.Q.rvs(size=dim, scale=w)
        cr.set_positions(self.cryst.get_positions() + dx)
        try:
            cr.calc.set(directory=f'{self.directory}/w_est/{len(self._eta_list):03d}')
        except AttributeError:
            pass
        E = cr.get_potential_energy()
        if E <= self.Ep0:
            print('Undistorted supercell energy is above the distorted cell energy!', file=sys.stderr)
            print('Make sure the supercell is calculated as single point and with the same params.', file=sys.stderr)

        assert E > self.Ep0
        try:
            if not cr.calc.converged:
                print(f'The calculation in {cr.calc.directory} did not converge.', file=sys.stderr)
                print('Ignoring and replacing with new displacement.', file=sys.stderr)
                continue
        except AttributeError:
            pass

        i = len(self._eta_list)
        self._eta_samples.append((i, i, dx, cr.get_forces(), (E - self.Ep0) / nat))
        self._eta_list.append([w, T, (E - self.Ep0) / nat])

        if pbar:
            pbar.update()


HECSS._estimate_width_scale_ser = _patch(_estimate_width_scale_ser)
@patch
def estimate_width_scale(self: HECSS, n=1, Tmin=0, Tmax=600,
                         set_scale=True, pbar=None, nwork=None):
    """
    Estimate coefficient between temperature and displacement scale (eta).
    """
    from hecss.util import get_cell_data

    if self.Ep0 is None:
        self.Ep0 = self.cryst.get_potential_energy()
    E0 = self.Ep0
    close_pbar = False
    if self.pbar and pbar is None:
        pbar = tqdm(total=n)
        close_pbar = True
    if pbar:
        pbar.reset(n)
        pbar.set_postfix_str('eta estimation')
        if self._eta_list:
            pbar.update(len(self._eta_list))
    try:
        self._estimate_width_scale_aio(n, Tmin, Tmax, set_scale, pbar, nwork)
    except NotImplementedError:
        if nwork is not None:
            print('WARNING: Parallel execution only supported for VASP.')
            print('Running serial version')
        self._estimate_width_scale_ser(n, Tmin, Tmax, set_scale, pbar)
    wm = np.array(self._eta_list).T
    pathlib.Path(f'{self.directory}/w_est/').mkdir(parents=True, exist_ok=True)
    np.savetxt(f'{self.directory}/w_est/w_est.dat', wm.T,
               header=f'w, T, (E-E0)/nat ; Tmax: {Tmax} K ')
    y = np.sqrt(3 * wm[1] * un.kB / (2 * wm[2]))
    m = y.mean()
    dim = (len(self.cryst), 3)
    xscale = np.ones(dim)
    vir = np.array([abs(s[2] * s[3]) for s in self._eta_samples])
    vir = vir / vir.mean(axis=(-1, -2))[:, None, None]
    elems = self.cryst.get_chemical_symbols()
    for n, el in enumerate(set(elems)):
        elmask = np.array(elems) == el
        xscale[elmask] = 1 / np.sqrt(vir[:, elmask, :].mean())
    if pbar and close_pbar:
        pbar.close()
    if set_scale:
        self.eta = m
        self.xscale_init = xscale
    return (m, y.std(), xscale)


HECSS.estimate_width_scale = _patch(estimate_width_scale)
@patch
def _sampler_ser(self: HECSS, T_goal, N=None, delta_sample=0.01, sigma=2,
                 eqdelta=0.05, eqsigma=0.2, xi=1, chi=1,
                 modify=None, modify_args=None, symprec=1e-5,
                 width_list=None, dofmu_list=None, xscale_list=None,
                 verb=True):
    """
    The core sampling generator.
    """
    from hecss.util import get_cell_data

    if self._pbar:
        self._pbar.set_postfix_str('Initialization')
    nat = len(self.cryst)
    dim = (nat, 3)
    symm = get_symmetry_dataset(get_cell_data(self.cryst), symprec=symprec)
    dofmap = symm.mapping_to_primitive
    dof = list(sorted(set(dofmap)))
    dofmu = np.ones((len(dof), 3))
    mu = np.ones(dim)
    xscale = np.array(self.xscale_init)
    assert xscale.shape == dim
    dofxs = np.array([xscale[dofmap == d, :].mean(axis=0) for d in dof])
    assert dofxs.shape == dofmu.shape
    xi = max(0, xi)
    xi = min(1, xi)
    assert 0 <= xi <= 1
    chi = max(0, chi)
    chi = min(1, chi)
    assert 0 <= chi <= 1
    if self.Ep0 is None:
        self.Ep0 = self.cryst.get_potential_energy()
    Ep0 = self.Ep0
    E_goal = 3 * T_goal * un.kB / 2
    Es = np.sqrt(3 / 2) * un.kB * T_goal / np.sqrt(nat)
    eta = self.eta
    w = self.eta * self.w_scale * np.sqrt(T_goal)
    w_prev = w
    if width_list is None:
        wl = []
    else:
        wl = width_list
    Q = self.Q
    P = Q.pdf
    i = 0
    n = 0
    if self.directory is None:
        basedir = f'calc/T_{T_goal:.1f}K'
    else:
        basedir = f'{self.directory}/T_{T_goal:.1f}K'
    cr = Atoms(self.cryst.get_atomic_numbers(),
               cell=self.cryst.get_cell(),
               scaled_positions=self.cryst.get_scaled_positions(),
               pbc=True,
               calculator=self.calc() if callable(self.calc) else self.calc)
    try:
        cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
    except AttributeError:
        pass
    e = 0
    x = np.zeros(dim)
    f = np.zeros(dim)
    k = 0
    if self._pbar:
        self._pbar.set_postfix_str(f'sampling eta={self.eta:.3g}')
    while True:
        x_star = xscale * Q.rvs(size=dim, scale=w)
        assert x_star.shape == dim
        if verb and (n > 0 or k > 0):
            self.smpl_print()
        cr.set_positions(self.cryst.get_positions() + x_star)
        try:
            cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
        except AttributeError:
            pass
        try:
            if modify is not None:
                e_star, f_star = modify(cr, self.cryst, 's', *modify_args)
            else:
                e_star = cr.get_potential_energy()
                f_star = cr.get_forces()
                if not cr.calc.converged:
                    print(f'Calculator in {cr.calc.directory} did not converge.\n', file=sys.stderr)
                    print('Replacing with next displacement.', file=sys.stderr)
                    continue
        except AttributeError:
            pass
        except calculator.CalculatorError:
            print(f'Calculator in {cr.calc.directory} faild.\n', file=sys.stderr)
            print('Replacing with next displacement.', file=sys.stderr)
            continue
        e_star = (e_star - Ep0) / nat
        wl.append((w / (self.w_scale * np.sqrt(T_goal)), e_star))
        if i == 0:
            delta = 10 * delta_sample
        else:
            delta = delta_sample
        w_prev = w
        mu = np.abs(f_star * x_star) / (un.kB * T_goal)
        dofmu = np.array([mu[dofmap == d, :].mean(axis=0) for d in dof])
        dofxs *= (1 - 2 * eqdelta * (expit((np.sqrt(dofmu) - 1) / eqsigma) - 0.5))
        dofxs /= np.sqrt((dofxs ** 2).mean())
        xscale = chi * dofxs[dofmap] + xscale * (1 - chi)
        xscale = xi * xscale + np.ones(dim) - xi
        if xscale_list is not None:
            xscale_list.append(np.array(xscale))
        if dofmu_list is not None:
            dofmu_list.append(np.array(dofmu))
        if self.w_search:
            w = w * (1 - 2 * delta * (expit((e_star - E_goal) / Es / 3) - 0.5))
            eta = w / (self.w_scale * np.sqrt(T_goal))
            if i == 0 and abs(e_star - E_goal) > 3 * sigma * Es:
                k += 1
                if k > self.maxburn:
                    print(f'\nError: reached maxburn ({self.maxburn}) without finding target energy.\n' +
                          f'You probably need to change initial width parameter (current:{w})' +
                          f" to a {('higher' if (e_star - E_goal) < 0 else 'lower')} value.")
                    return
                if self._pbar:
                    self._pbar.set_postfix_str(f'w search: eta={eta:.3g} ({(e_star - E_goal) / (sigma * Es):.2g})')
                continue
        if i == 0:
            wl.clear()
        x = x_star
        e = e_star
        f = f_star
        i += 1
        n += 1
        if self._pbar:
            self._pbar.set_postfix_str(f'sampling eta={eta:.3g}')
        self.smpl_print()
        if self._pbar:
            self._pbar.update()
        yield (n, i - 1, x, f, e)
        if N is not None and n >= N:
            break


HECSS._sampler_ser = _patch(_sampler_ser)
@patch
def sample(self: HECSS, T, N, sentinel=None, sentinel_args={}, nwork=None, **kwargs):
    '''
    Generate N samples using `HECSS._sampler_(ser/aio)` generator.
    '''
    self._pbar = None
    if self.pbar:
        self._pbar = tqdm(total=N)
    if self.eta is None:
        width, sigma, xscale = self.estimate_width_scale(2, T, pbar=self._pbar)
        if sigma > width / 5:
            print(f'Warning: low accuracy eta estimation: {width:.2g}+/-{sigma:.2g}')
    smpls = []
    if self._pbar:
        self._pbar.reset(N)
    if T in self.samplers:
        generator = self.samplers[T]
    else:
        try:
            generator = self._sampler_aio(T, **kwargs, nwork=nwork)
        except NotImplementedError:
            generator = self._sampler_ser(T, **kwargs)
        self.samplers[T] = generator
    for smpl in generator:
        smpls.append(smpl)
        if sentinel is not None and sentinel(smpl, smpls, **sentinel_args):
            break
        if len(smpls) >= N:
            break
    if self._pbar:
        self._pbar.close()
        self._pbar = None
    return smpls


HECSS.sample = _patch(sample)
@patch
def generate(self: HECSS, S, T=None, sigma_scale=1.0, border=False, probTH=0.25,
             Nmul=4, N=None, nonzero_w=True, debug=False):
    '''
    Generate new sample with normal energy probability distribution
    corresponding to temperature `T` and size of the system inferred
    from data.
    '''
    from hecss.optimize import make_sampling

    if T is None:
        T = 2 * np.mean([s[-1] for s in S]) / 3 / un.kB
    return make_sampling(S, T, sigma_scale=sigma_scale, border=border, probTH=probTH,
                         Nmul=Nmul, N=N, nonzero_w=nonzero_w, debug=debug)


HECSS.generate = _patch(generate)
del _patch

__all__ = ["HECSS", "_disp_dists"]