from ase import units as un
from numpy import sqrt, loadtxt, array
from IPython.display import clear_output
import subprocess
from time import sleep
from matplotlib import pyplot
from matplotlib.pyplot import plot, figure, subplot, legend, show, sca, semilogx
from matplotlib.pyplot import xlabel, ylabel, xticks, xlim, ylim, axhline, axvline
import sys

THz = 1e12 * un._hplanck * un.J # THz in eV

def plot_band_set(bnd, units=THz, lbl=None, **kwargs):
    if lbl is None:
        lbl=''
    kwa = {k:v for k, v in kwargs.items() if k not in ('color',)}
    plt=plot(bnd[0], un.invcm * bnd[1] / units, label=lbl, **kwargs)
    for b in bnd[2:]:
        plot(bnd[0], un.invcm * b / units, color=plt[0].get_color(), **kwa)
    

def plot_bands(fn, units=THz, decorate=True, lbl=None, **kwargs):
    bnd = loadtxt(fn).T
    
    with open(fn) as f:
        p_lbl = f.readline().split()[1:]
        p_pnt = [float(v) for v in f.readline().split()[1:]]
    p_lbl = [l if l!='G' else '$\Gamma$' for l in p_lbl]
    
    if lbl is None:
        lbl=fn
    plot_band_set(bnd, units, lbl, **kwargs)
    
    if decorate:
        xticks(p_pnt, p_lbl)
        xlim(p_pnt[0], p_pnt[-1])
        axhline(0,ls=':', lw=1, alpha=0.5)
        for p in p_pnt[1:-1]:
            axvline(p, ls=':', lw=1, alpha=0.5)
        xlabel('Wave vector')
        ylabel('Frequency (THz)')


def run_alamode(d='phon', o=1, n=None, c2=10):
    fit_cmd = f'/home/jochym/Projects/alamode-tools/devel/make-gen.py opt -p cryst -n ../sc/CONTCAR -o {o} --c2 {c2} -d {n}'.split()
    phon_cmd = '/home/jochym/Projects/alamode-tools/devel/make-gen.py phon -p cryst -n ../sc/CONTCAR -b 2 -k 3C_SiC.path'.split()
    alm_cmd = '/home/jochym/public/bin/alm fit.in'.split()
    anph_cmd = '/home/jochym/public/bin/anphon phon.in'.split()
    
    with open(f'{d}/fit.in', 'w') as ff:
        fit = subprocess.run(fit_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

    with open(f'{d}/phon.in', 'w') as ff:
        phon = subprocess.run(phon_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

    alm = subprocess.run(alm_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    anph = subprocess.run(anph_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def get_dfset_len(fn='phon/DFSET'):
    with open(fn) as dfset:
        return len([l for l in dfset if 'set:' in l])


def show_dc_conv(bl, directory='phon'):
    prev_n = get_dfset_len(f'{directory}/DFSET')
    plot_bands(f'{directory}/cryst.bands', lbl=f'{prev_n}', color='C3')
    alpha = 1
    for n in reversed(sorted(bl.keys())):
        if n > prev_n*0.5 :
            continue
        alpha *= 0.66
        plot_band_set(bl[n], lbl=f'{n}', alpha=alpha, color='C0', ls='--', lw=1)
        prev_n = n
    legend();

def build_bnd_lst(directory='phon', order=2, cutoff=10):
    N = get_dfset_len(f'{directory}/DFSET')
    bl = {}
    for n in range(1,N+1):
        run_alamode(d=directory, o=order, n=n, c2=cutoff)
        bl[n]=loadtxt(f'{directory}/cryst.bands').T      
    return bl

def build_omega(bl, kpnts):
    omega={}
    eps=1e-3
    for k,v in kpnts.items():
        omega[k] = array([[n] + list(bnd[1:,abs(bnd[0]-v)<eps][:,0]) for n, bnd in bl.items()]).T
        omega[k][1:] = omega[k][1:,-1][:,None] - omega[k][1:]
    return omega

def plot_omega(omega):
    for k, o in omega.items():
        l = k
        if k == 'G':
            l = '$\Gamma$'
        plt = plot(o[0], (un.invcm * o[1])/THz, '.', label=l)
        plot(o[0], (un.invcm * o[2:].T)/THz, '.', color=plt[0].get_color())
    legend();
    rng = 0.5*un.invcm * array([o[1:].reshape(-1) for o in omega.values()]).std()/THz
    ylim(-rng, rng)
    axhline(0, ls=':', lw=1)
    ylabel('Frequency convergence (THz)')
    xlabel('Number of samples');    


def monitor_phonons(directory='phon', order=2, cutoff=10):
    bnd_lst = build_bnd_lst()
    prev_N = 0
    
    if get_dfset_len(f'{directory}/DFSET') < 1:
        print('Waiting for the first sample.', end='')
        sys.stdout.flush()
        while get_dfset_len(f'{directory}/DFSET') < 1:
           sleep(15) 
           print('.', end='')
           sys.stdout.flush()
           print('done.', end='')
    print('Calculating the plots.',)
    sys.stdout.flush()
    clear_output(wait=True)

    with open(f'{directory}/cryst.bands') as f:
        p_lbl = f.readline().split()[1:]
        p_pnt = [float(v) for v in f.readline().split()[1:]]
    kpnts = {k:v for k,v in zip(p_lbl, p_pnt)}
    fig = None
    while True :
        N = get_dfset_len(f'{directory}/DFSET')
        if N > prev_N :
            run_alamode(d=directory, o=order, n=N, c2=cutoff)
            bnd_lst[N]=loadtxt(f'{directory}/cryst.bands').T
            if fig is not None:
                pyplot.close(fig)
            fig = figure(figsize=(14,5))
            (dcplt, omplt) = fig.subplots(1, 2)
            sca(dcplt)
            show_dc_conv(bnd_lst, directory)
            sca(omplt)
            if N>1:
                plot_omega(build_omega(bnd_lst, kpnts))
            show()
            clear_output(wait=True)
            prev_N = N
        else :
            sleep(15)
