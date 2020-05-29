#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is a part of HECSS project
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


from ase import units as un
from numpy import sqrt, loadtxt, array, linspace, histogram, median
from IPython.display import clear_output
import subprocess
from time import sleep
from matplotlib import pyplot as plt
from matplotlib.pyplot import plot, figure, subplot, legend, show, sca, semilogx, semilogy
from matplotlib.pyplot import xlabel, ylabel, xticks, xlim, ylim, axhline, axvline
from scipy import stats
import sys

THz = 1e12 * un._hplanck * un.J # THz in eV

def plot_band_set(bnd, units=THz, lbl=None, **kwargs):
    if lbl is None:
        lbl=''
    kwa = {k:v for k, v in kwargs.items() if k not in ('color',)}
    plt=plot(bnd[0], un.invcm * bnd[1] / units, label=lbl, **kwargs)
    for b in bnd[2:]:
        plot(bnd[0], un.invcm * b / units, color=plt[0].get_color(), **kwa)
    

def plot_bands(bnd, kpnts, units=THz, decorate=True, lbl=None, **kwargs):
    plot_band_set(bnd, units, lbl, **kwargs)

    lbls, pnts = kpnts
    
    if decorate:
        xticks(pnts, lbls)
        xlim(min(pnts), max(pnts))
        axhline(0,ls=':', lw=1, alpha=0.5)
        for p in sorted(pnts)[1:-1]:
            axvline(p, ls=':', lw=1, alpha=0.5)
        xlabel('Wave vector')
        ylabel('Frequency (THz)')


def plot_bands_file(fn, units=THz, decorate=True, lbl=None, **kwargs):
    bnd = loadtxt(fn).T
    
    with open(fn) as f:
        p_lbl = [l if l!='G' else '$\\Gamma$' for l in f.readline().split()[1:]]
        p_pnt = [float(v) for v in f.readline().split()[1:]]
    kpnts = (p_lbl, p_pnt)
    
    if lbl is None:
        lbl=fn

    plot_bands(bnd, kpnts, units, decorate, lbl, **kwargs)    


def run_alamode(d='phon', prefix='cryst', kpath='cryst', dfset='DFSET', sc='../sc/CONTCAR', o=1, n=0, c2=10, born=None, charge=None):
    fit_cmd = f'/home/jochym/Projects/alamode-tools/devel/make-gen.py opt -p {prefix} -n {sc} -f {dfset} -o {o} --c2 {c2} -d {n}'.split()
    b = ''
    if charge is None:
        charge = prefix
    if born is not None:
        b = f'-b {born} -c {charge}'
    phon_cmd = f'/home/jochym/Projects/alamode-tools/devel/make-gen.py phon -p {prefix} -n ../sc/CONTCAR {b} -k {kpath}.path'.split()
    alm_cmd = f'/home/jochym/public/bin/alm {prefix}_fit.in'.split()
    anph_cmd = f'/home/jochym/public/bin/anphon {prefix}_phon.in'.split()
    
    with open(f'{d}/{prefix}_fit.in', 'w') as ff:
        fit = subprocess.run(fit_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

    with open(f'{d}/{prefix}_phon.in', 'w') as ff:
        phon = subprocess.run(phon_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

    alm = subprocess.run(alm_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    anph = subprocess.run(anph_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for p, l in zip((fit, phon, alm, anph), ('fit', 'phon', 'alm', 'anphon')):
        if p.stdout is not None:
            with open(f'{d}/{prefix}_{l}.log', 'wt') as lf:
                lf.write(p.stdout.decode())
        if p.stderr is not None and len(p.stderr) > 0:
            with open(f'{d}/{prefix}_{l}.err', 'wt') as lf:
                lf.write(p.stderr.decode())

    return all([r.returncode==0 for r in  (fit, phon, alm, anph)]), fit, phon, alm, anph

def get_dfset_len(fn='phon/DFSET'):
    try :
        with open(fn) as dfset:
            return len([l for l in dfset if 'set:' in l])
    except FileNotFoundError:
            return 0


def show_dc_conv(bl, kpnts, max_plots=4):
    prev_n = sorted(bl.keys())[-1]
    plot_bands(bl[prev_n], kpnts, lbl=f'{prev_n}', color='C3')
    y_lims = ylim()
    alpha = 1
    plotted = 1
    for n in reversed(sorted(bl.keys())):
        if n > prev_n*0.75 :
            continue
        alpha *= 0.8
        plot_band_set(bl[n], lbl=f'{n}', alpha=alpha, color='C0', ls='--', lw=1)
        plotted += 1
        prev_n = n
        if plotted > max_plots :
            break
    ylim(y_lims)
    legend()

def build_bnd_lst(directory='phon', dfset='DFSET', prefix='cryst', kpath='crast', order=1, cutoff=10, born=None, charge=None, verbose=False):
    N = get_dfset_len(f'{directory}/{dfset}')
    bl = {}
    for n in range(1,N+1):
        if verbose :
            print(f'Using first {n:3} samples', end='\r')
        run_alamode(d=directory, prefix=prefix, dfset=dfset, kpath=kpath, o=order, n=n, c2=cutoff, born=born, charge=charge)
        bl[n]=loadtxt(f'{directory}/{prefix}.bands').T 
    if verbose :
        print()
    return bl

def build_omega(bl, kpnts):
    omega={}
    eps=1e-3
    kp_dict = {k:v for k,v in zip(*kpnts)}
    for k,v in kp_dict.items():
        omega[k] = array([[n] + list(bnd[1:,abs(bnd[0]-v)<eps][:,0]) for n, bnd in sorted(bl.items())]).T
        omega[k][1:] = omega[k][1:,-1][:,None] - omega[k][1:]
    return omega

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


def monitor_phonons(directory='phon', dfset='DFSET', prefix='cryst', kpath='cryst', 
                    order=1, cutoff=10, born=None, charge=None, k_list=None, fig_out=None):

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
    run_alamode(d=directory, dfset=dfset, prefix=prefix, kpath=kpath, o=order, n=N, c2=cutoff, born=born, charge=charge)
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
            r = run_alamode(d=directory, dfset=dfset, prefix=prefix, kpath=kpath, o=order, n=N, c2=cutoff, born=born, charge=charge)
            if r[0]:
                bnd_lst[N] = loadtxt(f'{directory}/{prefix}.bands').T
                fig = update_fig(fig, bnd_lst, kpnts, k_list)
                prev_N = N
                if fig_out is not None :
                    fig_out[-1]=fig
        else :
            SN = N//2
            all_done = True
            while SN > 0:
                for NN in range(N, 1, -SN):
                    if NN not in bnd_lst:
                        all_done = False
                        r = run_alamode(d=directory, dfset=dfset, prefix=prefix, kpath=kpath, 
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
                sleep(30)


def plot_stats(T=300, base_dir='phon', dfsetfn='DFSET', sqrN=False, show=True, plotchi2=False):
    '''
    Plot monitoring histograms for the configuration list in confs.
    If len(confs)<3 this function is silent.

    confs - configuration list
    nat   - number of atoms in the structure
    T     - target temperature in Kelvin
    show  - call show() fuction at the end (default:True)
    '''
    
    N = get_dfset_len(f'{base_dir}/{dfsetfn}')
    
    if N < 3:
        return

    dfset = loadtxt(f'{base_dir}/{dfsetfn}').reshape(N,-1,6)
    nat=dfset.shape[1]
    
    confs = []
    sets = []
    es = []
    with open(f'{base_dir}/{dfsetfn}') as dff:
        for l in dff:
            if 'set:' not in l:
                continue
            s, _, c, _, e = l.split()[2:7]
            sets.append(s)
            confs.append(c)
            es.append(float(e))
    
    #E0 = Vasp2(restart=base_dir+'/../calc/').get_potential_energy()
    #es = [(Vasp2(restart=d).get_potential_energy()-E0)/nat
    #          for d in sorted(glob(base_dir+'/../calc/T_600.0K/smpl/0*/'))]
        
    es = array(es)
    E_goal = 3*T*un.kB/2
    Es = sqrt(3/2)*un.kB*T/sqrt(nat)
    e = linspace(E_goal - 3*Es, E_goal + 3*Es, 200)
    n = len(es)
    
    plt.hist(es, bins='auto', density=True, label=f'{n} samples', alpha=0.5, rwidth=0.4, zorder=0)
    h = histogram(es, bins='auto', density=False)
    de = (h[1][-1]-h[1][0])/len(h[0])
    if sqrN :
        plt.errorbar((h[1][:-1]+h[1][1:])/2, h[0]/h[0].sum()/de, 
                        yerr=sqrt(h[0])/h[0].sum()/de, ls='', label='$1/\\sqrt{N}$')
    plt.axvline(E_goal, ls='--', color='C2', label='Target energy')
    pdf = stats.norm.pdf(e, E_goal, Es)
    plt.fill_between(e,  (pdf-sqrt(pdf)).clip(min=0), pdf+sqrt(pdf), label='$(1,2,3)/\\sqrt{N}$', color='C1', alpha=0.1, zorder=9)
    plt.fill_between(e,  (pdf-2*sqrt(pdf)).clip(min=0), pdf+2*sqrt(pdf), color='C1', alpha=0.1, zorder=9)
    plt.fill_between(e,  (pdf-3*sqrt(pdf)).clip(min=0), pdf+3*sqrt(pdf), color='C1', alpha=0.1, zorder=9)
    plt.plot(e, pdf, '--', color='C1', label='Target normal dist.')
    fit = stats.norm.fit(es)
    plt.plot(e,  stats.norm.pdf(e, *fit), '--', color='C3', label='Fitted normal dist.', zorder=10)
    if plotchi2 :
        fit = stats.chi2.fit(es, f0=3*nat)
        plt.plot(e,  stats.chi2.pdf(e, *fit), '--', color='C4', label='Fitted $\\chi^2$ dist.', zorder=10)
    plt.xlabel('Potential energy (eV/at)')
    plt.ylabel('Probability density')
    plt.xlim(E_goal-3*Es,E_goal+3*Es)
    plt.legend(loc='upper left', bbox_to_anchor=(0.7,0.5,0.5,0.5))
    if show :
        plt.show()

def monitor_stats(T=300, directory='phon', dfset='DFSET', plotchi2=False):
    
    prev_N = get_dfset_len(f'{directory}/{dfset}')-1

    if get_dfset_len(f'{directory}/{dfset}') < 3:
        print('Waiting for the first samples (>2).', end='')
        sys.stdout.flush()
        while get_dfset_len(f'{directory}/{dfset}') < 3:
           sleep(15) 
           print('.', end='')
           sys.stdout.flush()
        print('done.', end='')
    print('Calculating the plots.',)
    sys.stdout.flush()
    clear_output(wait=True)
    
    while True :
        N = get_dfset_len(f'{directory}/{dfset}')
        if N > prev_N :
            plot_stats(T=T, base_dir=directory, dfsetfn=dfset, plotchi2=plotchi2)
            show()
            clear_output(wait=True)
            prev_N = N
        else :
            sleep(15)
