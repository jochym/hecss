# AUTOGENERATED! DO NOT EDIT! File to edit: 03_cli.ipynb (unless otherwise specified).

__all__ = ['hecss_sampler']

# Cell
from fastcore.script import *

# Cell
@call_parse
def hecss_sampler(fname:Param("Basic structure file. Any type recognized by ASE is accepted.", str)="CONTCAR",
                  work_dir:Param("Work directory", str)="WORK",
                  label:Param("Label for the calculations. This got appended to work directory")="hecss",
                  T:Param("Target temperature in Kelvin", float)=300,
                  calc:Param("ASE calculator to be used for the job.\n"+
                             "Supported calculators: VASP (default)"
                             , str)="VASP",
                  N:Param("Number of samples to be generated", int)=10
                  ):
    '''
    Run HECSS parser on the structure in the directory.
    '''
    print(f'Run HECSS on {fname} at {T}K in {work_dir} directory using {calc}.')

    src_path = Path(fname)

    print(src_path.parent, src_path.name)

    if calc=="VASP":
        calculator = Vasp(label=label, directory=src_path.parent, restart=True)
        cryst = ase.Atoms(calculator.atoms)
        cryst.set_calculator(calculator)
        calculator.set(directory=work_dir)
        calculator.set(command=f'{os.getcwd()}/run-vasp -J "hecss"')

    sampler = HECSS(cryst, calculator, T, directory=work_dir)
    samples = sampler.generate(N)
    return samples