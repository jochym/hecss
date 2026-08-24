import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    #| default_exp monitor_bands
    return


@app.cell
def _(THz, plot, un):
    #| export
    #| export
    #| export
    def plot_band_set(bnd, units=THz, lbl=None, **kwargs):
        if lbl is None:
            lbl=''
        kwa = {k:v for k, v in kwargs.items() if k not in ('color',)}
        plt=plot(bnd[0], un.invcm * bnd[1] / units, label=lbl, **kwargs)
        for b in bnd[2:]:
            plot(bnd[0], un.invcm * b / units, color=plt[0].get_color(), **kwa)

    return (plot_band_set,)


@app.cell
def _(THz, axhline, axvline, plot_band_set, xlabel, xlim, xticks, ylabel):
    #| export
    #| export
    #| export
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

    return (plot_bands,)


@app.cell
def _(THz, loadtxt, plot_bands):
    #| export
    #| export
    #| export
    def plot_bands_file(fn, units=THz, decorate=True, lbl=None, **kwargs):
        bnd = loadtxt(fn).T

        with open(fn) as f:
            p_lbl = [l if l!='G' else '$\\Gamma$' for l in f.readline().split()[1:]]
            p_pnt = [float(v) for v in f.readline().split()[1:]]
        kpnts = (p_lbl, p_pnt)

        if lbl is None:
            lbl=fn

        plot_bands(bnd, kpnts, units, decorate, lbl, **kwargs)

    return


if __name__ == "__main__":
    app.run()
