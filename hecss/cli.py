"""Generated from notebooks/cli.py by build_package.py"""

from __future__ import annotations

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset

_version_message = ("HECSS, version %(version)s\n"
                        'High Efficiency Configuration Space Sampler\n'
                        '(C) 2021-2024 by Paweł T. Jochym\n'
                        '    License: GPL v3 or later')

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

def run_cli_cmd(cmd, args, prt_result=False):
        print(f'$ {cmd.name} {args}\n')
        run = CliRunner().invoke(cmd, args)
        print(run.output)
        if prt_result or run.exit_code != 0:
            print(run)
            if run.exit_code != 0:
                traceback.print_tb(run.exc_info[-1])

__all__ = ["hecss_sampler", "calculate_xscale", "reshape_sample", "plot_stats", "plot_bands", "dfset_writer", "run_cli_cmd", "_version_message"]