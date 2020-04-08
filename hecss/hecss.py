#!/usr/bin/env python
# -*- coding: utf-8 -*-

# HECSS
# Copyright (C) 2020 by Paweł T. Jochym <jochym@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

_ver_mjr, _ver_min = 0, 2

import sys
import ase
import scipy
from scipy import stats
from scipy.special import expit
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import ase.units as un

def normalize_conf(c, base):
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
    return dot(spos,cell.T), spos


def write_dfset(fn, c, n=0):
    '''
    Append displacement-force data from the conf to the fn file.
    The format is suitable for use as ALAMODE DFSET file.
    Optionaly you can provide configuration number in n.
    File need not exist prior to first call. 
    If it does not it will be created.
    '''
    i, x, f, e = c
    with open(fn, 'at') as dfset:
        print(f'# set: {n:04d} config: {i:04d}  energy: {e:8e} eV/at', file=dfset)
        for ui, fi in zip(x,f):
            print((3*'%15.7f ' + '     ' + 3*'%15.8e ') % 
                        (tuple(ui/un.Bohr) + tuple(fi*un.Bohr/un.Ry)), 
                        file=dfset)
    

def HECSS(cryst, calc, T_goal, delta=0.05, width=0.033, maxburn=20, sigma=2, 
            directory=None, reuse_base=None, verb=True):
    '''
    Run HECS sampler on the system `cryst` using calculator `calc` at target
    temperature `T_goal`. The `delta`, `width`, `maxburn` and `directory` parameters
    determine detailed aspects of the algorithm.

    This is a generator and cannot be used as regular function. 
    It is intended to be used as a source of the sequence of 
    configurations in the `for` loop and must be closed after 
    finishing the iteration. On the other hand, the iteration 
    may be continued if additional samples are required. 
    The state is preserved until the .close() method is called.

    ```
    sampler = HECSS(cryst, calc, T)
    for i, x, f, e in sampler:
        process_sample(i, x, f, e)
        if i > N :
            break
    sampler.close()
    ```

    INPUT
    =====
    cryst   - ASE structure to sample
    calc    - ASE calculator to use for potential energy evaluations
    T_goal  - Target temperature in Kelvin

    delta   - speed of the adaptation - maximal change of the prior width in one step
    width   - initial width of the position distribution in Angstrom
    maxburn - max number of burn-in steps
    sigma   - width in energy sigmas of the prior energy distribution.
              This should be approx 2 (default), if your posteriors seem too narrow
              make it bigger, if too wide make it smaller (1-3 range in general).
              Too large a number makes the acceptance ratio lower.

    directory - directory for calculations and generated samples. If left as None,
                the `calc/{T_goal:.1f}K/` will be used and the generated samples will be 
                stored in the `smpl/{i:04d}` subdirectories.

    reuse_base - None or the base calc directory for the ground state config
                 if None the base will be recalculated at the start of the run
                 if directory name - the energy from this dir will be reused as 
                 ground state energy for the calculation.
                 Be careful to have the same VASP setup in calc and reuse_base,
                 otherwise the ground state energy and distribution wil be wrong.

    verb    - print verbose progress messages for interactive use

    OUTPUT
    ======
    The generator yields samples from the thermodynamic distribution at T=T_goal as tuples
    (index, displacement, forces, energy):
    index        - integer numbering the samples in the `smpl` subdirectory. The index may
                   repeat if the sample must be repeated in the sequence. 
    displacement - set of atomic displacements (in A) in the sample (numpy array)
    forces       - set of forces (in eV/A) generated by the displacement
    energy       - potential energy of the configuration

    '''    

    def smpl_print(r=0):
        if i==0:
            print(f'Burn-in sample:{k}  w:{w:.4f}  alpha:{alpha:6.4e}  dE:{(e_star-E_goal)/(2*Es):+6.2f} sigma', end='\r')
        else :
            print(f'Sample:{i-1:04d}  a:{100*i/n:5.1f}%  w:{w:.4f}  <w>:{np.mean(wl):.4f}  alpha:{alpha:6g} ' + (r*'x'), end='\r')
        sys.stdout.flush()


    if verb:
        print(f'Calculating base structure.    ', end='\r')
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
    
    w = width
    w_prev = w
    x = Q.rvs(size=dim, scale=w)
    wl = []

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
    
    if verb:
        print(f'Calculating initial sample.    ', end='\r')
        sys.stdout.flush()

    cr.set_positions(cryst.get_positions()+x)
    cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')
    
    e = (cr.get_potential_energy()-Ep0)/nat
    f = cr.get_forces()
    
    k = 0
    r = 0
    alpha = 0

    
    if verb:
        print(f'Starting burn-in.            ', end='\r')
        sys.stdout.flush()

    while True:
        if verb and (n>0 or k>0):
            smpl_print(r)

        x_star = Q.rvs(size=dim, scale=w)

        cr.set_positions(cryst.get_positions()+x_star)
        cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')

        e_star = (cr.get_potential_energy()-Ep0)/nat
        f_star = cr.get_forces()
        
        alpha = P(e_star, E_goal, Es) / P(e, E_goal, Es)
        
        q_x = log(Q.pdf(x, w_prev)).sum()
        q_star_x_star = log(Q.pdf(x_star, w)).sum()
        q_star_x = log(Q.pdf(x, w)).sum()
        q_x_star = log(Q.pdf(x_star, w_prev)).sum()

        alpha *= exp(q_x + q_star_x_star - q_star_x - q_x_star)

        w_prev = w
        w *= 1-2*(expit((e_star-E_goal)/Es/sigma)-0.5)*delta*(10 if i==0 else 1)

        if np.random.rand() < alpha:
            x = x_star
            e = e_star
            f = f_star
            if i==0 and abs(e_star-E_goal) > 2*Es :
                # At the burn-in stage and still further then 2 sigma from target
                # Let us keep searching for correct w
                k += 1
                if k>maxburn :
                    print(f'\nError: reached maxburn ({maxburn}) without finding target energy.\n'+
                      f'You probably need to change initial width parameter to a {"higher" if (e_star-E_goal)<0 else "lower"} value.')
                    return
                continue
            else :
                # We are at sampling stage or just found the proper w
                # Either way: switch to the next sample directory (i)
                # and zero the rejection counter
                wl.append(w)
                i += 1
                n += 1
                r = 0
        else:
            # Sample rejected - nothing to yield. Try again
            r += 1
            n += 1
            continue

        if verb:
            smpl_print(r)

        yield i-1, x, f, e
        
        

if __name__ == '__main__':

    from ase.calculators.vasp import Vasp2, Vasp
    from ase.build import bulk
    import os, errno

    def mkdirs(newdir, mode=0o777):
        try: os.makedirs(newdir, mode)
        except OSError as err:
            # Reraise the error unless it's about an already existing directory 
            if err.errno != errno.EEXIST or not os.path.isdir(newdir): 
                raise


    print(f'HECS sampler ver.:{_ver_mjr}.{_ver_min}')
        
    n = 1
    a = 4.37165779
    #a = 4.38447739 # Approx 600K thermal expansion
    uc = bulk('SiC', crystalstructure='zincblende', a=a, cubic=True)
    uc = ase.build.sort(uc, tags= uc.get_masses())
    cryst = uc.repeat(n)
    cryst = ase.build.sort(cryst, tags= cryst.get_masses())
    
    calc = Vasp2(label='calc', directory='calc', xc='pbe',
                 command=f'~/devel/scripts/run-vasp/run-vasp54' + 
                 f' -b -N 1 -p 64 -q blade2 -J "sc_{n}x{n}x{n}"')
    
    cryst.set_calculator(calc)
    
    cryst.calc.set(kpts=[3,3,3], ibrion=1, isif=3, nsw=0, nelm=60,
                   ediff=1e-8, ncore=8, 
                   lcharg=False, lwave=False, isym=0)
    
    cryst.calc.set(directory='calc')
    
    print(f'P_0:{cryst.get_stress()[:3].mean()/un.GPa:0.4f} GPa') 
    
    T_goal = 2000
    nat = cryst.get_global_number_of_atoms()
    E_goal = 3*T_goal*un.kB/2
    Es = np.sqrt(3/2)*un.kB*T_goal/np.sqrt(nat)   
    
    idx = []
    xs = []
    fs = []
    es = []
    dfsetfn = f'calc/T_{T_goal:.1f}K/'
    mkdirs(f'calc/T_{T_goal:.1f}K/')
    dfsetfn = dfsetfn + 'DFSET'

    with open(dfsetfn , 'wt') as dfset:
        print(f'# Data from HECS sampling at {T_goal:.1f}K', file=dfset)

    sampler = HECSS(cryst, calc, T_goal)
    
    N=64
    for i, x, f, e in sampler:
        idx.append(i)
        xs.append(x)
        fs.append(f)
        es.append(e)
        with open(dfsetfn, 'at') as dfset:
            print(f'#\n# set: {len(idx)}  config: {i:04d}  energy: {e:8e} eV/at\n#', file=dfset)
            for ui, fi in zip(x,f):
                print(*tuple(ui/un.Bohr), *tuple(fi*un.Bohr/un.Ry), file=dfset)
        if len(idx) >= N:
            break
            
            
    sampler.close()
            
            
    