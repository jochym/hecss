"""Shared fixtures for the HECSS test suite."""

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
from ase import units as un


@pytest.fixture
def samples():
    """Synthetic sampler output in the (number, index, displacement, forces, energy) format."""
    rng = np.random.default_rng(42)
    nat, temperature, size = 4, 300.0, 40
    mu = 3 * temperature * un.kB / 2
    energies = rng.normal(mu, mu / 20, size=size)
    return [
        (n, n, rng.normal(size=(nat, 3)), rng.normal(size=(nat, 3)), float(e))
        for n, e in enumerate(energies)
    ]
