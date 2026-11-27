"""VASP integration tests.

These replace the notebook checks formerly marked ``#| vasp``. They are
skipped unless VASP is installed; run them with ``pytest -m vasp`` in the
dedicated VASP environment. Set ``HECSS_VASP_COMMAND`` if VASP is invoked
through a wrapper instead of the plain ``vasp`` executable.
"""

import os
import shutil
from glob import glob
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


def test_vasp_workflow_writes_each_calculation_once(tmp_path):
    from ase.calculators.vasp import Vasp

    from hecss import HECSS

    calc = Vasp(restart=True, directory=STRUCTURE)
    cryst = calc.atoms.copy()
    calc.set(directory=str(tmp_path / "sc"), command=VASP_COMMAND, nsw=0)
    cryst.calc = calc

    sampler = HECSS(cryst, calc, width=1.0, directory=str(tmp_path), pbar=False)
    n_est = 2
    sampler.estimate_width_scale(n_est, nwork=0)
    assert len(glob(str(tmp_path / "w_est" / "*" / "vasprun.xml"))) == n_est

    samples = sampler.sample(300, 2)
    assert len(glob(str(tmp_path / "T_300.0K" / "smpl" / "*"))) == len(samples)
