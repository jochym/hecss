import marimo

__generated_with = "0.23.16"
app = marimo.App()
#| default_exp monitor_stats


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Sampling statistics monitoring

    > Monitoring of statistics of the generated sampling is possible using functions provided in the `hecss.monitor` module: `plot_stats` (for static plots) and `monitor_stats` (for "live" plots).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The two functions are essentially the same except for the *live* aspect. They display the energy distribution in the sample relative to the target distribution (determined by the temperature). The shaded areas indicate 1,2,3$\sigma$ intervals for the distribution. The fitted distribution is a gaussian curve fitted to the sample. The the data sets presented here are examples provided in the
    `example/VASP_3C-SiC_calculated/` directory of the source distribution. Refer to the `Setup` document for information about installation of the source distribution.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Interpreting the statistics plot

    The sampling statistics plots show a number of characteristics of the generated sample. The orange bell curve with green central line shows target energy distribution for a given temperature. The shaded orange regions indicate $\sigma, 2\sigma,$ and $3\sigma$ zones around this distribution.
    The width of the standard deviation band is determined by the square of the target distribution scaled to the size of the sample and number of bins in the histogram. The blue-shaded bars show population in each bin of the histogram and red dashed curve is a normal distribution fitted to the data points in the sample. In general, both bars of the histogram and fitted distribution should fit inside the $3\sigma$ band - such distribution should be considered a correct sampling of the target distribution. However, in small samples the statistical fluctuations are large and sometimes this condition is not met. In such cases the size of the variance of the actual bin of the histogram should be considered. This value is not plotted by default, but may be switched on with `sqrN=True` parameter to `plot_stats` function. The hi-lo bars on top of histogram bins indicate *one standard deviation* intervals around the value of the histogram bin. You have to judge for yourself when the dstribution is satisfactorily reproduced. In general $2\sigma$ bars of the target and the bin should overlap.
    """)
    return


@app.cell
def _():
    #| hide
    #| hide
    from hecss.monitor import monitor_stats, plot_stats, load_dfset
    return load_dfset, monitor_stats, plot_stats


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Single data plot
    """)
    return


@app.cell
def _(load_dfset, plot_stats):
    T = 300
    supercell = '2x2x2'
    plot_stats(load_dfset(f'example/VASP_3C-SiC_calculated/{supercell}/T_{T:.0f}K/DFSET.dat'),
               T=T, sqrN=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Live plot

    Here, presented with optional `once=True` argument making it run just once. If you want to actually monitor the calculation live you shoul omit this option.
    """)
    return


@app.cell
def _(monitor_stats):
    #| export
    #| export
    T_1 = 600
    supercell_1 = '1x1x1'
    monitor_stats(T=T_1, dfset=f'example/VASP_3C-SiC_calculated/{supercell_1}/T_{T_1:.0f}K/DFSET.dat', once=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Multiple plots

    Example of multiple plots showing all pre-calculated data included in the source package. This example demonstrates how the `plot_stats` function may be used to build more complex figures (e.g. for
    inclusion in publication).
    """)
    return


@app.cell
def _(load_dfset, plot_stats):
    from glob import glob
    from matplotlib import pyplot as plt
    fig, axs = plt.subplots(4, 2, figsize=(14, 14))
    for n, d in enumerate(sorted(glob('example/VASP_3C-SiC_calculated/?x?x?/T_*K'), key=lambda s: (s.split('/')[-2], float(s.split('/')[-1][2:-1])))):
        T_2 = float(d.split('/')[-1][2:-1])
        sc = d.split('/')[-2]
        plt.sca(axs[n % 4][n // 4])
        plot_stats(load_dfset(f'{d}/DFSET.dat'), T=T_2, show=False)
        plt.text(0.05, 0.8, f'{sc}\n T={T_2}K', transform=plt.gca().transAxes)
    return


if __name__ == "__main__":
    app.run()