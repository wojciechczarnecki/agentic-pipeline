"""The repository's own pre-push hook: main is protected, and a minor or major release
tag needs a green eval receipt for the very commit being tagged.

These are repository rules, not plugin behaviour — the plugin stays project-independent,
so they cannot live in plugin/tests.
"""

import hashlib
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

    def write(fingerprint: str, green: bool):
        RECEIPT.write_text(
            json.dumps({"plugin_fingerprint": fingerprint, "green": green}) + "\n"
        )

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


def fingerprint(ref: str = "HEAD") -> str:
    """What plugin/ contains at `ref` — the receipt's own measure, recomputed."""
    listing = subprocess.run(
        ["git", "ls-tree", "-r", ref, "--", "plugin/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout
    kept = "".join(line + "\n" for line in listing.splitlines() if "evals/last-run.json" not in line)
    return hashlib.sha256(kept.encode()).hexdigest()


# A sha would not survive the squash merge that lands the release, so the receipt
# fingerprints plugin/'s contents and the hook recomputes them at tag time.
def test_a_receipt_from_a_different_plugin_state_is_rejected(receipt):
    receipt("0" * 64, green=True)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "plugin/ changed since the eval ran" in result.stderr


def test_the_fingerprint_ignores_the_receipt_itself(receipt):
    """Otherwise writing the receipt would invalidate the receipt."""
    before = fingerprint()
    receipt("whatever", green=True)
    assert fingerprint() == before


def test_a_red_receipt_is_rejected(receipt):
    receipt(fingerprint(), green=False)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "not green" in result.stderr


def test_a_green_receipt_with_plugin_unchanged_passes(receipt):
    receipt(fingerprint(), green=True)
    assert push("refs/tags/pipeline--v0.3.0", local_ref="HEAD").returncode == 0
