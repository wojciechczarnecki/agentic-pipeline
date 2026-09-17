import importlib.util
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin"
GUARD_PATH = BIN / "guard.py"
sys.path.insert(0, str(BIN))
_spec = importlib.util.spec_from_file_location("guard", GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

# State of the original guard test suite just before the move into the plugin.
# The plugin has to keep at least this many cases; the source file is not imported, because
# plugin/tests must run in any repository and outlive the original location.
# Raised by two cases when an owner decision narrowed the git-hooks rule, and by
# four more when the final review closed the shell-pattern hole in that same rule.
BASELINE = {"blocked_anywhere": 61, "allowed_anywhere": 52, "cases": 137}

WORKFLOW = {
    "production": {
        "hosts": ["example.com", "deploy_smoke"],
        "commands": ["railway", "vercel"],
    },
    "worktree": {"dir": "../wt"},
    "gitHooksDir": "scripts/git-hooks",
    "migrations": {
        "command": "alembic",
        "localHosts": ["localhost", "127.0.0.1", "::1", "db"],
    },
}


def git(repo: Path, *args: str) -> None:
    identity = ["-c", "user.name=guard", "-c", "user.email=guard@example.com"]
    subprocess.run(["git", "-C", str(repo), *identity, *args], check=True, capture_output=True)


def make_repo(root: Path, workflow: dict | None) -> Path:
    (root / "backend").mkdir(parents=True)
    hook = root / "scripts" / "git-hooks" / "pre-push"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\nexit 0\n")
    git(root, "init", "-b", "main")
    git(root, "commit", "--allow-empty", "-m", "init")
    if workflow is not None:
        (root / ".claude").mkdir()
        (root / ".claude" / "workflow.json").write_text(json.dumps(workflow))
    return root


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    return make_repo(tmp_path_factory.mktemp("guard") / "repo", WORKFLOW)


@pytest.fixture
def bare_repo(tmp_path):
    return make_repo(tmp_path / "bare", None)


@pytest.fixture
def on_main(repo):
    git(repo, "switch", "main")
    return repo


@pytest.fixture
def on_feature(repo):
    git(repo, "switch", "-C", "feat/001-x")
    return repo


def evaluate(command: str, repo: Path, **env: str) -> str | None:
    return guard.evaluate(command, repo, {"CLAUDE_PROJECT_DIR": str(repo), **env})


BLOCKED_ANYWHERE = [
    ("git push --force origin feat/001-x", "force, mirror and delete pushes"),
    ("git push -f", "force, mirror and delete pushes"),
    ("git push --force-with-lease", "force, mirror and delete pushes"),
    ("git push origin +feat/001-x", "force and delete pushes"),
    ("git push origin main", "main changes only through a PR"),
    ("git push origin HEAD:main", "main changes only through a PR"),
    ("git push origin feat/001-x:refs/heads/main", "main changes only through a PR"),
    ("git push origin :feat/001-x", "force and delete pushes"),
    ("git push origin --delete feat/001-x", "force, mirror and delete pushes"),
    ("git push --no-verify origin feat/001-x", "--no-verify"),
    ("git status && git push origin main", "main changes only through a PR"),
    ("bash -c 'git push origin main'", "main changes only through a PR"),
    ("echo $(git push --force)", "force, mirror and delete pushes"),
    ("git reset --hard HEAD~1", "reset --hard"),
    ("git clean -fdx", "git clean -f"),
    ("git branch -D main", "deleting, renaming or resetting main"),
    ("git -c core.hooksPath=/dev/null push origin feat/001-x", "core.hooksPath"),
    ("git config core.hooksPath .git/hooks", "core.hooksPath"),
    ("git config --unset core.hooksPath", "core.hooksPath"),
    ("gh pr merge 12 --squash", "owner's gate"),
    ("gh api -X DELETE repos/o/r/git/refs/heads/feat", "branch protection"),
    (
        "gh api repos/o/r/branches/main/protection -X PUT -f enforce_admins=false",
        "branch protection",
    ),
    ("gh repo delete o/r --yes", "repository settings"),
    ("railway up", "`railway` operates production"),
    ("vercel --prod", "`vercel` operates production"),
    ("sudo apt install x", "sudo is not available"),
    ("curl -s https://api.example.com/health", "production is off limits"),
    (
        "uv run python -c \"import httpx; httpx.get('https://app.example.com')\"",
        "production is off limits",
    ),
    ("uv run python -m app.scripts.deploy_smoke", "production is off limits"),
    (
        "cd backend && DATABASE_URL=postgresql://u:p@db.remote.test/x uv run alembic upgrade head",
        "database URL built from variables",
    ),
    ("DB_HOST=10.0.0.5 alembic downgrade -1", "non-local database"),
    ("export DB_HOST=10.0.0.5 && uv run alembic upgrade head", "non-local database"),
    ("ENVIRONMENT=production uv run alembic upgrade head", "ENVIRONMENT=production"),
    ("rm -rf /home/someone/other", "outside the project and scratch"),
    ("rm -rf ~", "outside the project and scratch"),
    ('rm -rf "$TARGET"', "path built from variables"),
    ("D=/etc; rm -rf $D", "outside the project and scratch"),
    ("D=/etc; rm -rf ${D}/nginx", "outside the project and scratch"),
    ("D=/etc; cd $D; rm -rf nginx", "outside the project and scratch"),
    ("cd $UNKNOWN_DIR && rm -rf build", "directory built from variables"),
    (f"test -d build && D=/tmp/claude-{os.getuid()}/x; rm -rf $D", "path built from variables"),
    ("for f in x; do rm -rf /etc; done", "outside the project and scratch"),
    ("while true; do rm -rf /etc; done", "outside the project and scratch"),
    ("rm -rf .", "removing the repository root"),
    ("rm -rf .git", "removing git internals"),
    ("rm -rf *", "removing the repository root"),
    ("cd /var/tmp && rm -rf build", "outside the project and scratch"),
    ("find / -name x -delete", "outside the project and scratch"),
    ("sed -i 's/a/b/' .claude/workflow.json", "guardrail files"),
    ("echo {} > .claude/settings.json", "guardrail files"),
    ("cp /dev/null scripts/git-hooks/pre-push", "an existing git hook"),
    ("git push origin 'unterminated", "could not be parsed"),
    ("cat <<EOF\n$(git push origin main)\nEOF", "main changes only through a PR"),
    (
        "cat > note.md <<'EOF'\nplain text\nEOF\ngit push origin main",
        "main changes only through a PR",
    ),
    ('cat <<< "x" && git push origin main', "main changes only through a PR"),
    ('echo "<<EOF"\ngit push origin main', "main changes only through a PR"),
    ("# see <<EOF\ngit push origin main", "main changes only through a PR"),
    ("echo $((a<<b))\ngit push origin main", "main changes only through a PR"),
    ("cat <<EOF\ngit push origin main", "could not be parsed"),
    ('echo "`git push origin main`"', "main changes only through a PR"),
    ("cat <<EOF\nit's $(git push origin main)\nEOF", "main changes only through a PR"),
]

ALLOWED_ANYWHERE = [
    "cp template scripts/git-hooks/pre-commit",
    "chmod +x scripts/git-hooks/pre-push",
    "git status",
    "git log --oneline -5",
    "git diff main...HEAD",
    "git fetch origin",
    "git config --get core.hooksPath",
    "git config get core.hooksPath",
    "git worktree add ../wt/014-x -b feat/014-x main",
    "gh pr create --fill",
    "gh pr view 12 --comments",
    "gh api repos/o/r/branches/main/protection",
    "uv run alembic upgrade head",
    "DB_HOST=localhost uv run alembic upgrade head",
    "cd backend && DB_NAME=app_check uv run alembic check",
    "docker compose exec backend uv run alembic upgrade head",
    "docker compose exec backend rm -rf /app/.pytest_cache",
    "rm -rf frontend/dist",
    "rm -rf node_modules/*",
    f"rm -f /tmp/claude-{os.getuid()}/scratch.txt",
    "find . -name '*.pyc' -delete",
    "curl -s http://localhost:8000/health",
    "grep -rn example.com docs/",
    "bash scripts/verify.sh",
    "sed -n '1,5p' .claude/workflow.json",
    "npm run test:run 2>&1 | tail -5",
    "bash scripts/verify.sh ui",
    "bash scripts/ui.sh --project=small",
    "docker compose -f docker-compose.ui.yml up -d --wait",
    "docker compose -f docker-compose.ui.yml down -v --remove-orphans",
    "docker compose -p app-ui ps -a -q",
    "cd ui && npx test-runner test --project=desktop",
    "cd ui && npx test-runner install chromium webkit",
    "cd ui && npx test-runner show-report",
    "gh pr checks 42 --watch",
    "gh run view 123 --json url",
    "cat >> PLAN.md <<'EOF'\nthe owner's decision\nEOF",
    "cat > note.md <<'EOF'\nnever run git push origin main by hand\nEOF",
    "git commit -F - <<'EOF'\nfix: don't push to main by hand\nEOF",
    'cat > note.md <<"EOF"\nit\'s quoted with double quotes\nEOF',
    "cat <<-EOF\n\tit's indented\n\tEOF",
    'cat <<< "it\'s a here-string"',
    'echo "use <<EOF for heredocs"',
    "echo $((1<<4))",
    "git commit -m 'fix: handle `<<WORD` inside quotes'",
    "git commit -m 'never `git push origin main` by hand'",
    f"D=/tmp/claude-{os.getuid()}/run; rm -rf $D",
    f"S=/tmp/claude-{os.getuid()}/run && rm -rf ${{S}}/screenshots",
    "OUT=frontend/dist && rm -rf $OUT",
    f"D=/tmp/claude-{os.getuid()}/run; cd $D; rm -rf logs",
    "for f in *.png; do echo $f; done",
    "cd frontend && rm -rf dist",
]

UNIVERSAL_BLOCKED = [
    ("git push origin main", "main changes only through a PR"),
    ("git push --force origin feat/001-x", "force, mirror and delete pushes"),
    ("git push --no-verify origin feat/001-x", "--no-verify"),
    ("git reset --hard HEAD~1", "reset --hard"),
    ("git clean -fdx", "git clean -f"),
    ("git config core.hooksPath .git/hooks", "core.hooksPath"),
    ("gh pr merge 12 --squash", "owner's gate"),
    ("sudo apt install x", "sudo is not available"),
    ("rm -rf /home/someone/other", "outside the project and scratch"),
    ("echo {} > .claude/settings.json", "guardrail files"),
]


@pytest.mark.parametrize("command, fragment", BLOCKED_ANYWHERE)
def test_blocked_on_a_feature_branch(on_feature, command, fragment):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert fragment in reason, reason


@pytest.mark.parametrize("command", ALLOWED_ANYWHERE)
def test_allowed_on_a_feature_branch(on_feature, command):
    assert evaluate(command, on_feature) is None


@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push -u origin feat/001-x",
        "git commit -m 'mention git push origin main in a message'",
        "git rebase main",
        "git pull",
    ],
)
def test_feature_branch_work_is_allowed(on_feature, command):
    assert evaluate(command, on_feature) is None


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git merge feat/001-x",
        "git rebase feat/001-x",
        "git cherry-pick abc123",
        "git push",
        "git push -u origin HEAD",
        "git pull",
    ],
)
def test_changing_main_is_blocked(on_main, command):
    assert evaluate(command, on_main) is not None


@pytest.mark.parametrize(
    "command", ["git pull --ff-only", "git switch -c feat/002-y", "git status"]
)
def test_syncing_and_branching_off_main_is_allowed(on_main, command):
    assert evaluate(command, on_main) is None


@pytest.mark.parametrize("command, fragment", UNIVERSAL_BLOCKED)
def test_universal_rules_without_config(bare_repo, command, fragment):
    git(bare_repo, "switch", "-C", "feat/001-x")
    reason = evaluate(command, bare_repo)
    assert reason is not None, command
    assert fragment in reason, reason


def test_production_hosts_blocked_and_localhost_allowed(on_feature):
    assert evaluate("curl https://api.example.com/health", on_feature) is not None
    assert evaluate("curl http://localhost:8000/health", on_feature) is None


def test_production_hosts_are_inactive_without_config(bare_repo):
    assert evaluate("curl https://api.example.com/health", bare_repo) is None
    assert evaluate("curl http://localhost:8000/health", bare_repo) is None


def test_production_commands(on_feature, bare_repo):
    reason = evaluate("railway up", on_feature)
    assert reason is not None and "owner" in reason
    assert evaluate("railway up", bare_repo) is None


def test_worktree_dir_from_config(on_feature):
    assert evaluate("rm -rf ../wt/014-x/dist", on_feature) is None
    assert evaluate("rm -rf ../elsewhere/014-x", on_feature) is not None


@pytest.mark.parametrize(
    "command",
    [
        "echo {} > .claude/settings.json",
        "echo {} > .claude/settings.local.json",
        "sed -i 's/a/b/' .claude/workflow.json",
        "cp /dev/null scripts/git-hooks/pre-push",
    ],
)
def test_guardrail_files_protected(on_feature, command):
    assert evaluate(command, on_feature) is not None


@pytest.mark.parametrize(
    "command",
    [
        "cp /dev/null scripts/git-hooks/pre-push",
        "rm scripts/git-hooks/pre-push",
        "chmod -x scripts/git-hooks/pre-push",
    ],
)
def test_an_existing_git_hook_is_protected(on_feature, command):
    assert evaluate(command, on_feature) is not None


@pytest.mark.parametrize(
    "command",
    [
        "cp template scripts/git-hooks/pre-commit",
        "echo x > scripts/git-hooks/pre-commit",
        "chmod +x scripts/git-hooks/pre-commit",
        "chmod 755 scripts/git-hooks/pre-push",
    ],
)
def test_creating_a_git_hook_and_making_it_executable_is_allowed(on_feature, command):
    assert evaluate(command, on_feature) is None


@pytest.mark.parametrize(
    "command",
    [
        "cp /dev/null scripts/git-hooks/*",
        "tee scripts/git-hooks/pre-*",
        "cp /dev/null 'scripts/git-hooks/pre-pus?'",
        "cp /dev/null scripts/git-hooks/pre-pus[h]",
    ],
)
def test_a_shell_pattern_cannot_slip_past_the_git_hook_rule(on_feature, command):
    assert evaluate(command, on_feature) is not None


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -- .claude/settings.json",
        "git restore .claude/workflow.json",
        "git checkout HEAD -- scripts/git-hooks/pre-push",
    ],
)
def test_restoring_a_guardrail_file_from_git_is_blocked(on_feature, command):
    assert evaluate(command, on_feature) is not None


def test_ordinary_checkouts_stay_allowed(on_feature):
    assert evaluate("git checkout -- PLAN.md", on_feature) is None
    assert evaluate("git restore --staged src/app.py", on_feature) is None


def test_a_worktree_outside_the_configured_directory_is_blocked(on_feature):
    assert evaluate("git worktree add ../wt/014-x -b feat/014-x main", on_feature) is None
    assert evaluate("git worktree add ../elsewhere/014-x main", on_feature) is not None


def test_a_worktree_directory_cannot_widen_the_removal_rule(tmp_path):
    for value in ["/", ".", "..", str(tmp_path)]:
        repo = make_repo(tmp_path / f"wide-{abs(hash(value))}", {"worktree": {"dir": value}})
        git(repo, "switch", "-C", "feat/001-x")
        assert evaluate("rm -rf /home/someone/other", repo) is not None, value
        assert evaluate("rm -rf .", repo) is not None, value


def test_the_plugin_directory_is_protected_only_when_known(on_feature):
    assert evaluate("rm -rf plugin/bin", on_feature) is None
    root = str(on_feature / "plugin")
    assert evaluate("rm -rf plugin/bin", on_feature, CLAUDE_PLUGIN_ROOT=root) is not None


def test_a_plugin_outside_the_project_adds_no_rule(on_feature, tmp_path):
    assert evaluate("rm -rf plugin/bin", on_feature, CLAUDE_PLUGIN_ROOT=str(tmp_path)) is None


@pytest.mark.parametrize(
    "command",
    [
        "DATABASE_URL=postgresql://u:p@db.remote.test:5432/x uv run alembic upgrade head",
        "DB_HOST=10.0.0.5 alembic downgrade -1",
        "ENVIRONMENT=production uv run alembic upgrade head",
        "uv run python -m alembic upgrade head",
    ],
)
def test_migrations_disabled_without_section(bare_repo, command):
    git(bare_repo, "switch", "-C", "feat/001-x")
    assert evaluate(command, bare_repo) is None


def test_migrations_read_the_database_host_from_dotenv(on_feature):
    dotenv = on_feature / "backend" / ".env"
    dotenv.write_text("DB_HOST=prod.example.test\n")
    try:
        assert evaluate("cd backend && uv run alembic upgrade head", on_feature) is not None
        assert evaluate("uv run alembic upgrade head", on_feature) is None
    finally:
        dotenv.unlink()


def test_the_process_environment_counts_for_migrations(on_feature):
    assert evaluate("uv run alembic upgrade head", on_feature, DB_HOST="10.0.0.5") is not None


def test_a_migration_inside_a_container_ignores_the_dotenv(on_feature):
    dotenv = on_feature / ".env"
    dotenv.write_text("DB_HOST=prod.example.test\n")
    try:
        command = "docker compose exec backend uv run alembic upgrade head"
        assert evaluate(command, on_feature) is None
    finally:
        dotenv.unlink()


def test_a_migration_reached_through_python_m_is_guarded(on_feature):
    command = "DB_HOST=10.0.0.5 uv run python -m alembic upgrade head"
    assert evaluate(command, on_feature) is not None


def hook_payload(command: str, repo: Path, session_id: str) -> str:
    return json.dumps(
        {"tool_input": {"command": command}, "cwd": str(repo), "session_id": session_id}
    )


def test_missing_config_warns_once(bare_repo):
    session = f"test-{uuid.uuid4()}"
    first = run_hook(hook_payload("git status", bare_repo, session), bare_repo)
    second = run_hook(hook_payload("git status", bare_repo, session), bare_repo)
    assert (first.returncode, second.returncode) == (0, 0)
    assert "workflow.json" in first.stderr
    assert second.stderr == ""


def test_config_error_does_not_block(tmp_path):
    repo = make_repo(tmp_path / "broken", {})
    (repo / ".claude" / "workflow.json").write_text('{"nope": 1}')
    git(repo, "switch", "-C", "feat/001-x")
    session = f"test-{uuid.uuid4()}"
    allowed = run_hook(hook_payload("git status", repo, session), repo)
    assert allowed.returncode == 0
    assert "unknown key `nope`" in allowed.stderr
    blocked = run_hook(hook_payload("git push origin main", repo, session), repo)
    assert blocked.returncode == 2


def test_one_bad_key_costs_only_its_own_section(tmp_path):
    workflow = {**WORKFLOW, "languge": "pl"}
    repo = make_repo(tmp_path / "typo", workflow)
    git(repo, "switch", "-C", "feat/001-x")
    assert evaluate("curl https://api.example.com/health", repo) is not None
    assert evaluate("railway up", repo) is not None
    assert evaluate("DB_HOST=10.0.0.5 alembic upgrade head", repo) is not None


def test_a_broken_config_does_not_advise_running_init(tmp_path):
    repo = make_repo(tmp_path / "broken-advice", {})
    (repo / ".claude" / "workflow.json").write_text('{"nope": 1}')
    git(repo, "switch", "-C", "feat/001-x")
    result = run_hook(hook_payload("git status", repo, f"test-{uuid.uuid4()}"), repo)
    assert result.returncode == 0
    assert "unknown key `nope`" in result.stderr
    assert "/pipeline:init" not in result.stderr


def run_wrapper(payload: str, repo: Path, path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(BIN / "guard")],
        input=payload,
        text=True,
        capture_output=True,
        env={"PATH": path, "CLAUDE_PROJECT_DIR": str(repo)},
    )


def test_wrapper_without_python_exits_zero(on_feature):
    payload = hook_payload("gh pr merge 1", on_feature, "wrapper")
    result = run_wrapper(payload, on_feature, "/nonexistent")
    assert result.returncode == 0
    assert "python3" in result.stderr


def test_wrapper_with_python_still_blocks(on_feature):
    payload = hook_payload("gh pr merge 1", on_feature, "wrapper")
    result = run_wrapper(payload, on_feature, os.environ["PATH"])
    assert result.returncode == 2
    assert "owner's gate" in result.stderr


def collected_cases(module) -> int:
    total = 0
    for name, obj in vars(module).items():
        if not name.startswith("test_") or not callable(obj):
            continue
        marks = getattr(obj, "pytestmark", [])
        sizes = [len(mark.args[1]) for mark in marks if mark.name == "parametrize"]
        count = 1
        for size in sizes:
            count *= size
        total += count
    return total


def test_case_count_not_regressed():
    # UNIVERSAL_BLOCKED repeats commands from BLOCKED_ANYWHERE, so counting it here would
    # buy ten cases of slack; the two lists that carry the coverage stand on their own.
    assert len(BLOCKED_ANYWHERE) >= BASELINE["blocked_anywhere"]
    assert len(ALLOWED_ANYWHERE) >= BASELINE["allowed_anywhere"]
    assert collected_cases(sys.modules[__name__]) >= BASELINE["cases"]


def run_hook(payload: str, repo: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}
    return subprocess.run(
        [sys.executable, str(GUARD_PATH)], input=payload, text=True, capture_output=True, env=env
    )


def test_hook_blocks_with_exit_code_2_and_a_reason(on_feature):
    payload = json.dumps({"tool_input": {"command": "gh pr merge 1"}, "cwd": str(on_feature)})
    result = run_hook(payload, on_feature)
    assert result.returncode == 2
    assert "owner's gate" in result.stderr


def test_hook_lets_safe_commands_through(on_feature):
    payload = json.dumps({"tool_input": {"command": "git status"}, "cwd": str(on_feature)})
    assert run_hook(payload, on_feature).returncode == 0


def test_hook_ignores_malformed_input(on_feature):
    assert run_hook("not json", on_feature).returncode == 0
