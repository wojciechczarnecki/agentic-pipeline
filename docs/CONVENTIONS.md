# Development conventions

Binding conventions for code and process. The iron rules are summarised in CLAUDE.md;
this document holds the details.

## Language

- Project documents (`docs/`, `specs/`, `CLAUDE.md`, root `README.md`) follow
  `language: "en"` in `.claude/workflow.json`; code, identifiers, comments and commit
  messages are English regardless of it.
- `plugin/README.md`, `plugin/docs/` and `plugin/CHANGELOG.md` are in English; they quote
  the Polish literals the skills produce (such as `## Decyzje właściciela`) verbatim in
  code spans.
- Plugin skills and agents are in Polish until translated in 0.6.0 (`docs/ROADMAP.md`,
  Stage 8); a translation is a behaviour change and ships as a release. Templates exist per
  language (`*.en.md`, `*.pl.md` — SPEC, PLAN and the `init` documents), and the Polish ones
  survive 0.6.0.
- Commit messages, PR titles and branch names are English for every consumer, whatever its
  `language` — a plugin rule since 0.5.0 (`plugin/README.md`, language contract).
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
- Repository rules and repository documents (root `README.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, cross-document links) are tested in the root `tests/`; `plugin/tests`
  holds only what ships with the plugin and runs from a bare `plugin/` checkout.
  `bash scripts/check.sh` and CI run both.
- Test mechanisms, not the prose of skills: structure, frontmatter, templates, the guard's
  verdicts, configuration handling.
- Write tests BEFORE or TOGETHER with the implementation.
- Cover key paths and edge cases; assertions check content where content matters.
- Full verification in one command: `bash scripts/check.sh`.
- `claude plugin eval` runs a real model, costs money and is run locally on demand — there
  is no CI workflow for it (`docs/DECISIONS.md`, 2026-09-20). The whole suite, with the
  receipt a release needs: `bash scripts/eval.sh`, which runs

  ```bash
  claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit \
    --trust-plugin --no-publish --ablation none
  ```

  `--allow-tools` is not implied by `--trust-plugin` and every case declares `Bash`; the
  guard case tests a `PreToolUse:Bash` hook, so without the grant it would score the
  model's own reluctance instead of the hook — and still pass. A granted shell tool also
  needs a sandbox backend (`bubblewrap` and `socat` on Linux): without it every run is
  refused at `turns: 0`, yet the LLM grader still votes FAIL on the empty transcript and
  bills for it, so the suite reads as a broken plugin. Add `--case <name>` to run one
  case and `--max-cost-usd <n>` for a ceiling. The receipt (`scripts/eval_receipt.py`)
  counts a case with several runs as passed when a majority of them passed (2 of 3), not
  by the CLI's own aggregate, and records the model the suite ran on.
- Eval cost policy (measured in SPEC 004, `docs/DECISIONS.md`, 2026-09-22): a new case, and
  an existing one that fails in any run, is measured with 5 runs on the default model; it
  keeps `runs: 1` at 5 of 5, gets `runs: 3` at 4 of 5, and below that gets sharper
  criteria or a new fixture — it is not shipped. Drafting a case may run on
  `--model sonnet`; measurements and receipts run only on the default model, because
  consumers work on the session model, and `pre-push` refuses a receipt made with
  `--model`. Every eval call carries `--max-cost-usd`: the ceiling is checked before each
  run launches, so it bounds the number of runs, not the cost of one, and a run that
  breaches it has its grader skipped — paid for, with no verdict.
- New eval cases are proven deterministic first: `plugin/tests/test_eval_cases.py` runs
  every `scaffold.sh` and checks that the fixture is what the case claims (the suite red
  where the case needs it red, the metrics check green), and a new case names its wrong
  behaviour explicitly in the grader's "incorrect" paragraph. The grader judges the run's
  last message, so criteria ask for what a final message shows.

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
- A **minor or major** release gets a canary before the tag — a mandatory step, though no
  mechanism enforces it (nothing can check that a plugin was used in another repository);
  patches are exempt, as for the eval receipt. On the clean `main` about to be tagged, the
  owner opens a session in a consumer project with the unreleased plugin beside the
  `--scope user` install and runs a real stage in it:

  ```bash
  claude --plugin-dir <clone>/plugin plugin list   # pipeline@inline, the new version
  cd <consumer> && claude --plugin-dir <clone>/plugin --debug-file /tmp/canary.log
  grep -E 'overrides installed version|Found [0-9]+ plugins' /tmp/canary.log
  ```

  The clone is not the install cache, so the consumer's `Read` rule for the cache does
  not cover the templates the stages read from it: add the absolute clone rule
  `Read(//<clone without its leading />/plugin/**)` to the consumer's settings (or user
  settings) for the canary — a headless canary run through `--settings` needs it in that
  file too — or the first stage stops on the read. The guard's notice names the exact rule.
  `--plugin-dir` overrides the installed copy for that session only. The pass marker is
  the log line `Plugin "pipeline" from --plugin-dir overrides installed version`, skills
  loaded from `<clone>/plugin`, and a `Found N plugins` count equal to a plain session's
  in the same consumer — the count covers every enabled plugin, so it is 1 only where
  `pipeline` is the sole one. `plugin list` shows the copy as `pipeline@inline` with the
  new version beside the installed one. Inside the session, confirm that a stage resolves
  `bin/` from the unreleased copy (`command -v workflow_metrics.py` points into
  `<clone>/plugin/bin`, and no other `pipeline` entry sits on `$PATH`): the sandbox
  measurement could not authenticate a session, so the first canary (0.4.0) is where this
  is first observed. The install, the marketplace registration and `stable` stay
  untouched (measured 2026-09-22 in a sandbox, `docs/DECISIONS.md`). The way back is a
  session without `--plugin-dir`. A canary that misbehaves stops the release: fix,
  merge, canary again.
  An agent may run the canary for the owner, headless, in a throwaway clone of the
  consumer with no remote (commits stay in the clone). Two traps, measured on the 0.5.0
  canary (2026-09-23): a `claude` started from inside another Claude Code session
  inherits that session's `PATH`, including the `bin/` of the plugin it loaded, so
  `command -v workflow_metrics.py` points at the installed copy until the plugin cache
  entries are stripped from `PATH` (`env PATH=<filtered> claude …`); and `claude -p`
  refuses file edits nobody can approve, so the stage needs
  `--permission-mode acceptEdits` and the consumer's rules through
  `--settings <consumer>/.claude/settings.json` (an untrusted clone ignores its own).
- The owner tags a clean `main` with `claude plugin tag plugin --push` (`pipeline--vX.Y.Z`).
- The owner — never an agent — then moves the release channel to the new tag:
  `git push origin 'pipeline--vX.Y.Z^{commit}:refs/heads/stable'`. The `^{commit}` is
  required: release tags are annotated, and a branch cannot point at a tag object — the
  bare tag name is rejected with `failed to update ref`. Consumers follow `stable`, not
  the tag, so a release is not out until this push. The channel feeds every project
  with a `--scope user` install and the `stable` ruleset lets the owner's credentials
  push it to any commit, so an agent is kept off it by the guard (`protectedBranches` in
  `.claude/workflow.json`), like tagging by agreement; the same guard keeps agents from
  detaching the plugin (`claude plugin disable|uninstall` or removing its marketplace).
- The owner then publishes the GitHub Release on the tag, with the matching
  `plugin/CHANGELOG.md` section (its body, without the heading) as the notes:

  ```bash
  awk -v v=X.Y.Z '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md \
    | gh release create pipeline--vX.Y.Z --verify-tag --title 'pipeline X.Y.Z' --notes-file -
  ```

  `--verify-tag` aborts when the tag is not on the remote, so the command never creates a
  tag.
- A **minor or major** tag needs a green eval receipt for the commit being tagged: run
  `bash scripts/eval.sh`, which writes `plugin/evals/last-run.json` and is committed with
  the release. The receipt fingerprints what `plugin/` contains rather than naming a
  commit, because it ships inside the release it certifies and a squash merge would
  invalidate any sha it named. The `pre-push` hook refuses the tag without it, and
  refuses a receipt that does not record its model, was produced with `--model`, or ran a
  case fewer times than its `case.yaml` asks (a `--runs` override); the receipt counts a
  run the cost ceiling never started as failed and is not green on a partial result.
  Patches are exempt — a full suite costs real money and a patch is usually a hook or a
  documentation fix. The hook is the only layer that can enforce this: the `release tags`
  ruleset has no `creation` rule, so the server accepts a new tag from anyone who can
  push.

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
