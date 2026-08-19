import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # VASP workflow

    > VASP workflow demo.

    These are tests for various aspects of the "typical" use with VASP calculator. At the same time this is an example of the typical VASP workflow with scan over multiple temperatures.
    """)
    return


@app.cell
def _():
    from ase.calculators.vasp import Vasp
    from ase import units as un
    from os.path import isfile
    import os

    from hecss import HECSS
    from hecss.util import write_dfset
    from hecss.monitor import plot_stats

    import numpy as np
    from matplotlib import pyplot as plt
    from collections import defaultdict
    from tempfile import TemporaryDirectory
    from glob import glob

    return (
        HECSS,
        TemporaryDirectory,
        Vasp,
        defaultdict,
        glob,
        np,
        os,
        plot_stats,
        plt,
        un,
    )


@app.cell
def _():
    supercell = '1x1x1'
    return (supercell,)


@app.cell
def _():
    supercell_1 = '2x2x2'
    return (supercell_1,)


@app.cell
def _():
    supercell_2 = '1x1x1'
    return (supercell_2,)


@app.cell
def _(TemporaryDirectory, supercell_2):
    base_dir = f'example/VASP_3C-SiC/{supercell_2}/'
    calc_dir = TemporaryDirectory(dir='TMP')
    return base_dir, calc_dir


@app.cell
def _(Vasp, base_dir, supercell_2):
    calc = Vasp(label='cryst', directory=f'{base_dir}/sc_{supercell_2}/', restart=True)
    cryst = calc.atoms.repeat(1)
    return calc, cryst


@app.cell
def _(calc, calc_dir, cryst, os):
    calc.set(directory=f'{calc_dir.name}/sc')
    calc.set(command=f'{os.getcwd()}/run-calc.sh "vasp_test"')
    calc.set(nsw=0)
    cryst.calc = calc
    return


@app.cell
def _(calc, un):
    print('Stress tensor: ', end='')
    for ss in calc.get_stress()/un.GPa:
        print(f'{ss:.3f}', end=' ')
    print('GPa')
    return


@app.cell
def _(defaultdict):
    samples = defaultdict(lambda: [])
    xsl = []
    return (samples,)


@app.cell
def _(HECSS, calc, calc_dir, cryst):
    hecss = HECSS(cryst, calc,
                  directory=calc_dir.name,
                  w_search=True,
                  pbar=True)
    return (hecss,)


@app.cell
def _(hecss, np, plt, un):
    N = 5
    m, s, xscl = hecss.estimate_width_scale(5, nwork=0)
    wm = np.array(hecss._eta_list).T
    y = np.sqrt((3*wm[1]*un.kB)/(2*wm[2]))
    plt.plot(wm[1], y, '.');
    x = np.linspace(0, 1.05*wm[1].max(), 2)
    fit = np.polyfit(wm[1], y, 1)
    plt.plot(x, np.polyval(fit, x), ':', label=f'{fit[1]:.4g} {fit[0]:+.4g} T')
    plt.axhline(m, ls='--', label=f'{m:.4g}±{s:.4g}')
    plt.axhspan(m-s, m+s, alpha=0.3)
    plt.ylim(m-4*s, m+4*s)
    plt.xlabel('Target temperature (K)')
    plt.ylabel('width scale ($\\AA/\\sqrt{K}$)')
    plt.legend();
    return (N,)


@app.cell
def _(N, calc_dir, glob):
    assert len(glob(f'{calc_dir.name}/w_est/*/vasprun.xml')) == N
    return


@app.cell
def _(hecss, samples):
    N_1 = 30
    T_list = (100, 200, 300)
    for T in T_list:
        samples[T] = samples[T] + hecss.sample(T, N_1)
    return (T_list,)


@app.cell
def _(T_list, hecss, plot_stats, samples):
    for T_1 in T_list:
        plot_stats(hecss.generate(samples[T_1]), sqrN=True)
    return


@app.cell
def _(T_list, calc_dir, glob, samples):
    for T_2 in T_list:
        assert len(glob(f'{calc_dir.name}/T_{T_2:.1f}K/smpl/*')) == len(samples[T_2])
    return


@app.cell
def _(calc_dir, glob):
    for d in ([f'{calc_dir.name}/sc'] +
              glob(f'{calc_dir.name}/w_est/???') +
              glob(f'{calc_dir.name}/*/smpl/*')):
        try:
            assert len(glob(f'{d}/slurm*.out')) == 1
        except AssertionError:
            print(f'Wrong number of calculations in: {d}')
            if d.endswith('smpl/0000'):
                print('Initial burn-in samples. This is OK. Ignoring')
            else:
                raise
    return


@app.cell
def _():
    CLEANUP = False
    return (CLEANUP,)


@app.cell
def _(CLEANUP, calc_dir):
    _ = None
    try:
        _ = CLEANUP
    except NameError:
        calc_dir.cleanup()
    return


if __name__ == "__main__":
    app.run()