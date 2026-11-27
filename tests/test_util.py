"""Tests for hecss.util."""

from pathlib import Path

import numpy as np
from ase.build import bulk
from numpy import allclose

from hecss.util import (
    calc_init_xscale,
    get_cell_data,
    get_dfset_len,
    load_dfset,
    normalize_conf,
    write_dfset,
)

EXAMPLE_DFSET = Path("example/VASP_3C-SiC_calculated/2x2x2/T_300K/DFSET.dat")


def test_dfset_roundtrip(tmp_path):
    confs = load_dfset(EXAMPLE_DFSET)
    assert confs

    output = tmp_path / "dfset_test.dat"
    output.touch()
    for conf in confs:
        write_dfset(output, conf)
    assert allclose(np.loadtxt(output), np.loadtxt(EXAMPLE_DFSET))


def test_get_dfset_len(tmp_path):
    assert get_dfset_len(tmp_path / "missing.dat") == 0
    assert get_dfset_len(EXAMPLE_DFSET) == len(load_dfset(EXAMPLE_DFSET))


def test_normalize_conf_unwraps_periodic_displacements():
    base = bulk("NaCl", "rocksalt", a=3.6, cubic=True).repeat((3, 3, 3))
    distorted = base.copy()
    distorted.rattle(stdev=0.5, seed=42)
    unwrapped = distorted.get_scaled_positions(wrap=False)
    distorted.set_scaled_positions(distorted.get_scaled_positions(wrap=True))
    assert allclose(unwrapped, normalize_conf(distorted, base)[1])


def test_normalize_conf_rejects_large_displacements():
    base = bulk("NaCl", "rocksalt", a=3.6, cubic=True)
    distorted = base.copy()
    positions = distorted.get_positions()
    positions[0] += base.get_cell()[0] / 2
    distorted.set_positions(positions)
    try:
        normalize_conf(distorted, base)
    except AssertionError:
        pass
    else:
        raise AssertionError("displacements above 1/3 of the cell must be rejected")


def test_calc_init_xscale():
    cryst = bulk("NaCl", "rocksalt", a=3.6, cubic=True).repeat((2, 2, 2))
    xsl = [np.full(cryst.get_positions().shape, value) for value in (1.0, 2.0)]
    result = calc_init_xscale(cryst, xsl)
    assert result.shape == cryst.get_positions().shape
    assert np.allclose(result, 1.5)


def test_get_cell_data():
    cryst = bulk("Cu", cubic=True)
    lattice, positions, numbers = get_cell_data(cryst)
    assert lattice.shape == (3, 3)
    assert positions.shape == (len(cryst), 3)
    assert np.array_equal(numbers, cryst.get_atomic_numbers())
