import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell
def _():
    #| hide
    #| hide
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Setup

    >At the moment the HECSS sampler supports only VASP and ASAP3/OpenKIM calculators. However, it is explicitly written in such a way that it should be quite easy to extend it to other calculators (e.g. QE, AbInit). The VASP and ASAP calculators are simply the only ones tested so far. The following instructions cover only VASP. Contributions extending support to other calculators are welcomed and will be included in the distribution.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Install

    The HECSS package is available on pypi and conda-forge additionally the package is present also in my personal anaconda channel (jochym). Installation is simple, but requires a number of other packages to be installed as well. Package managers handle these dependencies automatically.

    ### Install with pip
    It is advisable to install in a dedicated virtual environment e.g.:
    ```bash
    python3 -m venv venv
    . venv/bin/activate
    ```
    then install with `pip`:
    ```bash
    pip install hecss
    ```

    ### Install with conda
    Also installation with conda should be performed for dedicated or some other non-base environment. To create dedicated environment you can invoke `conda create`:
    ```bash
    conda create -n hecss -c conda-forge hecss
    ```
    or you can install in some working environment `venv`:
    ```bash
    conda install -n venv -c conda-forge hecss
    ```

    ### Example data archive

    The example data is not distributed within the library package. However, when you learn the software it is usefull to have some pre-calculated results and template configs to have a starting point. The `example` directory in the source distribution contains template configuration files for a calculation (`VASP_3C-SiC` subdirectory) and the example data calculated for the same systems (`VASP_3C-SiC_calculated` subdirectory).
    As the name suggests these are 1x1x1 and 2x2x2 supercells of the 3C-SiC (cubic silicon carbide) calculated with VASP DFT calculator.

    To obtain the data you need to download the zip archive from the source repository: [hecss-examples.zip](https://gitlab.com/jochym/hecss/-/archive/master/hecss-master.zip?path=example)

    The source is published at the [Gitlab hecss repository](https://gitlab.com/jochym/hecss).
    You can access it with git (recommended, particularly if you want to contribute to the development):
    ```bash
    git clone https://gitlab.com/jochym/hecss.git
    ```
    or you can download the whole distribution as a zip archive: [hecss.zip](https://gitlab.com/jochym/hecss/-/archive/master/hecss-master.zip)
    The example subdirectory from the source may be downloaded directly from the source repository: [hecss-examples.zip](https://gitlab.com/jochym/hecss/-/archive/master/hecss-master.zip?path=example)

    ### The source code

    The source is published at the [Gitlab hecss repository](https://gitlab.com/jochym/hecss).
    You can access it with git (recommended, particularly if you want to contribute to the development):
    ```bash
    git clone https://gitlab.com/jochym/hecss.git
    ```
    or you can download the whole distribution as a zip archive: [hecss.zip](https://gitlab.com/jochym/hecss/-/archive/master/hecss-master.zip)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Calculators

    To use HECSS you need some code for calculation of energies and forces in the form of ASE calculator. At this moment two calculators are supported: ASAP/LAMMPS/OpenKIM and VASP. The first is a free, fast, effective potential calculator which can be used for testing and experimentation. It is also used in HECSS test suite. VASP is a non-free, high quality, academic DFT code which you can use for research-grade calculations. Other calculators are available in ASE (abInit, gpaw and many others). There is no reason for other ASE calculators to not work with HECSS, these two are just supported and tested for now. The next in line will be probably abInit - since this is also a high-quality, research-grade DFT code which happen to be also free.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### ASAP/LAMMPS/OpenKIM

    The ASAP calculator is not installed by default with HECSS package, to not force it's installation on users which are not going to use it and to avoid blocking simple HECSS installation on systems where ASAP is not supported at the moment (e.g. Windows).
    To install ASAP in your conda environment run:
    ```bash
    conda install -c conda-forge asap3 openkim-models=2021.01.28
    ```
    No further configuration is required for this calculator.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### VASP

    The installation of VASP is beyond the scope of this manual. We assume that you have a working VASP setup and just installed HECSS package with its dependencies.

    To enable use of the VASP calculator in ASE you need to configure it. This involves configuring ASE (Atomistic Simulation Environment) to be able to generate VASP input files. Refer to [ASE documentation](https://wiki.fysik.dtu.dk/ase/ase/calculators/vasp.html) for details.

    Usually you need to:
    1. Put your pseudopotential files in a dedicated directory tree as described  in the docs. My setup contains a directory with three subdirs for LDA, GGA, and PBE pseudopotentials:

    ```bash
    potpaw
    potpaw_GGA
    potpaw_PBE
    ```
    2. Setting the `VASP_PP_PATH` environment variable to the location of this directory
    3. Preparing the `run-calc` script to execute vasp in your setup. The script *must* wait for the calculation to finish before it returns. The example script is included in the source and for SLURM queue manager may look similar to the following code:

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

    You need to adapt the script to your setup. The script works properly if you can go to the directory with the prepared VASP configuration and execute `run-calc` and have it run vasp in the directory and finish after the VASP job ends.
    """)
    return


if __name__ == "__main__":
    app.run()