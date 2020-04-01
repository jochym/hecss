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
import calc_monitor as cm

# %%
T=600
cm.monitor_stats(T=T, directory='example/phon', dfset=f'DFSET_T{T:.1f}K')

# %%
cm.plot_stats(T=T, base_dir='example/phon', dfsetfn=f'DFSET_T{T:.1f}K');
