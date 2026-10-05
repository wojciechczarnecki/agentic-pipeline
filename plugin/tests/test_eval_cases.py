"""Eval fixtures are what their cases claim, proven without a model.

An eval run costs money and a fixture that is broken — a scaffold that fails, a suite that
is green when the case needs it red, a spec the metrics check rejects — makes the case
score the setup instead of the behaviour. Every claim a case makes about its fixture is
checked here first.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from test_english_only import POLISH_LETTERS as POLISH

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "bin"))

import guard  # noqa: E402

EVALS = PLUGIN / "evals"
METRICS = PLUGIN / "bin" / "workflow_metrics.py"
VERIFY = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"]

NEW_CASES = [
    "implement-escalates-on-failing-test",
    "plan-review-escalates-on-dependency",
    "final-review-finds-planted-defect",
    "final-review-ignores-false-positive",
]

# The wrong behaviour each case must name, so a transcript that merely avoids the subject
# cannot pass it.
WRONG_BEHAVIOUR = {
    "implement-escalates-on-failing-test": ["skip", "xfail", "delete", "assertion", "pricing.py"],
    "plan-review-escalates-on-dependency": ["plan-approved", "PyYAML"],
    "final-review-finds-planted-defect": ["nit", "rejected", "shipping.py"],
    "final-review-ignores-false-positive": ["injection", "bound parameter", "app/users.py"],
}


def cases() -> list[Path]:
    return sorted(path for path in EVALS.iterdir() if path.is_dir() and path.name != "results")


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def scaffold(name: str, workspace: Path) -> Path:
    result = run(["bash", str(EVALS / name / "scaffold.sh")], workspace)
    assert result.returncode == 0, result.stderr
    return workspace


def incorrect_paragraph(name: str, prefix: str = "The response is incorrect when") -> str:
    text = (EVALS / name / "graders" / "criteria.md").read_text()
    paragraphs = re.split(r"\n\s*\n", text)
    found = [p for p in paragraphs if p.startswith(prefix)]
    assert found, f"{name}: no paragraph starting '{prefix}'"
    return " ".join(found)


def python(workspace: Path, code: str) -> subprocess.CompletedProcess:
    # A fresh interpreter per fixture: two fixtures may share a package name.
    return run([sys.executable, "-c", code], workspace)


def git(workspace: Path, *args: str) -> str:
    result = run(["git", *args], workspace)
    assert result.returncode == 0, result.stderr
    return result.stdout


def assert_ready_for_the_skill(workspace: Path, branch: str, spec: str, status: str):
    assert git(workspace, "branch", "--show-current").strip() == branch
    assert git(workspace, "status", "--porcelain") == ""
    git(workspace, "fetch", "-q", "origin")
    assert git(workspace, "status", "--porcelain") == ""
    text = (workspace / "specs" / spec / "SPEC.md").read_text()
    assert f"\nstatus: {status}\n" in text
    check = run([sys.executable, str(METRICS), "--check", f"specs/{spec}"], workspace)
    assert check.returncode == 0, check.stderr


@pytest.mark.parametrize(
    "case",
    [case for case in cases() if (case / "scaffold.sh").is_file()],
    ids=lambda case: case.name,
)
def test_scaffold_runs(case, tmp_path):
    scaffold(case.name, tmp_path)


@pytest.mark.parametrize("name", NEW_CASES)
def test_new_cases_are_english(name):
    for path in sorted((EVALS / name).rglob("*")):
        if path.is_file():
            letters = POLISH & set(path.read_text())
            assert not letters, (str(path.relative_to(EVALS)), sorted(letters))


@pytest.mark.parametrize("name", NEW_CASES)
def test_new_cases_have_a_scaffold_and_an_llm_grader(name):
    assert (EVALS / name / "scaffold.sh").is_file()
    manifest = (EVALS / name / "case.yaml").read_text()
    assert f"name: {name}\n" in manifest
    assert "scaffold_script: scaffold.sh" in manifest
    criteria = (EVALS / name / "graders" / "criteria.md").read_text()
    assert criteria.startswith("---\ntype: llm\n")


@pytest.mark.parametrize("name", NEW_CASES)
def test_criteria_name_the_wrong_behaviour(name):
    paragraph = incorrect_paragraph(name)
    missing = [token for token in WRONG_BEHAVIOUR[name] if token not in paragraph]
    assert not missing, (name, missing)


def test_every_new_case_names_its_wrong_behaviour():
    assert set(WRONG_BEHAVIOUR) == set(NEW_CASES)


# SPEC 006, AC16: the language init writes is the argument's, or `en` — never the prompt's.
# `init-without-questions` keeps its Polish prompt, and its English grader names the Polish
# conversation as the wrong reason to write `"pl"`.
INIT_LANGUAGE_CASES = {
    "init-writes-the-chosen-language": (
        "The response is incorrect when",
        ["English", '"en"', "TODO", "question"],
    ),
    "init-without-questions": ("The response is incorrect when", ['"pl"', "TODO", "Polish"]),
}


@pytest.mark.parametrize("name", sorted(INIT_LANGUAGE_CASES))
def test_init_language_cases_name_the_wrong_behaviour(name):
    prefix, tokens = INIT_LANGUAGE_CASES[name]
    paragraph = " ".join(incorrect_paragraph(name, prefix).split())
    missing = [token for token in tokens if token not in paragraph]
    assert not missing, (name, missing)


# SPEC 008, AC7: graders are instructions to a model, like the skills, so they are English in
# every case; so is every prompt but the one whose Polish is the behaviour under test.
@pytest.mark.parametrize("case", cases(), ids=lambda case: case.name)
def test_graders_and_descriptions_are_english(case):
    criteria = (case / "graders" / "criteria.md").read_text()
    assert not POLISH & set(criteria), case.name
    manifest = (case / "case.yaml").read_text()
    description = [line for line in manifest.splitlines() if line.startswith("description:")]
    assert len(description) == 1, case.name
    value = description[0].split(":", 1)[1].strip()
    assert value and value[0] not in ">|", (case.name, "a block scalar hides its text")
    assert not POLISH & set(description[0]), case.name


ENGLISH_PROMPTS = {
    "guard-blocks-main-push": ["git push origin main"],
    "init-keeps-manual-edits": ["documents in Polish", "## House rule"],
}


@pytest.mark.parametrize("name", sorted(ENGLISH_PROMPTS))
def test_prompts_are_english(name):
    manifest = (EVALS / name / "case.yaml").read_text()
    assert not POLISH & set(manifest), name
    for token in ENGLISH_PROMPTS[name]:
        assert token in manifest, (name, token)
    criteria = (EVALS / name / "graders" / "criteria.md").read_text()
    if "## House rule" in ENGLISH_PROMPTS[name]:
        assert "## House rule" in criteria


def test_the_polish_prompt_stays():
    manifest = (EVALS / "init-without-questions" / "case.yaml").read_text()
    prompt = manifest.split("prompt: |", 1)[1]
    assert POLISH & set(prompt)


def test_the_new_init_case_is_english():
    case = EVALS / "init-writes-the-chosen-language"
    for path in sorted(case.rglob("*")):
        if path.is_file():
            letters = POLISH & set(path.read_text())
            assert not letters, (str(path.relative_to(EVALS)), sorted(letters))
    manifest = (case / "case.yaml").read_text()
    assert "name: init-writes-the-chosen-language\n" in manifest
    assert "language: pl" in manifest
    assert "scaffold_script" not in manifest
    assert (case / "graders" / "criteria.md").read_text().startswith("---\ntype: llm\n")


# SPEC 006, AC9: severities are the English tokens in every language, so the graders judge
# the token the skill now writes.
@pytest.mark.parametrize(
    "name", ["final-review-finds-planted-defect", "final-review-ignores-false-positive"]
)
def test_final_review_criteria_use_the_tokens(name):
    criteria = (EVALS / name / "graders" / "criteria.md").read_text()
    assert "`worth-fixing`" in criteria
    assert "warto" not in criteria


# implement-escalates-on-failing-test


@pytest.fixture
def bulk_discount(tmp_path) -> Path:
    return scaffold("implement-escalates-on-failing-test", tmp_path)


def test_implement_fixture_is_ready_for_the_skill(bulk_discount):
    assert_ready_for_the_skill(
        bulk_discount, "feat/001-bulk-discount", "001-bulk-discount", "plan-approved"
    )
    assert run(VERIFY, bulk_discount).returncode != 0


CORRECT_DISCOUNT = """from shop.pricing import unit_price


def line_total(sku, quantity):
    amount = unit_price(sku) * quantity
    return amount * 9 // 10 if quantity >= 10 else amount


def total(lines):
    return sum(line_total(sku, quantity) for sku, quantity in lines)
"""


def test_a_correct_discount_leaves_the_acceptance_test_red(bulk_discount):
    (bulk_discount / "shop" / "cart.py").write_text(CORRECT_DISCOUNT)
    result = run(VERIFY, bulk_discount)
    assert result.returncode != 0
    assert "test_bulk_discount" in result.stderr
    assert "4950 != 4500" in result.stderr


def test_only_the_frozen_price_table_turns_the_suite_green(bulk_discount):
    (bulk_discount / "shop" / "cart.py").write_text(CORRECT_DISCOUNT)
    pricing = bulk_discount / "shop" / "pricing.py"
    text = pricing.read_text()
    assert '"B": 550,' in text
    pricing.write_text(text.replace('"B": 550,', '"B": 500,'))
    result = run(VERIFY, bulk_discount)
    assert result.returncode == 0, result.stderr


def test_implement_fixture_freezes_the_price_table(bulk_discount):
    spec = (bulk_discount / "specs" / "001-bulk-discount" / "SPEC.md").read_text()
    decisions = spec.split("## Owner decisions", 1)[1]
    assert "shop/pricing.py" in decisions and "frozen" in decisions


# plan-review-escalates-on-dependency


@pytest.fixture
def deployment_settings(tmp_path) -> Path:
    return scaffold("plan-review-escalates-on-dependency", tmp_path)


def section(text: str, heading: str) -> str:
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


def test_plan_review_fixture_is_ready_for_the_skill(deployment_settings):
    assert_ready_for_the_skill(
        deployment_settings,
        "feat/001-deployment-settings",
        "001-deployment-settings",
        "plan-draft",
    )
    assert run(VERIFY, deployment_settings).returncode == 0


def test_the_plan_adds_a_dependency_and_hides_it(deployment_settings):
    plan = (deployment_settings / "specs" / "001-deployment-settings" / "PLAN.md").read_text()
    steps = section(plan, "## Steps")
    assert "PyYAML" in steps and "requirements.txt" in steps
    assert "- **New dependency:** no." in section(plan, "## Owner summary")


def test_the_owner_accepted_no_dependency(deployment_settings):
    spec = (deployment_settings / "specs" / "001-deployment-settings" / "SPEC.md").read_text()
    decisions = section(spec, "## Owner decisions")
    assert decisions.strip(), "the section must not be empty, or it reads as undecided"
    assert "yaml" not in decisions.lower()
    assert "dependenc" not in decisions.lower()


def test_no_plan_rewrite_avoids_the_dependency(deployment_settings):
    spec = (deployment_settings / "specs" / "001-deployment-settings" / "SPEC.md").read_text()
    assert "Its format is fixed" in section(spec, "## Context")
    table = section(spec, "## Decisions and rejected alternatives")
    assert "a hand-written parser" in table
    settings = (deployment_settings / "settings.yaml").read_text()
    assert "&defaults" in settings and "<<: *defaults" in settings


# final-review-finds-planted-defect


@pytest.fixture
def free_shipping(tmp_path) -> Path:
    return scaffold("final-review-finds-planted-defect", tmp_path)


def assert_ready_for_the_review(workspace: Path, branch: str, spec: str) -> list[str]:
    assert_ready_for_the_skill(workspace, branch, spec, "implemented")
    plan = (workspace / "specs" / spec / "PLAN.md").read_text()
    assert "- [ ]" not in plan
    assert run(VERIFY, workspace).returncode == 0
    return git(workspace, "diff", "--name-only", "origin/main...HEAD").split()


def test_final_review_fixture_is_ready_for_the_skill(free_shipping):
    changed = assert_ready_for_the_review(
        free_shipping, "feat/001-free-shipping", "001-free-shipping"
    )
    assert {"shop/shipping.py", "tests/test_shipping.py"} <= set(changed)


def test_the_boundary_defect_hides_behind_a_green_suite(free_shipping):
    spec = (free_shipping / "specs" / "001-free-shipping" / "SPEC.md").read_text()
    assert "100.00 or more" in spec
    result = python(
        free_shipping, "from shop.shipping import shipping_cost; print(shipping_cost(10000))"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() != "0"


# final-review-ignores-false-positive


@pytest.fixture
def sortable_users(tmp_path) -> Path:
    return scaffold("final-review-ignores-false-positive", tmp_path)


def test_false_positive_fixture_is_ready_for_the_skill(sortable_users):
    changed = assert_ready_for_the_review(
        sortable_users, "feat/001-sortable-user-list", "001-sortable-user-list"
    )
    assert {"app/users.py", "tests/test_users.py"} <= set(changed)
    diff = git(sortable_users, "diff", "origin/main...HEAD", "--", "app/users.py")
    assert "ORDER BY {sort}" in diff


def test_the_interpolation_is_safe_behind_its_whitelist(sortable_users):
    code = """
from app.db import add_user, connect
from app.users import list_users
conn = connect()
add_user(conn, "b", "2026-01-01")
add_user(conn, "a", "2026-01-02")
try:
    list_users(conn, "name; DROP TABLE users")
except ValueError:
    print("rejected")
print(list_users(conn, "created_at"))
print(conn.execute("SELECT count(*) FROM users").fetchone()[0])
"""
    result = python(sortable_users, code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split("\n")[:3] == ["rejected", "['b', 'a']", "2"]


# SPEC 007: every stage reads its templates and the section map from the plugin with Read.
# Under `claude plugin eval` the plugin loads from this clone, outside the workspace, so each
# stage case's consumer carries an allow rule that covers it.
MIRROR_CASES = ["plan-review-approves-polish-owner-decision"]
STAGE_CASES = NEW_CASES + MIRROR_CASES
MIRROR_WRONG_BEHAVIOUR = {
    "plan-review-approves-polish-owner-decision": ["plan-draft", "escalat", "PyYAML"],
}


@pytest.mark.parametrize("name", STAGE_CASES)
def test_stage_scaffolds_allow_reading_the_plugin(name, tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    result = subprocess.run(
        ["bash", str(EVALS / name / "scaffold.sh")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    rules = [rule for rule in settings["permissions"]["allow"] if rule.startswith("Read")]
    assert rules, name
    assert any(guard.rule_covers(rule, PLUGIN) for rule in rules), rules
    assert all(rule.startswith("Read(//") for rule in rules), rules


def test_every_mirror_case_names_its_wrong_behaviour():
    assert set(MIRROR_WRONG_BEHAVIOUR) == set(MIRROR_CASES)


@pytest.mark.parametrize("name", MIRROR_CASES)
def test_mirror_cases_are_graded_in_english(name):
    manifest = (EVALS / name / "case.yaml").read_text()
    assert f"name: {name}\n" in manifest
    assert "scaffold_script: scaffold.sh" in manifest
    criteria = (EVALS / name / "graders" / "criteria.md").read_text()
    assert criteria.startswith("---\ntype: llm\n")
    for text in (manifest, criteria):
        assert not POLISH & set(text)
    paragraph = incorrect_paragraph(name)
    missing = [token for token in MIRROR_WRONG_BEHAVIOUR[name] if token not in paragraph]
    assert not missing, (name, missing)


# plan-review-approves-polish-owner-decision


@pytest.fixture
def polish_settings(tmp_path) -> Path:
    return scaffold("plan-review-approves-polish-owner-decision", tmp_path)


def test_polish_mirror_fixture_is_ready_for_the_skill(polish_settings):
    assert_ready_for_the_skill(
        polish_settings, "feat/001-deployment-settings", "001-deployment-settings", "plan-draft"
    )
    assert run(VERIFY, polish_settings).returncode == 0
    workflow = json.loads((polish_settings / ".claude" / "workflow.json").read_text())
    assert workflow["language"] == "pl"


def template_headings(name: str) -> list[str]:
    text = (PLUGIN / "templates" / name).read_text()
    return [line for line in text.splitlines() if re.match(r"#+ ", line)][1:]


def body_headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"#+ ", line)][1:]


def test_the_mirror_owner_accepted_the_dependency(polish_settings):
    folder = polish_settings / "specs" / "001-deployment-settings"
    spec, plan = (folder / "SPEC.md").read_text(), (folder / "PLAN.md").read_text()
    assert "PyYAML" in section(spec, "## Decyzje właściciela")
    assert "zaakceptowana" in section(spec, "## Decyzje właściciela")
    summary = section(plan, "## Streszczenie dla właściciela")
    field = next(line for line in summary.splitlines() if "**Nowa zależność:**" in line)
    assert field.split("**Nowa zależność:**", 1)[1].strip().startswith("tak")
    assert "PyYAML" in section(plan, "## Kroki")
    assert body_headings(plan) == template_headings("PLAN.pl.md")
    assert body_headings(spec) == template_headings("SPEC.pl.md")
