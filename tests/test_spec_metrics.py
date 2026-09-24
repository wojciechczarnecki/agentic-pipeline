"""Every spec of this repository passes the metrics check (SPEC 011, AC10: the old
`deviations` key still passes after the split)."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugin" / "bin" / "workflow_metrics.py"
SPECS = sorted(path.parent for path in (ROOT / "specs").glob("*/SPEC.md"))


@pytest.mark.parametrize("spec", SPECS, ids=[spec.name for spec in SPECS])
def test_every_repository_spec_passes_the_check(spec):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(spec)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
