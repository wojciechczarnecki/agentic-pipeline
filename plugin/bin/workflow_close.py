#!/usr/bin/env python3
# The scripted close of a spec, run by `workflow_metrics.py --close <spec-dir>`: cost, status
# `done`, derived counters, the closing commit, the push and the wait for green CI.
# The Bash call that runs it matches one allow rule, so the `git push` and `gh` calls inside it
# are never seen by the command guard: the script refuses `main`, `master` and the configured
# protectedBranches itself, pushes only `origin <current branch>`, never with force, and
# touches only SPEC.md.
# Exit codes: 0 — the checks of the new head are green; 1 — refused, or derive/check red,
# with nothing changed or committed; 3 — a job passed only on a later attempt and the backlog
# does not name it, nothing committed; 4 — the commit or the push failed; 5 — the checks are
# red after the one re-run, or the wait timed out. Every non-zero exit prints one line:
# `close stopped at <step>: <reason>; committed: yes|no, pushed: yes|no`. An unexpected error
# or a SIGTERM stops the same way, with the code of the state it left (1 before the commit,
# 4 before the push, 5 after it), and SPEC.md restored when nothing was committed.
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_config  # noqa: E402

ALWAYS_PROTECTED = ("main", "master")
GREEN = ("success", "skipped", "neutral")
RUN_FIELDS = "databaseId,status,conclusion,attempt,url,workflowName"
RESUME = "run `workflow_metrics.py --close` again to resume"


class TerminatedError(Exception):
    pass


class Progress:
    def __init__(self):
        self.step, self.committed, self.pushed = "preconditions", False, False


class StopError(Exception):
    def __init__(self, code: int, step: str, reason: str, committed=False, pushed=False):
        super().__init__(reason)
        self.code, self.step, self.reason = code, step, reason
        self.committed, self.pushed = committed, pushed

    def line(self) -> str:
        done = lambda flag: "yes" if flag else "no"  # noqa: E731
        return (
            f"close stopped at {self.step}: {self.reason}; "
            f"committed: {done(self.committed)}, pushed: {done(self.pushed)}"
        )


# Every git and gh call has a deadline and never prompts, so a stalled `gh` or a push that asks
# for credentials ends as a stop line instead of hanging the background call.
def command(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    limit = seconds("PIPELINE_CLOSE_CALL_TIMEOUT_SECONDS", 300)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GH_PROMPT_DISABLED": "1"}
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, check=False, env=env, timeout=limit
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"`{args[0]}` timed out after {limit} s")
    except OSError as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


def detail(result: subprocess.CompletedProcess) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text.splitlines()[-1] if text else f"exit code {result.returncode}"


def terminate(signum, frame) -> None:
    raise TerminatedError(f"signal {signum}")


def close(spec_dir: Path, metrics) -> int:
    progress = Progress()
    previous = signal.signal(signal.SIGTERM, terminate)
    try:
        return run_close(spec_dir.resolve(), metrics, progress)
    except StopError as stop:
        print(stop.line(), file=sys.stderr)
        return stop.code
    except (Exception, KeyboardInterrupt) as exc:
        code = 1 if not progress.committed else 4 if not progress.pushed else 5
        stop = StopError(
            code,
            progress.step,
            f"unexpected {type(exc).__name__}: {exc}; {RESUME}",
            progress.committed,
            progress.pushed,
        )
        print(stop.line(), file=sys.stderr)
        return code
    finally:
        signal.signal(signal.SIGTERM, previous)


def run_close(spec_dir: Path, metrics, progress: Progress) -> int:
    spec = spec_dir / "SPEC.md"
    if not spec.is_file():
        raise StopError(1, "preconditions", f"no SPEC.md in {spec_dir}; pass the spec directory")
    root = command(["git", "rev-parse", "--show-toplevel"], spec_dir)
    if root.returncode != 0:
        raise StopError(1, "preconditions", "not inside a git repository; run it in the lane")
    repo = Path(root.stdout.strip())
    branch = command(["git", "branch", "--show-current"], repo).stdout.strip()
    config, _ = workflow_config.load_sections(repo)
    protected = [*ALWAYS_PROTECTED, *(config.get("protectedBranches") or [])]
    if not branch or branch in protected:
        raise StopError(
            1,
            "preconditions",
            f"the branch `{branch or 'HEAD'}` is protected or detached; "
            "switch to the spec's lane branch",
        )
    resuming = is_resume(spec, spec_dir.name, repo, metrics)
    if not resuming and metrics.parse_status(spec.read_text(encoding="utf-8")) != "implemented":
        raise StopError(
            1, "preconditions", "the spec status is not `implemented`; finish the stages first"
        )
    if command(["git", "status", "--porcelain"], repo).stdout.strip():
        raise StopError(
            1, "preconditions", "the working tree is not clean; commit or stash the changes"
        )
    view = command(["gh", "pr", "view", "--json", "number,state,url,headRefOid"], repo)
    pr = None
    if view.returncode == 0:
        try:
            pr = json.loads(view.stdout)
        except ValueError:
            pr = None
    if not isinstance(pr, dict) or pr.get("state") != "OPEN":
        raise StopError(
            1, "preconditions", f"no open pull request for `{branch}`; open it with `gh pr create`"
        )
    original = spec.read_bytes()
    message = commit_message(spec_dir.name)
    if not resuming:
        try:
            prepare(spec, spec_dir, metrics, progress)
            progress.step = "flaky"
            flaky = flaky_jobs(repo, pr, config)
            if flaky:
                raise StopError(3, "flaky", flaky)
            progress.step = "commit"
            commit(spec, message, original, repo)
        except BaseException:
            restore(spec, original, repo)
            raise
        progress.committed = True
    progress.step = "push"
    push(repo, branch)
    progress.pushed = True
    progress.step = "wait"
    return wait(repo)


def commit_message(name: str) -> str:
    match = re.fullmatch(r"(\d+)-(.+)", name)
    return f"docs: close SPEC {match.group(1)} {match.group(2)}" if match else f"docs: close {name}"


def restore(spec: Path, original: bytes, repo: Path) -> None:
    spec.write_bytes(original)
    command(["git", "reset", "-q", "--", str(spec)], repo)


# Cost, status `done`, derived counters, and the check that stands in for the owner's eye: a red
# check stops the close before anything is committed.
def prepare(spec: Path, spec_dir: Path, metrics, progress: Progress) -> None:
    progress.step = "cost"
    metrics.record_cost(spec_dir, metrics.default_transcripts())
    progress.step = "status"
    now = datetime.now()
    text = spec.read_text(encoding="utf-8")
    done = mark_done(text, now.strftime("%Y-%m-%d"), now.strftime(metrics.TIME_FORMAT), metrics)
    if done is None:
        raise StopError(
            1, "status", "SPEC.md has no frontmatter with a `status` key; restore the template's"
        )
    spec.write_text(done, encoding="utf-8")
    progress.step = "derive"
    if metrics.derive(spec_dir) != 0:
        raise StopError(1, "derive", "SPEC.md could not be read")
    progress.step = "check"
    problems = metrics.check(spec_dir)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        count = f"{len(problems)} problem" + ("s" if len(problems) > 1 else "")
        raise StopError(
            1, "check", f"`--check` is red with {count}; fix them in the spec files and run again"
        )


def mark_done(text: str, today: str, now: str, metrics) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    head = text[4 : end + 1].splitlines(keepends=True)
    status = next(
        (i for i, line in enumerate(head) if re.match(r"status:", line)),
        None,
    )
    if status is None:
        return None
    head[status] = "status: done\n"
    history = next((i for i, line in enumerate(head) if line.rstrip() == "stage_history:"), None)
    if history is None:
        head[status + 1 : status + 1] = ["stage_history:\n", f'  - "done — {today}"\n']
    else:
        last = history + 1
        while last < len(head) and head[last].startswith(" "):
            last += 1
        indent = re.match(r" *", head[last - 1]).group(0) if last > history + 1 else "  "
        head.insert(last, f'{indent}- "done — {today}"\n')
    return metrics.write_costs("---\n" + "".join(head) + text[end + 1 :], {"finished_at": now})


# The jobs of the PR head's checks that failed on an earlier attempt and passed on a later one,
# unless the backlog already names them as a code span (`` `plugin` ``): a bare substring test
# would excuse a job called `plugin` or `test` by any sentence that uses the word. Returns the
# reason to stop, or an empty string.
def flaky_jobs(repo: Path, pr: dict, config) -> str:
    sha = pr.get("headRefOid")
    if not isinstance(sha, str) or not sha:
        return ""
    backlog_path = config.get("docs.backlog")
    backlog = ""
    if isinstance(backlog_path, str) and (repo / backlog_path).is_file():
        backlog = (repo / backlog_path).read_text(encoding="utf-8", errors="replace")
    for run in runs_of(repo, sha, "flaky", 1, False):
        attempt = run.get("attempt")
        if not isinstance(attempt, int) or attempt < 2 or run.get("conclusion") not in GREEN:
            continue
        later = {
            job["name"]
            for job in jobs_of(repo, run, None)
            if job.get("conclusion") == "success" and "name" in job
        }
        for earlier in range(1, attempt):
            for job in jobs_of(repo, run, earlier):
                name = job.get("name")
                if (
                    job.get("conclusion") == "failure"
                    and name in later
                    and f"`{name}`" not in backlog
                ):
                    return (
                        f"the job `{name}` passed only on attempt {attempt} of {run.get('url')}; "
                        f"fix it, or name it as `{name}` in a {backlog_path} entry"
                    )
    return ""


def jobs_of(repo: Path, run: dict, attempt: int | None) -> list[dict]:
    args = ["gh", "run", "view", str(run.get("databaseId"))]
    viewed = command(
        [*args, *(["--attempt", str(attempt)] if attempt else []), "--json", "jobs"], repo
    )
    try:
        jobs = json.loads(viewed.stdout)["jobs"] if viewed.returncode == 0 else None
    except (ValueError, KeyError, TypeError):
        jobs = None
    if not isinstance(jobs, list):
        raise StopError(1, "flaky", f"gh run view failed: {detail(viewed)}; {RESUME}")
    return [job for job in jobs if isinstance(job, dict)]


def commit(spec: Path, message: str, original: bytes, repo: Path) -> None:
    added = command(["git", "add", "--", str(spec)], repo)
    made = (
        added
        if added.returncode != 0
        else command(["git", "commit", "-q", "-m", message, "--", str(spec)], repo)
    )
    if made.returncode != 0:
        restore(spec, original, repo)
        raise StopError(4, "commit", f"git could not commit: {detail(made)}; {RESUME}")


def push(repo: Path, branch: str) -> None:
    pushed = command(["git", "push", "origin", branch], repo)
    if pushed.returncode != 0:
        raise StopError(4, "push", f"git push failed: {detail(pushed)}; {RESUME}", committed=True)


def seconds(name: str, default: int) -> int:
    value = os.environ.get(name, "")
    return int(value) if value.isdigit() else default


def runs_of(repo: Path, sha: str, step: str, code: int = 5, shipped: bool = True) -> list[dict]:
    listed = command(
        ["gh", "run", "list", "--commit", sha, "--json", RUN_FIELDS, "--limit", "100"], repo
    )
    try:
        runs = json.loads(listed.stdout) if listed.returncode == 0 else None
    except ValueError:
        runs = None
    if not isinstance(runs, list):
        raise StopError(
            code, step, f"gh run list failed: {detail(listed)}; {RESUME}", shipped, shipped
        )
    return [run for run in runs if isinstance(run, dict)]


# The runs of the head once all are completed. A run that was re-run counts only once its attempt
# has grown past the one that failed: right after `gh run rerun` GitHub may still report the old
# completed attempt, and judging it would call the re-run red before it ran.
def wait_for(repo: Path, sha: str, rerun: dict | None = None) -> list[dict]:
    deadline = time.monotonic() + seconds("PIPELINE_CLOSE_TIMEOUT_SECONDS", 3600)
    poll = seconds("PIPELINE_CLOSE_POLL_SECONDS", 15)
    rerun = rerun or {}
    while True:
        runs = runs_of(repo, sha, "wait")
        if runs and all(settled(run, rerun) for run in runs):
            return runs
        if time.monotonic() >= deadline:
            raise StopError(
                5, "wait", f"timed out waiting for the checks of {sha[:7]}; {RESUME}", True, True
            )
        time.sleep(poll)


def settled(run: dict, rerun: dict) -> bool:
    if run.get("status") != "completed":
        return False
    before = rerun.get(run.get("databaseId"))
    if before is None:
        return True
    attempt = run.get("attempt")
    return isinstance(attempt, int) and attempt > before


def red(runs: list[dict]) -> list[dict]:
    return [run for run in runs if run.get("conclusion") not in GREEN]


def failed_jobs(repo: Path, run: dict) -> str:
    viewed = command(["gh", "run", "view", str(run.get("databaseId")), "--json", "jobs"], repo)
    try:
        jobs = json.loads(viewed.stdout)["jobs"] if viewed.returncode == 0 else []
    except (ValueError, KeyError, TypeError):
        jobs = []
    if not isinstance(jobs, list):
        jobs = []
    names = [
        str(job.get("name", "?"))
        for job in jobs
        if isinstance(job, dict) and job.get("conclusion") not in GREEN
    ]
    return ", ".join(names) or str(run.get("workflowName", "?"))


def wait(repo: Path) -> int:
    sha = command(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    runs = wait_for(repo, sha)
    failed = red(runs)
    if not failed:
        return 0
    names = []
    rerun: dict = {}
    for run in failed:
        names.append(f"{failed_jobs(repo, run)} ({run.get('url', '?')})")
        started = command(["gh", "run", "rerun", str(run.get("databaseId")), "--failed"], repo)
        if started.returncode != 0:
            raise StopError(
                5,
                "wait",
                f"gh could not re-run a failed job: {detail(started)}; {RESUME}",
                True,
                True,
            )
        attempt = run.get("attempt")
        rerun[run.get("databaseId")] = attempt if isinstance(attempt, int) else 1
    still = red(wait_for(repo, sha, rerun))
    if still:
        raise StopError(
            5,
            "wait",
            "the checks are red after one re-run: "
            + "; ".join(names)
            + "; fix the failure, push, and run `workflow_metrics.py --close` again",
            True,
            True,
        )
    print("passed only on a re-run: " + "; ".join(names))
    return 0


def is_resume(spec: Path, name: str, repo: Path, metrics) -> bool:
    if metrics.parse_status(spec.read_text(encoding="utf-8")) != "done":
        return False
    match = re.fullmatch(r"(\d+)-(.+)", name)
    if not match:
        return False
    subject = command(["git", "log", "-1", "--format=%s", "--", str(spec)], repo).stdout.strip()
    return subject == f"docs: close SPEC {match.group(1)} {match.group(2)}"
