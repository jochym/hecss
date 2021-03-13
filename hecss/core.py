# AUTOGENERATED! DO NOT EDIT! File to edit: 02_core.ipynb (unless otherwise specified).

__all__ = ['normalize_conf', 'write_dfset', 'HECSS_Sampler', 'HECSS']

# Cell
import sys
import ase
from ase import units
import scipy
from scipy import stats
from scipy.special import expit
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import ase.units as un
from tqdm.auto import tqdm
from itertools import islice

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
def HECSS_Sampler(cryst, calc, T_goal, width=1, maxburn=20,
            N=None, w_search=True, delta_sample=0.01,
            directory=None, reuse_base=None, verb=True, pbar=None,
            priors=None, posts=None, width_list=None):
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
    directory    : (only for VASP calculator) directory for calculations and generated samples.
                   If left as None, the `calc/{T_goal:.1f}K/` will be used and the generated
                   samples will be stored in the `smpl/{i:04d}` subdirectories.
    reuse_base   : (only for VASP calculator) None or the base calc directory for the ground
                   state config. If None the base will be recalculated at the start of the run.
                   If directory name - the energy from this dir will be reused as ground state
                   energy for the calculation. Be careful to have the same VASP setup in calc
                   and reuse_base, otherwise the ground state energy and distribution
                   will be wrong.
    verb         : print verbose progress messages for interactive use
    pbar         : tqdm progress bar object. If None (default) there will be no output.

    **Output parameters**

    priors       : Output parameter. If not None, store in passed list the sequence of priors.
    posts        : Output parameter. If not None, store in passed list the sequence of posteriors.
    width_list   : Output parameter. If not None, store in passed list the sequence of widths.

    OUTPUT
    ------
    The generator yields samples from the thermodynamic distribution at T=T_goal as tuples
    (number, index, displacement, forces, energy):

    - number       : sample number, always increasing
    - index        : integer numbering the samples in the `smpl` subdirectory. The index may
                   repeat if the sample must be repeated in the sequence.
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
                pbar.set_postfix(Sample='burn-in', n=k, w=w, alpha=alpha, dE=f'{(e_star-E_goal)/Es:+6.2f} sigma')
            else :
                pbar.set_postfix(config=f'{i:04d}', a=f'{100*i/n:5.1f}%', w=w,
                                 w_bar=np.mean([_[0] for _ in wl]) if wl else w,
                                 alpha=alpha, rej=(min(r,max_r)*'x') + (max_r-min(r,max_r))*' ')
        else :
            if i==0:
                print(f'Burn-in sample:{k}  w:{w:.4f}  alpha:{alpha:6.4e}  dE:{(e_star-E_goal)/Es:+6.2f} sigma', end='\n')
            else :
                print(f'Sample:{n:04d}  a:{100*i/n:5.1f}%  w:{w:.4f}  <w>:{np.mean([_[0] for _ in wl]) if wl else w:.4f}  alpha:{alpha:10.3e} ' + (min(r,max_r)*'x') + (max_r-min(r,max_r))*' ', end='\n')
            sys.stdout.flush()

    nat = cryst.get_global_number_of_atoms()
    dim = (nat, 3)

    if reuse_base is not None :
        calc0 = ase.calculators.vasp.Vasp2(label='base', directory=reuse_base, restart=True)
        Ep0 = calc0.get_potential_energy()
    else :
        Ep0 = cryst.get_potential_energy()

    E_goal = 3*T_goal*un.kB/2
    Es = np.sqrt(3/2)*un.kB*T_goal/np.sqrt(nat)

    P = stats.norm.pdf
    Q = stats.norm

    # This comes from the fitting to 3C-SiC case
    w_scale = 1.667e-3 * (T_goal**0.5) #(T_goal**0.47)

    w = width
    w_prev = w

    x = Q.rvs(size=dim, scale=w * w_scale  )

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

    cr = ase.Atoms(numbers = cryst.get_atomic_numbers(),
                   cell=cryst.get_cell(),
                   scaled_positions=cryst.get_scaled_positions(),
                   pbc=True, calculator=calc)

    if pbar:
        pbar.set_postfix(Sample='initial')

    cr.set_positions(cryst.get_positions()+x)
    try :
        cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
    except AttributeError :
        pass

    e = (cr.get_potential_energy()-Ep0)/nat
    f = cr.get_forces()

    k = 0
    r = 0
    alpha = 0

    if pbar:
        pbar.set_postfix(Sample='burn-in')

    while N is None or n < N:
        if verb and (n>0 or k>0):
            smpl_print(r)

        x_star = Q.rvs(size=dim, scale=w * w_scale )

        cr.set_positions(cryst.get_positions()+x_star)
        try :
            cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
        except AttributeError :
            pass

        e_star = (cr.get_potential_energy()-Ep0)/nat
        f_star = cr.get_forces()

        wl.append((w,e_star))

        if i==0 :
            delta = 0.05
        else :
            delta = delta_sample
        w_prev = w

        if w_search :
            w = w*(1-2*delta*(expit((e_star-E_goal)/Es/3)-0.5))
            if i==0 and abs(e_star-E_goal) > Es :
                # We are in w-search mode but still far from E_goal
                # Continue
                k += 1
                if k>maxburn :
                    print(f'\nError: reached maxburn ({maxburn}) without finding target energy.\n'+
                        f'You probably need to change initial width parameter (current:{w})' +
                        f' to a {"higher" if (e_star-E_goal)<0 else "lower"} value.')
                    return
                # Continue searching for proper w
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
                if  len(priors) > 1.1*prior_len:
                    # Re-fit the prior only if we get 10% more samples
                    pfit = stats.norm.fit([_[-1] for _ in priors])
                    prior_len = len(priors)

                # Take into account estimated transition probability
                alpha *= stats.norm.pdf(e, *pfit)/stats.norm.pdf(e_star, *pfit)

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

    if pbar:
        pbar.close()

# Cell
class HECSS:
    '''
    Class facilitating more traditional use of the `HECSS_Sampler` generator.
    '''
    def __init__(self, cryst, calc, T_goal, width=1, maxburn=20,
                 N=None, w_search=True, delta_sample=0.01,
                 directory=None, reuse_base=None, verb=True,
                 pbar=True, priors=None, posts=None, width_list=None):
        self.pbar = tqdm(total=N)
        self.pbar.disable = not pbar
        self.N=N
        self.total_N=0
        self.T=T_goal
        self.sampler = HECSS_Sampler(cryst, calc, T_goal,
                                     width=width, maxburn=maxburn,
                                     w_search=w_search,
                                     delta_sample=delta_sample,
                                     pbar=self.pbar,
                                     directory=directory,
                                     reuse_base=reuse_base, verb=verb,
                                     priors=priors, posts=posts, width_list=width_list)

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