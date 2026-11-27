"""VASP integration tests.

These replace the notebook checks formerly marked ``#| vasp``. They are
skipped unless VASP is installed; run them with ``pytest -m vasp`` in the
dedicated VASP environment. Set ``HECSS_VASP_COMMAND`` if VASP is invoked
through a wrapper instead of the plain ``vasp`` executable.
"""

import os
import shlex
import shutil
from collections import Counter
from pathlib import Path

import pytest

VASP_COMMAND = os.environ.get("HECSS_VASP_COMMAND", "vasp")

pytestmark = [
    pytest.mark.vasp,
    pytest.mark.skipif(
        shutil.which(VASP_COMMAND.split()[0]) is None,
        reason="VASP executable is required",
    ),
]

STRUCTURE = Path("example/VASP_3C-SiC/1x1x1/sc_1x1x1")


def counted_command(tmp_path):
    """Wrap VASP so every invocation appends its working directory to a log."""
    log = tmp_path / "vasp_calls.log"
    wrapper = tmp_path / "vasp_counted"
    wrapper.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$PWD" >> {shlex.quote(str(log))}\n'
        f'exec {VASP_COMMAND} "$@"\n'
    )
    wrapper.chmod(0o755)
    return str(wrapper), log


def test_vasp_workflow_writes_each_calculation_once(tmp_path):
    from ase.calculators.vasp import Vasp

    from hecss import HECSS

    command, log = counted_command(tmp_path)
    calc = Vasp(restart=True, directory=STRUCTURE)
    cryst = calc.atoms.copy()
    calc.set(directory=str(tmp_path / "sc"), command=command, nsw=0)
    cryst.calc = calc

    sampler = HECSS(cryst, calc, width=1.0, directory=str(tmp_path), pbar=False)
    n_est = 2
    sampler.estimate_width_scale(n_est, nwork=0)
    assert len(list((tmp_path / "w_est").glob("*/vasprun.xml"))) == n_est

    samples = sampler.sample(300, 2)
    assert len(list((tmp_path / "T_300.0K" / "smpl").glob("*"))) == len(samples)

    calls = Counter(line.strip() for line in log.read_text().splitlines())
    assert calls[str((tmp_path / "sc").resolve())] == 1

    width_dirs = sorted((tmp_path / "w_est").glob("???"))
    assert len(width_dirs) == n_est
    assert all(calls[str(d.resolve())] == 1 for d in width_dirs)

    sample_dirs = sorted((tmp_path / "T_300.0K" / "smpl").glob("*"))
    assert len(sample_dirs) == len(samples)
    for directory in sample_dirs:
        count = calls[str(directory.resolve())]
        if directory.name == "0000":
            # Burn-in samples may legitimately be recomputed.
            assert count >= 1
        else:
            assert count == 1
