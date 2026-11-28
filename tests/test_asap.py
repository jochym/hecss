"""Integration tests using ASAP3 with an OpenKIM potential.

These are the notebook checks formerly marked ``#| asap``. Run them with
``pytest -m asap`` in an environment that provides ASAP3 and OpenKIM models.
"""

import importlib.util

import numpy as np
import pytest
from ase import units as un
from ase.build import bulk

from hecss import HECSS
from hecss.util import create_asap_calculator, select_asap_model


def has_openkim_support():
    if importlib.util.find_spec("asap3") is None:
        return False
    import asap3

    return hasattr(asap3, "OpenKIMavailable")


pytestmark = [
    pytest.mark.asap,
    pytest.mark.skipif(
        not has_openkim_support(), reason="ASAP3 with OpenKIM support is required"
    ),
]


@pytest.fixture(scope="module")
def model():
    selected = select_asap_model("SiC")
    if selected is None:
        pytest.skip("No working SiC OpenKIM model available")
    return selected


@pytest.fixture
def sampler(model):
    cryst = bulk("SiC", crystalstructure="zincblende", a=4.38120844, cubic=True)
    cryst.calc = create_asap_calculator(model)
    return HECSS(
        cryst,
        lambda: create_asap_calculator(model),
        width=1.05,
        w_search=False,
        pbar=False,
    )


def test_select_asap_model(model):
    assert "SiC" in model


def test_samples_can_be_appended(sampler):
    first = sampler.sample(300, 2)
    first += sampler.sample(300, 2)
    first += sampler.sample(300, 3)
    assert len(first) == 7
    assert [s[0] for s in first] == list(range(1, 8))


def test_mean_energy_matches_target(model):
    """Restore the historical ASAP temperature regression from 11_core.ipynb."""
    rng_state = np.random.get_state()
    np.random.seed(42)
    try:
        cryst = bulk("SiC", crystalstructure="zincblende", a=4.38120844, cubic=True)
        cryst = cryst.repeat((2, 2, 2))
        cryst.calc = create_asap_calculator(model)
        sampler = HECSS(
            cryst,
            lambda: create_asap_calculator(model),
            width=1.05,
            pbar=False,
        )
        temperature, n_samples = 300, 100
        samples = sampler.sample(temperature, n_samples)
        assert len(samples) == n_samples

        mean = np.mean([s[-1] for s in samples])
        target = 3 * temperature * un.kB / 2
        sigma = np.sqrt(3 / 2) * un.kB * temperature / np.sqrt(len(cryst))
        assert abs(mean - target) < 2 * sigma
    finally:
        np.random.set_state(rng_state)


def test_estimate_width_scale(model, tmp_path):
    cryst = bulk("SiC", crystalstructure="zincblende", a=4.38120844, cubic=True)
    cryst.calc = create_asap_calculator(model)
    sampler = HECSS(
        cryst,
        lambda: create_asap_calculator(model),
        directory=str(tmp_path),
        pbar=False,
    )
    mean, std, xscale = sampler.estimate_width_scale(2, Tmin=100, Tmax=600)
    assert mean > 0
    assert np.isfinite(std)
    assert xscale.shape == cryst.get_positions().shape
