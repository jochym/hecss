"""Tests for plotting and smoothing helpers in hecss.monitor."""

import inspect

import numpy as np
import pytest

from hecss import monitor
from hecss.monitor import build_bnd_lst, ewma, moving_average, plot_stats, run_alamode


def test_kpath_defaults_agree():
    for func in (run_alamode, build_bnd_lst):
        assert inspect.signature(func).parameters["kpath"].default == "cryst"


def test_alamode_tool_defaults_are_portable():
    params = inspect.signature(run_alamode).parameters
    for name in ("make_gen", "alm", "anphon"):
        assert "/home/" not in str(params[name].default)


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


def test_ewma_matches_recursive_filter():
    values = np.array([1.0, 2.0, 3.0, 0.5])
    alpha = 2 / (3 + 1)
    expected = np.empty(len(values))
    y = values[0]
    for i, x in enumerate(values):
        if i:
            y = alpha * x + (1 - alpha) * y
        expected[i] = y
    assert np.allclose(ewma(values, 3), expected)


def test_ewma_long_run_is_finite():
    assert np.isfinite(ewma(np.ones(10000), 10)).all()


def test_build_bnd_lst_stops_on_failed_fit(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, 'get_dfset_len', lambda fn: 1)
    monkeypatch.setattr(
        monitor, 'run_alamode', lambda **kwargs: (False, None, None, None, None)
    )
    loaded = []
    monkeypatch.setattr(monitor, 'loadtxt', lambda *a, **k: loaded.append(a))

    with pytest.raises(RuntimeError, match='ALAMODE failed'):
        build_bnd_lst(directory=str(tmp_path))

    assert not loaded
