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
    # Mapping of DOFs to minimal set

    > procedures for mapping degrees of freedom in the supercell to the minimal set of DOFs in the primitive unit cell.
    """)
    return


@app.cell
def _():
    import spglib as spg
    import ase
    import ase.io
    import numpy as np

    return ase, np, spg


@app.cell
def _():
    from ase import spacegroup as sg
    from hecss.util import get_cell_data

    return get_cell_data, sg


@app.cell
def _(ase):
    # cryst = ase.io.read('/home/jochym/cryst/TiO2_hecss/PBE_2x2x4/uc/CONTCAR')
    # cryst = ase.io.read('/home/jochym/cryst/TiO2_hecss/PBE_Tetra/uc/CONTCAR')*(2,2,4)
    # cryst = ase.io.read('/home/pastukh/Czech.calculation/sc/CONTCAR')
    cryst = ase.io.read('example/VASP_3C-SiC_calculated/2x2x2/sc/CONTCAR')
    return (cryst,)


@app.cell
def _(ase, cryst, get_cell_data, spg):
    puc = spg.find_primitive(get_cell_data(cryst))
    cryst_pc = ase.Atoms(cell=puc[0], scaled_positions=puc[1], numbers=puc[2], pbc=True)
    sym = spg.get_symmetry(get_cell_data(cryst_pc))
    symds = spg.get_symmetry_dataset(get_cell_data(cryst_pc))
    spg.get_spacegroup(get_cell_data(cryst_pc))
    return cryst_pc, puc, symds


@app.cell
def _(cryst_pc, sg):
    SG = sg.get_spacegroup(cryst_pc)
    SG
    return (SG,)


@app.cell
def _(cryst_pc, sg):
    sg.get_basis(cryst_pc)
    return


@app.cell
def _(np):
    eps = 0.01
    dv = eps*np.diag(np.ones(3))
    uvec = {n:v for n, v in zip((0,1,2),dv)}
    uvec
    return eps, uvec


@app.cell
def _(np):
    def find_key(val, dic):
        for k, v in dic.items():
            if np.allclose(v, val):
                return k

    return (find_key,)


@app.cell
def _(SG, eps, find_key, np, puc, symds, uvec):
    eqdir = {}
    for sp in set(symds['equivalent_atoms']):
        pci = symds['mapping_to_primitive'][sp]
        print(sp, pci, puc[1][pci], puc[2][pci])
        pos = puc[1][pci]
        m = {}
        for n, d in uvec.items():
            v = pos + d
            m[n] = set()
            for elp in SG.equivalent_lattice_points([v]):
                if np.any(elp - pos < 0):  # if np.allclose(v, elp):
                    continue  #     continue
                if np.all(np.abs(elp - pos) < 2 * eps):
                    di = v - pos
                    df = elp - pos
                    m[n] = m[n] | {find_key(elp - pos, uvec)}
        for k, v in m.items():
            print(k, '->', sorted(v)[0])
        eqdir[sp] = np.array([sorted(v)[0] for k, v in sorted(m.items())])  # print(find_key(v-pos, uvec), '->',  find_key(elp-pos, uvec))
    # print(SG.tag_sites(cryst_pc.get_scaled_positions()))
    print(eqdir)  # print(m)
    return (eqdir,)


@app.cell
def _(cryst, get_cell_data, spg, symds):
    at_map = symds['equivalent_atoms'][spg.get_symmetry_dataset(get_cell_data(cryst))['mapping_to_primitive']]
    return (at_map,)


@app.cell
def _(cryst):
    dc = cryst.copy()
    dc.rattle()
    return (dc,)


@app.cell
def _(cryst, dc):
    dx = dc.get_positions() - cryst.get_positions()
    return (dx,)


@app.cell
def _(at_map, dx):
    d_avg = {ai:dx[at_map == ai] for ai in set(at_map)}
    return (d_avg,)


@app.cell
def _(d_avg, eqdir):
    for ai, eqd in eqdir.items():
        for di_1 in set(eqd):
            print(ai, di_1, d_avg[ai][:, eqd == di_1].shape, d_avg[ai][:, eqd == di_1].std())
    return


@app.cell
def _(cryst, np):
    cryst.get_scaled_positions()[np.zeros((64),dtype=int)].shape
    return


@app.cell
def _(np):
    np.array(np.zeros((64,2)), dtype=int)
    return


if __name__ == "__main__":
    app.run()
