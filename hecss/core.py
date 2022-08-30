# AUTOGENERATED! DO NOT EDIT! File to edit: ../11_core.ipynb.

# %% auto 0
__all__ = ['HECSS', 'write_dfset', 'calc_init_xscale']

# %% ../11_core.ipynb 3
import sys
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
import spglib
from spglib import find_primitive, get_symmetry_dataset

from hecss.util import select_asap_model

# %% ../11_core.ipynb 4
class HECSS:
    '''
    Class encapsulating the sampling and weight generation 
    for the HECSS algorithm.
    '''
    def __init__(self, cryst, calc, maxburn=20, 
                 delta_sample=0.01, sigma=2,
                 eqdelta=0.05, eqsigma=0.2,
                 xi=1, chi=1, 
                 width=None, 
                 w_search=True,
                 xscale_init=None,
                 logistic_dist = False,
                 Ep0=None, modify=None, modify_args=None,
                 directory=None, reuse_base=None, verb=True, 
                 pbar=False, width_list=None, 
                 dofmu_list=None, xscale_list=None, monitor=None):
        self.cryst = cryst
        self.calc = calc
        self.maxburn = maxburn
        self.w_search = w_search
        self.directory = directory
        self.w_list = []
        self.w_scale = 1e-3 # Overall scale in w(T) function (Ang/sqrt(K))
        self.eta = width # width = eta * w_scale sqrt(T)
        
        if logistic_dist:
            self.Q = stats.logistic
        else:
            self.Q = stats.norm

        self.pbar = None
        self._pbar = None
        if pbar is not None:
            self.pbar = pbar
            
        self.samplers = {}
        
    def smpl_print(self):
        return
        max_r = 15
        if pbar:
            if i==0:
                pbar.set_postfix(Sample='burn-in', n=k, w=w,
                                 dE=f'{(e_star-E_goal)/Es:+6.2f} sigma', 
                                 xs=f'{sqrt(xscale.std()):6.3f}')
            else :
                pbar.set_postfix(xs=f'{sqrt(xscale.std()):6.3f}', config=f'{i:04d}', 
                                 w=w, w_bar=f'{np.mean([_[0] for _ in wl]) if wl else w:7.3f}')
        elif pbar is None :
            if i==0:
                print(f'Burn-in sample {sqrt(xscale.std()):6.3f}:{k}'
                      f'  w:{w:.4f}'
                      f'  dE:{(e_star-E_goal)/Es:+6.2f} sigma', end='\n')
            else :
                print(f'Sample {sqrt(xscale.std()):6.3f}:{n:04d}'
                      f'w:{w:.4f}  <w>:{np.mean([_[0] for _ in wl]) if wl else w:.4f}', end='\n')
            sys.stdout.flush()
        else :
            pass

        
    def print_xs(self, c, s):
        return
        elmap = c.get_atomic_numbers()
        for el in sorted(set(elmap)):
            print(f'{chemical_symbols[el]:2}: {s[elmap==el,:].mean():8.4f}', end='  ')
        print()
        
    

# %% ../11_core.ipynb 5
@patch 
def estimate_width_scale(self: HECSS, n=1, Tmax=600, set_scale=True, wm_out=False, pbar=None):
    '''
    Estimate coefficient between temperature and displacement scale (eta).
    Calculate energy increase from the `n` temperatures uniformly 
    distributed between 0 and `Tmax` and calculate avarage $\sqrt{E-E0/T}$
    which is a width scale for a given temperature:
    $$
        w = \\alpha\\sqrt{T}
    $$
    which comes from the assumed approximate relationship:
    $$
        \\frac{E(w(T))-E_0}{T} \\approx \\mathrm{const} = \\alpha^2.
    $$
    
    '''

    E0 = self.cryst.get_potential_energy()
    nat = len(self.cryst)
    dim = (nat, 3)    
    
    if self.directory is None :
        basedir = f'calc'
    else :
        basedir = self.directory
        
    cr = ase.Atoms(self.cryst.get_atomic_numbers(), 
                   cell=self.cryst.get_cell(),
                   scaled_positions=self.cryst.get_scaled_positions(),
                   pbc=True, 
                   calculator= self.calc() if callable(self.calc) 
                                           else self.calc)
    close_pbar = False
    
    if self.pbar and pbar is None:
        pbar = tqdm(total=n)
        close_pbar = True
    
    if pbar:
        pbar.reset(n)
        pbar.set_postfix_str('eta estimation')
        if self.w_list:
            pbar.update(len(self.w_list))
        
    while len(self.w_list) < n:
        T = stats.uniform.rvs(0, Tmax) # Kelvin
        if not T:
            continue
        w = self.w_scale * np.sqrt(T)
        dx = self.Q.rvs(size=dim, scale=w)
        cr.set_positions(self.cryst.get_positions()+dx)
        try :
            cr.calc.set(directory=f'{basedir}/w_est/{len(self.w_list):03d}')
        except AttributeError :
            # Calculator is not directory-based
            # Ignore the error
            pass
        E = cr.get_potential_energy()
        self.w_list.append([w, T, (E-E0)/nat])
        if pbar:
            pbar.update()

    wm = np.array(self.w_list).T
    y = np.sqrt((3*wm[1]*un.kB)/(2*wm[2]))
    m = y.mean()
    
    if pbar and close_pbar:
        pbar.close()
    
    if set_scale:
        self.eta = m
        
    if wm_out:
        return m, y.std(), wm
    else :
        return m, y.std()

# %% ../11_core.ipynb 6
@patch
def _sampler(self: HECSS, T_goal, N=None, 
           delta_sample=0.01, sigma=2,
           eqdelta=0.05, eqsigma=0.2,
           xi=1, chi=1, xscale_init=None,
           Ep0=None, modify=None, modify_args=None, symprec=1e-5,
           reuse_base=None, verb=True,
           width_list=None, dofmu_list=None, xscale_list=None):
    '''
    Run HECS sampler on the system `cryst` using calculator `calc` at target
    temperature `T_goal`. The `delta`, `width`, `maxburn` and `directory` 
    parameters determine detailed aspects of the algorithm.

    This is a generator and cannot be used as regular function. 
    It is intended to be used as a source of the sequence of 
    configurations in the `for` loop and must be closed after 
    finishing the iteration. On the other hand, the iteration 
    may be continued if additional samples are required. 
    The state is preserved until the .close() method is called.
    
    INPUT
    -----
    T_goal       : Target temperature in Kelvin
    width        : initial width of the position distribution, relative 
                   to the heurestic value defined inside function                  
    maxburn      : max number of burn-in steps
    N            : Number of iterations. If None (default) the generator never stops.
    w_search     : Run search for initial w. If false start from whatever 
                   is passed as width.
    delta_sample : Prior width adaptation rate. The default is sufficient in most cases.
    sigma        : Range around E0 in sigmas to stop w-serach mode
    eqdelta      : Max. speed of amplitude correction from step to step (0.05=5%)
    eqsigma      : Half width of linear part of amplitude correction function.
    xi           : strength of the amplitude correction term [0-1]
    chi          : strength of the amplitude correction term mixing [0-1]
    xscale_init  : Initial values of the amplitude correction coefficients.
                   Array with shape `cryst.get_positions().shape`.
                   May be generated with `calc_init_xscale` function.
    Ep0          : T=0 energy (base, no dstortions), if None (default) calculate E0.
    modify       : pass your own pre-processing function to modify the structure 
                   before calculation. The function must return a  (e, f) tuple
                   with energy of the structure (e, scalar) and forces (f, array).
    modify_args  : dictionary of extra arguments to pass to modify function
    symprec      : symmetry detection treshold for spglib functions
    directory    : (only for VASP calculator) directory for calculations and generated samples. 
                   If left as None, the `calc/{T_goal:.1f}K/` will be used and the generated 
                   samples will be stored in the `smpl/{i:04d}` subdirectories.
    reuse_base   : None or the base calculator created by restarting the ground 
                   state config. If None the base will be recalculated at the start of the run.
                   If the value is a calculator - the energy from this calculator will be used 
                   as ground state energy for the calculation. Be careful to have the same setup 
                   in calc and reuse_base, otherwise the ground state energy and distribution 
                   will be wrong.
    verb         : print verbose progress messages for interactive use
    pbar         : tqdm progress bar object. If False (default) there will be no output.
                   If set to None the display will be printed to stdout.
    
    **Output parameters**
    
    width_list   : Output parameter. If not None, store in passed list the sequence of widths.
    dofmu_list   : Output parameter. If not None, store in passed list the array of DOF virials
                   relative to temperature (T_goal).
    xscale_list  : Output parameter. If not None, store in passed list the array of amplitude 
                   correction coefficients (normalized). May be used to generate `xscale_init`
                   values with the help of `calc_init_xscale` function.

    OUTPUT
    ------
    The generator yields samples from the thermodynamic distribution at T=T_goal as tuples
    (number, index, displacement, forces, energy):
    
    - number       : sample number, always increasing
    - index        : integer numbering the samples in the `smpl` subdirectory. 
                     Index repeats if the sample must be repeated in the sequence. 
    - displacement : set of atomic displacements (in A) in the sample (numpy array)
    - forces       : set of forces (in eV/A) generated by the displacement
    - energy       : potential energy of the configuration

    '''    
    
    if self._pbar :
        self._pbar.set_postfix_str('Initialization')
        
    nat = len(self.cryst)
    dim = (nat, 3)
    
    symm = get_symmetry_dataset(self.cryst, symprec=symprec)
    dofmap = symm['mapping_to_primitive']
    dof = list(sorted(set(dofmap)))
    dofmu = np.ones((len(dof), 3))
    mu = np.ones(dim)

    if xscale_init is None:
        xscale = np.ones(dim)
    else :
        xscale = np.array(xscale_init)
        assert xscale.shape == dim
    
    # Initialise dofxs from data passed in xscale_init
    dofxs = np.array([xscale[dofmap==d,:].mean(axis=0) for d in dof])
    assert dofxs.shape == dofmu.shape
            
    xi = max(0,xi)
    xi = min(1,xi)

    assert 0 <= xi <= 1 
    
    chi = max(0,chi)
    chi = min(1,chi)

    assert 0 <= chi <= 1 
    
    if Ep0 is None:
        if reuse_base is not None:
            calc0 = reuse_base
            Ep0 = calc0.get_potential_energy()
        else:
            Ep0 = self.cryst.get_potential_energy()
    
    E_goal = 3*T_goal*un.kB/2
    Es = np.sqrt(3/2)*un.kB*T_goal/np.sqrt(nat)   
    
    eta = self.eta
    w = self.eta * self.w_scale * np.sqrt(T_goal) 
    w_prev = w

    if width_list is None :
        wl = []
    else :
        wl = width_list

    Q = self.Q
    P = Q.pdf
    
    i = 0
    n = 0
    
    if self.directory is None :
        basedir = f'calc/T_{T_goal:.1f}K'
    else :
        basedir = f'{self.directory}/T_{T_goal:.1f}K'

    cr = ase.Atoms(self.cryst.get_atomic_numbers(), 
                   cell=self.cryst.get_cell(),
                   scaled_positions=self.cryst.get_scaled_positions(),
                   pbc=True, 
                   calculator= self.calc() if callable(self.calc) else self.calc)
    
    try :
        cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
    except AttributeError :
        # Calculator is not directory-based
        # Ignore the error
        pass

    # Start from the equilibrium position
    e = 0
    x = np.zeros(dim)
    f = np.zeros(dim)
    
    k = 0
    
    if self._pbar:
        self._pbar.set_postfix_str(f'sampling eta={self.eta:.3g}')

    while True:

        # print_xs(cryst, xscale)
        #x_star =  Q.rvs(size=dim, scale=w * w_scale * xscale)
        x_star = xscale * Q.rvs(size=dim, scale=w)

        assert x_star.shape == dim        

        if verb and (n>0 or k>0):
            self.smpl_print()
        
        cr.set_positions(self.cryst.get_positions()+x_star)
        try :
            cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
        except AttributeError :
            pass

        try :
            if modify is not None:
                e_star, f_star = modify(cr, self.cryst, 's', *modify_args)
            else:
                e_star = cr.get_potential_energy()
                f_star = cr.get_forces()
        except calculator.CalculatorError:
            print(f"Calculator in {cr.calc.directory} faild.\n", file=sys.stderr)
            print("Ignoring. Generating next displacement.", file=sys.stderr)
            continue

        e_star = (e_star-Ep0)/nat
        
        wl.append((w/(self.w_scale*np.sqrt(T_goal)),e_star))

        if i==0 :
            # w-search mode
            delta = 10 * delta_sample
        else :
            # sampling mode
            delta = delta_sample

        w_prev = w

        # Equilibrate all degrees of freedom
        mu = np.abs(f_star*x_star)/(un.kB*T_goal)
        # mu = np.abs(f_star*x_star)/(np.abs(f_star*x_star).mean())
        
        # Avarage mu over images of the atom in the P.U.C.
        dofmu = np.array([mu[dofmap==d,:].mean(axis=0) for d in dof])

        # We use sqrt(mu) since the energy is quadratic in position
        # eqdelta = 0.05 => 5% maximum change in xscale from step to step
        # eqsigma = 0.2 => half width/sharpness of the sigmoid, 
        #                  roughly linear part of the curve
        dofxs *= (1-2*eqdelta*(expit((np.sqrt(dofmu)-1)/eqsigma)-0.5))
        
        # We need to normalize to unchanged energy ~ xs**2
        # The scale must be back linear in xs, thus sqrt(<xs>)
        dofxs /= np.sqrt((dofxs**2).mean())
        
        xscale = (chi * dofxs[dofmap] + xscale * (1 - chi))
        
        # mix with unity: (xi*xs + (1-xi)*1), 0 < xi < 1
        xscale = (xi*xscale + np.ones(dim) - xi) 

        if xscale_list is not None:
            xscale_list.append(np.array(xscale))

        if dofmu_list is not None:
            dofmu_list.append(np.array(dofmu))
        
        if self.w_search :
            w = w*(1-2*delta*(expit((e_star-E_goal)/Es/3)-0.5))
            eta = w/(self.w_scale*np.sqrt(T_goal))
            if i==0 and abs(e_star-E_goal) > sigma*Es :
                # We are in w-search mode but still far from E_goal
                # Continue
                k += 1
                if k>self.maxburn :
                    print(f'\nError: reached maxburn ({maxburn}) without finding target energy.\n'+
                        f'You probably need to change initial width parameter (current:{w})' +
                        f' to a {"higher" if (e_star-E_goal)<0 else "lower"} value.')
                    return
                # Continue searching for proper w
                if self._pbar:
                    self._pbar.set_postfix_str(f'w search: {eta=:.3g} ({(e_star-E_goal)/(sigma*Es):.2g})')
                continue

        if i==0 :
            # We are in w-search mode and just found a proper w
            # switch to sampling mode by cleaning up after the initial samples
            # clean up the w table
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

        yield n, i-1, x, f, e
        
        if N is not None and n >= N:
            # print('Generator terminated')
            break

# %% ../11_core.ipynb 7
@patch
def sample(self: HECSS, T, N, sentinel=None, sentinel_args={}, **kwargs):
        '''
        Generate N samples using `HECSS.sampler` generator.
        `sentinel` parameter is a call-back function 
        which is called on every sample to decide if the
        iteration should be stopped early. If it returns
        True the iteration will be stopped and the current 
        list of samples is returned. The sentinel is called
        *after* generating each sample (i.e. first time after 
        first sample is produced). This may take considerable 
        time at the start since first initial and burn-in 
        samples must be produced.
        '''
           
        # This is a workaround for the miss-design of tqdm 
        # where bool() for total==None returns error 
        # if self.pbar is not None and self.pbar is not False:
        #     self.pbar.reset(N)

        self._pbar = None
        if self.pbar:
            self._pbar = tqdm(total=N)
        
        if self.eta is None:
            width, sigma = self.estimate_width_scale(2, T, pbar=self._pbar)
            if sigma > width/5 :
                print(f'Warning: low accuracy eta estimation: {width:.2g}±{sigma:.2g}')
        
        smpls = []
        if self._pbar:
            self._pbar.reset(N)

        if T in self.samplers:
            generator = self.samplers[T]
        else :
            generator = self._sampler(T, **kwargs)
            self.samplers[T] = generator
            
        for smpl in generator:
            smpls.append(smpl)
            if sentinel is not None and sentinel(smpl, smpls, **sentinel_args):
                break
            if len(smpls) >= N:
                break
        # self.total_N += len(smpls)
        # print(kwargs)
        if self._pbar :
            self._pbar.close()
            self._pbar=None
        return smpls

# %% ../11_core.ipynb 8
from hecss.optimize import make_sampling

# %% ../11_core.ipynb 9
@patch
def generate(self: HECSS, S, T, N=None, nonzero_w=False, 
                                debug=False, N_bins=None):
    return make_sampling(S, T, N=N, nonzero_w=nonzero_w, 
                         debug=debug, N_bins=N_bins)

# %% ../11_core.ipynb 14
def write_dfset(fn, c):
    '''
    Append displacement-force data from the conf to the fn file.
    The format is suitable for use as ALAMODE DFSET file.
    Optionaly you can provide configuration number in n.
    File need not exist prior to first call. 
    If it does not it will be created.
    '''
    n, i, x, f, e = c
    with open(fn, 'at') as dfset:
        print(f'# set: {n:04d} config: {i:04d}  energy: {e:8e} eV/at', file=dfset)
        for ui, fi in zip(x,f):
            print((3*'%15.7f ' + '     ' + 3*'%15.8e ') % 
                        (tuple(ui/un.Bohr) + tuple(fi*un.Bohr/un.Ry)), 
                        file=dfset)

# %% ../11_core.ipynb 15
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
        xscale[elmap==el] = xs[:,elmap==el,:].mean()
    return xscale
