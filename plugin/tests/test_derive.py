import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin"
SCRIPT = BIN / "workflow_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "derive"
SECTIONS = BIN.parent / "templates" / "sections.md"
ROW = re.compile(r"^\| `([^`]+)` \| (SPEC|PLAN) \| `([^`]*)` \| `([^`]*)` \|$")

EXPECTED = {
    "plan_steps": 4,
    "implement_steps": 4,
    "implement_iterations": 3,
    "deviations_minor": 1,
    "deviations_major": 1,
    "plan_review_blockers": 1,
    "plan_review_majors": 2,
    "final_review_blockers": 1,
    "final_review_worth_fixing": 2,
    "final_review_nits": 1,
    "findings_accepted": 3,
    "findings_rejected": 1,
    "escalations": 4,
    "escalations_permission": 1,
    "escalations_tooling": 1,
}


def polish(text: str) -> str:
    # The Polish copy is built from the section map at run time, so no Polish letter lives in
    # a file outside the allowlist of test_english_only.py.
    for line in SECTIONS.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match and match.group(4).startswith("#") and match.group(3) != match.group(4):
            text = re.sub(rf"(?m)^{re.escape(match.group(4))}$", match.group(3), text)
        if match and match.group(1) == "pass-condition":
            text = text.replace(match.group(4), match.group(3))
    return text


def make_spec(tmp_path: Path, language: str = "en", name: str = "001-demo") -> Path:
    target = tmp_path / name
    target.mkdir(parents=True, exist_ok=True)
    for file in ("SPEC.md", "PLAN.md"):
        text = (FIXTURE / file).read_text()
        (target / file).write_text(polish(text) if language == "pl" else text)
    return target


def derive(directory: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--derive", str(directory), *extra],
        capture_output=True,
        text=True,
    )


def check(directory: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(directory)], capture_output=True, text=True
    )


def metrics_of(directory: Path) -> dict[str, str]:
    sys.path.insert(0, str(BIN))
    import workflow_metrics

    return workflow_metrics.parse_metrics((directory / "SPEC.md").read_text())


def metric_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"  [a-z_]+: ", line)]


@pytest.mark.parametrize("language", ["en", "pl"])
def test_derive_writes_every_key(tmp_path, language):
    spec = make_spec(tmp_path, language)
    result = derive(spec)
    assert result.returncode == 0, result.stderr
    metrics = metrics_of(spec)
    for key, value in EXPECTED.items():
        assert metrics.get(key) == str(value), (key, metrics.get(key), result.stderr)
    assert check(spec).returncode == 0, check(spec).stderr


def test_derive_keeps_every_other_byte(tmp_path):
    spec = make_spec(tmp_path)
    before = (spec / "SPEC.md").read_text()
    derive(spec)
    after = (spec / "SPEC.md").read_text()

    def others(text: str) -> list[str]:
        return [
            line
            for line in text.splitlines()
            if not (re.match(r"  [a-z_]+: ", line) and line.split(":")[0].strip() in EXPECTED)
        ]

    assert metrics_of(spec)["plan_steps"] == "4"
    assert others(after) == others(before)
    assert "  plan_changes: 3" in after and "  started_at: 2026-10-05T09:00" in after
    assert (spec / "PLAN.md").read_text() == (FIXTURE / "PLAN.md").read_text()


def test_derive_is_idempotent(tmp_path):
    spec = make_spec(tmp_path)
    derive(spec)
    first = (spec / "SPEC.md").read_bytes()
    assert derive(spec).returncode == 0
    assert (spec / "SPEC.md").read_bytes() == first


def test_a_missing_iteration_note_leaves_iterations_unwritten(tmp_path):
    spec = make_spec(tmp_path)
    plan = (spec / "PLAN.md").read_text()
    (spec / "PLAN.md").write_text(plan.replace(" — `iterations: 2`", ""))
    text = (spec / "SPEC.md").read_text()
    (spec / "SPEC.md").write_text(
        text.replace("  escalations: 0\n", "  escalations: 0\n  implement_iterations: 9\n")
    )
    result = derive(spec)
    assert result.returncode == 0
    assert metrics_of(spec)["implement_iterations"] == "9"
    assert "step 2" in result.stderr and "implement_iterations" in result.stderr
    assert metrics_of(spec)["implement_steps"] == "4"


def test_missing_sources_are_named(tmp_path):
    spec = make_spec(tmp_path)
    plan = (spec / "PLAN.md").read_text()
    head = plan.split("## Steps")[0]
    bare = (
        head
        + "## Steps\n\n- [ ] 1. First — files: `a`\n\n## Owner decisions\n\n"
        + "_(appended)_\n\n## Review log\n\n_(filled in)_\n\n## Deviations\n\n_(filled in)_\n\n"
        + "## Final review\n\n_(filled in)_\n"
    )
    (spec / "PLAN.md").write_text(bare)
    text = (spec / "SPEC.md").read_text().replace("status: implemented", "status: plan-approved")
    (spec / "SPEC.md").write_text(text)
    result = derive(spec)
    assert result.returncode == 0
    metrics = metrics_of(spec)
    for key in (
        "plan_review_blockers",
        "plan_review_majors",
        "final_review_blockers",
        "final_review_worth_fixing",
        "final_review_nits",
        "implement_steps",
        "implement_iterations",
        "deviations_minor",
        "deviations_major",
        "findings_accepted",
        "findings_rejected",
    ):
        assert key not in metrics, key
        assert key in result.stderr, key
    assert metrics["plan_steps"] == "1"


def test_escalations_by_kind(tmp_path):
    spec = make_spec(tmp_path)
    text = (spec / "SPEC.md").read_text()
    extra = "- 2026-10-05 — plan — `maybe` — An unknown kind — Not counted.\n"
    (spec / "SPEC.md").write_text(text + extra)
    derive(spec)
    metrics = metrics_of(spec)
    assert metrics["escalations"] == "4"
    assert metrics["escalations_permission"] == "1"
    assert metrics["escalations_tooling"] == "1"

    (spec / "PLAN.md").unlink()
    again = derive(spec)
    assert again.returncode == 0
    metrics = metrics_of(spec)
    assert metrics["escalations"] == "1"
    assert metrics["escalations_permission"] == "0"
    assert "plan_steps" in again.stderr


def test_an_unformed_plan_decision_leaves_escalations_unwritten(tmp_path):
    spec = make_spec(tmp_path)
    plan = (spec / "PLAN.md").read_text()
    (spec / "PLAN.md").write_text(
        plan.replace("## Review log", "- Asked about colour, answered blue.\n\n## Review log")
    )
    result = derive(spec)
    assert result.returncode == 0
    metrics = metrics_of(spec)
    assert metrics["escalations"] == "0"
    for key in ("escalations", "escalations_permission", "escalations_tooling"):
        assert key in result.stderr, key


def test_derive_needs_a_spec(tmp_path):
    result = derive(tmp_path)
    assert result.returncode == 1
    assert "SPEC.md" in result.stderr


def test_derive_is_exclusive(tmp_path):
    spec = make_spec(tmp_path)
    for other in ("--check", "--record-cost"):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--derive", other, str(spec)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, other
        assert "separate runs" in result.stderr, other


def test_derive_without_a_directory_is_a_usage_error():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--derive"], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "usage" in result.stderr


def test_a_copy_without_a_plan_still_derives_escalations(tmp_path):
    spec = tmp_path / "001-solo"
    spec.mkdir()
    shutil.copy(FIXTURE / "SPEC.md", spec / "SPEC.md")
    assert derive(spec).returncode == 0
    assert metrics_of(spec)["escalations"] == "1"


# SPEC 014, AC11: a plan copied from a template counts nothing.
@pytest.mark.parametrize("language", ["en", "pl"])
def test_the_bare_template_derives_nothing(tmp_path, language):
    spec = make_spec(tmp_path, language)
    template = BIN.parent / "templates" / f"PLAN.{language}.md"
    (spec / "PLAN.md").write_text(template.read_text())
    text = (spec / "SPEC.md").read_text().replace("status: implemented", "status: plan-draft")
    (spec / "SPEC.md").write_text(text)
    result = derive(spec)
    assert result.returncode == 0
    metrics = metrics_of(spec)
    for key in (
        "plan_steps",
        "implement_steps",
        "implement_iterations",
        "plan_review_blockers",
        "final_review_nits",
        "findings_accepted",
        "deviations_minor",
    ):
        assert key not in metrics, key
    assert metrics["escalations"] == "1"
