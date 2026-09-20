"""The repository's own pre-push hook: main is protected, and a minor or major release
tag needs a green eval receipt for the very commit being tagged.

These are repository rules, not plugin behaviour — the plugin stays project-independent,
so they cannot live in plugin/tests.
"""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "git-hooks" / "pre-push"
RECEIPT = ROOT / "plugin" / "evals" / "last-run.json"
SHA = "0" * 40


def push(ref: str, local_ref: str = "refs/heads/local") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(HOOK), "origin", "git@github.com:o/r.git"],
        input=f"{local_ref} {SHA} {ref} {SHA}\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


@pytest.fixture
def receipt():
    """Swap in a receipt and restore whatever was there, so a real one is never lost."""
    previous = RECEIPT.read_text() if RECEIPT.exists() else None

    def write(commit: str, green: bool):
        RECEIPT.write_text(json.dumps({"commit": commit, "green": green}) + "\n")

    yield write

    if previous is None:
        RECEIPT.unlink(missing_ok=True)
    else:
        RECEIPT.write_text(previous)


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/heads/master"])
def test_push_to_protected_branch_is_rejected(ref):
    assert push(ref).returncode == 1


def test_push_to_feature_branch_passes():
    assert push("refs/heads/feat/001-x").returncode == 0


# A patch is usually a hook or a documentation fix, and a full suite costs real money.
def test_a_patch_tag_needs_no_eval():
    assert push("refs/tags/pipeline--v0.3.1").returncode == 0


@pytest.mark.parametrize("tag", ["pipeline--v0.3.0", "pipeline--v1.0.0"])
def test_a_minor_or_major_tag_without_a_receipt_is_rejected(tag):
    result = push(f"refs/tags/{tag}")
    assert result.returncode == 1
    assert "scripts/eval.sh" in result.stderr


def head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()


# The receipt is committed with the release, so it can never name its own commit. The
# check is therefore "plugin/ is unchanged since the run", not "the shas match".
def test_a_receipt_from_before_a_plugin_change_is_rejected(receipt):
    stale = subprocess.run(
        ["git", "log", "--format=%H", "-1", "--skip=1", "--", "plugin/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not stale:
        pytest.skip("history has no earlier commit touching plugin/")
    receipt(stale, green=True)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "plugin/ changed since the eval ran" in result.stderr


def test_a_red_receipt_is_rejected(receipt):
    receipt(head(), green=False)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "not green" in result.stderr


def test_a_green_receipt_with_plugin_unchanged_passes(receipt):
    receipt(head(), green=True)
    assert push("refs/tags/pipeline--v0.3.0", local_ref="HEAD").returncode == 0
