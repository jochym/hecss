import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Parallel sampler

    > Implementation of async/parallel generator execuing calculations in a pool of nwork workers. Implemented for VASP but should be fairly easy to port/extend to other directory/cluster-based calculators.
    """)
    return


@app.cell
def _():
    #| hide
    from fastcore.basics import patch

    return (patch,)


@app.cell
def _():
    #| hide
    import ase
    from ase.calculators.vasp import Vasp
    from ase.calculators import calculator
    from ase.calculators.vasp.vasp import check_atoms
    from ase import units as un
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from tqdm.auto import tqdm
    from scipy import stats
    import numpy as np

    return ase, calculator, np, un


@app.cell
def _():
    #| hide
    from hecss import *
    import hecss
    return

@app.cell
def _():
    #|hide 
    from hecss.core import HECSS

    return (HECSS,)


@app.cell
def _():
    #| hide
    from hecss.util import write_dfset, calc_init_xscale
    from hecss.optimize import make_sampling

    return


@app.cell
def _():
    #| hide
    from glob import glob
    from tempfile import TemporaryDirectory
    import os
    import subprocess
    from collections import defaultdict
    from matplotlib import pyplot as plt

    return


@app.cell
def _(
    HECSS,
    ase,
    calculator,
    expit,
    get_cell_data,
    get_symmetry_dataset,
    maxburn,
    np,
    patch,
    sys,
    un,
):
    #| exporti core
    @patch
    async def __sampler_aio(self: HECSS, T_goal, N=None, delta_sample=0.01, sigma=2,
                 eqdelta=0.05, eqsigma=0.2, xi=1, chi=1,
                 modify=None, modify_args=None, symprec=1e-5,
                 width_list=None, dofmu_list=None, xscale_list=None,
                 verb=True, ):
        '''
        The the core functionality of the module is implemented in this generator function 
        which yields samples of the prior distribution. This is an internal implementation 
        mechanism. In principle, it can be used by outside code but it is **strongly** 
        discouraged as the implementation details may change without any notice 
        (even for minor revisions).
    
        This is a generator and cannot be used as regular function. 
        It is intended to be used as a source of the sequence of 
        configurations in the `for` loop and must be closed after 
        finishing the iteration. On the other hand, the iteration 
        may be continued if additional samples are required. 
        The state is preserved until the .close() method is called.
        The sampling loop may be run for `N` iterations or indefinitely (default).

    
        #### INPUT
        T_goal       : Target temperature in Kelvin
        N            : Number of iterations. If None (default) the generator never stops.
        delta_sample : Prior width adaptation rate. The default is sufficient in most cases.
        sigma        : Range around E0 in sigmas to stop w-serach mode
        eqdelta      : Max. speed of amplitude correction from step to step (0.05=5%)
        eqsigma      : Half width of linear part of amplitude correction function.
        xi           : strength of the amplitude correction term [0-1]
        chi          : strength of the amplitude correction term mixing [0-1]
        xscale_init  : Initial values of the amplitude correction coefficients.
                       Array with shape `cryst.get_positions().shape`.
                       May be generated with `calc_init_xscale` function.
        Ep0          : T=0 energy (base, no displacements), if None (default) calculate E0.
        modify       : pass your own pre-processing function to modify the structure 
                       before calculation. The function must return a  (e, f) tuple
                       with energy of the structure (e, scalar) and forces (f, array).
        modify_args  : dictionary of extra arguments to pass to modify function
        symprec      : symmetry detection treshold for spglib functions
        directory    : (only for VASP calculator) directory for calculations and generated samples. 
                       If left as None, the `calc/{T_goal:.1f}K/` will be used and the generated 
                       samples will be stored in the `smpl/{i:04d}` subdirectories.
        verb         : print verbose progress messages for interactive use
    
        **Output parameters**
    
        width_list   : Output parameter. If not None, store in passed list the sequence of widths.
        dofmu_list   : Output parameter. If not None, store in passed list the array of DOF virials
                       relative to temperature (T_goal).
        xscale_list  : Output parameter. If not None, store in passed list the array of amplitude 
                       correction coefficients (normalized). May be used to generate `xscale_init`
                       values with the help of `calc_init_xscale` function.

        #### OUTPUT
        The generator yields samples from the prior distribution at T_goal temperature 
        as tuples: (number, index, displacement, forces, energy):
    
        - number       : sample number, always increasing
        - index        : integer numbering the samples in the `smpl` subdirectory. 
                         Index repeats if the sample is repeated in the sequence. 
        - displacement : set of atomic displacements (in A) in the sample (numpy array)
        - forces       : set of forces (in eV/A) generated by the displacement
        - energy       : potential energy of the configuration

        '''    
    
        if self._pbar :
            self._pbar.set_postfix_str('Initialization')
        
        nat = len(self.cryst)
        dim = (nat, 3)
        # lattice = np.array(cell.get_cell().T, dtype="double", order="C")
        # positions = np.array(cell.get_scaled_positions(), dtype="double", order="C")
        # numbers = np.array(cell.get_atomic_numbers(), dtype="intc")
        symm = get_symmetry_dataset(get_cell_data(self.cryst), symprec=symprec)
        dofmap = symm['mapping_to_primitive']
        dof = list(sorted(set(dofmap)))
        dofmu = np.ones((len(dof), 3))
        mu = np.ones(dim)

        xscale = np.array(self.xscale_init)
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
    
        if self.Ep0 is None:
            self.Ep0 = self.cryst.get_potential_energy()
        Ep0 = self.Ep0
    
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
                if i==0 and abs(e_star-E_goal) > 3*sigma*Es :
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
                        self._pbar.set_postfix_str(f'w search: eta={eta:.3g} ({(e_star-E_goal)/(sigma*Es):.2g})')
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

    return


@app.cell
def _(HECSS, patch):
    #|exporti core

    @patch
    def _sampler_aio(self: HECSS, T_goal, N=None, delta_sample=0.01, sigma=2,
                 eqdelta=0.05, eqsigma=0.2, xi=1, chi=1,
                 modify=None, modify_args=None, symprec=1e-5,
                 width_list=None, dofmu_list=None, xscale_list=None,
                 verb=True, nwork=None):
        '''
        Runner for the parallel version of the sampler.
        '''
    
        if nwork is None:
            # Silent. This is parallel version. Use serial version instead.
            raise NotImplementedError
    
        if self.calc.name in ('vasp',):
            raise NotImplementedError
        else :
            # Warn if the call was for unsupported calculator. 
            print('WARNING: Parallel execution supported only for some calculators.')
            print('Using serial version')
            raise NotImplementedError

    return


if __name__ == "__main__":
    app.run()
