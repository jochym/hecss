"""Tests for hecss.optimize."""

import numpy as np
import pytest

from hecss.optimize import get_sample_weights, make_sampling


def test_get_sample_weights(samples):
    weights, index = get_sample_weights(samples, 300.0)
    assert np.isclose(weights.sum(), 1.0)
    assert len(index) == len(samples)
    energies = np.fromiter((s[-1] for s in samples), float)
    assert np.all(np.diff(energies[index]) >= 0)


def test_get_sample_weights_needs_two_samples(samples):
    with pytest.raises(AssertionError):
        get_sample_weights(samples[:1], 300.0)


def test_make_sampling(samples):
    result = make_sampling(samples, 300.0, N=10, probTH=0)
    assert result
    assert [s[0] for s in result] == list(range(len(result)))
    energies = [s[-1] for s in result]
    assert energies == sorted(energies)


def test_make_sampling_preserves_all_configurations(samples):
    # N=1 with nonzero_w=True clamps every small weight to one, inflating the
    # output to all input configurations (which are energy-sorted).
    result = make_sampling(
        samples, 300.0, probTH=0, Nmul=1 / len(samples), nonzero_w=True
    )
    assert len(result) == len(samples)
    assert sorted(s[1] for s in result) == sorted(s[1] for s in samples)


def test_make_sampling_short_input_is_unchanged(samples):
    short = samples[:1]
    assert make_sampling(short, 300.0) is short


def test_make_sampling_with_identical_energies():
    data = [
        (i, i, np.zeros((4, 3)), np.zeros((4, 3)), 0.1)
        for i in range(3)
    ]
    result = make_sampling(data, 300.0)
    assert result
    assert np.isfinite([s[-1] for s in result]).all()
