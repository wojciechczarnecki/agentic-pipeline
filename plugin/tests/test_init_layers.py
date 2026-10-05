import json
import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
WORKFLOWS = PLUGIN / "templates" / "github" / "workflows"
SUBDIRECTORY_MARKER = "# subdirectory layer"
ROOT_MARKER = "# root layer"


# The rendering the `init` skill spells out, step by step: a layer is a root layer or a
# subdirectory layer, and the lines that belong to the other form go away.
def render(name: str, layer: str, directory: str | None = None) -> str:
    lines = []
    for line in (WORKFLOWS / name).read_text().splitlines():
        if directory is None:
            if line.rstrip().endswith(SUBDIRECTORY_MARKER):
                continue
            line = re.sub(rf"\s+{ROOT_MARKER}$", "", line)
        else:
            if line.rstrip().endswith(ROOT_MARKER):
                continue
            line = re.sub(rf"\s+{SUBDIRECTORY_MARKER}$", "", line)
            line = line.replace("<dir>", directory)
        lines.append(line.replace("<layer>", layer))
    return "\n".join(lines) + "\n"


def uncommented(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_ci_renders_a_subdirectory_layer():
    python = render("ci-python.yml", "backend", "backend")
    assert "\n  backend:\n" in python
    assert "    defaults:\n      run:\n        working-directory: backend\n" in python
    setup = (
        "        uses: astral-sh/setup-uv@v7\n        with:\n          working-directory: backend\n"
    )
    assert setup in python
    node = render("ci-node.yml", "frontend", "frontend")
    assert "\n  frontend:\n" in node
    assert "          cache-dependency-path: frontend/package-lock.json\n" in node
    assert "        working-directory: frontend\n" in node
    for text in (python, node):
        assert SUBDIRECTORY_MARKER not in text and ROOT_MARKER not in text
        assert "<dir>" not in text and "<layer>" not in text


def test_ci_renders_a_root_layer_as_today():
    python = render("ci-python.yml", "python")
    node = render("ci-node.yml", "node")
    assert "\n  python:\n" in python and "\n  node:\n" in node
    for text in (python, node):
        assert "working-directory" not in text and "defaults:" not in text
        assert SUBDIRECTORY_MARKER not in text and ROOT_MARKER not in text
        assert "<dir>" not in text and "<layer>" not in text
    assert "          cache-dependency-path: package-lock.json\n" in node
    assert "      - uses: actions/checkout@v7\n" in python


PLACEHOLDERS = {
    "ci-python-placeholder.yml": "ci-python.yml",
    "ci-node-placeholder.yml": "ci-node.yml",
}


def step_lines(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:- )?(run|uses): (.+?)(?:\s+#.*)?$", line)
        if match:
            found.append(f"{match.group(1)}: {match.group(2)}")
    return found


@pytest.mark.parametrize("placeholder, real", sorted(PLACEHOLDERS.items()))
def test_placeholder_jobs_pass_and_list_the_real_steps(placeholder, real):
    text = (WORKFLOWS / placeholder).read_text()
    assert "continue-on-error" not in text
    live = uncommented(text)
    assert "uses: actions/checkout@v7" in live
    runs = re.findall(r"^\s+run: +([^#\s].*)$", live, re.M)
    assert len(runs) == 1 and runs[0].startswith("echo"), runs
    commented = [line.lstrip("# ").strip() for line in text.splitlines() if "#" in line]
    commented_steps = step_lines("\n".join(f"  {line}" for line in commented))
    for step in step_lines(uncommented((WORKFLOWS / real).read_text())):
        if step == "uses: actions/checkout@v7":
            continue
        assert step in commented_steps, (placeholder, step)
    assert "\n  <layer>:\n" in text
    for directory in (None, "backend"):
        rendered = render(placeholder, "backend" if directory else "python", directory)
        assert "<dir>" not in rendered and "<layer>" not in rendered
        assert SUBDIRECTORY_MARKER not in rendered and ROOT_MARKER not in rendered


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("ci-*.yml")), ids=lambda path: path.name)
def test_every_ci_template_names_the_required_check(path):
    comments = [line for line in path.read_text().splitlines() if line.startswith("#")]
    assert any("required check" in line and "ruleset" in line for line in comments), path.name


GITHUB = PLUGIN / "templates" / "github"


def render_dependabot(directory: str) -> str:
    return (GITHUB / "dependabot.yml").read_text().replace("<dir>", directory)


def directory_of(text: str, ecosystem: str) -> str:
    match = re.search(rf"package-ecosystem: {ecosystem}\n\s+directory: (\S+)", text)
    assert match, ecosystem
    return match.group(1)


def test_dependabot_renders_the_layer_directory():
    layer = render_dependabot("backend")
    assert directory_of(layer, "uv") == "/backend"
    assert directory_of(layer, "npm") == "/backend"
    root = render_dependabot("")
    assert directory_of(root, "uv") == "/" and directory_of(root, "npm") == "/"
    for text in (layer, root):
        assert directory_of(text, "github-actions") == "/"
        assert "<dir>" not in text


def test_the_ruleset_template():
    ruleset = json.loads((GITHUB / "repository" / "ruleset.json").read_text())
    assert ruleset["target"] == "branch" and ruleset["enforcement"] == "active"
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    rules = {rule["type"]: rule for rule in ruleset["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"} <= set(rules)
    assert rules["pull_request"]["parameters"]["allowed_merge_methods"] == ["squash"]
    checks = rules["required_status_checks"]["parameters"]["required_status_checks"]
    assert checks == [{"context": "<job>"}]


def test_the_repository_settings_template():
    settings = json.loads((GITHUB / "repository" / "settings.json").read_text())
    assert settings == {
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
        "delete_branch_on_merge": True,
        "allow_update_branch": True,
    }
