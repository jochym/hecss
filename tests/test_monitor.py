"""Tests for plotting and smoothing helpers in hecss.monitor."""

import inspect

import numpy as np

from hecss.monitor import build_bnd_lst, ewma, moving_average, plot_stats, run_alamode


def test_kpath_defaults_agree():
    for func in (run_alamode, build_bnd_lst):
        assert inspect.signature(func).parameters["kpath"].default == "cryst"


def test_moving_average():
    values = np.arange(10.0)
    result = moving_average(values, 3)
    assert result.shape == (8,)
    assert np.allclose(result[:2], [1.0, 2.0])


def test_ewma():
    values = np.ones(10)
    result = ewma(values, 3)
    assert result.shape == values.shape
    assert np.allclose(result, 1.0)


def test_plot_stats(samples):
    plot_stats(samples, T=300, sqrN=True, show=False)
