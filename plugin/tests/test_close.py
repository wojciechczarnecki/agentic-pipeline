import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
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
    if args[args.index("--commit") + 1] == state["pr"]["headRefOid"]:
        if state.get("head_sleep"):
            import time
            time.sleep(state["head_sleep"])
        print(json.dumps(state.get("head_runs", [])))
        sys.exit(0)
    queue = state["run_list"]
    answer = queue.pop(0) if len(queue) > 1 else queue[0]
    with open(state_path, "w") as handle:
        json.dump(state, handle)
    if answer == "fail":
        sys.exit("HTTP 502: bad gateway")
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


def go_detached(lane: Lane) -> None:
    lane.git("switch", "-q", "--detach")


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
    "detached": go_detached,
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


def head_subject(lane: Lane) -> str:
    return lane.git("log", "-1", "--format=%s")


def commit_count(lane: Lane) -> int:
    return int(lane.git("rev-list", "--count", "HEAD"))


def queue(lane: Lane, *answers: list[dict]) -> None:
    lane.write_state(run_list=list(answers))


def reruns(lane: Lane) -> list[str]:
    return [call for call in lane.gh_calls() if call.startswith("run rerun")]


# SPEC 014, AC20: cost, `done`, derive, check, the closing commit, the push and the wait.
def test_close_green_path(lane):
    before = commit_count(lane)
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert head_subject(lane) == "docs: close SPEC 001 demo"
    assert commit_count(lane) == before + 1
    assert lane.git("show", "--name-only", "--format=", "HEAD").splitlines() == [f"{SPEC}/SPEC.md"]
    text = (lane.repo / SPEC / "SPEC.md").read_text()
    assert "\nstatus: done\n" in text
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    assert f'  - "done — {today}"\n' in text
    assert re.search(r"\n  finished_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}\n", text)
    assert lane.remote_head() == lane.git("rev-parse", "HEAD")
    head = lane.git("rev-parse", "HEAD")
    assert any(call.startswith(f"run list --commit {head}") for call in lane.gh_calls())
    assert lane.git("status", "--porcelain") == ""


def test_the_close_leaves_a_checkable_spec(lane):
    assert lane.close().returncode == 0
    check = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", SPEC],
        cwd=lane.repo,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr


def test_a_red_check_restores_the_spec(lane):
    plan = lane.repo / SPEC / "PLAN.md"
    plan.write_text(plan.read_text().replace("; `rejected`: F4", "; `rejected`: none"))
    lane.git("commit", "-q", "-am", "unbalance the gate")
    lane.git("push", "-q")
    spec_before, head_before = lane.spec_bytes(), lane.git("rev-parse", "HEAD")
    result = lane.close()
    assert result.returncode != 0
    assert lane.spec_bytes() == spec_before
    assert lane.git("rev-parse", "HEAD") == head_before
    assert lane.git("status", "--porcelain") == ""
    assert len(stop_lines(result)) == 1
    assert stop_lines(result)[0].startswith("close stopped at check:")
    assert stop_lines(result)[0].endswith("committed: no, pushed: no")


def test_red_then_green_after_one_rerun(lane):
    failed = run("ci", conclusion="failure", databaseId=11)
    jobs = {"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}}
    lane.write_state(jobs=jobs)
    queue(lane, [failed], [run("ci", attempt=2)])
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert reruns(lane) == ["run rerun 11 --failed"]
    assert "plugin" in result.stdout


def test_red_twice_stops(lane):
    failed = run("ci", conclusion="failure", databaseId=11)
    lane.write_state(jobs={"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}})
    queue(lane, [failed], [{**failed, "attempt": 2}])
    result = lane.close()
    assert result.returncode == 5, result.stderr
    assert "red after one re-run" in stop_lines(result)[0]
    assert len(reruns(lane)) == 1
    assert stop_lines(result)[0].endswith("committed: yes, pushed: yes")
    assert head_subject(lane) == "docs: close SPEC 001 demo"


def test_a_timeout_stops_at_the_wait(lane):
    lane.env["PIPELINE_CLOSE_TIMEOUT_SECONDS"] = "1"
    queue(lane, [run("ci", status="in_progress", conclusion="")])
    result = lane.close()
    assert result.returncode == 5, result.stderr
    assert "timed out" in result.stderr
    assert stop_lines(result)[0].endswith("committed: yes, pushed: yes")


def test_a_failed_push_stops(lane):
    lane.git("remote", "set-url", "origin", str(lane.root / "nowhere.git"))
    result = lane.close()
    assert result.returncode == 4, result.stderr
    assert stop_lines(result)[0].endswith("committed: yes, pushed: no")
    assert head_subject(lane) == "docs: close SPEC 001 demo"


def test_every_stop_prints_one_state_line(lane):
    lane.git("remote", "set-url", "origin", str(lane.root / "nowhere.git"))
    result = lane.close()
    assert len(stop_lines(result)) == 1
    assert STOP_LINE.match(stop_lines(result)[0])
    assert stop_lines(result)[0].startswith("close stopped at push:")


def test_cost_warnings_do_not_stop_the_close(lane):
    result = lane.close()
    assert result.returncode == 0
    assert "no stage transcripts" in result.stderr
    assert stop_lines(result) == []


def test_a_failed_commit_restores_the_spec(lane):
    hooks = lane.root / "hooks"
    hooks.mkdir()
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
    lane.git("config", "core.hooksPath", str(hooks))
    spec_before, head_before = lane.spec_bytes(), lane.git("rev-parse", "HEAD")
    result = lane.close()
    assert result.returncode == 4, result.stderr
    assert stop_lines(result)[0].endswith("committed: no, pushed: no")
    assert lane.spec_bytes() == spec_before
    assert lane.git("rev-parse", "HEAD") == head_before
    assert lane.git("status", "--porcelain") == ""


FLAKY_URL = "https://example.test/runs/21"


def flaky_pr_head(lane: Lane) -> None:
    flaky = run("ci", databaseId=21, attempt=2, url=FLAKY_URL)
    jobs = {
        "21": {
            "1": [{"name": "plugin", "conclusion": "failure"}],
            "latest": [{"name": "plugin", "conclusion": "success"}],
        }
    }
    lane.write_state(head_runs=[flaky], jobs=jobs)


# SPEC 014, AC21: a job that passed only on a later attempt stops the close before the commit,
# unless the backlog already names it.
def test_a_flaky_job_without_a_backlog_entry_stops(lane):
    flaky_pr_head(lane)
    spec_before, head_before = lane.spec_bytes(), lane.git("rev-parse", "HEAD")
    result = lane.close()
    assert result.returncode == 3, result.stderr
    assert "plugin" in stop_lines(result)[0] and FLAKY_URL in stop_lines(result)[0]
    assert stop_lines(result)[0].endswith("committed: no, pushed: no")
    assert lane.git("rev-parse", "HEAD") == head_before
    assert lane.spec_bytes() == spec_before
    assert lane.git("status", "--porcelain") == ""


def test_a_flaky_job_in_the_backlog_passes(lane):
    flaky_pr_head(lane)
    backlog = lane.repo / "docs" / "BACKLOG.md"
    backlog.write_text("# Backlog\n\n- P3: the `plugin` job flakes on the first attempt\n")
    lane.git("commit", "-q", "-am", "name the flaky job")
    lane.git("push", "-q")
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert head_subject(lane) == "docs: close SPEC 001 demo"


def test_a_job_that_failed_in_the_latest_attempt_is_not_flaky(lane):
    run_21 = run("ci", databaseId=21, attempt=2, conclusion="failure", url=FLAKY_URL)
    lane.write_state(head_runs=[run_21], jobs={"21": {"1": [], "latest": []}})
    assert lane.close().returncode == 0


# SPEC 014, AC22: a close that committed but did not go green resumes from the push or the wait.
def test_resume_after_a_stop_at_the_wait(lane):
    failed = run("ci", conclusion="failure", databaseId=11)
    lane.write_state(jobs={"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}})
    queue(lane, [failed])
    assert lane.close().returncode == 5
    commits = commit_count(lane)
    queue(lane, [run("ci")])
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert commit_count(lane) == commits
    assert lane.remote_head() == lane.git("rev-parse", "HEAD")
    assert "pushed: yes" not in result.stderr


def test_resume_after_a_failed_push(lane):
    lane.git("remote", "set-url", "origin", str(lane.root / "nowhere.git"))
    assert lane.close().returncode == 4
    commits = commit_count(lane)
    lane.git("remote", "set-url", "origin", str(lane.remote))
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert commit_count(lane) == commits
    assert lane.remote_head() == lane.git("rev-parse", "HEAD")


def test_done_without_the_close_commit_is_refused(lane):
    path = lane.repo / SPEC / "SPEC.md"
    path.write_text(path.read_text().replace("status: implemented", "status: done"))
    lane.git("commit", "-q", "-am", "set done by hand")
    lane.git("push", "-q")
    result = lane.close()
    assert result.returncode == 1
    assert stop_lines(result)[0].startswith("close stopped at preconditions:")


# Final review F3: right after the re-run GitHub may still report the failed attempt; the close
# waits for the attempt to grow instead of calling the re-run red.
def test_the_old_attempt_after_a_rerun_is_not_judged(lane):
    failed = run("ci", conclusion="failure", databaseId=11)
    lane.write_state(jobs={"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}})
    queue(lane, [failed], [failed], [run("ci", attempt=2)])
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert len(reruns(lane)) == 1


def test_a_rerun_that_never_starts_times_out(lane):
    lane.env["PIPELINE_CLOSE_TIMEOUT_SECONDS"] = "1"
    failed = run("ci", conclusion="failure", databaseId=11)
    lane.write_state(jobs={"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}})
    queue(lane, [failed])
    result = lane.close()
    assert result.returncode == 5, result.stderr
    assert "timed out" in stop_lines(result)[0]


# Final review F2: the backlog excuses a job only when an entry names it as a code span.
def test_the_word_in_backlog_prose_does_not_excuse_the_job(lane):
    flaky_pr_head(lane)
    backlog = lane.repo / "docs" / "BACKLOG.md"
    backlog.write_text("# Backlog\n\n- P3: the plugins and the plugin docs need a review\n")
    lane.git("commit", "-q", "-am", "prose that uses the word")
    lane.git("push", "-q")
    result = lane.close()
    assert result.returncode == 3, result.stderr
    assert "name it as `plugin`" in stop_lines(result)[0]


# Final review F11: the close never forces, so a remote moved ahead stops it at the push.
def test_a_remote_moved_ahead_stops_the_push(lane):
    other = lane.root / "other"
    run_git(lane.root, "clone", "-q", "-b", BRANCH, str(lane.remote), str(other), env=lane.env)
    (other / "elsewhere.txt").write_text("x\n")
    run_git(other, "add", "-A", env=lane.env)
    run_git(other, "commit", "-q", "-m", "elsewhere", env=lane.env)
    run_git(other, "push", "-q", "origin", BRANCH, env=lane.env)
    remote_before = lane.remote_head()
    result = lane.close()
    assert result.returncode == 4, result.stderr
    assert stop_lines(result)[0].startswith("close stopped at push:")
    assert stop_lines(result)[0].endswith("committed: yes, pushed: no")
    assert lane.remote_head() == remote_before


def test_an_empty_run_list_is_not_green(lane):
    lane.env["PIPELINE_CLOSE_TIMEOUT_SECONDS"] = "1"
    queue(lane, [])
    result = lane.close()
    assert result.returncode == 5, result.stderr
    assert "timed out" in stop_lines(result)[0]


def test_runs_that_appear_late_are_waited_for(lane):
    queue(lane, [], [run("ci")])
    result = lane.close()
    assert result.returncode == 0, result.stderr
    head = lane.git("rev-parse", "HEAD")
    assert sum(call.startswith(f"run list --commit {head}") for call in lane.gh_calls()) == 2


def test_a_failed_rerun_stops_at_the_wait(lane):
    failed = run("ci", conclusion="failure", databaseId=11)
    lane.write_state(
        jobs={"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}}, rerun_fails=True
    )
    queue(lane, [failed])
    result = lane.close()
    assert result.returncode == 5, result.stderr
    assert "could not re-run" in stop_lines(result)[0]
    assert stop_lines(result)[0].endswith("committed: yes, pushed: yes")


def test_a_gh_failure_in_the_flaky_check_restores_the_spec(lane):
    lane.write_state(head_runs=[run("ci", databaseId=21, attempt=2)], jobs={})
    spec_before, head_before = lane.spec_bytes(), lane.git("rev-parse", "HEAD")
    result = lane.close()
    assert result.returncode == 1, result.stderr
    assert stop_lines(result)[0].startswith("close stopped at flaky:")
    assert stop_lines(result)[0].endswith("committed: no, pushed: no")
    assert lane.spec_bytes() == spec_before
    assert lane.git("rev-parse", "HEAD") == head_before
    assert lane.git("status", "--porcelain") == ""


def test_a_gh_failure_after_the_push_stops_at_the_wait(lane):
    queue(lane, "fail")
    result = lane.close()
    assert result.returncode == 5, result.stderr
    assert "gh run list failed: HTTP 502" in stop_lines(result)[0]
    assert stop_lines(result)[0].endswith("committed: yes, pushed: yes")


def test_resume_after_an_unrelated_commit(lane):
    failed = run("ci", conclusion="failure", databaseId=11)
    lane.write_state(jobs={"11": {"latest": [{"name": "plugin", "conclusion": "failure"}]}})
    queue(lane, [failed])
    assert lane.close().returncode == 5
    (lane.repo / "docs" / "BACKLOG.md").write_text("# Backlog\n\n- P3: later\n")
    lane.git("commit", "-q", "-am", "docs: record owner decision for 001")
    commits = commit_count(lane)
    queue(lane, [run("ci")])
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert commit_count(lane) == commits
    assert lane.remote_head() == lane.git("rev-parse", "HEAD")


# Final review F5: a signal (or any error) after `done` was written restores SPEC.md and still
# prints the stop line.
def test_a_sigterm_before_the_commit_restores_the_spec(lane):
    lane.write_state(head_sleep=30)
    spec_before, head_before = lane.spec_bytes(), lane.git("rev-parse", "HEAD")
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--close", SPEC],
        cwd=lane.repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=lane.env,
    )
    head = lane.git("rev-parse", "HEAD")
    deadline = time.monotonic() + 20
    while not any(call.startswith(f"run list --commit {head}") for call in lane.gh_calls()):
        assert time.monotonic() < deadline, "the close never reached the flaky check"
        time.sleep(0.05)
    assert b"status: done" in lane.spec_bytes()
    process.send_signal(signal.SIGTERM)
    _, stderr = process.communicate(timeout=20)
    assert process.returncode == 1, stderr
    lines = [line for line in stderr.splitlines() if line.startswith("close stopped at")]
    assert len(lines) == 1 and STOP_LINE.match(lines[0]), stderr
    assert lines[0].startswith("close stopped at flaky: unexpected")
    assert lines[0].endswith("committed: no, pushed: no")
    assert lane.spec_bytes() == spec_before
    assert lane.git("rev-parse", "HEAD") == head_before
    assert lane.git("status", "--porcelain") == ""


# Final review F12: every git and gh call has a deadline and never prompts.
def test_a_stalled_call_ends_at_its_deadline(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(BIN))
    import workflow_close

    monkeypatch.setenv("PIPELINE_CLOSE_CALL_TIMEOUT_SECONDS", "1")
    started = time.monotonic()
    result = workflow_close.command([sys.executable, "-c", "import time; time.sleep(10)"], tmp_path)
    assert time.monotonic() - started < 5
    assert result.returncode == 124
    assert "timed out after 1 s" in result.stderr


def test_calls_never_prompt(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(BIN))
    import workflow_close

    script = "import os; print(os.environ['GIT_TERMINAL_PROMPT'], os.environ['GH_PROMPT_DISABLED'])"
    result = workflow_close.command([sys.executable, "-c", script], tmp_path)
    assert result.stdout.split() == ["0", "1"]


# Final review F1: a final review with no findings records a gate entry with empty lists, and the
# close goes green on it instead of stopping at the check.
def test_a_review_without_findings_closes(lane):
    plan = lane.repo / SPEC / "PLAN.md"
    head = plan.read_text().split("## Final review")[0]
    head = head.replace(
        "`accepted`: F1, F2, F3; `rejected`: F4", "`accepted`: none; `rejected`: none"
    )
    plan.write_text(head + "## Final review\n\nNo findings.\n\nLeft out: 0 nit findings\n")
    lane.git("commit", "-q", "-am", "a clean final review")
    lane.git("push", "-q")
    result = lane.close()
    assert result.returncode == 0, result.stderr
    assert head_subject(lane) == "docs: close SPEC 001 demo"
    text = (lane.repo / SPEC / "SPEC.md").read_text()
    assert "\n  findings_accepted: 0\n" in text and "\n  final_review_nits: 0\n" in text
