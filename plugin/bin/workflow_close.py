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
# `close stopped at <step>: <reason>; committed: yes|no, pushed: yes|no`.
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_config  # noqa: E402

ALWAYS_PROTECTED = ("main", "master")
GREEN = ("success", "skipped", "neutral")
RUN_FIELDS = "databaseId,status,conclusion,attempt,url,workflowName"


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


def command(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


def detail(result: subprocess.CompletedProcess) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text.splitlines()[-1] if text else f"exit code {result.returncode}"


def close(spec_dir: Path, metrics) -> int:
    try:
        return run_close(spec_dir.resolve(), metrics)
    except StopError as stop:
        print(stop.line(), file=sys.stderr)
        return stop.code


def run_close(spec_dir: Path, metrics) -> int:
    spec = spec_dir / "SPEC.md"
    if not spec.is_file():
        raise StopError(1, "preconditions", f"no SPEC.md in {spec_dir}")
    root = command(["git", "rev-parse", "--show-toplevel"], spec_dir)
    if root.returncode != 0:
        raise StopError(1, "preconditions", "not inside a git repository")
    repo = Path(root.stdout.strip())
    branch = command(["git", "branch", "--show-current"], repo).stdout.strip()
    config, _ = workflow_config.load_sections(repo)
    protected = [*ALWAYS_PROTECTED, *(config.get("protectedBranches") or [])]
    if not branch or branch in protected:
        raise StopError(
            1, "preconditions", f"the branch `{branch or 'HEAD'}` is protected or detached"
        )
    resuming = is_resume(spec, spec_dir.name, repo, metrics)
    if not resuming and metrics.parse_status(spec.read_text(encoding="utf-8")) != "implemented":
        raise StopError(1, "preconditions", "the spec status is not `implemented`")
    if command(["git", "status", "--porcelain"], repo).stdout.strip():
        raise StopError(1, "preconditions", "the working tree is not clean")
    view = command(["gh", "pr", "view", "--json", "number,state,url,headRefOid"], repo)
    pr = None
    if view.returncode == 0:
        try:
            pr = json.loads(view.stdout)
        except ValueError:
            pr = None
    if not isinstance(pr, dict) or pr.get("state") != "OPEN":
        raise StopError(1, "preconditions", f"no open pull request for `{branch}`")
    raise StopError(1, "close", "the close steps after the preconditions are not built yet")


def is_resume(spec: Path, name: str, repo: Path, metrics) -> bool:
    if metrics.parse_status(spec.read_text(encoding="utf-8")) != "done":
        return False
    match = re.fullmatch(r"(\d+)-(.+)", name)
    if not match:
        return False
    subject = command(["git", "log", "-1", "--format=%s", "--", str(spec)], repo).stdout.strip()
    return subject == f"docs: close SPEC {match.group(1)} {match.group(2)}"
