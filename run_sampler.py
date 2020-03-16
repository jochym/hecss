# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
# %pylab inline

# %%
import ase
from ase import units as un
from ase.calculators.vasp import Vasp2
from hecss import HECSS, plot_stats
from scipy import stats

# %%
from IPython.display import clear_output

# %%
calc = Vasp2(label='cryst', directory='./cryst', restart=True)
cryst = calc.atoms.repeat(2)

# %%
calc.set(directory='calc')
calc.set(command=f'/home/jochym/devel/scripts/run-vasp/run-vasp54' + 
                 f' -b -N 1 -p 64 -q blade2 -J "hecss"')
cryst.set_calculator(calc)

# %%
calc.get_stress()/un.GPa

# %%
T_goal = 600
nat = cryst.get_global_number_of_atoms()

# %%
sampler = HECSS(cryst, calc, T_goal, width=0.041)

# %%
idx = []
xs = []
fs = []
es = []
dfsetfn = f'phon/DFSET'

# %%
for i, x, f, e in sampler:
    idx.append(i)
    xs.append(x)
    fs.append(f)
    es.append(e)
    with open(dfsetfn, 'at') as dfset:
        print(f'#\n# set: {len(idx)}  config: {i:04d}  energy: {e:8e} eV/at\n#', file=dfset)
        for ui, fi in zip(x,f):
            print(*tuple(ui/un.Bohr), *tuple(fi*un.Bohr/un.Ry), file=dfset)

    if len(idx) > 3 :
        plot_stats(es, nat, T_goal)
        show();
        clear_output(wait=True)

# %%
