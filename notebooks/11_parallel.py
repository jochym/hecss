import marimo

__generated_with = "0.24.0"
app = marimo.App()

#| default_exp parallel



@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Parallel calculations

    > Support for parallel/async calulations.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Presently, these routines are implemented for VASP. It should be trivial to extend this to any calculator based on external process execution (e.g. abinit or any other which runs blocking shell script to execute the calculation). The support for internal calculators (e.g. ASAP3) should be possible, but is not trivial, and is not planned at the moment. Such in-memory calculators are probably not worth it. The real gain comes from the cluster-run calculations.
    """)
    return


@app.cell
def _():
    #| hide
    #| exporti

    from fastcore.basics import patch

    import ase
    from ase.utils import workdir
    from ase.calculators.vasp import Vasp
    from ase.calculators import calculator
    from ase.calculators.vasp.vasp import check_atoms

    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    return (
        ThreadPoolExecutor,
        Vasp,
        asyncio,
        calculator,
        check_atoms,
        patch,
        workdir,
    )


@app.cell
def _(ThreadPoolExecutor, asyncio):
    #|exporti

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

    return


@app.cell
def _(Vasp, asyncio, patch):
    #|exporti

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

    return


@app.cell
def _(Vasp, calculator, check_atoms, patch, workdir):
    #|exporti

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
        # Make sure the working directory exists
        with workdir(self.directory, mkdir=True):
            pass
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

    return


if __name__ == "__main__":
    app.run()
