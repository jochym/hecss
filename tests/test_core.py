"""Tests for the HECSS sampler, using ASE's EMT calculator instead of an external code."""

import numpy as np
from ase.build import bulk
from ase.calculators.emt import EMT

from hecss import HECSS


def emt_sampler():
    cryst = bulk("Cu", cubic=True)
    cryst.calc = EMT()
    return HECSS(cryst, EMT, width=1.0, w_search=False, pbar=False)


def test_sample_returns_requested_number_of_samples():
    sampler = emt_sampler()
    samples = sampler.sample(300, 5)
    assert len(samples) == 5
    assert [s[0] for s in samples] == list(range(1, 6))
    assert samples[-1][2].shape == sampler.cryst.get_positions().shape
    assert all(np.isfinite(s[-1]) for s in samples)


def test_sample_can_be_extended():
    sampler = emt_sampler()
    first = sampler.sample(300, 2)
    second = sampler.sample(300, 3)
    assert len(first) == 2
    assert len(second) == 3
    assert second[0][0] == 3


def test_w_search_maxburn_message(capsys):
    cryst = bulk("Cu", cubic=True)
    cryst.calc = EMT()
    sampler = HECSS(cryst, EMT, width=1.0, maxburn=0, pbar=False)
    assert sampler.sample(300, 1, sigma=0) == []
    assert "reached maxburn (0)" in capsys.readouterr().out


def test_generate_delegates_to_make_sampling(samples):
    result = emt_sampler().generate(samples, T=300, N=10, probTH=0, nonzero_w=False)
    assert 0 < len(result) <= len(samples)
    assert [s[-1] for s in result] == sorted(s[-1] for s in result)
