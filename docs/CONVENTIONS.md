# Development conventions

Binding conventions for code and process. The iron rules are summarised in CLAUDE.md;
this document holds the details.

## Language

- Project documents (`docs/`, `specs/`, `CLAUDE.md`, root `README.md`) follow
  `language: "en"` in `.claude/workflow.json`; code, identifiers, comments and commit
  messages are English regardless of it.
- Plugin skills, agents and `plugin/README.md` are in Polish until translated
  (`docs/BACKLOG.md`); a translation is a behaviour change and ships as a release.
- No mixing of languages within one document.

## Code style

- Line length: 100.
- Formatting and lint: `uv run black` and `uv run ruff check --fix` (the same commands as
  `format[]` in `.claude/workflow.json`); ruff rules `E, F, I, B, N`, target Python 3.12.
- No docstrings; self-documenting code.
- Comments only where the code cannot express a constraint.
- Runtime code (`plugin/hooks`, `plugin/bin`) imports only the standard library.

## User-facing text

Messages printed by hooks and `bin/` scripts are English and name the rule that fired
and the way out (for the guard: which configuration or approval unlocks the action).

## Tests

- `plugin/tests` (pytest), run by `uv run pytest`; hooks and scripts are exercised as
  subprocesses on plain `python3` where their contract is the command line.
- Test mechanisms, not the prose of skills: structure, frontmatter, templates, the guard's
  verdicts, configuration handling.
- Write tests BEFORE or TOGETHER with the implementation.
- Cover key paths and edge cases; assertions check content where content matters.
- Full verification in one command: `bash scripts/check.sh`.
- `claude plugin eval` runs a real model, costs money and is run locally on demand — there
  is no CI workflow for it (`docs/DECISIONS.md`, 2026-09-20). The whole suite:

  ```bash
  claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit \
    --trust-plugin --no-publish
  ```

  `--allow-tools` is not implied by `--trust-plugin` and every case declares `Bash`; the
  guard case tests a `PreToolUse:Bash` hook, so without the grant it would score the
  model's own reluctance instead of the hook — and still pass. A granted shell tool also
  needs a sandbox backend (`bubblewrap` and `socat` on Linux): without it every run is
  refused at `turns: 0`, yet the LLM grader still votes FAIL on the empty transcript and
  bills for it, so the suite reads as a broken plugin. Add `--case <name>` to run one
  case and `--max-cost-usd <n>` for a ceiling.

## Commits and branches

- Commit types: `feat` / `fix` / `test` / `docs` / `refactor` / `chore` / `ci`.
- Imperative mood (`add`, `fix`, `harden`).
- One branch per task: `feat/NNN-<slug>`, `fix/...`, `chore/...`, `docs/...`.
- PRs to `main` are **squash** merged; CI must be green before merge.
- The PR title becomes the commit message after the squash, so it follows the commit rules:
  a type prefix and imperative mood (`chore: add the project scaffold`).
- Agent commits: after every green step, only the files of that step.
- Updating a branch: `git merge origin/main`, not rebase.

## Releases

- Semantic versioning in `plugin/.claude-plugin/plugin.json`; the version grows with
  behaviour (skills, agents, hooks, guard, templates), not with docs or tests.
- Every release has a `plugin/CHANGELOG.md` section.
- The owner tags a clean `main` with `claude plugin tag plugin --push` (`pipeline--vX.Y.Z`).
- The owner, or an agent, then moves the release channel to the new tag:
  `git push origin 'pipeline--vX.Y.Z^{commit}:refs/heads/stable'`. The `^{commit}` is
  required: release tags are annotated, and a branch cannot point at a tag object — the
  bare tag name is rejected with `failed to update ref`. Consumers follow `stable`, not
  the tag, so a release is not out until this push.
- A **minor or major** tag needs a green eval receipt for the commit being tagged: run
  `bash scripts/eval.sh`, which writes `plugin/evals/last-run.json` and is committed with
  the release. The receipt fingerprints what `plugin/` contains rather than naming a
  commit, because it ships inside the release it certifies and a squash merge would
  invalidate any sha it named. The `pre-push` hook refuses the tag without it. Patches are exempt — a full
  suite costs real money and a patch is usually a hook or a documentation fix. The hook is
  the only layer that can enforce this: the `release tags` ruleset has no `creation` rule,
  so the server accepts a new tag from anyone who can push.

## Parallel work

Each lane gets its own branch and working directory (git worktree) in `worktree.dir`.
The agent takes the first spec number free across the specs directory, branch names and
worktrees.

## Workflow metrics

Every spec carries a flat `metrics:` block in its SPEC.md frontmatter, filled in by the
pipeline stages. Keys, the report and the `--check` gate: `plugin/README.md` → metrics
section. The script is called by name through `PATH` (`workflow_metrics.py --check
<spec-dir>`): Claude Code appends an enabled plugin's `bin/` to the session's `PATH`, in
consumers too. Never through `${CLAUDE_PLUGIN_ROOT}` — skill text gets it substituted, but
permission rules do not, so the absolute path never matches an `allow` rule and a stage
subagent, which cannot answer the prompt, stalls. The allow rule is
`Bash(workflow_metrics.py *)`.

## Dependencies

- Dev tools only, pinned exactly in `pyproject.toml` (`[dependency-groups] dev`) with
  `uv.lock` committed; the plugin has no runtime dependencies.
- Dependabot: monthly grouped minor/patch updates for uv and GitHub Actions; major
  versions are upgraded deliberately as their own task.
