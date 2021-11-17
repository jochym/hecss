# AUTOGENERATED! DO NOT EDIT! File to edit: 03_cli.ipynb (unless otherwise specified).

__all__ = ['dfset_writer', 'hecss_sampler']

# Cell
# export
import click
from pathlib import Path
import os
import ase
from ase.calculators.vasp import Vasp
from ase import units as un
from .core import *
import hecss

# Cell
def dfset_writer(s, sl, workdir=''):
    '''
    Just write samples to the DFSET.dat file in the workdir directory.
    '''
    wd = Path(workdir)
    write_dfset(f'{wd.joinpath("DFSET.dat")}', s)
    # Important! Return False to keep iteration going
    return False

# Cell
@click.command()
@click.argument('fname', type=click.Path())
@click.option('-W', '--workdir', default="WORK", type=click.Path(exists=True), help="Work directory")
@click.option('-l', '--label', default="hecss", help="Label for the calculations.")
@click.option('-T', '--temp', default=300, type=float, help="Target temperature in Kelvin.")
@click.option('-w', '--width', default=1.0, type=float, help="Initial scale of the prior distribution")
@click.option('-C', '--calc', default="VASP", type=str,
              help="ASE calculator to be used for the job. "
                      "Supported calculators: VASP (default)")
@click.option('-n', '--nodfset', is_flag=True, help='Do not write DFSET file for ALAMODE')
@click.option('-N', '--nsamples', default=10, type=int, help="Number of samples to be generated")
@click.option('-c', '--command', default='./run-calc', help="Command to run calculator")
@click.version_option(hecss.__version__, '-V', '--version',
                      message="HECSS, version %(version)s\n"
                          'High Efficiency Configuration Space Sampler\n'
                          '(C) 2021 by Paweł T. Jochym\n'
                          '    License: GPL v3 or later')
@click.help_option('-h', '--help')
def hecss_sampler(fname, workdir, label, temp, width, calc, nodfset, nsamples, command):
    '''
    Run HECSS sampler on the structure in the provided file (FNAME).

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

    if calc=="VASP":
        calculator = Vasp(label=label, directory=src_path.parent, restart=True)
        cryst = ase.Atoms(calculator.atoms)
        cryst.set_calculator(calculator)
        calculator.set(directory=workdir)
        command = Path(command)
        calculator.set(command=f'{command.absolute()} {label}')
    else:
        print(f'The {calc} calculator is not supported.')
        return

    if nodfset :
        sentinel = None
    else :
        sentinel = dfset_writer
    sampler = HECSS(cryst, calculator, temp, directory=workdir, width=width)
    samples = sampler.generate(nsamples, sentinel=sentinel, workdir=workdir)
    return