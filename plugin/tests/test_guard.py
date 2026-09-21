import importlib.util
import json
import os
import re
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
    ("gh api -X DELETE repos/o/r/git/refs/heads/feat", "branch and tag refs"),
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


# DELETE through `gh api` is blocked only where a gh subcommand is the owner's call too.
API_DELETE_BLOCKED = [
    ("repos/o/r", "the repository"),
    ("/repos/o/r/", "the repository"),
    ("https://api.github.com/repos/o/r", "the repository"),
    ("repos/{owner}/{repo}", "the repository"),
    ("repos/o/r/git/refs/heads/main", "branch and tag refs"),
    ("repos/o/r/git/refs/tags/pipeline--v1.0.0", "branch and tag refs"),
    ("repos/o/r/merges", "merges"),
    ("repos/o/r/branches/main/protection", "branch protection"),
    ("repos/o/r/branches/main/protection/required_status_checks", "branch protection"),
    ("repos/o/r/rulesets/42", "rulesets"),
    ("repos/o/r/releases/42", "releases"),
    ("repos/o/r/actions/runs/42", "workflow runs"),
    ("repos/o/r/actions/runs/42/logs", "workflow runs"),
    ("repos/o/r/actions/secrets/TOKEN", "secrets"),
    ("repos/o/r/environments/prod/secrets/TOKEN", "environments"),
    ("repos/o/r/actions/variables/NAME", "variables"),
    ("repos/o/r/environments/prod", "environments"),
    ("repos/o/r/hooks/42", "webhooks"),
    ("repos/o/r/keys/42", "keys"),
    ("user/keys/42", "keys"),
    ("user/gpg_keys/42", "keys"),
    ("repos/o/r/collaborators/someone", "collaborator access"),
    ("repos/o/r/invitations/42", "collaborator access"),
    ("https://ghe.example.com/api/v3/repos/o/r", "the repository"),
    ("repositories/1", "the repository"),
    ("repositories/1/git/refs/heads/main", "branch and tag refs"),
    ("https://ghe.example.com/api/v3/repos/o/r/git/refs/heads/main", "branch and tag refs"),
    ("orgs/o", "the organization"),
    ("orgs/o/teams/core", "organization teams and members"),
    ("orgs/o/members/someone", "organization teams and members"),
    ("orgs/o/memberships/someone", "organization teams and members"),
    ("orgs/o/outside_collaborators/someone", "collaborator access"),
    ("repos/o/r/pages", "the Pages site"),
    ("repos/o/r/deployments/42", "deployments"),
    ("repos/o/r/vulnerability-alerts", "security settings"),
    ("repos/o/r/automated-security-fixes", "security settings"),
    ("repos/o/r/private-vulnerability-reporting", "security settings"),
]

API_DELETE_ALLOWED = [
    "repos/o/r/actions/artifacts/42",
    "repos/o/r/actions/caches/42",
    "repos/o/r/actions/caches?key=deps",
    "repos/o/r/issues/comments/42",
    "repos/o/r/issues/12/labels/bug",
    "repos/o/r/pulls/comments/42",
    "notifications/threads/42/subscription",
]


@pytest.mark.parametrize("endpoint, fragment", API_DELETE_BLOCKED)
@pytest.mark.parametrize("method", ["-X DELETE", "--method DELETE", "--method=delete", "-XDELETE"])
def test_api_delete_on_owner_ground_is_blocked(on_feature, endpoint, fragment, method):
    reason = evaluate(f"gh api {method} {endpoint}", on_feature)
    assert reason is not None
    assert fragment in reason and "owner's call" in reason, reason
    assert endpoint in reason, reason


@pytest.mark.parametrize("endpoint", API_DELETE_ALLOWED)
def test_api_delete_elsewhere_is_allowed(on_feature, endpoint):
    assert evaluate(f"gh api -X DELETE '{endpoint}'", on_feature) is None


def test_compound_refusal_names_the_blocked_part(on_feature):
    reason = evaluate("git status && gh pr merge 12 --squash", on_feature)
    assert reason is not None
    assert "`gh pr merge 12 --squash`: merging a PR is the owner's gate" in reason, reason
    assert "other 1 of 2 parts passed" in reason, reason
    assert "git status`" not in reason, reason


def test_compound_refusal_names_every_blocked_part(on_feature):
    reason = evaluate("gh pr merge 1; sudo ls; git status", on_feature)
    assert reason is not None
    assert "`gh pr merge 1`" in reason and "`sudo ls`" in reason, reason
    assert "other 1 of 3 parts passed" in reason, reason


def test_compound_refusal_without_a_passing_part(on_feature):
    reason = evaluate("gh pr merge 1 && sudo ls", on_feature)
    assert reason is not None
    assert "passed" not in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        'gh api -X DELETE "$EP"',
        "EP=repos/o/r; gh api -X DELETE $EP",
        "gh api -X DELETE repos/o/${REPO}",
        "gh api -X DELETE repos/o/r/git/refs/heads/`git branch --show-current`",
    ],
)
def test_api_delete_on_a_variable_endpoint_is_blocked(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None
    assert "built from variables" in reason, reason


def test_a_pipeline_is_one_part_of_a_compound_refusal(on_feature):
    reason = evaluate("git status; gh pr merge 1 | cat", on_feature)
    assert reason is not None
    assert "`gh pr merge 1 | cat`: merging a PR" in reason, reason
    assert "other 1 of 2 parts passed" in reason, reason


def test_a_lone_pipeline_refusal_stays_plain(on_feature):
    assert evaluate("gh pr merge 1 | cat", on_feature) == "merging a PR is the owner's gate"


# The part around a blocked substitution would run it again, so it is never offered back.
def test_blocked_substitution_is_not_offered_as_a_passing_part(on_feature):
    reason = evaluate("git status && echo $(gh pr merge 1)", on_feature)
    assert reason == "merging a PR is the owner's gate", reason


def test_single_command_refusal_stays_plain(on_feature):
    assert evaluate("gh pr merge 1", on_feature) == "merging a PR is the owner's gate"


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


PUSH_TO_MAIN_BY_VARIABLE = [
    "B=main; git push origin $B",
    "B=main && git push origin $B",
    "export B=main && git push origin $B",
    "B=main; git push origin ${B}",
    "B=main; git push origin HEAD:$B",
    'B=main; git push origin "$B"',
    "B=main; git push origin refs/heads/$B",
]


@pytest.mark.parametrize("command", PUSH_TO_MAIN_BY_VARIABLE)
def test_a_push_variable_resolving_to_main_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "pushing to main" in reason, reason


def test_hook_refuses_a_push_variable_resolving_to_main(on_feature):
    payload = json.dumps(
        {"tool_input": {"command": "B=main; git push origin $B"}, "cwd": str(on_feature)}
    )
    result = run_hook(payload, on_feature)
    assert result.returncode == 2
    assert "pushing to main" in result.stderr


PUSH_UNRESOLVED = [
    ("git push origin $UNKNOWN", "$UNKNOWN"),
    ("git push origin HEAD:$UNKNOWN", "HEAD:$UNKNOWN"),
    ("git push origin $(echo main)", "$(...)"),
    ("git push origin `echo main`", "`echo"),
    ("false || B=feat/x; git push origin $B", "$B"),
]


@pytest.mark.parametrize("command, shown", PUSH_UNRESOLVED)
def test_an_unresolvable_push_refspec_is_refused(on_feature, command, shown):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "spell the branch out" in reason and shown in reason, reason


@pytest.mark.parametrize("branch", ["on_main", "on_feature"])
def test_a_prefix_assignment_does_not_resolve_its_own_push(request, branch):
    repo = request.getfixturevalue(branch)
    reason = evaluate("B=feat/x git push origin $B", repo)
    assert reason is not None
    assert "spell the branch out" in reason, reason


def test_an_empty_push_variable_pushes_the_current_branch(repo):
    git(repo, "switch", "-C", "feat/001-x")
    assert evaluate("E=; git push origin $E", repo) is None
    git(repo, "switch", "main")
    reason = evaluate("E=; git push origin $E", repo)
    assert reason is not None
    assert "pushing to main" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "B=feat/002-x; git push origin $B",
        "export B=feat/002-x && git push -u origin $B",
        "B=feat/002-x; git push origin HEAD:$B",
    ],
)
def test_a_push_variable_resolving_to_a_feature_branch_is_allowed(on_feature, command):
    assert evaluate(command, on_feature) is None


def test_a_variable_remote_with_literal_refspecs(on_feature):
    assert evaluate("git push $REMOTE feat/002-x", on_feature) is None
    assert evaluate("R=origin; git push $R feat/002-x", on_feature) is None
    reason = evaluate("git push $REMOTE main", on_feature)
    assert reason is not None
    assert "pushing to main" in reason, reason


def test_a_split_push_variable_is_checked_word_by_word(on_feature):
    for command in ['B="origin main"; git push $B', 'B="feat/x main"; git push origin $B']:
        reason = evaluate(command, on_feature)
        assert reason is not None, command
        assert "pushing to main" in reason, reason
    assert evaluate('B="feat/x feat/y"; git push origin $B', on_feature) is None


@pytest.mark.parametrize(
    "command", ["git push $(git remote) main", "git push $(git remote) feat/002-x"]
)
def test_a_substitution_in_the_remote_position_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "spell the branch out" in reason and "$(...)" in reason, reason


# Final review F1: a value the shell drops, changes or never assigns must not stay "known".
# On main each of these pushes main in a real shell while the guard used to read feat/x.
PUSH_VARIABLE_NOT_FOLLOWED = [
    "true || export B=feat/x; git push origin $B",
    "(B=feat/x); git push origin $B",
    "B=feat/x | true; git push origin $B",
    "B=feat/x & git push origin $B",
    "bash -c 'B=feat/x'; git push origin $B",
    "B=feat/x; bash -c 'git push origin $B'",
    "export B=feat/x; export -n B; bash -c 'git push origin $B'",
    "B=feat/x; unset B; git push origin $B",
    "B=feat/x; if false; then B=main; fi; git push origin $B",
    "if false; then B=feat/x; fi; git push origin $B",
    "B=feat/x; for B in main; do git push origin $B; done",
    "B=ma; B+=in; git push origin $B",
    "B=feat/x; B[0]=main; git push origin $B",
    "B=(main); git push origin $B",
    "B=feat/x; read B; git push origin $B",
    "B=feat/x; declare B=main; git push origin $B",
    "B=feat/x; printf -v B main; git push origin $B",
    "B=feat/x; mapfile B < f; git push origin $B",
    "IFS=:; B=feat/x:main; git push origin $B",
]


@pytest.mark.parametrize("branch", ["on_main", "on_feature"])
@pytest.mark.parametrize("command", PUSH_VARIABLE_NOT_FOLLOWED)
def test_a_push_variable_the_guard_cannot_follow_is_refused(request, branch, command):
    reason = evaluate(command, request.getfixturevalue(branch))
    assert reason is not None, command
    assert "spell the branch out" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "(B=main; git push origin $B)",
        "B=main; (git push origin $B)",
        "B=main; echo x | git push origin $B",
        "export B=main; bash -c 'git push origin $B'",
        "B=main bash -c 'git push origin $B'",
    ],
)
def test_a_variable_still_reaches_its_own_subshell(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "pushing to main" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "B=feat/x; (B=main); git push origin $B",
        "export B=feat/002-x; bash -c 'git push origin $B'",
        "while IFS= read -r line; do echo $line; done < f",
        "(cd /etc) && rm -rf build",
    ],
)
def test_subshell_changes_stay_in_the_subshell(on_feature, command):
    assert evaluate(command, on_feature) is None


@pytest.mark.parametrize(
    "command",
    [
        "if git push origin main; then :; fi",
        "while git push origin main; do :; done",
        "until git push origin main; do :; done",
        "! git push origin main",
        "if true; then :; elif git push origin main; then :; fi",
    ],
)
def test_a_command_behind_a_control_keyword_is_checked(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "pushing to main" in reason, reason


# Final review F2: destructive options are read after expansion.
@pytest.mark.parametrize(
    "command",
    [
        "B=-f; git push origin $B",
        "B=--force; git push origin feat/x $B",
        "B=--delete; git push origin $B feat/x",
        "B=--mirror; git push $B origin",
        "B='--force-with-lease'; git push origin $B",
    ],
)
def test_a_destructive_push_option_from_a_variable_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "force, mirror and delete pushes" in reason, reason


def test_no_verify_from_a_variable_is_refused(on_feature):
    reason = evaluate("B=--no-verify; git push origin feat/x $B", on_feature)
    assert reason is not None
    assert "--no-verify" in reason, reason


# Final review F3: pushes that reach main without spelling it.
@pytest.mark.parametrize("command", ["git push --all origin", "git push --branches origin"])
def test_a_push_of_every_branch_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "every branch" in reason and "push the feature branch by name" in reason, reason


@pytest.mark.parametrize(
    "command, shown",
    [
        ("git push origin '*:*'", "*:*"),
        ("git push origin 'refs/heads/*:refs/heads/*'", "refs/heads/*:refs/heads/*"),
        ("git push origin {feat/x,main}", "{feat/x,main}"),
        ("git push origin HEAD:ma{in,}", "HEAD:ma{in,}"),
        ("git push origin feat/?", "feat/?"),
    ],
)
def test_a_push_refspec_pattern_is_refused(on_feature, command, shown):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "pattern or brace expansion" in reason and shown in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "git push origin HEAD:heads/main",
        "git push origin heads/main",
        "git push origin feat/x:heads/master",
        "git push --repo=origin main",
    ],
)
def test_a_push_to_main_in_a_short_ref_form_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "pushing to main" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "git -c remote.origin.push=HEAD:main push origin",
        "git -c Remote.Origin.Push=HEAD:main push origin",
        "git -c remote.origin.mirror=true push origin",
        "git -c push.default=matching push origin",
        "git config remote.origin.push HEAD:main",
        "git config --global push.default matching",
        "git config set remote.upstream.mirror true",
        "git config --rename-section x remote.origin",
    ],
)
def test_push_configuration_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "push configuration" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "git config remote.origin.push",
        "git config --get push.default",
        "git config remote.origin.url https://example.org/r.git",
        "git -c push.autoSetupRemote=true push origin feat/x",
        "git push --tags origin feat/x",
    ],
)
def test_other_push_settings_pass(on_feature, command):
    assert evaluate(command, on_feature) is None


# Final review F4: the value of a push option is not the remote.
def test_a_push_option_value_is_not_the_remote(repo):
    git(repo, "switch", "main")
    for command in [
        "git push -o ci.skip origin",
        "git push --push-option ci.skip origin",
        "git push --receive-pack git-receive-pack origin",
    ]:
        reason = evaluate(command, repo)
        assert reason is not None, command
        assert "pushing to main" in reason, reason
    git(repo, "switch", "-C", "feat/001-x")
    for command in [
        "git push -o ci.skip $REMOTE feat/002-x",
        "git push origin feat/x -o 'ci.variable=A=$B'",
        "git push --push-option=ci.skip origin feat/x",
        "git push -o 'a b' origin feat/x",
    ]:
        assert evaluate(command, repo) is None, command


# Final review F5: an editor can write any key.
@pytest.mark.parametrize(
    "command", ["git config --edit", "git config -e", "git config edit", "git config --global -e"]
)
def test_editing_git_configuration_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "--edit" in reason and "core.hooksPath" in reason, reason


@pytest.mark.parametrize(
    "command, fragment",
    [
        ("K=core.hooksPath; git config $K /dev/null", "core.hooksPath"),
        ("git config $KEY /dev/null", "built from variables"),
        ("git -c $KV push origin feat/x", "built from variables"),
        ("K=alias.p; git config $K push", "alias cannot be verified"),
    ],
)
def test_a_configuration_key_from_a_variable_is_checked(on_feature, command, fragment):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert fragment in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "git config core.hooksPath",
        "git config --global core.hooksPath",
        "git config --local core.hooksPath",
        "git config --show-origin core.hooksPath",
        "git config --file .git/config core.hooksPath",
        "git config --get core.hooksPath",
        "git config get core.hooksPath",
    ],
)
def test_reading_core_hooks_path_is_allowed(on_feature, command):
    assert evaluate(command, on_feature) is None


@pytest.mark.parametrize(
    "command",
    [
        "git config core.hooksPath x",
        'git config core.hooksPath ""',
        "git config --global core.hooksPath x",
        "git config --file .git/config core.hooksPath x",
        "git config set core.hooksPath x",
        "git config --unset core.hooksPath",
        "git config --unset-all core.hooksPath",
        "git config unset core.hooksPath",
        "git -c core.hooksPath=/dev/null push origin feat/001-x",
    ],
)
def test_writing_core_hooks_path_is_refused(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "core.hooksPath" in reason, reason


def assert_alias_refused(reason: str | None) -> None:
    assert reason is not None
    assert "alias cannot be verified" in reason and "run the git command itself" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "git -c alias.p=push p origin main",
        "git -c alias.x='!git push origin main' x",
        "git -c Alias.P=push P origin feat/x",
    ],
)
def test_a_command_line_alias_is_refused(on_feature, command):
    assert_alias_refused(evaluate(command, on_feature))


@pytest.mark.parametrize(
    "command",
    ["git config alias.p push", "git config --global alias.p push", "git config set alias.p push"],
)
def test_writing_a_persistent_alias_is_refused(on_feature, command):
    assert_alias_refused(evaluate(command, on_feature))


@pytest.mark.parametrize("command", ["git config alias.p", "git config --get-regexp alias"])
def test_reading_an_alias_is_allowed(on_feature, command):
    assert evaluate(command, on_feature) is None


def test_other_command_line_config_keys_pass(on_feature):
    assert evaluate("git -c user.name=x commit -m y", on_feature) is None


def test_section_operations_on_core_or_alias_are_refused(on_feature):
    for command in [
        "git config --remove-section core",
        "git config --rename-section core x",
        "git config remove-section core",
    ]:
        reason = evaluate(command, on_feature)
        assert reason is not None, command
        assert "core.hooksPath" in reason, reason
    assert_alias_refused(evaluate("git config --rename-section x alias", on_feature))
    assert evaluate("git config --remove-section user", on_feature) is None


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


GUARD_DOC = BIN.parent / "docs" / "GUARD.md"


def guard_doc_section(heading: str) -> str:
    text = GUARD_DOC.read_text()
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


def split_cells(line: str) -> list[str]:
    cells, current, index = [], "", 0
    body = line.strip().strip("|")
    while index < len(body):
        if body.startswith("\\|", index):
            current += "|"
            index += 2
            continue
        if body[index] == "|":
            cells.append(current.strip())
            current = ""
        else:
            current += body[index]
        index += 1
    cells.append(current.strip())
    return cells


# The table is the document's claim that the guard stops what a string deny rule lets
# through; parsing it here keeps the claim and the guard from drifting apart.
def deny_table_rows() -> list[tuple[str, str, str]]:
    lines = [
        line
        for line in guard_doc_section("## Deny rules versus the guard").splitlines()
        if line.startswith("|")
    ]
    rows = []
    for line in lines[2:]:
        spans = []
        for cell in split_cells(line):
            assert cell.startswith("`") and cell.endswith("`") and cell.count("`") == 2, line
            spans.append(cell[1:-1])
        assert len(spans) == 3, line
        rows.append((spans[0], spans[1], spans[2]))
    return rows


def test_the_deny_table_has_at_least_five_rows():
    assert len(deny_table_rows()) >= 5


@pytest.mark.parametrize("command, rule, fragment", deny_table_rows())
def test_every_deny_table_command_is_refused(on_feature, command, rule, fragment):
    assert rule.startswith("Bash("), rule
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert fragment in reason, reason


def test_guard_md_records_the_deny_measurement():
    section = guard_doc_section("## Deny rules versus the guard")
    assert re.search(r"Measured on \d{4}-\d{2}-\d{2} with Claude Code \d+\.\d+\.\d+", section)


def test_guard_md_has_the_required_sections():
    lines = GUARD_DOC.read_text().splitlines()
    for heading in [
        "# The pipeline guard",
        "## Threat model",
        "## Three layers",
        "### The command guard",
        "### The pre-push hook",
        "### GitHub rulesets",
        "## Deny rules versus the guard",
        "## Fail-open by design",
        "## Known limits",
    ]:
        assert heading in lines, heading


def test_guard_md_names_the_known_limits():
    section = guard_doc_section("## Known limits")
    for token in [
        "Alembic",
        "stable",
        "Edit",
        "Write",
        "script",
        "interpreter",
        "function",
        "gh api -X DELETE",
        "docs/BACKLOG.md",
    ]:
        assert token in section, token
