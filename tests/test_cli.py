"""Smoke tests for the console entry points."""

import pytest
from click.testing import CliRunner

import hecss
from hecss.cli import (
    calculate_xscale,
    hecss_sampler,
    plot_bands,
    plot_stats,
    reshape_sample,
    run_cli_cmd,
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


def test_run_cli_cmd(capsys):
    run_cli_cmd(hecss_sampler, ["--version"])
    assert hecss.__version__ in capsys.readouterr().out
