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

# %%
from hecss import monitor_stats, plot_stats

# %%
T = 600
monitor_stats(T=T, directory='../phon', dfset=f'DFSET_T{T:.1f}K')

# %%
T = 600
plot_stats(T=T, base_dir='example/phon', dfsetfn=f'DFSET_T{T:.1f}K');
