from ase import units as un
from numpy import sqrt, loadtxt, array, linspace, histogram
from IPython.display import clear_output
import subprocess
from time import sleep
from matplotlib import pyplot as plt
from matplotlib.pyplot import plot, figure, subplot, legend, show, sca, semilogx
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
    

def plot_bands(fn, units=THz, decorate=True, lbl=None, **kwargs):
    bnd = loadtxt(fn).T
    
    with open(fn) as f:
        p_lbl = f.readline().split()[1:]
        p_pnt = [float(v) for v in f.readline().split()[1:]]
    p_lbl = [l if l!='G' else '$\\Gamma$' for l in p_lbl]
    
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


def run_alamode(d='phon', prefix='cryst', kpath='cryst', o=1, n=0, c2=10, born=None):
    fit_cmd = f'/home/jochym/Projects/alamode-tools/devel/make-gen.py opt -p {prefix} -n ../sc/CONTCAR -o {o} --c2 {c2} -d {n}'.split()
    b = '' if born is None else f'-b {born}'
    phon_cmd = f'/home/jochym/Projects/alamode-tools/devel/make-gen.py phon -p {prefix} -n ../sc/CONTCAR {b} -k {kpath}.path'.split()
    alm_cmd = f'/home/jochym/public/bin/alm {prefix}_fit.in'.split()
    anph_cmd = f'/home/jochym/public/bin/anphon {prefix}_phon.in'.split()
    
    with open(f'{d}/{prefix}_fit.in', 'w') as ff:
        fit = subprocess.run(fit_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

    with open(f'{d}/{prefix}_phon.in', 'w') as ff:
        phon = subprocess.run(phon_cmd, cwd=d, stdout=ff, stderr=subprocess.PIPE)

    alm = subprocess.run(alm_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    anph = subprocess.run(anph_cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return fit, phon, alm, anph

def get_dfset_len(fn='phon/DFSET'):
    try :
        with open(fn) as dfset:
            return len([l for l in dfset if 'set:' in l])
    except FileNotFoundError:
            return 0


def show_dc_conv(bl, directory='phon', dfset='DFSET', prefix='cryst'):
    prev_n = get_dfset_len(f'{directory}/{dfset}')
    plot_bands(f'{directory}/{prefix}.bands', lbl=f'{prev_n}', color='C3')
    alpha = 1
    for n in reversed(sorted(bl.keys())):
        if n > prev_n*0.5 :
            continue
        alpha *= 0.66
        plot_band_set(bl[n], lbl=f'{n}', alpha=alpha, color='C0', ls='--', lw=1)
        prev_n = n
    legend()

def build_bnd_lst(directory='phon', dfset='DFSET', prefix='cryst', order=1, cutoff=10):
    N = get_dfset_len(f'{directory}/{dfset}')
    bl = {}
    for n in range(1,N+1):
        run_alamode(d=directory, o=order, n=n, c2=cutoff)
        bl[n]=loadtxt(f'{directory}/{prefix}.bands').T      
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
            l = '$\\Gamma$'
        p = plot(o[0], (un.invcm * o[1])/THz, '.', label=l)
        plot(o[0], (un.invcm * o[2:].T)/THz, '.', color=p[0].get_color())
    legend()
    rng = 0.5*un.invcm * array([o[1:].reshape(-1) for o in omega.values()]).std()/THz
    ylim(-rng, rng)
    axhline(0, ls=':', lw=1)
    ylabel('Frequency convergence (THz)')
    xlabel('Number of samples')    


def monitor_phonons(directory='phon', dfset='DFSET', prefix='cryst', order=1, cutoff=10, born=None):
    bnd_lst = build_bnd_lst()
    prev_N = 0
    
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

    with open(f'{directory}/{prefix}.bands') as f:
        p_lbl = f.readline().split()[1:]
        p_pnt = [float(v) for v in f.readline().split()[1:]]
    kpnts = {k:v for k,v in zip(p_lbl, p_pnt)}
    fig = None
    while True :
        N = get_dfset_len(f'{directory}/{dfset}')
        if N > prev_N :
            run_alamode(d=directory, o=order, n=N, c2=cutoff, born=born)
            bnd_lst[N]=loadtxt(f'{directory}/{prefix}.bands').T
            if fig is not None:
                plt.close(fig)
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


def plot_stats(T=300, base_dir='phon', dfsetfn='DFSET', sqrN=False, show=True):
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
    fit = stats.chi2.fit(es, f0=3*nat)
    plt.plot(e,  stats.chi2.pdf(e, *fit), '--', color='C4', label='Fitted $\\chi^2$ dist.', zorder=10)
    plt.xlabel('Potential energy (eV/at)')
    plt.ylabel('Probability density')
    plt.xlim(E_goal-3*Es,E_goal+3*Es)
    plt.legend(loc='upper left', bbox_to_anchor=(0.7,0.5,0.5,0.5))
    if show :
        plt.show()

def monitor_stats(T=300, directory='phon', dfset='DFSET'):
    
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
            plot_stats(T=T, base_dir=directory, dfsetfn=dfset)
            show()
            clear_output(wait=True)
            prev_N = N
        else :
            sleep(15)
