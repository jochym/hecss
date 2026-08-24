import marimo

__generated_with = "0.23.16"
app = marimo.App()
#| default_exp cli


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import subprocess
    return (subprocess,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # CLI

    > The command line interface for the HECSS sampler
    """)
    return


@app.cell
def _():
    #| hide
    #| hide
    import click
    from pathlib import Path
    import os
    import ase
    from ase.calculators.vasp import Vasp
    from ase import units as un
    from numpy import savetxt, loadtxt, array, sqrt
    import hecss
    from hecss.util import write_dfset, calc_init_xscale
    from hecss.optimize import make_sampling
    import traceback
    from tempfile import TemporaryDirectory
    import ast

    return (
        Path, TemporaryDirectory, Vasp, click, traceback,
        os, ase, un, savetxt, loadtxt, array, sqrt,
        hecss, write_dfset, calc_init_xscale, make_sampling,
        ast,
    )


@app.cell
def _(TemporaryDirectory):
    #| hide
    #| hide
    calc_dir = TemporaryDirectory(dir='TMP')
    calc_dir_2 = TemporaryDirectory(dir='TMP')
    return calc_dir, calc_dir_2


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Command line hecss sampler
    """)
    return


@app.cell
def _():
    #| hide
    #| hide
    _version_message = ("HECSS, version %(version)s\n"
                        'High Efficiency Configuration Space Sampler\n'
                        '(C) 2021-2024 by Paweł T. Jochym\n'
                        '    License: GPL v3 or later')
    return (_version_message,)


@app.cell
def _(CliRunner, traceback):
    #| hide
    #| hide
    def run_cli_cmd(cmd, args, prt_result=False):
        print(f'$ {cmd.name} {args}\n')
        run = CliRunner().invoke(cmd, args)
        print(run.output)
        if prt_result or run.exit_code != 0:
            print(run)
            if run.exit_code != 0:
                traceback.print_tb(run.exc_info[-1])

    return (run_cli_cmd,)


@app.cell
def _(Path, savetxt, write_dfset):
    #| hide
    #| hide
    def dfset_writer(s, sl, workdir='', dfset='', scale='', xsl=None):
        '''
        Write samples to the DFSET file in the workdir directory.
        If the scale and xsl list are not empy save amplitude correction
        and empty the xsl list (!).
        '''
        wd = Path(workdir)
        write_dfset(f'{wd.joinpath(dfset)}.raw', s)
        if scale and xsl:
            with open(wd.joinpath(scale), 'at') as sf:
                for xs in xsl:
                    savetxt(sf, xs, fmt='%8.5f', header=f'{xs.shape}, {len(sl)}, {len(xsl)}')
            xsl.clear()
        return False

    return (dfset_writer,)


@app.cell
def _(
    HECSS,
    Path,
    Vasp,
    array,
    ase,
    ast,
    click,
    dfset_writer,
    hecss,
    loadtxt,
    sqrt,
    un,
    write_dfset,
    _version_message,
):
    @click.command()
    @click.argument('fname', type=click.Path(exists=True))
    @click.option('-W', '--workdir', default="WORK", type=click.Path(exists=True), help="Work directory")
    @click.option('-l', '--label', default="hecss", help="Label for the calculations.")
    @click.option('-T', '--temp', default=300, type=float, help="Target temperature in Kelvin.")
    @click.option('-w', '--width', default=None, type=float, help="Initial scale of the prior distribution")
    @click.option('-a', '--ampl', default='', type=click.Path(), help='Initialise amplitude correction from the file.')
    @click.option('-s', '--scale', default='', type=click.Path(), help='Save amplitude correction history')
    @click.option('-m', '--symprec', default=1e-5, type=float, help='Symmetry search tolerance.')
    @click.option('-C', '--calc', default="VASP", type=str,
                  help="ASE calculator to be used for the job. "
                       "Supported calculators: VASP (default)")
    @click.option('-S', '--setups', default="guess", type=str,
                  help="setups parameter of the calculator to force use of the "
                       "particular variants of pseudopotentials in the calculations. "
                       "By default pseudopotentials are guessed from the POTCAR in "
                       "the supercell directory.")
    @click.option('-n', '--nodfset', is_flag=True, default=False, help='Do not write DFSET file for ALAMODE')
    @click.option('-d', '--dfset', default='DFSET.dat', help='Name of the DFSET file')
    @click.option('-N', '--nsamples', default=10, type=int, help="Number of samples to be generated")
    @click.option('-e', '--neta', default=2, type=int, help="Number of samples for width scale estimation")
    @click.option('-c', '--command', default='./run-calc', help="Command to run calculator")
    @click.option('-k', '--nwork', default=None, type=int, help="Number of parallel workers to run (0=unlimited)")
    @click.option('-p', '--pbar', is_flag=True, default=True, help="Do not show progress bar")
    @click.version_option(hecss.__version__, '-V', '--version', message=_version_message)
    @click.help_option('-h', '--help')
    def hecss_sampler(fname, workdir, label, temp, width, ampl, scale, symprec, calc, setups, nodfset, dfset, nsamples, neta, command, nwork, pbar):
        '''
        Run HECSS sampler on the structure in the provided file (FNAME).\b
        Read the docs at: https://jochym.github.io/hecss/

        \b
        FNAME - Supercell structure file. The containing
                directory must be readable by Vasp(restart).
                Usually this is a CONTCAR file for a supercell.
        '''

        print(f'HECSS ({hecss.__version__})\n'
              f'Supercell:      {fname}\n'
              f'Temperature:    {temp}K\n'
              f'Work directory: {workdir}\n'
              f'Calculator:     {calc}')

        src_path = Path(fname)
        workdir = Path(workdir)
        Ep0 = None
        if calc == "VASP":
            calculator = Vasp(label=label, directory=src_path.parent, restart=True)
            Ep0 = calculator.get_potential_energy()
            cryst = ase.Atoms(calculator.atoms)
            cryst.calc = calculator
            calculator.set(directory=workdir)
            command = Path(command)
            calculator.set(command=f'{command.absolute()} {label}')
            calculator.set(nsw=0)
            if setups:
                if setups == 'guess':
                    setups = {}
                    with open(src_path.parent / Path("POTCAR"), "r") as pf:
                        for l in pf.readlines():
                            if "TITEL" in l:
                                l = l.strip().split()[3].split("_")
                                el = l[0]
                                st = ""
                                if len(l) > 1:
                                    st = f"_{l[1]}"
                                setups[el] = st
                    print(f"Setups guessed from {src_path.parent / Path('POTCAR')}: {setups}")
                else:
                    if setups in {'recommended', 'minimal', 'gw'}:
                        pass
                    else:
                        setups = ast.literal_eval(setups)
                    print(f"Setups forced: {setups}")
                calculator.set(setups=setups)
        else:
            print(f'The {calc} calculator is not supported.')
            return

        if nodfset:
            sentinel = None
        else:
            sentinel = dfset_writer

        xsl = None
        if scale:
            xsl = []

        wl = []

        sampler = HECSS(cryst, calculator, directory=workdir, width=width, pbar=pbar)
        sampler.Ep0 = Ep0

        if ampl:
            sampler.xscale_init = loadtxt(ampl)

        if width is not None and neta > 0:
            print('Conflicting parameters: -w and -e')
            print('Either specify width or run the estimation.')
            print('Refusing the job.')
            return

        if nsamples < 2 and scale:
            print('Need at least 2 samples (-N 2) to calculate amplitudes (-s).')
            print('Refusing the job.')
            return

        if nsamples < 1:
            print('WARNING: No samples will be generated (N=0)')
            print('Continue with the job')

        if width is None and neta > 0:
            if (workdir / 'w_est').exists():
                print(f'Directory {workdir / "w_est"} exists.')
                print('Make sure you specified correct working directory.')
                print('I refuse to overwrite existing calculations.')
                print(f'Either specify w on the command line, \n'
                      f'or remove w_est directory from {workdir}.')
                if (workdir / 'w_est/w_est.dat').exists():
                    wm = loadtxt(workdir / 'w_est/w_est.dat').T
                    y = sqrt((3 * wm[1] * un.kB) / (2 * wm[2]))
                    print(f'Width scale from {workdir / "w_est/w_est.dat"} data: {y.mean():.3g}+/-{y.std():.3g}')
                return
            print('Estimating width scale.')
            eta, sigma, xscale = sampler.estimate_width_scale(neta, Tmin=temp/2, Tmax=temp, pbar=sampler._pbar, nwork=nwork)
            if nsamples < 2:
                print(f'Width scale from {neta} pts.: {eta:.3g}+/-{sigma:.3g}')
                print('Width scale estimation run (N<2). Not running sampling.')
                return

        if (workdir / f"T_{temp:.1f}K").exists():
            print(f'Directory {workdir / f"T_{temp:.1f}K"} exists.')
            print('Make sure you specified correct working directory.')
            print('I refuse to overwrite existing calculations.')
            print(f'Correct your workdir or move {workdir / f"T_{temp:.1f}K"} to a different location.')
            return

        print('Sampling configurations')
        samples = sampler.sample(temp, nsamples,
                                 width_list=wl,
                                 sentinel=dfset_writer,
                                 sentinel_args={'workdir': f'{workdir}/T_{temp:.1f}K/',
                                                'dfset': dfset,
                                                'scale': scale,
                                                'xsl': xsl
                                               },
                                 xscale_list=xsl,
                                 symprec=symprec)
        # generate distribution centered at mean energy
        T_m = 2 * array([s[-1] for s in samples]).mean() / 3 / un.kB
        print(f'Generating distribution centered at: {T_m:.3f} K')
        distr = sampler.generate(samples, T_m)
        if len(wl) > 1:
            wl = array(wl).T
            print(f'Average width scale ({len(wl[0])} pnts): {wl[0].mean():.3g}+/-{wl[0].std():.3g}')

        if not nodfset:
            wd = Path(workdir)
            for s in distr:
                write_dfset(f'{wd.joinpath(dfset)}', s)

        return

    return (hecss_sampler,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The HECSS sampler can be also used from the command line using `hecss-sampler` command:
    """)
    return


@app.cell
def _(hecss_sampler, run_cli_cmd):
    #| hide
    #| hide
    run_cli_cmd(hecss_sampler, '-V')
    run_cli_cmd(hecss_sampler, '--help')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    To use it you need to prepare:

    1. `run-calc` script which should start the VASP calculation. You need to put this script in the root of your project tree. The example of such a script is included in the source as `run-calc.example`. :
    ```bash
    #!/bin/bash

    # This script should run vasp in current directory
    # and wait for the run to finish.
    #
    # A generic line using SLURM would look like this:
    #
    # sbatch [job_params] -W vasp_running_script
    #
    # The "-W" param makes the sbatch command wait for the job to finish.

    JN=`pwd`
    JN=`basename ${JN}`

    # Partition of the cluster
    PART=small

    # Number of nodes
    N=1

    # Number of MPI tasks
    ntask=64

    # Name the job after directory if no label is passed as first argument
    if [ "${1}." != "." ]; then
      JN=${1}
    fi

    sbatch -W -J ${JN} -p $PART -N $N -n $ntask run-vasp-script
    ```

    2. A directory with fully converged and optimized supercell structure which can be read in by the ASE `Vasp(restart=...)` command

    3. A directory for the generated samples.

    The directory tree may look like this:

    ```
    my_project ----- sc
                 |
                 +-- T_100
                 |
                 +-- T_200
                 |
                 +-- ...
                 |
                 +-- run-calc
    ```

    You execute the sampler from the `my_project` directory (remember to activate your virtual environment first). Generation of N=30 samples at T=100K:

    ```bash
    ~$ cd my_project
    ~$ hecss_sampler -W T_100 -T 100 -N 30 -c ./run-calc sc/CONTCAR
    ```

    The above command will put the generated samples inside the `T_100` directory, together with the DFSET file with displacement-force data extracted from the calculation. The calculation may take a long time. Thus it is advisable to execute the hecss command inside `screen` (or some similar terminal multiplexer) to prevent the break of the calculation in case of session disconnection. The `hecss` command shows a progress to guide you through the calculation (ETA, time/it, data about last sample etc.). The example run is included at the bottom of this document.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Width scale estimation

    Calling the sampler with N=0 runs only width scale (eta) estimation procedure for the temperature range 0-T Kelvin. The calculated value may be used as the -w parameter in subsequent calculations. Possibly even for temperatures outside of this range.
    """)
    return


@app.cell
def _(calc_dir, hecss_sampler, run_cli_cmd):
    #| export
    #| export
    run_cli_cmd(hecss_sampler,
                f"-W {calc_dir.name} "
                "-T 1000 -N 0 -e 10 "
                "-k 0 "
                "-c ./run-calc.sh "
                "example/VASP_3C-SiC/1x1x1/sc_1x1x1/CONTCAR")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Calculating amplitude correction data

    The amplitude correction data can be saved into the file (-s parameter) and used in subsequent calculations (see below). This will speed up the initial equilibration of the degrees of freedom. This will be merged with eta estimation in future versions.
    """)
    return


@app.cell
def _(calc_dir, hecss_sampler, run_cli_cmd):
    #| export
    #| export
    open(f'{calc_dir.name}/DFSET.dat', 'wt').close()
    open(f'{calc_dir.name}/DFSET.dat.raw', 'wt').close()

    run_cli_cmd(hecss_sampler,
                f"-W {calc_dir.name} "
                "-T 300 -N 10 -w 1.85 "
                "-c ./run-calc.sh "
                "-s scale.dat "
                "example/VASP_3C-SiC/1x1x1/sc_1x1x1/CONTCAR")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Calculate initial amplitude correction

    By saving the amplitude correction coefficients into the file with `-s` option of the sampler we can initialise following calculations with proper relations of relative displacement amplitudes. This may be also used to continue
    the calculations with minimal startup overhead.
    """)
    return


@app.cell
def _(ase, calc_init_xscale, click, hecss, loadtxt, savetxt, _version_message):
    #| hide
    #| hide
    @click.command()
    @click.argument('supercell', type=click.Path(exists=True))
    @click.argument('scale', type=click.Path(exists=True))
    @click.option('-o', '--output', type=click.Path(), default="", help='Write output to the file.')
    @click.option('-s', '--skip', default=0, type=int, help='Skip this number of samples at the beginning')
    @click.version_option(hecss.__version__, '-V', '--version', message=_version_message)
    @click.help_option('-h', '--help')
    def calculate_xscale(supercell, scale, output, skip):
        '''
        Calculate initial values for amplitude correction coefficients
        from the scale file data for the specified supercell.
        '''
        sc = ase.io.read(supercell)
        xsl = loadtxt(scale).reshape((-1, len(sc), 3))
        xsi = calc_init_xscale(sc, xsl, skip=skip if skip else None)
        savetxt(output, xsi, fmt='%9.4f')
        print(f'Done. The initial scale saved to: {output}')

    return (calculate_xscale,)


@app.cell
def _(calc_dir, calculate_xscale, run_cli_cmd):
    #| export
    #| export
    run_cli_cmd(calculate_xscale, "--help")
    run_cli_cmd(calculate_xscale,
                f"-o {calc_dir.name}/iscale.dat -s 10 "
                "example/VASP_3C-SiC/1x1x1/sc_1x1x1/CONTCAR "
                f"{calc_dir.name}/T_300.0K/scale.dat")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Continue the calculation
    """)
    return


@app.cell
def _(calc_dir, calc_dir_2, hecss_sampler, run_cli_cmd):
    #| export
    #| export
    open(f'{calc_dir_2.name}/DFSET.dat', 'wt').close()
    open(f'{calc_dir_2.name}/DFSET.dat.raw', 'wt').close()

    run_cli_cmd(hecss_sampler,
                f"-W {calc_dir_2.name} -T 300 -N 10 -w 1.85 "
                f"-c ./run-calc.sh -s scale.dat -a {calc_dir.name}/iscale.dat"
                " example/VASP_3C-SiC/1x1x1/sc_1x1x1/CONTCAR")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Sampling re-shaping

    The reshaper of the sample set to any given temperature.
    """)
    return


@app.cell
def _(Path, Vasp, array, click, hecss, make_sampling, un, write_dfset, _version_message):
    #| hide
    #| hide
    @click.command()
    @click.argument('dfset', type=click.Path(exists=True))
    @click.argument('T', default=-1, type=float)
    @click.option('-N', '--nmul', default=4, type=int, help="Sample length multiplier (default: 4)")
    @click.option('-p', '--prob', type=float, default=0.25, help='Probability treshold (default: 0.25)')
    @click.option('-w', is_flag=True, default=True, help='Force non-zero weights for samples above probability treshold. (default: True)')
    @click.option('-b', is_flag=True, default=False, help='Border samples account for the rest of domain')
    @click.option('-c', '--check', type=click.Path(), default="", help='Check and skip unconverged samples in calc directory.')
    @click.option('-o', '--output', type=click.Path(), default="", help='Write output to the file.')
    @click.option('-d', is_flag=True, default=False, help='Plot debug plots')
    @click.version_option(hecss.__version__, '-V', '--version', message=_version_message)
    def reshape_sample(dfset, t, nmul, prob, w, check, b, output, d):
        '''
        Reshape the sample to the normal distribution centered around mean energy (temperature),
        or around provided temperature T (Kelvin). The reshaping is done by adjusting weighting
        of the samples by repeating the ones which should be up-weighted.
        The parameters are the variants of the weighting algorithm (see the docs).\b

        The procedure reads and produces a file with in the DFSET format.
        For the 'check' function to work the parameter must point to the root directory
        of the calculated samples. The checked directories will be in the form: '{root}/nnnn'.

        In check mode the raw file is *not* reshaped, just filtered.
        '''
        from hecss.util import load_dfset
        p = Path(dfset)
        smpl = load_dfset(p)

        if check:
            from tqdm.auto import tqdm
            print(f"Checking convergence in {check}/nnnn")
            configs = {i for n, i, x, f, e in smpl}
            converged = {i for i in tqdm(configs)
                         if Vasp(restart=True, directory=f'{check}/{i:04d}').converged}
            print(f"Number of converged calculations: {len(converged)}/{len(configs)}")
            dist = [s for s in smpl if s[1] in converged]
            print(f"Rewriting the raw dfset (skipping reshape).")
        else:
            if t < 0:
                t = 2 * array([s[-1] for s in smpl]).mean() / 3 / un.kB
            dist = make_sampling(smpl, t, border=b, probTH=prob, Nmul=nmul, nonzero_w=w, debug=d)
            print(f'Done. Distribution reshaped to {t:.2f} K.')

        print(f'Done. Saving to: {output}')
        for s in dist:
            write_dfset(output, s)

    return (reshape_sample,)


@app.cell
def _(reshape_sample, run_cli_cmd, subprocess, calc_dir, calc_dir_2):
    subprocess.call(['cat', f'{calc_dir.name}/T_300.0K/DFSET.dat.raw', f'{calc_dir_2.name}/T_300.0K/DFSET.dat.raw', '>', 'TMP/DFSET_raw.dat'])
    subprocess.call(['rm', '-f', 'TMP/DFSET.dat'])
    run_cli_cmd(reshape_sample, "--help")
    run_cli_cmd(reshape_sample,
                " -d -o TMP/DFSET.dat"
                " TMP/DFSET_raw.dat")
    return


@app.cell
def _(calc_dir, reshape_sample, run_cli_cmd, subprocess):
    #| export
    #| export
    subprocess.call(['rm', '-f', f'{calc_dir.name}/T_300.0K/DFSET.dat'])
    run_cli_cmd(reshape_sample,
                f" -N 1 -w -d -o {calc_dir.name}/T_300.0K/DFSET.dat"
                f" --check {calc_dir.name}/T_300.0K/smpl"
                f" {calc_dir.name}/T_300.0K/DFSET.dat.raw")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Command line statistics monitoring

    This simple command line interface to the statistics plotting function allows for quick monitoring of the running calculation. If the sixelplot package is installed it is even possible to plot hi-res plots in the remote terminal supporting sixel standard (e.g. mlterm, xterm on Linux, iterm2 on OSX).
    """)
    return


@app.cell
def _(Path, click, hecss, _version_message):
    #| hide
    #| hide
    @click.command()
    @click.argument('dfset', type=click.Path(exists=True))
    @click.argument('T', default=-1, type=float)
    @click.option('-n', '--sqrn', is_flag=True, help='Show sqrt(N) bars on the histogram.')
    @click.option('-s', '--sixel', is_flag=True, help='Use SixEl driver for terminal graphics.')
    @click.option('-w', '--width', type=float, default=6, help='Width of the figure.')
    @click.option('-h', '--height', type=float, default=4, help='Height of the figure.')
    @click.option('-o', '--output', type=click.Path(), default="", help='Write output to the file.')
    @click.option('-x', is_flag=True, default=False, help='Make plot in an interactive window')
    @click.version_option(hecss.__version__, '-V', '--version', message=_version_message)
    def plot_stats(dfset, t, output, x, sixel, sqrn, width, height):
        """
        Plot the statistics of the samples from the DFSET file.
        Use T(K) as a reference target temperature. Optionally
        write out the plot to the output graphics file.
        """
        from hecss.util import load_dfset
        from hecss.monitor import plot_stats
        import matplotlib.pylab as plt

        p = Path(dfset)
        smpl = load_dfset(p)
        plt.figure(figsize=(float(width), float(height)))
        plot_stats(smpl, T=t if t > 0 else None, sqrN=sqrn, show=x)
        if output:
            plt.savefig(output)
        if sixel:
            try:
                import sixelplot
            except ImportError:
                print('SixEl graphics support not installed. Install sixelplot package.')
                return
            sixelplot.show()

    return (plot_stats,)


@app.cell
def _(plot_stats, run_cli_cmd):
    #| export
    #| export
    run_cli_cmd(plot_stats, "--help")

    run_cli_cmd(plot_stats,
                "-n "
                "-w 7 -h 4 "
                "TMP/DFSET_raw.dat "
                "300")
    return


@app.cell
def _(plot_stats, run_cli_cmd):
    #| export
    #| export
    run_cli_cmd(plot_stats,
                "-n "
                "-w 7 -h 4 "
                "TMP/DFSET.dat ")
    return


@app.cell
def _(plot_stats, run_cli_cmd):
    #| export
    #| export
    run_cli_cmd(plot_stats,
                "-n "
                "-w 7 -h 4 "
                "example/VASP_3C-SiC_calculated/2x2x2/T_1200K/DFSET.dat "
                "1200")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Command line phonon monitoring

    This simple command line interface to the phonon plotting function allows for quick monitoring of the phonon calculation. If the sixelplot package is installed it is even possible to plot hi-res plots in the remote terminal supporting sixel standard (e.g. mlterm, xterm on Linux, iterm2 on OSX).
    """)
    return


@app.cell
def _(Path, click, hecss, os, _version_message):
    #| hide
    #| hide
    @click.command()
    @click.argument('bands', type=click.Path(exists=True), nargs=-1)
    @click.option('-s', '--sixel', is_flag=True, help='Use SixEl driver for terminal graphics.')
    @click.option('-n', '--nodecor', is_flag=True, help='Decorate the plot.')
    @click.option('-w', '--width', type=float, default=6, help='Width of the figure.')
    @click.option('-h', '--height', type=float, default=4, help='Height of the figure.')
    @click.option('-o', '--output', type=click.Path(), default="",
                  help='Write output to the file.')
    @click.option('-l', '--label', type=str, default="",
                  help='Label(s) for the plot. Comma-separated list')
    @click.option('-x', is_flag=True, default=False,
                  help='Make plot in an interactive window')
    @click.version_option(hecss.__version__, '-V', '--version', message=_version_message)
    def plot_bands(bands, output, x, sixel, width, height, label, nodecor):
        """
        Plot the phonon dispersion from the file generated by ALAMODE.
        Optionally write out the plot to the output graphics file.
        """
        import hecss.monitor as hm
        import matplotlib.pylab as plt

        plt.figure(figsize=(float(width), float(height)))

        ll = label.split(',')
        if len(ll) < len(bands):
            cp = os.path.commonpath(bands)
            rpl = [p[len(cp):][::-1] for p in bands]
            cs = os.path.commonpath(rpl)
            ll = [p[len(cp):-len(cs)] for p in bands]

        for b, l in zip(bands, ll):
            p = Path(b)

            hm.plot_bands_file(p, lbl=l, decorate=not nodecor)

        if label or len(bands) > 1:
            plt.legend()

        if output:
            plt.savefig(output)
        if sixel:
            try:
                import sixelplot
            except ImportError:
                print('SixEl graphics support not installed. Install sixelplot package.')
                return
            sixelplot.show()

    return (plot_bands,)


@app.cell
def _(plot_bands, run_cli_cmd):
    #| export
    #| export
    run_cli_cmd(plot_bands, "--help")
    run_cli_cmd(plot_bands,
                   "-w 7 -h 4 -l '300K,600K,3000K' "
                   "example/VASP_3C-SiC_calculated/2x2x2/T_300K/phon/cryst.bands "
                   "example/VASP_3C-SiC_calculated/2x2x2/T_600K/phon/cryst.bands "
                   "example/VASP_3C-SiC_calculated/2x2x2/T_3000K/phon/cryst.bands ")
    return


@app.cell
def _():
    #| hide
    #| hide
    CLEANUP = False
    return (CLEANUP,)


@app.cell
def _(CLEANUP, calc_dir, calc_dir_2):
    #| hide
    #| hide
    _ = None
    try:
        _ = CLEANUP
    except NameError:
        calc_dir.cleanup()
        calc_dir_2.cleanup()
    return


@app.cell
def _(CLEANUP):
    #| hide
    #| hide
    try:
        del CLEANUP
    except NameError:
        pass
    return


if __name__ == "__main__":
    app.run()