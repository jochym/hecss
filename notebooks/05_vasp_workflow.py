import marimo

__generated_with = "0.24.0"
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
    #|vasp
    # Import VASP calculator and unit modules
    from ase.calculators.vasp import Vasp
    from ase import units as un
    from os.path import isfile
    import os

    # The sample generator, monitoring display and dfset writer
    from hecss import HECSS
    from hecss.util import write_dfset
    from hecss.monitor import plot_stats

    # Numerical and plotting routines
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
    #| vasp
    # Quick test using conventional unit cell
    supercell = '1x1x1'
    return


@app.cell
def _():
    #| vasp
    #| slow
    # Slow more realistic test
    supercell_1 = '2x2x2'
    return


@app.cell
def _():
    #|hide
    #|eval: false
    # Reset supercell for interactive work (not executed in tests)
    supercell_2 = '1x1x1'
    return (supercell_2,)


@app.cell
def _(TemporaryDirectory, supercell_2):
    #|vasp
    # Directory in which our project resides
    base_dir = f'example/VASP_3C-SiC/{supercell_2}/'
    calc_dir = TemporaryDirectory(dir='TMP')
    return base_dir, calc_dir


@app.cell
def _(Vasp, base_dir, supercell_2):
    #| vasp
    # Read the structure (previously calculated unit(super) cell)
    # The command argument is specific to the cluster setup
    calc = Vasp(label='cryst', directory=f'{base_dir}/sc_{supercell_2}/', restart=True)
    # This just makes a copy of atoms object
    # Do not generate supercell here - your atom ordering will be wrong!
    cryst = calc.atoms.repeat(1)
    return calc, cryst


@app.cell
def _(calc, calc_dir, cryst, os):
    #|vasp
    # Setup the calculator - single point energy calculation
    # The details will change here from case to case
    # We are using run-vasp from the current directory!
    calc.set(directory=f'{calc_dir.name}/sc')
    calc.set(command=f'{os.getcwd()}/run-calc.sh "vasp_test"')
    calc.set(nsw=0)
    cryst.calc = calc
    return


@app.cell
def _(calc, un):
    #|vasp
    print('Stress tensor: ', end='')
    for ss in calc.get_stress()/un.GPa:
        print(f'{ss:.3f}', end=' ')
    print('GPa')
    return


@app.cell
def _(defaultdict):
    #|vasp
    # Prepare space for the results.
    # We use defaultdict to automatically
    # initialize the items to empty list.
    samples = defaultdict(lambda : [])

    # Space for amplitude correction data
    xsl = []
    return (samples,)


@app.cell
def _(HECSS, calc, calc_dir, cryst):
    #|vasp
    # Build the sampler
    hecss = HECSS(cryst, calc, 
                  directory=calc_dir.name,
                  w_search = True,
                  pbar=True,
                  )
    return (hecss,)


@app.cell
def _(hecss, np, plt, un):
    #|vasp
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
    #|hide
    #|vasp
    assert len(glob(f'{calc_dir.name}/w_est/*/vasprun.xml')) == N
    return


@app.cell
def _(hecss, samples):
    #|vasp
    # Desired number of samples and T list.
    N_1 = 30
    T_list = (100, 200, 300)
    for T in T_list:
        samples[T] = samples[T] + hecss.sample(T, N_1)
    return (T_list,)


@app.cell
def _(T_list, hecss, plot_stats, samples):
    #|vasp
    # Plot the resulting distributions
    for T_1 in T_list:
        plot_stats(hecss.generate(samples[T_1]), sqrN=True)
    return


@app.cell
def _(T_list, calc_dir, glob, samples):
    #|hide
    #|vasp
    for T_2 in T_list:
        assert len(glob(f'{calc_dir.name}/T_{T_2:.1f}K/smpl/*')) == len(samples[T_2])
    return


@app.cell
def _(calc_dir, glob):
    #|hide
    #|vasp
    # Test if all the calculations are run in separate dirs only once 
    for d in ([f'{calc_dir.name}/sc'] + 
              glob(f'{calc_dir.name}/w_est/???') + 
              glob(f'{calc_dir.name}/*/smpl/*')):
        try :
            assert len(glob(f'{d}/slurm*.out')) == 1
        except AssertionError:
            print(f'Wrong number of calculations in: {d}')
            if d.endswith('smpl/0000'):
                print('Inittial burn-in samples. This is OK. Ignoring')
            else :
                raise
    return


@app.cell
def _():
    #|hide
    #|vasp
    #|eval: false
    CLEANUP=False
    return (CLEANUP,)


@app.cell
def _(CLEANUP, calc_dir):
    #|hide
    #|vasp
    try :
        CLEANUP
    except NameError:
        calc_dir.cleanup()
    return


if __name__ == "__main__":
    app.run()
