import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    #| default_exp monitor_stats
    return


@app.cell
def _(fromiter, histogram, linspace, plt, sqrt, stats, un):
    #| export
    #| export
    #| export
    def plot_stats(confs, T=None, sqrN=False, show=True, 
                   plotchi2=False, show_samples=True):
        '''
        Plot monitoring histograms for the configuration list in confs.
        If len(confs)<3 this function is silent.

        confs - configuration list
        T     - target temperature in Kelvin
        show  - call show() fuction at the end (default:True)
        show_samples - show individual samples above the histogram
        '''

        if len(confs) < 3:
            return

        #E0 = Vasp2(restart=base_dir+'/../calc/').get_potential_energy()
        #es = [(Vasp2(restart=d).get_potential_energy()-E0)/nat
        #          for d in sorted(glob(base_dir+'/../calc/T_600.0K/smpl/0*/'))]
    
        es = fromiter((_[-1] for _ in confs), float)

        if T is None:
            T = 2*es.mean()/3/un.kB
    
        nat = confs[0][-3].shape[0]
    
        E_goal = 3*T*un.kB/2
        Es = sqrt(3/2)*un.kB*T/sqrt(nat)
        e = linspace(E_goal - 3*Es, E_goal + 3*Es, 200)
        n = len(es)
        us = list(set(es))

        plt.hist(es, bins='auto', density=False, label=f'{n}({len(us)}) samples', alpha=0.5, rwidth=0.4, zorder=0)
        h = histogram(es, bins='auto', density=False)
        de = (h[1][-1]-h[1][0])/len(h[0])
        N = len(es)
        if sqrN :
            plt.errorbar((h[1][:-1]+h[1][1:])/2, h[0],
                         yerr=sqrt(h[0]), fmt='+', color='C0', alpha=0.66,
                         capsize=6, label='$\\pm\\sqrt{n}$')
            # plt.errorbar((h[1][:-1]+h[1][1:])/2, h[0],
            #              yerr=2*sqrt(h[0]), fmt='+', color='C0', alpha=0.33,
            #              capsize=4, label='$2/\\sqrt{N}$')

        plt.axvline(E_goal, ls='--', color='C2', label=f'Target energy {T:.2f} K')
        pdf = N*de*stats.norm.pdf(e, E_goal, Es)
        plt.fill_between(e,  (pdf-sqrt(pdf)).clip(min=0), pdf+sqrt(pdf), label='$\\sigma, 2\\sigma, 3\\sigma$', color='C1', alpha=0.1, zorder=9)
        plt.fill_between(e,  (pdf-2*sqrt(pdf)).clip(min=0), pdf+2*sqrt(pdf), color='C1', alpha=0.1, zorder=9)
        plt.fill_between(e,  (pdf-3*sqrt(pdf)).clip(min=0), pdf+3*sqrt(pdf), color='C1', alpha=0.1, zorder=9)
        plt.plot(e, pdf, '--', color='C1', label='Target normal dist.')
        fit = stats.norm.fit(es)
        plt.plot(e,  N*de*stats.norm.pdf(e, *fit), '--', color='C3', label='Fitted normal dist.', zorder=10)
        if plotchi2 :
            fit = stats.chi2.fit(es, f0=3*nat)
            plt.plot(e,  stats.chi2.pdf(e, *fit), '--', color='C4', label='Fitted $\\chi^2$ dist.', zorder=10)
        
        if show_samples:
            skip = len(us)//2000
            skip = int(max(1, skip))
            a = sqrt(2/(len(us)//skip))
            a = max(a, 0.01)
            a = min(a, 1)
            for s in us[::skip]:
                plt.axvline(s, ymin=0.97, ymax=0.99, 
                            ls='-', lw=1, color='r', alpha=a)
     
        plt.xlabel('Potential energy (meV/at)')
        plt.ylabel('Samples')
        plt.xlim(E_goal-3*Es,E_goal+3*Es)
        plt.legend(loc='upper right', bbox_to_anchor=(1.08, 0.965))
        if show :
            plt.show()

    return (plot_stats,)


@app.cell
def _(clear_output, get_dfset_len, load_dfset, plot_stats, show, sleep, sys):
    #| export
    def monitor_stats(T, dfset, plotchi2=False, sqrN=False, once=False):

        prev_N = get_dfset_len(dfset)-1

        if get_dfset_len(dfset) < 3:
            print('Waiting for the first samples (>2).', end='')
            sys.stdout.flush()
            while get_dfset_len(dfset) < 3:
               sleep(15)
               print('.', end='')
               sys.stdout.flush()
            print('done.', end='')
        print('Calculating the plots.',)
        sys.stdout.flush()
        clear_output(wait=True)

        while True :
            N = get_dfset_len(dfset)
            if N > prev_N :
                plot_stats(load_dfset(dfset), T=T, plotchi2=plotchi2, sqrN=sqrN)
                show()
                if once:
                    break
                clear_output(wait=True)
                prev_N = N
            else :
                sleep(15)

    return


@app.cell
def _(arange, array, cumsum, figure, plot, xlabel, ylabel):
    #| export

    def plot_acceptance_history(smpl):
        figure(figsize=(10,4))
        na = array([n for i, n, x, f, e in smpl])
        na = cumsum((na[1:]-na[:-1])%2)
        plot(100*(na/arange(1,len(na)+1))[1:])
        xlabel('Step')
        ylabel('Acceptance ratio (approx., %)');

    return


if __name__ == "__main__":
    app.run()
