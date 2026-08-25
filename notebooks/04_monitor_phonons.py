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
    # Phonon convergence monitoring

    > Phonon monitoring is a more complicated issue and requires additional external tools. Here we include only few examples to guide you how it could be done using tools provided in `dxutils` and `alamode` and to show the kind of physical results which could be obtained with the help of HECSS. For more examples see the [SciPost Phys. 10, 129 (2021)](https://scipost.org/SciPostPhys.10.6.129) paper and the works citing it (list avaliable on the SciPost page).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Note:** *The phonon monitoring functions are not complete and are at the **alpha** level. Thus, they may not work as described or at all.*
    """)
    return


@app.cell
def _():
    from hecss.monitor import monitor_phonons, plot_bands_file
    from matplotlib import pyplot as plt
    return monitor_phonons, plot_bands_file, plt


@app.cell
def _(plot_bands_file, plt):
    fig, axs = plt.subplots(1, 2, figsize=(14, 4))
    for sc, ax in zip(('1x1x1', '2x2x2'), axs):
        plt.sca(ax)
        for T in 300, 600, 1200, 3000:
            plot_bands_file(f'example/VASP_3C-SiC_calculated/{sc}/T_{T}K/phon/cryst.bands', lbl=f'T={T}K')
        plt.legend()
        plt.title(f'Supercell: {sc}')
    return


@app.cell
def _(monitor_phonons):
    #| export
    #| export
    T_1 = 3000
    supercell = '2x2x2'
    monitor_phonons(directory=f'example/VASP_3C-SiC_calculated/{supercell}/phon/', dfset=f'../T_3000K/DFSET.dat', kpath='3C_SiC', charge='3C_SiC', sc=f'../sc/CONTCAR', order=1, cutoff=10, born=2, k_list=None, once=True)
    return


if __name__ == "__main__":
    app.run()