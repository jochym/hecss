"""Generated from notebooks/monitor_phonons.py by build.py"""

"Generated from notebooks/monitor_phonons.py by build.py"

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
import subprocess


def monitor_phonons(directory='phon', dfset='DFSET', prefix='cryst', kpath='cryst', sc='../sc/CONTCAR',
                        order=1, cutoff=10, born=None, charge=None, k_list=None, 
                        fig_out=None, once=False):

        def update_fig(fig, bnd_lst, kpnts, k_lst):
            if fig is not None:
                plt.close(fig)
            fig = figure(figsize=(14,5))
            (dcplt, omplt) = fig.subplots(1, 2)
            sca(dcplt)
            show_dc_conv(bnd_lst, kpnts)
            sca(omplt)
            if N>1:
                if k_lst is None:
                    plot_omega(build_omega(bnd_lst, kpnts))
                else :
                    plot_omega(build_omega(bnd_lst,
                                            ([l for l in kpnts[0] if l in k_lst],
                                             [v for l, v in zip(*kpnts) if l in k_lst])))
            show()
            clear_output(wait=True)
            return fig

        bnd_lst = {}

        if get_dfset_len(f'{directory}/{dfset}') < 1:
            print('Waiting for the first sample.', end='')
            sys.stdout.flush()
            while get_dfset_len(f'{directory}/{dfset}') < 1:
               sleep(15)
               print('.', end='')
               sys.stdout.flush()
            print('done.', end='')
        print('Calculating the plots.',)
        sys.stdout.flush()
        clear_output(wait=True)

        N = get_dfset_len(f'{directory}/{dfset}')
        run_alamode(d=directory, dfset=dfset, prefix=prefix, kpath=kpath, sc=sc,
                    o=order, n=N, c2=cutoff, born=born, charge=charge)
        bnd_lst[N] = loadtxt(f'{directory}/{prefix}.bands').T
        prev_N = N

        with open(f'{directory}/{prefix}.bands') as f:
            p_lbl = [v if v!='G' else '$\\Gamma$' for v in f.readline().split()[1:]]
            p_pnt = [float(v) for v in f.readline().split()[1:]]
        kpnts = (p_lbl, p_pnt)

        fig = update_fig(None, bnd_lst, kpnts, k_list)
        if fig_out is not None :
            fig_out.append(fig)

        while True :
            N = get_dfset_len(f'{directory}/{dfset}')
            if N > prev_N:
                r = run_alamode(d=directory, dfset=dfset, prefix=prefix, kpath=kpath, sc=sc,
                                o=order, n=N, c2=cutoff, born=born, charge=charge)
                if r[0]:
                    bnd_lst[N] = loadtxt(f'{directory}/{prefix}.bands').T
                    fig = update_fig(fig, bnd_lst, kpnts, k_list)
                    if fig_out is not None :
                        fig_out[-1]=fig
                    prev_N = N
            else :
                SN = N//2
                all_done = True
                while SN > 0:
                    for NN in range(N, 1, -SN):
                        if NN not in bnd_lst:
                            all_done = False
                            r = run_alamode(d=directory, dfset=dfset, prefix=prefix, kpath=kpath, sc=sc,
                                            o=order, n=NN, c2=cutoff, born=born, charge=charge)
                            if r[0]:
                                bnd_lst[NN] = loadtxt(f'{directory}/{prefix}.bands').T
                                fig = update_fig(fig, bnd_lst, kpnts, k_list)
                                if fig_out is not None :
                                    fig_out[-1]=fig
                        if get_dfset_len(f'{directory}/{dfset}') > prev_N:
                            SN = 0
                            all_done = False
                            break
                    SN = SN//2
                if all_done:
                    if once :
                        break
                    sleep(30)

def plot_omega(omega):
        for k, o in omega.items():
            if len(o[0])<2 :
                return
            l = k
            if k == 'G':
                l = '$\\Gamma$'
            semilogy(o[0, :-1], (un.invcm * o[1:,:-1].std(axis=0))/THz, '-', label=l)

        legend()
        plt.gca().set_xscale('function', functions=(lambda x: x**(1/2), lambda x: x**2))
        rng = 10*un.invcm*median([o[1:].std(axis=0) for o in omega.values()])/THz
        if rng > 1e-3:
            ylim(None, rng)
        #axhline(0, ls=':', lw=1)
        ylabel('Frequency convergence (THz)')
        xlabel('Number of samples')

def run_alamode(d='phon', prefix='cryst', kpath='cryst', dfset='DFSET', sc='../sc/CONTCAR',
                    o=1, n=0, c2=10, c3=6, born=None, charge=None, skip_fit=False):
        fit_cmd = (f'/home/jochym/Projects/alamode-tools/devel/make-gen.py opt ' +
                   f'-p {prefix} -n {sc} -f {dfset} -o {o} --c2 {c2} --c3 {c3} -d {n}').split()
        b = ''
        if charge is None:
            charge = prefix
        if born is not None:
            b = f'-b {born} -c {charge}'
        phon_cmd = f'/home/jochym/Projects/alamode-tools/devel/make-gen.py phon -p {prefix} -n {sc} {b} -k {kpath}.path'.split()
        alm_cmd = f'/home/jochym/public/bin/alm {prefix}_fit.in'.split()
        anph_cmd = f'/home/jochym/public/bin/anphon {prefix}_phon.in'.split()

        if not skip_fit:
            with open(f'{d}/{prefix}_fit.in', 'w') as ff:
                fit = subprocess.run(fit_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)
            alm = subprocess.run(alm_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else :
            fit = None
            alm = None

        with open(f'{d}/{prefix}_phon.in', 'w') as ff:
            phon = subprocess.run(phon_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

        anph = subprocess.run(anph_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for p, l in zip((fit, phon, alm, anph), ('fit', 'phon', 'alm', 'anphon')):
            if p is None:
                continue
            if p.stdout is not None:
                with open(f'{d}/{prefix}_{l}.log', 'wt') as lf:
                    lf.write(p.stdout.decode())
            if p.stderr is not None and len(p.stderr) > 0:
                with open(f'{d}/{prefix}_{l}.err', 'wt') as lf:
                    lf.write(p.stderr.decode())

        return (all([r.returncode==0 for r in (fit, phon, alm, anph) if r is not None]), 
                fit, phon, alm, anph)


__all__ = ["monitor_phonons", "plot_omega", "run_alamode"]