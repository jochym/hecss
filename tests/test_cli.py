"""Smoke tests for the console entry points."""

import numpy as np
import pytest
from ase.build import bulk
from click.testing import CliRunner

import hecss
from hecss.cli import (
    calculate_xscale,
    hecss_sampler,
    plot_bands,
    plot_stats,
    reshape_sample,
    run_cli_cmd,
    xsl_writer,
)

COMMANDS = (hecss_sampler, plot_stats, plot_bands, calculate_xscale, reshape_sample)


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: c.name)
def test_help(command):
    result = CliRunner().invoke(command, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: c.name)
def test_version(command):
    result = CliRunner().invoke(command, ["--version"])
    assert result.exit_code == 0
    assert hecss.__version__ in result.output


def test_sampler_cli_disables_dfset_and_progress(monkeypatch, tmp_path):
    from hecss import cli

    captured = {}

    class FakeVasp:
        name = "vasp"

        def __init__(self, **kwargs):
            self.atoms = bulk("Cu")

        def get_potential_energy(self):
            return 0.0

        def set(self, **kwargs):
            pass

    class FakeSampler:
        def __init__(self, cryst, calc, **kwargs):
            captured["pbar"] = kwargs.get("pbar")

        def sample(self, temperature, n, **kwargs):
            captured["sentinel"] = kwargs.get("sentinel")
            return [(0, 0, np.zeros((1, 3)), np.zeros((1, 3)), 0.1)]

        def generate(self, *args, **kwargs):
            return []

    monkeypatch.setattr(cli, "Vasp", FakeVasp)
    monkeypatch.setattr(cli, "HECSS", FakeSampler)
    structure = tmp_path / "CONTCAR"
    structure.write_text("dummy")
    result = CliRunner().invoke(
        cli.hecss_sampler,
        ["-W", str(tmp_path), "-n", "--no-pbar", "-e", "0",
         "-S", "recommended", str(structure)],
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert captured["pbar"] is False
    assert captured["sentinel"] is None


def test_xsl_writer_saves_scale_without_dfset(tmp_path):
    corrections = [np.ones((1, 3))]
    assert xsl_writer(
        None, [], workdir=str(tmp_path), dfset="DFSET.dat",
        scale="scale.dat", xsl=corrections,
    ) is False
    assert (tmp_path / "scale.dat").exists()
    assert not list(tmp_path.glob("*.raw"))


def test_run_cli_cmd(capsys):
    run_cli_cmd(hecss_sampler, ["--version"])
    assert hecss.__version__ in capsys.readouterr().out
