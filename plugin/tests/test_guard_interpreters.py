from pathlib import Path

import pytest
from test_guard import WORKFLOW, evaluate, git, make_repo

EDIT_WRITE = "Edit/Write"


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    repo = make_repo(tmp_path_factory.mktemp("interp") / "repo", WORKFLOW)
    git(repo, "switch", "-C", "feat/001-x")
    return repo


@pytest.fixture
def home(tmp_path):
    root = tmp_path / "cache" / "pipeline"
    (root / "hooks").mkdir(parents=True)
    (root / "hooks" / "x").write_text("x\n")
    config = tmp_path / "config" / "plugins"
    config.mkdir(parents=True)
    (config / "installed_plugins.json").write_text('{"plugins": {}}')
    (config / "known_marketplaces.json").write_text("{}")
    return tmp_path


def env_for(home) -> dict[str, str]:
    return {
        "HOME": str(home),
        "CLAUDE_PLUGIN_ROOT": str(home / "cache" / "pipeline"),
        "CLAUDE_CONFIG_DIR": str(home / "config"),
    }


REFUSED = [
    "python3 - <<'EOF'\nprint(open('.claude/workflow.json').read())\nEOF\n",
    "node <<EOF\nrequire('fs').readFileSync('.claude/settings.local.json')\nEOF\n",
    "python3 <<-'EOF'\n\topen('.claude/workflow.json')\n\tEOF\n",
    "python3 -c \"open('.claude/workflow.json', 'w')\"",
    "python3.12 -c \"open('.claude/workflow.json')\"",
    "perl -e 'open(F, \">.claude/settings.json\")'",
    "perl -E 'say 1; open(F, \".claude/settings.json\")'",
    "ruby -e \"File.read('.claude/settings.json')\"",
    "node -e \"require('fs').readFileSync('.claude/settings.json')\"",
    "node --eval \"require('fs').readFileSync('.claude/settings.json')\"",
    "node -p \"require('fs').readFileSync('.claude/settings.json')\"",
    "node --print \"require('fs').readFileSync('.claude/settings.json')\"",
    "python3 <<< \"open('.claude/workflow.json')\"",
    "uv run python -c \"open('.claude/workflow.json')\"",
    "env python3 -c \"open('.claude/workflow.json')\"",
    "timeout 5 python3 -c \"open('.claude/workflow.json')\"",
    'bash -c "python3 -c \'open(\\".claude/workflow.json\\")\'"',
    "git status && python3 - <<'EOF'\nopen('.claude/workflow.json')\nEOF\n",
    "python3 -c \"open('x.py'); open('.claude/workflow.json')\"",
]


@pytest.mark.parametrize("command", REFUSED)
def test_interpreter_code_naming_a_guardrail_file_is_refused(repo, command):
    reason = evaluate(command, repo)
    assert reason is not None, command
    assert EDIT_WRITE in reason, reason


def test_an_unquoted_heredoc_expands_the_plugin_root(repo, home):
    command = "python3 - <<EOF\nopen('$CLAUDE_PLUGIN_ROOT/hooks/x', 'w')\nEOF\n"
    reason = evaluate(command, repo, **env_for(home))
    assert reason is not None and EDIT_WRITE in reason, reason


@pytest.mark.parametrize(
    "template",
    [
        "python3 -c \"open('{root}/hooks/x')\"",
        "python3 -c \"open('~/cache/pipeline/hooks/x')\"",
        "python3 -c \"open('{state}/installed_plugins.json')\"",
        "node -e \"require('fs').readFileSync('known_marketplaces.json')\"",
    ],
)
def test_interpreter_code_naming_the_plugin_or_its_install_state_is_refused(repo, home, template):
    root = home / "cache" / "pipeline"
    command = template.format(root=root, state=home / "config" / "plugins")
    reason = evaluate(command, repo, **env_for(home))
    assert reason is not None and EDIT_WRITE in reason, reason


ALLOWED = [
    "python3 - <<'EOF'\nprint(1)\nEOF\n",
    'python3 -c "print(1)"',
    "node -e \"console.log('.claude/other.json')\"",
    "perl -e 'print 1'",
    "python3 scripts/tool.py .claude/workflow.json",
    "cat <<EOF > notes.md\nsee .claude/workflow.json for the settings\nEOF\n",
    "cat <<'EOF'\nsee .claude/settings.json\nEOF\n",
    "git commit -m \"$(cat <<'EOF'\nchore: mention .claude/workflow.json\nEOF\n)\"",
    "cat <<EOF > a.md\nsee .claude/workflow.json\nEOF\npython3 - <<EOF\nprint(1)\nEOF\n",
    "python3 - <<EOF\nprint(1)\nEOF\ncat <<EOF > a.md\nsee .claude/workflow.json\nEOF\n",
    "sh -c 'echo .claude/other.json'",
]


@pytest.mark.parametrize("command", ALLOWED)
def test_interpreter_code_without_a_guardrail_path_passes(repo, command):
    assert evaluate(command, repo) is None


def test_a_heredoc_to_a_non_interpreter_keeps_todays_rules(repo):
    command = "cat <<EOF > .claude/workflow.json\n{}\nEOF\n"
    reason = evaluate(command, repo)
    assert reason is not None and EDIT_WRITE in reason, reason
    assert evaluate("cat <<EOF > notes.md\n.claude/workflow.json\nEOF\n", repo) is None


def test_the_shell_c_flag_is_not_interpreter_code(repo):
    assert evaluate("sh -c 'echo .claude/other.json'", repo) is None


PLUGIN = Path(__file__).resolve().parents[1]


def bullet(document: str, marker: str) -> str:
    start = document.index(marker)
    end = document.find("\n- **", start + 1)
    return document[start : end if end != -1 else len(document)]


def test_guard_doc_has_the_interpreter_rule():
    text = bullet((PLUGIN / "docs" / "GUARD.md").read_text(), "- **Interpreter code")
    for word in ["python", "node", "perl", "ruby", "-c", "-e", "heredoc", "here-string"]:
        assert word in text, word
    assert "Edit/Write" in text


def test_guard_doc_narrows_the_interpreter_limit():
    text = bullet(
        (PLUGIN / "docs" / "GUARD.md").read_text(), "- **Scripts, interpreters and shell functions"
    )
    assert "names a guardrail" in text
    assert "run time" in text and "script file" in text


def test_guard_doc_says_to_send_separate_calls():
    text = bullet((PLUGIN / "docs" / "GUARD.md").read_text(), "- **How the refusal reads")
    assert "separate calls" in text


def test_readme_guard_paragraph_names_the_new_rules():
    readme = (PLUGIN / "README.md").read_text()
    section = readme[readme.index("### Command guard") :]
    section = section[: section.index("\n## ")]
    assert "alembic.ini" in section and "migrations" in section
    assert "interpreter" in section.lower()
