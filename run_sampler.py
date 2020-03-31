# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# ### Example code for the HECSS configuration generator

# %%
# Import VASP calculator and unit modules
from ase.calculators.vasp import Vasp2
from ase import units as un
from os.path import isfile
import os

# The sample generator, monitoring display and dfset writer
from hecss import HECSS, write_dfset

# clear_output function for nice monitoring display
from matplotlib.pylab import show
from IPython.display import clear_output

# %%
# Read the structure (previously calculated unit(super) cell)
# The command argument is specific to the cluster setup
calc = Vasp2(label='cryst', directory='./sc/', restart=True)

# This just makes a copy of atoms object
# Do not generate supercell here - your atom ordering will be wrong!
cryst = calc.atoms.repeat(1)

# %% [markdown]
# If you have magmoms in your system you need to use following 
# temporary fix for a bug in magmom handling in Vasp2 calculator:
# ```python
# if 'magmom' in calc.list_float_params:
#     calc.list_float_params['magmom'] = cryst.get_initial_magnetic_moments()
# ```
# Just copy the above code to a new cell here and execute it.

# %%
# Setup the calculator - single point energy calculation
# The details will change here from case to case
calc.set(directory='calc')
calc.set(command='/home/jochym/Projects/hecss/run-vasp -J "3C-SiC-h"')
calc.set(nsw=0)
cryst.set_calculator(calc)

# %% [markdown]
# You should probably check the calculator setup and the stress tensor of the supercell to make sure it is in equilibrium before running long sequence of
# DFT calculations. Here is an example:
# ```python
# print('Stress tensor: ', end='')
# for ss in calc.get_stress()/un.GPa:
#     print(f'{ss:.3f}', end=' ')
# print('GPa')
# ```

# %%
# Setup the calculation parameters: Temperature and number of atoms
T_goal = 600
nat = cryst.get_global_number_of_atoms()

# %%
# Space for results and desired number of samples
confs = []
dfsetfn = f'phon/DFSET_T{T_goal:.1f}K'
N = 4

# %%
# Build the sampler
sampler = HECSS(cryst, calc, T_goal, width=0.041)

# %%
# Iterate over samples (conf == i, x, f, e) collect the configurations
# and write displacement-force data to the dfsetfn file
# You can continue the iteration by manually increasing N and just
# re-running this loop. It will continue from the last computed sample.
for conf in sampler:
    # Collect results
    confs.append(conf)    
    write_dfset(dfsetfn, conf, len(confs))
    
    clear_output(wait=True)
    
    # Check if we have enough samples
    if len(confs) >= N:
        break
        
    if isfile('STOP_HECSS'):
        os.remove('STOP_HECSS')
        break

# %%
# Need more samples. Increase N and run the loop above again.
N = 512

# %%
