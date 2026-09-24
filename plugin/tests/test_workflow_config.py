import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import workflow_config  # noqa: E402

MODULE = Path(workflow_config.__file__)


def write_config(root: Path, data: dict) -> Path:
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    path = root / ".claude" / "workflow.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "backend").mkdir()
    return tmp_path


def test_defaults_cover_every_documented_key():
    data = workflow_config.defaults()
    assert data["production"] == {"hosts": [], "commands": []}
    assert data["worktree"]["dir"] == "../worktrees"
    assert data["verify"] == {"command": "bash scripts/verify.sh", "scopes": []}
    assert data["format"] == []
    assert data["docs"]["roadmap"] == "docs/ROADMAP.md"
    assert data["docs"]["specsDir"] == "specs"
    assert data["gitHooksDir"] == "scripts/git-hooks"
    assert data["language"] == "en"
    assert "migrations" not in data


def test_missing_file_yields_defaults_and_says_so(repo):
    config = workflow_config.load(repo)
    assert config.found is False
    assert config.path is None
    assert config.data == workflow_config.defaults()


def test_config_is_found_from_a_nested_directory(repo):
    path = write_config(repo, {"language": "en"})
    config = workflow_config.load(repo / "backend")
    assert config.path == path
    assert config.get("language") == "en"


def test_search_stops_at_the_repository_root(repo):
    outer = repo.parent
    (outer / ".claude").mkdir(parents=True, exist_ok=True)
    (outer / ".claude" / "workflow.json").write_text(json.dumps({"language": "en"}))
    assert workflow_config.load(repo).found is False


def test_partial_override_keeps_the_other_keys(repo):
    write_config(repo, {"docs": {"roadmap": "ROADMAP.md"}, "production": {"hosts": ["x.test"]}})
    config = workflow_config.load(repo)
    assert config.get("docs.roadmap") == "ROADMAP.md"
    assert config.get("docs.decisions") == "docs/DECISIONS.md"
    assert config.get("production.hosts") == ["x.test"]
    assert config.get("production.commands") == []
    assert config.get("verify.command") == "bash scripts/verify.sh"


def test_migrations_section_is_absent_unless_configured(repo):
    assert workflow_config.load(repo).get("migrations") is None
    write_config(repo, {"migrations": {"command": "alembic", "localHosts": ["localhost"]}})
    assert workflow_config.load(repo).get("migrations.command") == "alembic"


@pytest.mark.parametrize(
    "data, fragment",
    [
        ({"prodaction": {}}, "unknown key `prodaction`"),
        ({"production": {"host": []}}, "unknown key `production.host`"),
        ({"docs": {"roadmaps": "x"}}, "unknown key `docs.roadmaps`"),
        ({"migrations": {"command": "a", "hosts": []}}, "unknown key `migrations.hosts`"),
        ({"language": 7}, "`language` has to be str"),
        ({"production": "example.com"}, "`production` has to be an object"),
        ({"production": {"hosts": "example.com"}}, "`production.hosts` has to be list"),
        ({"production": {"hosts": [1]}}, "`production.hosts[0]` has to be str"),
        ({"format": ["black"]}, "`format[0]` has to be an object"),
        ({"format": [{"match": "*.py"}]}, "`format[0]` is missing `command`"),
        ({"format": [{"match": 1, "command": "black"}]}, "`format[0].match` has to be str"),
        ({"format": [{"match": "*", "command": "b", "x": 1}]}, "unknown key `format[0].x`"),
    ],
)
def test_invalid_config_raises_a_readable_error(repo, data, fragment):
    write_config(repo, data)
    with pytest.raises(workflow_config.ConfigError) as error:
        workflow_config.load(repo)
    assert fragment in str(error.value)


def test_broken_json_names_the_file(repo):
    write_config(repo, {})
    (repo / ".claude" / "workflow.json").write_text("{ nope")
    with pytest.raises(workflow_config.ConfigError) as error:
        workflow_config.load(repo)
    assert "not valid JSON" in str(error.value)


def test_top_level_has_to_be_an_object(repo):
    (repo / ".claude").mkdir(parents=True, exist_ok=True)
    (repo / ".claude" / "workflow.json").write_text("[]")
    with pytest.raises(workflow_config.ConfigError):
        workflow_config.load(repo)


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MODULE), *args], cwd=str(cwd), capture_output=True, text=True
    )


def test_check_returns_zero_for_a_valid_config(repo):
    write_config(repo, {"language": "en"})
    result = run_cli(repo, "--check")
    assert result.returncode == 0
    assert "workflow.json" in result.stdout


def test_check_returns_zero_without_a_config(repo):
    result = run_cli(repo, "--check")
    assert result.returncode == 0
    assert "defaults" in result.stdout


def test_check_returns_one_for_a_broken_config(repo):
    write_config(repo, {"nope": 1})
    result = run_cli(repo, "--check")
    assert result.returncode == 1
    assert "unknown key `nope`" in result.stderr


def test_format_for_prints_the_matching_command(repo):
    write_config(repo, {"format": [{"match": "backend/*.py", "command": "black -q {file}"}]})
    result = run_cli(repo, "--format-for", str(repo / "backend" / "app" / "main.py"))
    assert result.returncode == 0
    assert result.stdout.strip() == "black -q backend/app/main.py"


def test_format_for_appends_the_path_without_a_placeholder(repo):
    write_config(repo, {"format": [{"match": "*.ts", "command": "npx eslint --fix"}]})
    result = run_cli(repo, "--format-for", str(repo / "src" / "a.ts"))
    assert result.stdout.strip() == "npx eslint --fix src/a.ts"


def test_format_for_prints_nothing_without_a_match(repo):
    write_config(repo, {"format": [{"match": "backend/*.py", "command": "black {file}"}]})
    assert run_cli(repo, "--format-for", str(repo / "src" / "a.ts")).stdout.strip() == ""


def test_format_for_prints_nothing_without_a_config(repo):
    result = run_cli(repo, "--format-for", str(repo / "backend" / "a.py"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_format_for_ignores_paths_outside_the_project(repo):
    write_config(repo, {"format": [{"match": "*.py", "command": "black {file}"}]})
    assert run_cli(repo, "--format-for", "/etc/hosts").stdout.strip() == ""


@pytest.mark.parametrize("value", [["stable"], []])
def test_protected_branches_is_accepted(repo, value):
    write_config(repo, {"protectedBranches": value})
    result = run_cli(repo, "--check")
    assert result.returncode == 0, result.stderr
    assert workflow_config.load(repo).get("protectedBranches") == value


def test_protected_branches_is_absent_unless_configured(repo):
    assert "protectedBranches" not in workflow_config.defaults()
    assert workflow_config.load(repo).get("protectedBranches") is None


@pytest.mark.parametrize(
    "value, fragment",
    [
        ("stable", "`protectedBranches` has to be list"),
        (["stable", 1], "`protectedBranches[1]` has to be str"),
    ],
)
def test_protected_branches_must_be_a_list_of_strings(repo, value, fragment):
    write_config(repo, {"protectedBranches": value})
    result = run_cli(repo, "--check")
    assert result.returncode == 1
    assert fragment in result.stderr


def test_load_sections_drops_only_a_bad_protected_branches(repo):
    write_config(
        repo,
        {"protectedBranches": "stable", "language": "en", "production": {"hosts": ["x.test"]}},
    )
    config, problems = workflow_config.load_sections(repo)
    assert problems == ["`protectedBranches` has to be list"]
    assert config.get("protectedBranches") is None
    assert config.get("language") == "en"
    assert config.get("production.hosts") == ["x.test"]


@pytest.mark.parametrize("value", ["de", "EN", ""])
def test_an_unsupported_language_is_rejected(repo, value):
    write_config(repo, {"language": value})
    result = run_cli(repo, "--check")
    assert result.returncode == 1
    assert "`language` has to be one of: en, pl" in result.stderr


@pytest.mark.parametrize("value", ["en", "pl"])
def test_supported_languages_pass(repo, value):
    write_config(repo, {"language": value})
    result = run_cli(repo, "--check")
    assert result.returncode == 0, result.stderr
    assert workflow_config.load(repo).get("language") == value


def test_load_sections_falls_back_to_english(repo):
    write_config(repo, {"language": "de", "production": {"hosts": ["x.test"]}})
    config, problems = workflow_config.load_sections(repo)
    assert problems == ["`language` has to be one of: en, pl"]
    assert config.get("language") == "en"
    assert config.get("production.hosts") == ["x.test"]


STAGES = ["plan", "plan-review", "implement", "final-review"]
ALIASES = ["inherit", "sonnet", "opus", "haiku", "fable"]


# SPEC 011, AC14: a model per stage, passed by /pipeline:ship to the Agent tool.
@pytest.mark.parametrize("stage", STAGES)
@pytest.mark.parametrize("value", ALIASES)
def test_models_accepts_every_stage_and_alias(repo, stage, value):
    write_config(repo, {"models": {stage: value}})
    result = run_cli(repo, "--check")
    assert result.returncode == 0, result.stderr
    assert workflow_config.stage_model(workflow_config.load(repo), stage) == value


def test_stage_model_defaults_to_inherit(repo):
    config = workflow_config.load(repo)
    for stage in STAGES:
        assert workflow_config.stage_model(config, stage) == "inherit"
    write_config(repo, {"models": {"implement": "sonnet"}})
    config = workflow_config.load(repo)
    assert workflow_config.stage_model(config, "implement") == "sonnet"
    assert workflow_config.stage_model(config, "plan") == "inherit"


# The guard and the report load section by section; for `models` a bad entry costs only its
# own stage, which then inherits, and the other stages keep their model.
def test_a_bad_models_entry_warns_and_only_that_stage_inherits(repo):
    write_config(repo, {"models": {"implement": "gpt", "plan": "opus"}, "language": "en"})
    config, problems = workflow_config.load_sections(repo)
    assert len(problems) == 1 and "models.implement" in problems[0], problems
    assert workflow_config.stage_model(config, "implement") == "inherit"
    assert workflow_config.stage_model(config, "plan") == "opus"

    write_config(repo, {"models": {"deploy": "opus", "plan": "haiku"}})
    config, problems = workflow_config.load_sections(repo)
    assert len(problems) == 1 and "models.deploy" in problems[0], problems
    assert workflow_config.stage_model(config, "plan") == "haiku"
    assert config.get("models.deploy") is None


@pytest.mark.parametrize(
    "models, fragment",
    [
        (
            {"implement": "gpt"},
            "`models.implement` has to be one of: inherit, sonnet, opus, haiku, fable",
        ),
        ({"implement": 3}, "`models.implement` has to be str"),
        ({"deploy": "opus"}, "unknown key `models.deploy`"),
        ("sonnet", "`models` has to be an object"),
    ],
)
def test_models_errors_are_readable(repo, models, fragment):
    write_config(repo, {"models": models})
    result = run_cli(repo, "--check")
    assert result.returncode == 1
    assert fragment in result.stderr


# SPEC 012, AC4: `implement.chunked` turns the chunked implementer on; anything but a boolean
# warns and counts as off, and the guard never blocks on it.
@pytest.mark.parametrize("value", [True, False])
def test_implement_chunked_accepts_a_boolean(repo, value):
    write_config(repo, {"implement": {"chunked": value}})
    assert run_cli(repo, "--check").returncode == 0
    assert workflow_config.load(repo).get("implement.chunked") is value


def test_implement_chunked_is_off_without_the_section(repo):
    assert workflow_config.defaults()["implement"] == {"chunked": False}
    write_config(repo, {"language": "en"})
    assert workflow_config.load(repo).get("implement.chunked") is False
    config, problems = workflow_config.load_sections(repo)
    assert problems == []
    assert config.get("implement.chunked") is False


@pytest.mark.parametrize(
    "section, fragment",
    [
        ({"chunked": "yes"}, "`implement.chunked` has to be bool"),
        ({"chunked": 1}, "`implement.chunked` has to be bool"),
        ({"chunked": True, "size": 3}, "unknown key `implement.size`"),
        ("on", "`implement` has to be an object"),
    ],
)
def test_implement_bad_values_warn_and_count_as_off(repo, section, fragment):
    write_config(repo, {"implement": section, "language": "en"})
    config, problems = workflow_config.load_sections(repo)
    assert len(problems) == 1 and fragment in problems[0], problems
    assert config.get("implement.chunked") is False
    assert config.get("language") == "en"
    result = run_cli(repo, "--check")
    assert result.returncode == 1
    assert fragment in result.stderr


@pytest.mark.parametrize(
    "data, fragment",
    [
        ({"language": True}, "`language` has to be str"),
        ({"verify": {"command": True}}, "`verify.command` has to be str"),
        ({"protectedBranches": False}, "`protectedBranches` has to be list"),
    ],
)
def test_implement_bool_does_not_open_other_keys(repo, data, fragment):
    write_config(repo, data)
    with pytest.raises(workflow_config.ConfigError, match=fragment):
        workflow_config.load(repo)
