import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin"
SCRIPT = BIN / "workflow_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "derive"
SPEC = "specs/001-demo"
BRANCH = "feat/001-demo"
STOP_LINE = re.compile(r"^close stopped at [a-z-]+: .+; committed: (yes|no), pushed: (yes|no)$")

GH_STUB = """#!{python}
import json, os, sys

state_path = os.environ["GH_STUB_STATE"]
with open(state_path) as handle:
    state = json.load(handle)
with open(os.environ["GH_STUB_LOG"], "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if args[:2] == ["pr", "view"]:
    if not state.get("pr"):
        sys.exit("no pull requests found for this branch")
    print(json.dumps(state["pr"]))
elif args[:2] == ["run", "list"]:
    queue = state["run_list"]
    answer = queue.pop(0) if len(queue) > 1 else queue[0]
    with open(state_path, "w") as handle:
        json.dump(state, handle)
    print(json.dumps(answer))
elif args[:2] == ["run", "view"]:
    run_id = args[2]
    attempt = args[args.index("--attempt") + 1] if "--attempt" in args else "latest"
    print(json.dumps({{"jobs": state["jobs"][run_id][attempt]}}))
elif args[:2] == ["run", "rerun"]:
    if state.get("rerun_fails"):
        sys.exit("cannot rerun")
else:
    sys.exit("unexpected gh call: " + " ".join(args))
"""


def run_git(repo: Path, *args: str, env=None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, env=env, check=True
    )
    return result.stdout.strip()


class Lane:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.remote = root / "remote.git"
        self.bin = root / "bin"
        self.state = root / "gh-state.json"
        self.log = root / "gh.log"
        self.config = root / "claude-config"
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_STUB_STATE": str(self.state),
            "GH_STUB_LOG": str(self.log),
            "CLAUDE_CONFIG_DIR": str(self.config),
            "PIPELINE_CLOSE_POLL_SECONDS": "0",
            "PIPELINE_CLOSE_TIMEOUT_SECONDS": "5",
            "GIT_AUTHOR_NAME": "Lane",
            "GIT_AUTHOR_EMAIL": "lane@example.com",
            "GIT_COMMITTER_NAME": "Lane",
            "GIT_COMMITTER_EMAIL": "lane@example.com",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    def git(self, *args: str) -> str:
        return run_git(self.repo, *args, env=self.env)

    def write_state(self, **changes) -> None:
        state = json.loads(self.state.read_text()) if self.state.exists() else {}
        state.update(changes)
        self.state.write_text(json.dumps(state))

    def close(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--close", SPEC, *extra],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=self.env,
        )

    def gh_calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def remote_head(self, branch: str = BRANCH) -> str:
        out = subprocess.run(
            ["git", "--git-dir", str(self.remote), "rev-parse", branch],
            capture_output=True,
            text=True,
            env=self.env,
        )
        return out.stdout.strip()

    def spec_bytes(self) -> bytes:
        return (self.repo / SPEC / "SPEC.md").read_bytes()


def run(name: str, runs: list[dict] | None = None, **extra) -> dict:
    base = {
        "databaseId": 11,
        "status": "completed",
        "conclusion": "success",
        "attempt": 1,
        "url": "https://example.test/runs/11",
        "workflowName": "ci",
    }
    return {**base, "workflowName": name, **extra}


@pytest.fixture
def lane(tmp_path):
    lane = Lane(tmp_path)
    lane.bin.mkdir()
    lane.config.mkdir()
    gh = lane.bin / "gh"
    gh.write_text(GH_STUB.format(python=sys.executable))
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    run_git(tmp_path, "init", "-q", "--bare", "-b", "main", str(lane.remote), env=lane.env)
    run_git(tmp_path, "init", "-q", "-b", "main", str(lane.repo), env=lane.env)
    lane.git("config", "core.hooksPath", "/dev/null")
    (lane.repo / ".claude").mkdir()
    (lane.repo / ".claude" / "workflow.json").write_text(
        json.dumps({"protectedBranches": ["stable"], "docs": {"backlog": "docs/BACKLOG.md"}})
    )
    (lane.repo / "docs").mkdir()
    (lane.repo / "docs" / "BACKLOG.md").write_text("# Backlog\n")
    (lane.repo / SPEC).mkdir(parents=True)
    for name in ("SPEC.md", "PLAN.md"):
        shutil.copy(FIXTURE / name, lane.repo / SPEC / name)
    lane.git("add", "-A")
    lane.git("commit", "-q", "-m", "init")
    lane.git("remote", "add", "origin", str(lane.remote))
    lane.git("push", "-q", "origin", "main")
    lane.git("switch", "-q", "-c", BRANCH)
    lane.git("push", "-q", "-u", "origin", BRANCH)
    head = lane.git("rev-parse", "HEAD")
    pr = {"number": 7, "state": "OPEN", "url": "https://example.test/pull/7", "headRefOid": head}
    lane.write_state(pr=pr, run_list=[[run("ci")]], jobs={})
    return lane


def stop_lines(result: subprocess.CompletedProcess) -> list[str]:
    return [line for line in result.stderr.splitlines() if line.startswith("close stopped at")]


def break_status(lane: Lane) -> None:
    path = lane.repo / SPEC / "SPEC.md"
    path.write_text(path.read_text().replace("status: implemented", "status: plan-approved"))
    lane.git("commit", "-q", "-am", "status")
    lane.git("push", "-q")


def go_main(lane: Lane) -> None:
    lane.git("switch", "-q", "main")


def go_master(lane: Lane) -> None:
    lane.git("switch", "-q", "-c", "master")


def go_stable(lane: Lane) -> None:
    lane.git("switch", "-q", "-c", "stable")


def make_dirty(lane: Lane) -> None:
    (lane.repo / "docs" / "BACKLOG.md").write_text("# Backlog\n\nedited\n")


def make_untracked(lane: Lane) -> None:
    (lane.repo / "stray.txt").write_text("x\n")


def no_pr(lane: Lane) -> None:
    lane.write_state(pr=None)


def closed_pr(lane: Lane) -> None:
    state = json.loads(lane.state.read_text())
    lane.write_state(pr={**state["pr"], "state": "CLOSED"})


REFUSALS = {
    "main": go_main,
    "master": go_master,
    "stable": go_stable,
    "status": break_status,
    "dirty": make_dirty,
    "untracked": make_untracked,
    "no-pr": no_pr,
    "closed-pr": closed_pr,
}


# SPEC 014, AC19, AC22: a refused close changes nothing and says where it stopped.
@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_close_refuses(lane, case):
    REFUSALS[case](lane)
    spec_before, head_before = lane.spec_bytes(), lane.git("rev-parse", "HEAD")
    remote_before = lane.remote_head()
    result = lane.close()
    assert result.returncode == 1, result.stderr
    assert lane.spec_bytes() == spec_before
    assert lane.git("rev-parse", "HEAD") == head_before
    assert lane.remote_head() == remote_before
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1, lines
    assert STOP_LINE.match(lines[0]), lines[0]
    assert lines[0].endswith("committed: no, pushed: no")
    assert "run list" not in " ".join(lane.gh_calls())


def test_close_needs_a_spec_directory(lane):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--close"],
        cwd=lane.repo,
        capture_output=True,
        text=True,
        env=lane.env,
    )
    assert result.returncode == 1
    assert "usage" in result.stderr


def test_close_is_exclusive(lane):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--close", "--check", SPEC],
        cwd=lane.repo,
        capture_output=True,
        text=True,
        env=lane.env,
    )
    assert result.returncode == 2
    assert "separate runs" in result.stderr
