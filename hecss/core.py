# AUTOGENERATED! DO NOT EDIT! File to edit: 11_core.ipynb (unless otherwise specified).

__all__ = ['write_dfset', 'calc_init_xscale', 'HECSS_Sampler', 'HECSS', 'normalize_conf']

# Cell
import sys
import ase
import ase.units as un
from ase.calculators import calculator
import scipy
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from spglib import find_primitive, get_symmetry_dataset
import spglib
from collections import Counter
from ase.data import chemical_symbols
from matplotlib import pyplot as plt

# Cell
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

# Cell
def calc_init_xscale(cryst, xsl, skip=None):
    from numpy import array, ones
    elmap = cryst.get_atomic_numbers()
    if skip is not None:
        skip = min(skip, len(xsl)//2)
    xs = array(xsl)[skip:]
    xscale = ones(xs[0].shape)
    for i, el in enumerate(set(elmap)):
        xscale[elmap==el] = xs[skip:,elmap==el,:].mean()
    return xscale

# Cell
def HECSS_Sampler(cryst, calc, T_goal, width=1, maxburn=20,
            N=None, w_search=True, delta_sample=0.01, sigma=2,
            eqdelta=0.05, eqsigma=0.2,
            xi=1, chi=1, xscale_init=None,
            Ep0=None, modify=None, modify_args=None, symprec=1e-5,
            directory=None, reuse_base=None, verb=True, pbar=None,
            priors=None, posts=None, width_list=None,
            dofmu_list=None, xscale_list=None):
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
    cryst        : ASE structure to sample
    calc         : ASE calculator to use for potential energy evaluations
    T_goal       : Target temperature in Kelvin
    width        : initial width of the position distribution, relative
                   to the heurestic value defined inside function
    maxburn      : max number of burn-in steps
    N            : Number of iterations. If None (default) the generator never stops.
    w_search     : Run search for initial w. If false start from whatever
                   is passed as width.
    delta_sample : Prior width adaptation rate. The default is sufficient in most cases.
    sigma        : Range around E0 in sigmas to stop w-serach mode
    xi           : strength of the amplitude correction term [0-1]
    chi          : strength of the amplitude correction term mixing [0-1]
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
    pbar         : tqdm progress bar object. If None (default) there will be no output.

    **Output parameters**

    priors       : Output parameter. If not None, store in passed list the sequence of priors.
    posts        : Output parameter. If not None, store in passed list the sequence of posteriors.
    width_list   : Output parameter. If not None, store in passed list the sequence of widths.
    xscale_list  : Output parameter. If not None, store in passed list the array of xscales (normalized).

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

    if pbar:
        pbar.set_postfix(Sample='initial')

    def smpl_print(r=0):
        max_r = 15
        if pbar:
            if i==0:
                pbar.set_postfix(Sample='burn-in', n=k, w=w, alpha=alpha, dE=f'{(e_star-E_goal)/Es:+6.2f} sigma', xs=f'{xscale.std():6.3f}')
            else :
                pbar.set_postfix(xs=f'{sqrt(xscale.std()):6.3f}', config=f'{i:04d}', a=f'{100*i/n:5.1f}%', w=w,
                                 w_bar=f'{np.mean([_[0] for _ in wl]) if wl else w:7.3f}',
                                 alpha=f'{alpha:7.1e}', rej=f'{r:4d}')
        elif pbar is None :
            if i==0:
                print(f'Burn-in sample {sqrt(xscale.std()):6.3f}:{k}  w:{w:.4f}  alpha:{alpha:7.1e}  dE:{(e_star-E_goal)/Es:+6.2f} sigma', end='\n')
            else :
                print(f'Sample {sqrt(xscale.std()):6.3f}:{n:04d}  a:{100*i/n:5.1f}%  w:{w:.4f}  <w>:{np.mean([_[0] for _ in wl]) if wl else w:.4f}'
                      +  f' alpha:{alpha:10.3e} ' + f' rej:{r:d}', end='\n')
            sys.stdout.flush()
        else :
            pass


    def print_xs(c, s):
        elmap = c.get_atomic_numbers()
        for el in sorted(set(elmap)):
            print(f'{chemical_symbols[el]:2}: {s[elmap==el,:].mean():8.4f}', end='  ')
        print()


    nat = len(cryst)
    dim = (nat, 3)

    symm = get_symmetry_dataset(cryst, symprec=symprec)
    dofmap = symm['mapping_to_primitive']
    dof = list(sorted(set(dofmap)))
    dofmu = np.ones((len(dof), 3))
    mu = np.ones(dim)

    if xscale_init is None:
        xscale = np.ones(dim)
    else :
        xscale = np.array(xscale_init)
        assert xscale.shape == dim

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
            Ep0 = cryst.get_potential_energy()

    E_goal = 3*T_goal*un.kB/2
    Es = np.sqrt(3/2)*un.kB*T_goal/np.sqrt(nat)

    P = stats.norm.pdf
    Q = stats.norm

    # This comes from the fitting to 3C-SiC case
    w_scale = 1.667e-3 * (T_goal**0.5) #(T_goal**0.47)

    w = width
    w_prev = w

    if width_list is None :
        wl = []
    else :
        wl = width_list

    if priors is None:
        priors = []

    if posts is None:
        posts = []

    i = 0
    n = 0

    if directory is None :
        basedir = f'calc/T_{T_goal:.1f}K'
    else :
        basedir = directory

    cr = ase.Atoms(cryst.get_atomic_numbers(),
                   cell=cryst.get_cell(),
                   scaled_positions=cryst.get_scaled_positions(),
                   pbc=True, calculator=calc)

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
    r = 0
    alpha = 0
    prior_len=0
    pfit = None

    if pbar:
        pbar.set_postfix(Sample='burn-in')

    while True:

        # print_xs(cryst, xscale)
        #x_star =  Q.rvs(size=dim, scale=w * w_scale * xscale)
        x_star = xscale * Q.rvs(size=dim, scale=w * w_scale)

        assert x_star.shape == dim

        if verb and (n>0 or k>0):
            smpl_print(r)

        cr.set_positions(cryst.get_positions()+x_star)
        try :
            cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
        except AttributeError :
            pass

        try :
            if modify is not None:
                e_star, f_star = modify(cr, cryst, 's', *modify_args)
            else:
                e_star = cr.get_potential_energy()
                f_star = cr.get_forces()
        except calculator.CalculatorError:
            print(f"Calculator in {cr.calc.directory} faild.\n", file=sys.stderr)
            print("Ignoring. Generating next displacement.", file=sys.stderr)
            continue

        e_star = (e_star-Ep0)/nat

        wl.append((w,e_star))

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

        if w_search :
            w = w*(1-2*delta*(expit((e_star-E_goal)/Es/3)-0.5))
            if i==0 and abs(e_star-E_goal) > sigma*Es :
                # We are in w-search mode but still far from E_goal
                # Continue
                k += 1
                if k>maxburn :
                    print(f'\nError: reached maxburn ({maxburn}) without finding target energy.\n'+
                        f'You probably need to change initial width parameter (current:{w})' +
                        f' to a {"higher" if (e_star-E_goal)<0 else "lower"} value.')
                    return
                # Continue searching for proper w
                # print(f'{w=} ({abs(e_star-E_goal)/(sigma*Es)}). Continue searching')
                continue

        priors.append((n, i, x_star, f_star, e_star))

        if i==0 :
            # We are in w-search mode and just found a proper w
            # switch to sampling mode by making sure the sample is accepted
            # 2 is larger than any result of np.random.rand()
            alpha = 2
            # clean up the w table
            wl.clear()
            prior_len=1
        else :
            # Sampling mode
            alpha = P(e_star, E_goal, Es) / P(e, E_goal, Es)

            if len(priors) > 3 :
                # There is no sense in fitting priors to normal dist if we have just 2-3 samples
                # The 4 samples is still rather low but seems to work well enough
                # On the first visit here len(priors)>3 and prior_len==1
                # Thus, the pfit will be initialized before first use  below.
                if  len(priors) > 1.1*prior_len:
                    # Re-fit the prior only if we get 10% more samples
                    pfit = Q.fit([_[-1] for _ in priors])
                    prior_len = len(priors)

                assert pfit is not None
                # Take into account estimated transition probability
                alpha *= Q.pdf(e, *pfit)/Q.pdf(e_star, *pfit)


        if np.random.rand() < alpha:
            x = x_star
            e = e_star
            f = f_star
            i += 1
            r = 0
        else:
            # Sample rejected - stay put
            r += 1

        n += 1

        smpl_print(r)
        if pbar:
            pbar.update()

        if posts is not None :
            posts.append((n, i-1, x, f, e))

        yield n, i-1, x, f, e

        if N is not None and n > N:
            break

    if pbar:
        pbar.close()

# Cell
class HECSS:
    '''
    Class facilitating more traditional use of the `HECSS_Sampler` generator.
    '''
    def __init__(self, cryst, calc, T_goal, width=1, maxburn=20,
                 N=None, w_search=True, delta_sample=0.01, sigma=2,
                 eqdelta=0.05, eqsigma=0.2,
                 xi=1, chi=1, xscale_init=None,
                 Ep0=None, modify=None, modify_args=None,
                 directory=None, reuse_base=None, verb=True,
                 pbar=True, priors=None, posts=None, width_list=None,
                 dofmu_list=None, xscale_list=None):
        if pbar is True:
            self.pbar = tqdm(total=N)
        else:
            self.pbar = pbar
        self.N=N
        self.total_N=0
        self.T=T_goal
        self.sampler = HECSS_Sampler(cryst, calc, T_goal,
                                     width=width, maxburn=maxburn,
                                     w_search=w_search,
                                     delta_sample=delta_sample,
                                     sigma=sigma,
                                     eqdelta=eqdelta, eqsigma=eqsigma,
                                     xi=xi, chi=chi,
                                     xscale_init=xscale_init,
                                     Ep0=Ep0, modify=modify, modify_args=modify_args,
                                     pbar=self.pbar,
                                     directory=directory,
                                     reuse_base=reuse_base, verb=verb,
                                     priors=priors, posts=posts,
                                     width_list=width_list,
                                     dofmu_list=dofmu_list,
                                     xscale_list=xscale_list)

    def generate(self, N=None, sentinel=None, **kwargs):
        '''
        Generate and return the list of N samples provided
        by the `HECSS_Sampler` generator in `self.sampler`.
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
        if N is None:
            N = self.N

        # This is a workaround for the miss-design of tqdm
        # where bool() for total==None returns error
        if self.pbar is not None and self.pbar is not False:
            self.pbar.reset(self.total_N + N)
            self.pbar.update(self.total_N)

        smpls = []
        for smpl in self.sampler:
            smpls.append(smpl)
            if sentinel is not None and sentinel(smpl, smpls, **kwargs):
                break
            if len(smpls) >= N:
                #self.pbar.close()
                break
        self.total_N += len(smpls)
        return smpls

# Cell
def normalize_conf(c, base):
    '''
    Normalize the configuration `c` relative to the basic structure `base`.
    Normalization is performed by "nuwrapping" the displacements of atoms
    when they cross the periodic boundary conditions in such a way that the
    atoms are not "jumping" from one side of the cell to the other.

    E.g. if the atom at r=(0,0,0) goes to the relative position (-0.01, 0, 0)
    it is "wrapped" by PBC to the r=(0.99, 0, 0). Thus if we naiively calculate
    the displacement we will get a large positive displacement (0.99 of the cell
    vector) instead of a small negative one.

    This function reverses that process making the positions suitable for
    differentiation. The positions may be part of a continous trajectory or
    just independent configurations. This makes it impossible for described
    procedure to work if the displacements are above 1/2 of the unit cell.
    For sefety this implementation is limited to displacements < 1/3 of the
    unit cell. If any coordinate changes by more then 1/3 the function
    will rise an AssertionError exception.

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

    # Return carthesian positions, fractional positions
    return dot(spos,cell), spos