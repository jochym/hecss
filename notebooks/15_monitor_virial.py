import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    #| default_exp monitor_virial
    return


@app.cell
def _(array, axvline, legend, plot_hist, title, un, xlabel, xlim, ylabel):
    #| export

    def plot_virial_stat(cryst, smpl, T, normal=False):
        elems = cryst.get_chemical_symbols()
        vir = array([abs(s[2]*s[3]) for s in smpl])/(un.kB*T)
        nat = len(elems)
        m, s = plot_hist(vir.mean(axis=(-1,-2)), 'Total', 0, normal=True)
        for n, el in enumerate(set(elems)):
            elmask = array(elems)==el
            plot_hist(vir[:, elmask, :].mean(axis=(-1,-2)), 
                      el, n+1, normal=normal, df=3*sum(elmask))
        axvline(T/T, ls=':', color='C5', label=f'{T:.0f} K')
        xlim(m - 5*s, m + 7*s)
        legend()
        title('Virial distribution in the sample')
        ylabel('Probability density')
        xlabel('Virial/Temperature');

    return


@app.cell
def _(
    Counter,
    arange,
    array,
    axvspan,
    chemical_symbols,
    ewma,
    figure,
    get_cell_data,
    get_symmetry_dataset,
    legend,
    moving_average,
    plot,
    plot_hist,
    semilogy,
    show,
    title,
    xlabel,
    xlim,
    ylabel,
):
    #| export

    def plot_dofmu_stat(cryst, dofmu, skip=10, window=10, normal=False):
        symm = get_symmetry_dataset(get_cell_data(cryst))
        dofmap = symm.mapping_to_primitive
        dof = set(dofmap)
        dofmul = Counter(symm.mapping_to_primitive)
        elems = dict(zip(symm.std_mapping_to_primitive, symm.std_types))
        elmap = array(sorted(elems.items())).T
        xdof = array(dofmu)
        skip = min(skip, len(dofmu)//2)
        window = min(window, len(dofmu)//2)

        figure(figsize=(10,4))

        for i, el in enumerate(set(elmap[1])):
            n = len(xdof)
            elmask = elmap[1]==el
            semilogy()
            plot(xdof[:,elmask,:].reshape((-1,3*sum(elmask))),
                     '.', color=f'C{i}', ms=1, alpha=0.2)

            asx = moving_average(xdof[:,elmask,:].mean((-1,-2)), window)
            plot((n-len(asx))//2+arange(len(asx)), asx, '--',
                     label=f'{chemical_symbols[el]} (ma, w={window})', color=f'C{i}');

            asx = ewma(xdof[:,elmask,:].mean((-1,-2)), window)
            plot((n-len(asx))//2+arange(len(asx)), asx, 
                     label=f'{chemical_symbols[el]} (ewma, w={window})', color=f'C{i}');

        axvspan(0, skip, color='k', alpha=0.2)
        title('Virial history')
        xlabel('Steps')
        ylabel('Virial/Temperature V$_{DOF}$/T')
        legend();
        show();

        mi, ma = -1, -1

        for i, el in enumerate(set(elmap[1])):
            elmask = elmap[1]==el
            m, s = plot_hist(xdof[skip:,elmask,:].mean((-2, -1)), 
                             chemical_symbols[el], i,
                             normal=normal, df=3*sum(elmask))
            if mi < 0 or mi > m-3*s:
                mi = m-3*s
            if ma < 0 or ma < m+4*s:
                ma = m+4*s
        legend();
        xlim(mi, ma)
        title('Virial distribution')
        ylabel('Probability density')
        xlabel('Virial/Temperature')
        show() ;

    return


@app.cell
def _(
    Counter,
    arange,
    array,
    axvspan,
    chemical_symbols,
    ewma,
    get_cell_data,
    get_symmetry_dataset,
    legend,
    moving_average,
    plot,
    plot_hist,
    plt,
    show,
    title,
    xlabel,
    xlim,
    ylabel,
):
    #| export

    def plot_xs_stat(cryst, xsl, skip=10, window=10):
        symm = get_symmetry_dataset(get_cell_data(cryst))
        dofmap = symm.mapping_to_primitive
        dof = set(dofmap)
        dofmul = Counter(symm.mapping_to_primitive)
        elems = dict(zip(symm.std_mapping_to_primitive,symm.std_types))
        elmap = array(sorted(elems.items())).T
        elmap = cryst.get_atomic_numbers()
        xdof = array(xsl)
        skip = min(skip, len(xsl)//2)
        window = min(window, len(xsl)//2)

        plt.figure(figsize=(10,4))

        for i, el in enumerate(set(elmap)):
            n = len(xdof)
            plot(xdof[:,elmap==el,:].mean((-2,-1)),
                     '.', color=f'C{i}', ms=2, alpha=0.25)

            asx = moving_average(xdof[:,elmap==el,:].mean((-1,-2)), window)
            plot((n-len(asx))//2 + arange(len(asx)), asx, '--',
                     label=f'{chemical_symbols[el]} (ma, w={window})', color=f'C{i}');

            asx = ewma(xdof[:,elmap==el,:].mean((-1,-2)), window)
            plot((n-len(asx))//2 + arange(len(asx)), asx, 
                     label=f'{chemical_symbols[el]} (ewma, w={window})', color=f'C{i}');

        axvspan(0, skip, color='k', alpha=0.2)

        title('Amplitude correction history')
        xlabel('Steps')
        ylabel('Virial/Temperature V$_{DOF}$/T')
        legend();
        show();

        mi, ma = -1, -1
        for i, el in enumerate(set(elmap)):
            m, s = plot_hist(xdof[skip:,elmap==el,:].mean((-2,-1)), 
                      chemical_symbols[el], i)
            if mi < 0 or mi > m-3*s:
                mi = m-3*s
            if ma < 0 or ma < m+3*s:
                ma = m+3*s
        legend();
        xlim(mi, ma)
        title('Amplitude correction distribution')
        ylabel('Probability density')
        xlabel('Virial/Temperature')
        show() ;

    return


if __name__ == "__main__":
    app.run()
