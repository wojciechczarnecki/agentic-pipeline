import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "templates" / "pre-push"
SHA = "0" * 40


def push(*remote_refs: str) -> subprocess.CompletedProcess:
    lines = "".join(f"refs/heads/local {SHA} {ref} {SHA}\n" for ref in remote_refs)
    return subprocess.run(
        ["bash", str(HOOK), "origin", "git@github.com:o/r.git"],
        input=lines,
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/heads/master"])
def test_push_to_protected_branch_is_rejected(ref):
    result = push(ref)
    assert result.returncode == 1
    assert "open a PR" in result.stderr


def test_push_to_feature_branch_passes():
    assert push("refs/heads/feat/014-x").returncode == 0


def test_main_hidden_among_other_refs_is_rejected():
    assert push("refs/heads/feat/014-x", "refs/heads/main").returncode == 1


def test_tags_and_similarly_named_branches_pass():
    assert push("refs/tags/v1.0", "refs/heads/main-followup").returncode == 0


def test_empty_push_passes():
    assert push().returncode == 0


def test_the_template_is_executable():
    assert os.access(HOOK, os.X_OK)
