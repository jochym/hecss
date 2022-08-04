# AUTOGENERATED! DO NOT EDIT! File to edit: 14_optimize.ipynb (unless otherwise specified).

__all__ = ['HECSS_Sampler_TNG', 'make_sampling', 'get_sample_weights']

# Cell
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
from scipy import stats
from scipy.special import expit
from matplotlib import pylab as plt
import ase
import ase.units as un
from ase.build import bulk
from spglib import find_primitive, get_symmetry_dataset
import spglib
import asap3
from tqdm.auto import tqdm
from .core import select_asap_model
from .monitor import plot_stats
from .planner import plan_T_scan
from .core import HECSS_Sampler

# Cell
def HECSS_Sampler_TNG(cryst, calc, T_goal, width=1, maxburn=20,
            N=None, w_search=True, delta_sample=0.01, sigma=2,
            eqdelta=0.05, eqsigma=0.2,
            xi=1, chi=1, xscale_init=None,
            logistic_dist = True,
            Ep0=None, modify=None, modify_args=None, symprec=1e-5,
            directory=None, reuse_base=None, verb=True, pbar=False,
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

    if pbar:
        pbar.set_postfix(Sample='initial')

    def smpl_print():
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
            Ep0 = cryst.get_potential_energy()

    E_goal = 3*T_goal*un.kB/2
    Es = np.sqrt(3/2)*un.kB*T_goal/np.sqrt(nat)


    # This comes from the fitting to 3C-SiC case
    w_scale = 1.667e-3 * (T_goal**0.5) #(T_goal**0.47)

    w = width
    w_prev = w

    if width_list is None :
        wl = []
    else :
        wl = width_list

    if logistic_dist:
        Q = stats.logistic
        w_scale *= 0.5
        # adiust w scalling to the distro shape
    else:
        Q = stats.norm

    P = Q.pdf

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

    if pbar:
        pbar.set_postfix(Sample='burn-in')

    while True:

        # print_xs(cryst, xscale)
        #x_star =  Q.rvs(size=dim, scale=w * w_scale * xscale)
        x_star = xscale * Q.rvs(size=dim, scale=w * w_scale)

        assert x_star.shape == dim

        if verb and (n>0 or k>0):
            smpl_print()

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

        smpl_print()
        if pbar:
            pbar.update()

        yield n, i-1, x, f, e

        if N is not None and n > N:
            break

    if pbar:
        pbar.close()

# Cell
def make_sampling(data, T, sigma_scale=1.0, N=None, Nb=None, nonzero_w=False, debug=False):
    if N is None:
        N = 4*len(data)
    if Nb is None :
        Nb = min(len(data)//4, 15)
    # Use slightly (10%) wider sigma to compensate
    # for the missing tails below weight=1
    nat = data[0][2].shape[0]
    mu = 3*T*un.kB/2
    sigma = np.sqrt(3/2)*un.kB*T/np.sqrt(nat)

    g = stats.norm(mu, sigma_scale*sigma)
    e = np.fromiter((s[-1] for s in data), float)
    idx = np.argsort(e)
    ridx = np.arange(len(idx))[idx]
    d = e[idx]
    if debug:
        # print(idx.shape, d.shape, mu-sigma, 2*sigma)
        mh = plt.hist(d, bins=Nb, density=False)[0].max()

        plt.plot(d, 1.1*mh*np.ones(d.shape), '|', alpha=max(0.01, min(1.0, 100/len(d))))
        # plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.title('Raw data')
        plt.show()
    # bw = d[2:]-d[:-2]
    # bp = (d[2:]+d[:-2])/2
    bw = np.zeros(d.shape)
    bp = np.zeros(d.shape)
    bp[:-1] = (d[1:] + d[:-1])/2
    bw[1:-1] = bp[1:-1] - bp[:-2]
    bw[0] = d[1]-d[0]
    bw[-1] = d[-1]-d[-2]
    bp[1:-1] = (bp[0:-2] + bp[1:-1])/2
    bp[0] = d[0]
    bp[-1] = d[-1]

    w = g.pdf(bp)*bw
    # w = stats.uniform.pdf(bp, mu-sigma, 2*sigma)*bw
    w /= w.sum()
    nf = N

    if debug:
        plt.plot(bp, w, '.')
        # plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.plot(bp, 2*np.cumsum(w)/len(w), '.')
        x = linspace(e.min(), e.max(), 100)
        plt.plot(x, 2*g.cdf(x)/len(w), '-')
        plt.axhline(2/len(w), ls=':', color='k', lw=1)
        plt.title('Data weights')
        plt.show()
        plt.hist(d, weights=w, bins=Nb, density=True)
        plt.title('Weighted data (without nonzero_w)')
        # plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.show()

    # Block zero weights in the +/- 3*sigma zone to not lose data
    w = np.round(w*nf)
    if nonzero_w:
        w += (1*(np.abs(d - mu) < 3*sigma))

    # wdi = np.fromiter(flatten(int(ww)*[ii] for ww, ii in zip(w,ridx[1:-1]) if ww>=1), int)
    # wd = [data[i] for i in wdi]
    # wde = d[wdi]
    wd = []
    for ww, ii in zip(w,idx):
        if ww<1:
            continue
        wd += int(ww)*[data[ii]]
    # print(len(wd), wde.shape)
    # assert len(wd) == N
    if debug:
        wde = np.fromiter((s[-1] for s in wd), float)
        h, b, _ = plt.hist(wde, bins=Nb, density=True, alpha=0.3);
        # assert h.sum() == len(wde)
        x = np.linspace(mu-3*sigma, mu+3*sigma, 300)
        fit = stats.norm.fit(wde)
        plt.plot( x, stats.norm.pdf(x, mu, sigma), '--',
                 label=f'$\mu$={2*mu/3/un.kB:.1f}; $\sigma$={2*sigma/3/un.kB:.1f} (Target)' )
        plt.plot( x, stats.norm.pdf(x, *fit),
                 label=f'$\mu$={2*fit[0]/3/un.kB:.1f}; $\sigma$={2*fit[1]/3/un.kB:.1f} (Fit)' )
        plt.title('Generated weighted sample')
        skip = len(d)//2000
        skip = int(max(1, skip))
        print(skip)
        nf = (w[::skip]).max()
        for s, a in zip(d[::skip], w[::skip]):
            if a<1e-3:
                continue
            plt.axvline(s, ymin=0.95, ymax=0.99, ls='-', color='r', alpha=np.sqrt(a/nf))
        plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.legend(loc='upper right', bbox_to_anchor=(1.0, 0.95));
    return wd

# Cell
def get_sample_weights(data, T, Nb=None, nonzero_w=False, debug=False):

    if Nb is None :
        Nb = min(len(data)//4, 15)

    nat = data[0][2].shape[0]
    mu = 3*T*un.kB/2
    sigma = np.sqrt(3/2)*un.kB*T/np.sqrt(nat)

    g = stats.norm(mu, sigma)
    e = np.fromiter((s[-1] for s in data), float)
    idx = np.argsort(e)
    ridx = np.arange(len(idx))[idx]
    d = e[idx]
    if debug:
        # print(idx.shape, d.shape, mu-sigma, 2*sigma)
        mh = plt.hist(d, bins=Nb, density=False)[0].max()
        plt.plot(d, 1.1*mh*np.ones(d.shape), '|')
        # plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.title('Raw data')
        plt.show()

    bw = np.zeros(d.shape)
    bp = np.zeros(d.shape)
    bp[:-1] = (d[1:] + d[:-1])/2
    bw[1:-1] = bp[1:-1] - bp[:-2]
    bw[0] = d[1]-d[0]
    bw[-1] = d[-1]-d[-2]
    bp[1:-1] = (bp[0:-2] + bp[1:-1])/2
    bp[0] = d[0]
    bp[-1] = d[-1]
    w = g.pdf(bp)*bw
    # w = stats.uniform.pdf(bp, mu-sigma, 2*sigma)*bw
    w /= w.sum()

    if debug:
        plt.plot(d, w, '.')
        # plt.plot(bp, w, '|')
        # plt.step(d, w, where='mid')
        plt.plot(bp, 2*np.cumsum(w)/len(w), '.')
        x = linspace(e.min(), e.max(), 100)
        plt.plot(x, 2*g.cdf(x)/len(w), '-')
        plt.axhline(2/len(w), ls=':', color='k', lw=1)
        # plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.title('Data weights')
        plt.show()
        plt.hist(d, weights=w, bins=Nb, density=False)
        plt.title('Weighted data (without nonzero_w)')
        # plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.show()

    # Block zero weights in the +/- 3*sigma zone to not lose data
    if nonzero_w:
        w += (nonzero_w*w.mean()*(np.abs(d[1:-1] - mu) < 3*sigma))

    # wdi = np.fromiter(flatten(int(ww)*[ii] for ww, ii in zip(w,ridx[1:-1]) if ww>=1), int)
    # wd = [data[i] for i in wdi]
    # wde = d[wdi]
    # wd = []
    # for ww, ii in zip(w,idx[1:-1]):
    #     if ww<1:
    #         continue
    #     wd += int(ww)*[data[ii]]
    # print(len(wd), wde.shape)
    # assert len(wd) == N
    if debug:

        def get_stats(d, w):
            m = np.average(d, weights=w)
            s = np.sqrt(np.average((d - m)**2, weights=w))
            return m, s

        # wde = np.fromiter((s[-1] for s in data), float)
        h, b, _ = plt.hist(d, weights=w, bins=Nb, density=True, alpha=0.3);
        x = np.linspace(mu-3*sigma, mu+3*sigma, 300)
        fit = get_stats(d, w)
        plt.plot( x, stats.norm.pdf(x, mu, sigma), '--',
                 label=f'$\mu$={2*mu/3/un.kB:.1f}; $\sigma$={2*sigma/3/un.kB:.1f} (Target)' )
        plt.plot( x, stats.norm.pdf(x, *fit),
                 label=f'$\mu$={2*fit[0]/3/un.kB:.1f}; $\sigma$={2*fit[1]/3/un.kB:.1f} (Fit)' )
        plt.title('Final weighted data')
        skip = len(d)//2000
        skip = int(max(1, skip))
        # print(skip)
        nf = (w[::skip]).max()
        for s, a in zip(d[1:-1:skip], w[::skip]):
            if a<1e-3:
                continue
            plt.axvline(s, ymin=0.95, ymax=0.99, ls='-', color='r', alpha=np.sqrt(a/nf))
        plt.xlim(mu-3*sigma, mu+4*sigma)
        plt.legend(loc='upper right', bbox_to_anchor=(1.0, 0.95));
    return w