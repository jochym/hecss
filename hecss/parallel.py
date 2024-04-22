# AUTOGENERATED! DO NOT EDIT! File to edit: ../11_parallel.ipynb.

# %% auto 0
__all__ = []

# %% ../11_parallel.ipynb 2
from fastcore.basics import patch

# %% ../11_parallel.ipynb 3
import ase
from ase.calculators.vasp import Vasp
from ase.calculators import calculator
from ase.calculators.vasp.vasp import check_atoms
from ase import units as un
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tqdm.auto import tqdm
from scipy import stats
import numpy as np

# %% ../11_parallel.ipynb 4
from hecss import *
import hecss

# %% ../11_parallel.ipynb 6
from hecss.util import write_dfset, calc_init_xscale
from hecss.optimize import make_sampling

# %% ../11_parallel.ipynb 9
def __run_async(func, *args, **kwargs):
    '''
    Run async methods detecting running loop in jupyter.
    '''
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = None
    
    if loop and loop.is_running():        
        # print('Async event loop already running. Running in new thread.')
        # Create a separate thread so we can block before returning
        with ThreadPoolExecutor(1) as pool:
            result = pool.submit(lambda: asyncio.run(func(*args, **kwargs))).result()
    else:
        # print('Starting new event loop')
        result = asyncio.run(func(*args, **kwargs))
    return result

# %% ../11_parallel.ipynb 10
@patch
async def _arun(self: Vasp, command=None, out=None, directory=None):
    """
    Method to explicitly execute VASP in async mode
    This is an asyncio version of the function.
    """
    # DEBUG
    # print(f'Async _run {command} in {directory}')
    if command is None:
        command = self.command
    if directory is None:
        directory = self.directory

    proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=directory
            )

    stdout, stderr = await proc.communicate()

    # DEBUG
    # print(f'[{command!r} exited with {proc.returncode}]')
    # if stdout:
    #     print(f'[stdout]\n{stdout.decode()}')
    # if stderr:
    #     print(f'[stderr]\n{stderr.decode()}')
    
    return proc.returncode

# %% ../11_parallel.ipynb 11
@patch
async def __calculate_aio(self: Vasp,
                        atoms=None,
                        properties=('energy', ),
                        system_changes=tuple(calculator.all_changes)
                       ):
    """
    Do a VASP calculation in the specified directory.
    
    This will generate the necessary VASP input files, and then
    execute VASP. After execution, the energy, forces. etc. are read
    from the VASP output files.

    This is an asyncio version of the function.
    """
    # Check for zero-length lattice vectors and PBC
    # and that we actually have an Atoms object.
    check_atoms(atoms)
    
    self.clear_results()
    
    if atoms is not None:
        self.atoms = atoms.copy()
    
    command = self.make_command(self.command)
    self.write_input(self.atoms, properties, system_changes)
    
    with self._txt_outstream() as out:
        errorcode = await self._arun(command=command,
                                     out=out,
                                     directory=self.directory)
    
    if errorcode:
        raise calculator.CalculationFailed(
            '{} in {} returned an error: {:d}'.format(
                self.name, self.directory, errorcode))
    
    # Read results from calculation
    self.update_atoms(atoms)
    self.read_results()
    return errorcode
