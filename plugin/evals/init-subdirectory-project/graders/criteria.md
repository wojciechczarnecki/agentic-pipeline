---
type: llm
weight: 1
---

The repository holds one Python project, in `backend/`, that declares `ruff` and `pytest` as
dev dependencies and has no test file. The response is correct when the agent finishes
without asking a question, and the files it shows say `backend` consistently:

1. `.github/workflows/ci.yml` has a job named `backend` (not `python`) with
   `defaults.run.working-directory: backend`, and because the layer has no tests yet the job
   is a placeholder: a checkout and one step that passes (an `echo`), with the real steps
   (`uv sync`, `ruff`, `pytest`) kept as comments or otherwise not run;
2. `.github/dependabot.yml` has the `uv` entry with `directory: /backend`;
3. `verify.command` runs the layer's checks in `backend` (for example `cd backend && uv run
   ruff check . && ...`);
4. every `format` entry matches `backend/` files (for example `backend/*.py`) and runs its
   tool for that project (`uv run --project backend ...`);
5. the commands block of `CLAUDE.md` and the verification line of `docs/CONVENTIONS.md`
   carry the same command as `verify.command`;
6. the first lines of `scripts/git-hooks/pre-push` show the configured hooks directory, with
   no literal `<gitHooksDir>` left;
7. the closing list names the placeholder job as a `TODO:` to replace once `backend` has
   tests.

The response is incorrect when the CI job is named `python:` or anything but `backend`, the
Dependabot `uv` entry has `directory: /`, the job runs a real `pytest` step on a layer that
has no tests (so CI would fail on the first run), `backend` is missing from the verify
command or the format entries, `verify.command` differs from the commands in `CLAUDE.md` or
`docs/CONVENTIONS.md`, a `<gitHooksDir>` is left in the hook, or the agent stops on a question
instead of finishing.

The eval run blocks writes in `.claude/` regardless of the permission rules, so the absence
of `.claude/settings.json` and `.claude/workflow.json` is a limitation of the environment,
and NOT a behaviour of the skill. Naming them with the content to paste satisfies the points
about `verify.command` and `format` in full, and the response may not be judged incorrect for
that reason.
