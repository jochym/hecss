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
    # LAMMPS Tutorial
    > This example uses ASAP3/LAMMPS potential to calculate forces and energies. This is a free calculator which can be installed either from conda-forge or separately. At the moment conda-forge version supports only linux environment. You can run this tutorial on binder: [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gl/jochym%2Fhecss/devel?labpath=01_LAMMPS_Tutorial.ipynb).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    HECSS sampler may be used in multiple ways. Three main modes are:

    1. Jupyter notebook
    2. (I)Python scripts
    3. Command line programs included with the HECSS library. See the [CLI](cli.html) sction for more information.

    Probably the easiest way to start is a notebook path presented here. You can quite easily convert your notebooks to more sophisticated python scripts by saving them as such from the JupyterLab file menu (File/Save and Export as/Executable script). The CLI route is also fairly simple, but limits the use of the library to pre-packaged procedures with limited configurability.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Preamble
    Every non-trivial python program starts with a series of `import` statements. Here, we import `HECSS` class from the main part of the library, `plot_stats` diagnostic plotting function from the `hecss.monitor` sub-module, two utility functions encapsulating the ASAP calculator use from the `hecss.util` sub-module and, finally, the `bulk` crystal builder from the `ase.build` library.
    """)
    return


@app.cell
def _():
    #| asap
    from hecss import HECSS
    from hecss.monitor import plot_stats
    from hecss.util import select_asap_model, create_asap_calculator
    from ase.build import bulk

    return HECSS, bulk, create_asap_calculator, plot_stats, select_asap_model


@app.cell
def _():
    #| hide
    import hecss.optimize
    from hecss.optimize import make_sampling

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Crystal building

    To build the structure of the crystal we are using the `bulk` method from ASE and provide the information defining the crystal (cubic 3C SiC structure in our case):
    * composition: 'SiC'
    * type of structure: 'zincblende'
    * size of the cell: a=4.38...
    * variant of the unit cell: cubic (instead of primitive)
    * size of the supercell: 3x3x3
    """)
    return


@app.cell
def _(bulk):
    #| asap
    sc = (3,3,3)
    cryst = bulk('SiC', crystalstructure='zincblende',
                 a=4.38120844, cubic=True).repeat(sc)
    return (cryst,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Calculator setup

    The next step requires defining of the calculator used for evaluating energies and forces in the system. In our case it will be ASAP3 calculator. The `hecss.util` module provides two functions which simplify use of this calculator:
    * `select_asap_model`: automatically selects the model for the given composition (list of elements)
    * `create_asap_calculator`: creates calculator object
    These are fairly thin wrappers around ASE functions intended as a starting point for the user which is not familiar with ASE library and the calculator setup.

    Thus, we first select the type of the potential (`model`) and then assign the created calculator object to the `cryst` object.
    """)
    return


@app.cell
def _(create_asap_calculator, cryst, select_asap_model):
    #| asap
    model = select_asap_model('SiC')
    cryst.calc = create_asap_calculator(model)
    return (model,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### The HECSS sampler object

    In the next step we create object of the `HECSS` class, which encapsulates all of the configuration space functionality. By default, you can provide just the crystal object and either the calculator object (if it can be re-used) or the calculator generation function.

    In the case of ASAP calculator we need to provide a generator, since, due to the peculiarities of the ASAP implementation of the ASE calculator which cannot be re-used when the sampler is re-executed. This is achieved with the second parameter with the `lambda` anonymous function. This construct is probably not required for all calculators (e.g. for VASP we can use just calculator object).

    The last parameter (`pbar`) specifies that we want to have progress bar indicating the progress of the calculation.
    """)
    return


@app.cell
def _(HECSS, create_asap_calculator, cryst, model):
    #| asap
    hecss_1 = HECSS(cryst, lambda: create_asap_calculator(model), pbar=True)
    return (hecss_1,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Prior distribution

    The configuration space sampling starts with the generation of the prior energy distribution with the `HECSS.sampe` method. It generates a number (`N` here) of configurations with corresponding displacements, forces and energies targeted at some temperature (`T` here). The energy distribution of the sample is somewhat wider then the intended thermodynamic distribution described in the [Background](10_Background.html) section. Nevertheless, we expect the distribution to be fairly close to the target (orange, dashed line), and the plot provided by the `plot_stats` confirms our expectation.
    """)
    return


@app.cell
def _(hecss_1, plot_stats):
    #| asap
    T = 600
    N = 250
    samples = hecss_1.sample(T, N)
    plot_stats(samples, T)
    return T, samples


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Thermodynamic distribution

    The second step in the configuration space sampling is a proper re-shaping of the sample to give it normal average energy distribution expected in the thermodynamic equilibrium. This is achieved by creating proper weighting of the samples generated in the previous step. This weighting is realised with the `HECSS.generate` method which, in turn, encapsulates distribution shaper implemented in `make_sampling` function from the `hecss.optimize` sub-module. See [Optimize](optimize.html) section for implementation details.

    The final sampling is generated for the target temperature (`T`) and should fall close to the expected thermal equilibrium distribution - as the diagnostic plot below confirms.
    """)
    return


@app.cell
def _(T, hecss_1, plot_stats, samples):
    #| asap
    distrib = hecss_1.generate(samples, T)
    plot_stats(distrib, T)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Alternatively, if the precise temperature is not important, you can generate distribution around actual mean energy - optimising the effectiveness of the sampling.
    """)
    return


@app.cell
def _(hecss_1, plot_stats, samples):
    #| asap
    distrib_1 = hecss_1.generate(samples)
    plot_stats(distrib_1)
    return


if __name__ == "__main__":
    app.run()
