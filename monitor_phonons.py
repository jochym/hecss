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
# ### Phonon convergence monitoring notebook

# %%
from hecss import monitor_phonons

# %%
T=900
monitor_phonons(directory='example/phon/', dfset=f'DFSET_T{T:.1f}K', 
                   kpath='3C_SiC', charge='3C_SiC', 
                   order=2, cutoff=10, born=2)

# %%

# %%
