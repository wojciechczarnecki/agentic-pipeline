import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from test_guard import GUARD_PATH, WORKFLOW, make_repo

# SPEC 007: stages read the plugin's templates and section map with `Read`; a stage subagent
# cannot answer the permission prompt, so the guard tells the owner and the model once per
# session when no settings file allows reading the plugin's directory.
NOTICE = "no Read allow rule covers this plugin's directory"


class Setup:
    def __init__(self, tmp_path: Path, plugin_root: Path | None = None):
        self.home = tmp_path / "home"
        self.config_dir = self.home / ".claude"
        self.config_dir.mkdir(parents=True)
        self.repo = make_repo(tmp_path / "repo", WORKFLOW)
        self.plugin_root = plugin_root or (
            self.config_dir / "plugins" / "cache" / "mkt" / "pipeline" / "0.6.0"
        )
        self.plugin_root.mkdir(parents=True, exist_ok=True)
        self.session = f"test-{uuid.uuid4()}"

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
        env.update(
            HOME=str(self.home),
            CLAUDE_CONFIG_DIR=str(self.config_dir),
            CLAUDE_PROJECT_DIR=str(self.repo),
            CLAUDE_PLUGIN_ROOT=str(self.plugin_root),
        )
        return env

    def run(self, command: str = "git status") -> subprocess.CompletedProcess:
        payload = json.dumps(
            {"tool_input": {"command": command}, "cwd": str(self.repo), "session_id": self.session}
        )
        return subprocess.run(
            [sys.executable, str(GUARD_PATH)],
            input=payload,
            text=True,
            capture_output=True,
            env=self.env(),
        )


def write_settings(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data))


def allow(*rules: str) -> dict:
    return {"permissions": {"allow": list(rules)}}


def notice_of(result: subprocess.CompletedProcess) -> dict:
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 1, result.stdout
    return json.loads(lines[0])


def without_slash(path: Path) -> str:
    return str(path).lstrip("/")


@pytest.fixture
def cache(tmp_path):
    return Setup(tmp_path)


@pytest.fixture
def clone(tmp_path):
    return Setup(tmp_path, tmp_path / "clone" / "plugin")


def test_no_rule_warns_once_without_blocking(cache):
    first, second = cache.run(), cache.run()
    assert (first.returncode, second.returncode) == (0, 0)
    assert NOTICE in notice_of(first)["systemMessage"]
    assert second.stdout == ""


def test_the_notice_reaches_the_owner_and_the_model(cache):
    notice = notice_of(cache.run())
    rule = "Read(~/.claude/plugins/cache/mkt/pipeline/**)"
    assert rule in notice["systemMessage"]
    specific = notice["hookSpecificOutput"]
    assert specific["hookEventName"] == "PreToolUse"
    assert rule in specific["additionalContext"]
    assert "permissionDecision" not in specific
    assert "permissions.allow" in notice["systemMessage"]


# The notice reaches any session's first Bash call, where the owner may still approve the
# prompt: it informs, and the stop belongs to a read that actually fails (final review F1).
def test_the_notice_escalates_only_on_a_failed_read(cache):
    message = notice_of(cache.run())["systemMessage"]
    assert "escalates instead of reading" not in message
    assert "if a read of a template or the section map fails, escalate" in message


def test_a_blocked_first_call_carries_the_notice(cache):
    result = cache.run("gh pr merge 1")
    assert result.returncode == 2
    assert "owner's gate" in result.stderr
    assert "Read(~/.claude/plugins/cache/mkt/pipeline/**)" in result.stderr
    assert result.stdout == ""


def settings_path(setup: Setup, where: str) -> Path:
    return {
        "user": setup.config_dir / "settings.json",
        "project": setup.repo / ".claude" / "settings.json",
        "local": setup.repo / ".claude" / "settings.local.json",
    }[where]


@pytest.mark.parametrize("where", ["user", "project", "local"])
@pytest.mark.parametrize(
    "rule",
    [
        "Read(~/.claude/plugins/cache/mkt/pipeline/**)",
        "Read(~/.claude/plugins/**)",
        "Read(~/**)",
        "Read",
    ],
)
def test_a_covering_rule_silences_the_notice_for_the_cache(cache, where, rule):
    write_settings(settings_path(cache, where), allow("Bash(git *)", rule))
    result = cache.run()
    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("where", ["user", "project", "local"])
def test_a_covering_rule_silences_the_notice_for_a_clone(clone, where):
    rule = f"Read(//{without_slash(clone.plugin_root)}/**)"
    write_settings(settings_path(clone, where), allow(rule))
    assert clone.run().stdout == ""


def test_the_user_settings_follow_the_config_dir(tmp_path):
    setup = Setup(tmp_path)
    setup.config_dir = tmp_path / "config"
    setup.config_dir.mkdir()
    write_settings(setup.home / ".claude" / "settings.json", allow("Read"))
    assert NOTICE in setup.run().stdout
    other = Setup(tmp_path / "second")
    other.config_dir = tmp_path / "second" / "config"
    write_settings(other.config_dir / "settings.json", allow("Read(~/.claude/plugins/**)"))
    assert other.run().stdout == ""


def test_a_clone_gets_the_absolute_rule(clone):
    notice = notice_of(clone.run())
    rule = f"Read(//{without_slash(clone.plugin_root)}/**)"
    assert rule in notice["systemMessage"]
    assert rule in notice["hookSpecificOutput"]["additionalContext"]
    write_settings(settings_path(clone, "project"), allow(rule))
    clone.session = f"test-{uuid.uuid4()}"
    assert clone.run().stdout == ""


def test_the_cache_gets_the_home_rule(cache):
    notice = notice_of(cache.run())
    assert '"Read(~/.claude/plugins/cache/mkt/pipeline/**)"' in notice["systemMessage"]
    assert "0.6.0/**" not in notice["systemMessage"]


def test_a_config_dir_cache_gets_a_version_free_rule(tmp_path):
    config = tmp_path / "config"
    setup = Setup(tmp_path, config / "plugins" / "cache" / "mkt" / "pipeline" / "0.6.0")
    setup.config_dir = config
    notice = notice_of(setup.run())
    rule = f"Read(//{without_slash(config)}/plugins/cache/mkt/pipeline/**)"
    assert rule in notice["systemMessage"]
    assert "0.6.0" not in notice["systemMessage"].split("Add", 1)[1]
    write_settings(config / "settings.json", allow(rule))
    setup.session = f"test-{uuid.uuid4()}"
    assert setup.run().stdout == ""


# Well-formed rules that point elsewhere must not silence the notice (final review F4).
@pytest.mark.parametrize(
    "rule",
    [
        "Read(~/.claude/plugins/cache/other/pipeline/**)",
        "Read(~/.claude/plugins/cache/mkt/*)",
        "Edit(~/.claude/plugins/**)",
        "Bash(cat ~/.claude/plugins/**)",
    ],
)
def test_a_rule_elsewhere_does_not_count(cache, rule):
    write_settings(settings_path(cache, "project"), allow(rule))
    assert NOTICE in notice_of(cache.run())["systemMessage"]


@pytest.mark.parametrize(
    "rule",
    [
        lambda root: f"Read(//{without_slash(root.parent)}/other/**)",
        lambda root: f"Read(//{without_slash(root)}/*)",
        lambda root: f"Edit(//{without_slash(root)}/**)",
    ],
)
def test_an_absolute_rule_elsewhere_does_not_count(clone, rule):
    write_settings(settings_path(clone, "project"), allow(rule(clone.plugin_root)))
    assert NOTICE in notice_of(clone.run())["systemMessage"]


# Claude Code reads `/x` in a permission rule as relative to the settings file, and `//x` as
# absolute; a rule the guard cannot place is not counted.
def test_a_settings_relative_rule_does_not_count(clone):
    write_settings(
        settings_path(clone, "project"),
        allow(f"Read({clone.plugin_root}/**)", "Read(./**)", "Read(plugin/**)"),
    )
    assert NOTICE in notice_of(clone.run())["systemMessage"]


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        {"permissions": ["Read"]},
        {"permissions": {"allow": "Read"}},
        {"permissions": {"allow": [1, None, {"Read": True}]}},
        ["Read"],
    ],
)
def test_broken_settings_count_as_no_rule(cache, content):
    write_settings(settings_path(cache, "project"), content)
    result = cache.run()
    assert result.returncode == 0
    assert NOTICE in notice_of(result)["systemMessage"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a file whatever its mode")
def test_an_unreadable_settings_file_counts_as_no_rule(cache):
    path = settings_path(cache, "project")
    write_settings(path, allow("Read"))
    path.chmod(0o000)
    try:
        result = cache.run()
    finally:
        path.chmod(0o600)
    assert result.returncode == 0
    assert NOTICE in notice_of(result)["systemMessage"]


def test_the_config_notice_is_unchanged(tmp_path):
    setup = Setup(tmp_path)
    (setup.repo / ".claude" / "workflow.json").unlink()
    first = setup.run()
    assert first.returncode == 0
    assert "no .claude/workflow.json found" in first.stderr
    assert NOTICE not in first.stderr
    # a project without the pipeline reads no templates: no read-rule notice (final review F2)
    assert first.stdout == ""
    second = setup.run()
    assert (second.stdout, second.stderr) == ("", "")
    # independent markers: a rule-covered session still gets the config warning once
    other = Setup(tmp_path / "second")
    (other.repo / ".claude" / "workflow.json").unlink()
    write_settings(settings_path(other, "user"), allow("Read"))
    result = other.run()
    assert "no .claude/workflow.json found" in result.stderr
    assert result.stdout == ""


def test_a_broken_config_still_gets_the_notice(cache):
    (cache.repo / ".claude" / "workflow.json").write_text("{not json")
    result = cache.run()
    assert result.returncode == 0
    assert "falling back to the defaults" in result.stderr
    assert NOTICE in notice_of(result)["systemMessage"]
