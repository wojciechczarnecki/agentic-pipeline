import json
import shutil
from pathlib import Path

import pytest
from test_guard import BIN, WORKFLOW, evaluate, git, make_repo

PLUGIN_ROOT = BIN.parent
REFUSAL = "install is the owner's to change"


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    repo = make_repo(tmp_path_factory.mktemp("detach") / "repo", WORKFLOW)
    git(repo, "switch", "-C", "feat/001-x")
    return repo


@pytest.fixture
def config_dir(tmp_path):
    path = tmp_path / "config"
    path.mkdir()
    return path


def write_install_state(config_dir: Path, plugins: dict | str) -> None:
    path = config_dir / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = plugins if isinstance(plugins, str) else json.dumps({"version": 2, "plugins": plugins})
    path.write_text(text)


def check(command: str, repo: Path, config_dir: Path, **env: str) -> str | None:
    return evaluate(command, repo, CLAUDE_CONFIG_DIR=str(config_dir), **env)


DETACHING = [
    "claude plugin disable pipeline@any-m",
    "claude plugin disable pipeline",
    "claude plugin disable",
    "claude plugin disable --all",
    "claude plugin disable -a",
    "claude plugin uninstall pipeline@m",
    "claude plugins remove pipeline@m",
    "claude plugins uninstall pipeline@wcz-tools",
]
SCOPES = ["", " --scope user", " -s project", " --scope=local"]
WRAPPED = [
    "env claude plugin disable pipeline@m",
    "bash -c 'claude plugin uninstall pipeline@m'",
    "eval claude plugin disable pipeline",
    "/usr/local/bin/claude plugins remove pipeline@m",
    "claude --debug plugin uninstall pipeline@m",
    'claude plugin uninstall "$P"',
    "P=pipeline@m; claude plugin uninstall $P",
]


@pytest.mark.parametrize(
    "command", [f"{command}{scope}" for command in DETACHING for scope in SCOPES] + WRAPPED
)
def test_detaching_this_plugin_is_refused(repo, config_dir, command):
    reason = check(command, repo, config_dir)
    assert reason is not None, command
    expected = "built from variables" if '"$P"' in command else REFUSAL
    assert expected in reason, reason


def test_the_refusal_names_the_owners_terminal(repo, config_dir):
    reason = check("claude plugin uninstall pipeline@m", repo, config_dir)
    assert reason is not None
    assert "pipeline plugin's install" in reason and "terminal" in reason, reason


@pytest.mark.parametrize("verb", ["remove", "rm"])
def test_removing_this_plugins_marketplace_is_refused(repo, config_dir, tmp_path, verb):
    # (a) the install state
    write_install_state(config_dir, {"pipeline@state-m": [{"scope": "user"}]})
    reason = check(f"claude plugin marketplace {verb} state-m", repo, config_dir)
    assert reason is not None and REFUSAL in reason, reason
    # (b) a cache-layout plugin root
    cache_root = config_dir / "plugins" / "cache" / "cache-m" / "pipeline" / "0.4.0"
    (cache_root / ".claude-plugin").mkdir(parents=True)
    shutil.copy(PLUGIN_ROOT / ".claude-plugin" / "plugin.json", cache_root / ".claude-plugin")
    reason = check(
        f"claude plugin marketplace {verb} cache-m",
        repo,
        config_dir,
        CLAUDE_PLUGIN_ROOT=str(cache_root),
    )
    assert reason is not None and REFUSAL in reason, reason
    # (c) the marketplace manifest beside the running guard's directory, no install state
    empty = tmp_path / "empty-config"
    empty.mkdir()
    reason = check(f"claude plugins marketplace {verb} wcz-tools", repo, empty)
    assert reason is not None and REFUSAL in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "claude plugin marketplace rm $M",
        'claude plugin marketplace remove "$(echo m)"',
    ],
)
def test_an_unresolved_marketplace_is_refused(repo, config_dir, command):
    reason = check(command, repo, config_dir)
    assert reason is not None, command
    assert "built from variables" in reason, reason


def test_a_marketplace_with_an_unreadable_install_state_is_refused(repo, config_dir):
    write_install_state(config_dir, "{ not json")
    reason = check("claude plugin marketplace rm other-m", repo, config_dir)
    assert reason is not None
    assert "cannot read the plugin install state" in reason, reason
    write_install_state(config_dir, json.dumps({"plugins": []}))
    reason = check("claude plugin marketplace rm other-m", repo, config_dir)
    assert reason is not None
    assert "cannot read the plugin install state" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "claude plugin disable other@m",
        "claude plugin uninstall other@m",
        "claude plugins remove other@m --scope user",
        "claude plugin marketplace remove other-m",
        "claude plugin marketplace rm other-m",
        "claude plugin list",
        "claude plugin details pipeline",
        "claude plugin validate plugin/",
        "claude plugin eval plugin/",
        "claude plugin update pipeline@wcz-tools --scope user",
        "claude plugin install pipeline@wcz-tools --scope user",
        "claude plugin i pipeline@wcz-tools",
        "claude plugin enable pipeline@wcz-tools",
        "claude plugin marketplace add x",
        "claude plugin marketplace list",
        "claude plugin marketplace update wcz-tools",
        "claude plugin disable --help",
        "claude plugin uninstall pipeline@m -h",
        "claude plugins remove pipeline@m --help",
        "claude plugin marketplace rm wcz-tools --help",
        "claude plugin help disable",
        "claude -p 'say hi'",
        "claude --version",
    ],
)
def test_other_plugin_commands_pass(repo, config_dir, command):
    write_install_state(config_dir, {"pipeline@wcz-tools": [{"scope": "user"}]})
    assert check(command, repo, config_dir) is None
