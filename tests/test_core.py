"""Tests for the HECSS sampler, using ASE's EMT calculator instead of an external code."""

import numpy as np
import pytest
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


def test_invalid_temperature_ranges_are_rejected():
    sampler = emt_sampler()
    for tmin, tmax in ((0, 0), (-10, 300), (600, 300), (float('nan'), 300)):
        with pytest.raises(ValueError):
            sampler.estimate_width_scale(1, Tmin=tmin, Tmax=tmax)


def test_sample_rejects_zero_temperature():
    with pytest.raises(ValueError):
        emt_sampler().sample(0, 1)


def test_zero_samples_skips_sampling_and_sentinel():
    sampler = emt_sampler()
    called = []
    assert sampler.sample(300, 0, sentinel=lambda *a, **k: called.append(1)) == []
    assert not called


def test_modify_hook_with_default_args():
    def modify(cr, base, s, *args):
        return 0.0, cr.get_forces()

    assert len(emt_sampler().sample(300, 1, modify=modify)) == 1


def test_nwork_reports_serial_sampling(capsys):
    sampler = emt_sampler()
    assert len(sampler.sample(300, 2, nwork=2)) == 2
    assert 'width estimation only' in capsys.readouterr().out


def test_async_width_estimation_uses_tmin(monkeypatch, tmp_path):
    calls = []

    class FakeDist:
        @staticmethod
        def rvs(loc, scale):
            calls.append((loc, scale))
            return 300.0

    class FakeVasp:
        name = 'vasp'
        command = ''

        def __init__(self):
            self.atoms = bulk('Cu', cubic=True)

        def asdict(self):
            return {}

        def fromdict(self, d):
            pass

        def set(self, **kwargs):
            if 'command' in kwargs:
                self.command = kwargs['command']

        def get_potential_energy(self):
            return 1.0

        def get_forces(self):
            return np.zeros((len(self.atoms), 3))

    async def noop(self, atoms):
        return 0

    setattr(FakeVasp, '__calculate_aio', noop)
    monkeypatch.setattr('hecss.core.stats.uniform', FakeDist())

    cryst = bulk('Cu', cubic=True)
    cryst.calc = EMT()
    sampler = HECSS(cryst, FakeVasp(), width=1.0, directory=str(tmp_path), pbar=False)
    sampler.estimate_width_scale(1, Tmin=100, Tmax=600, nwork=1)

    assert calls == [(100, 500)]
