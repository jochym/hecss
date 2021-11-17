# AUTOGENERATED! DO NOT EDIT! File to edit: 03_cli.ipynb (unless otherwise specified).

__all__ = ['dfset_writer', 'hecss_sampler']

# Cell
# export
import click
from fastcore.script import Param, call_parse, bool_arg, store_true, store_false
from pathlib import Path
import os
import ase
from ase.calculators.vasp import Vasp
from ase import units as un
from .core import *

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
@click.option('-V', '--version', is_flag=True, help="Print version and exit")
def hecss_sampler(fname, workdir, label, temp, width, calc, nodfset, nsamples, command, version):
    '''
    Run HECSS sampler on the structure in the directory.
    fname - Supercell structure file.
    The containing directory must be readable by Vasp(restart).
    '''

    import hecss

    if version:
        print(f'HECSS ver. {hecss.__version__}\n'
               'High Efficiency Configuration Space Sampler\n'
               '(C) 2021 by Paweł T. Jochym\n'
               '    License: GPL v3 or later')
        return


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