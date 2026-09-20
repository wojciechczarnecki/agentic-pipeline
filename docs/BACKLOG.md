# Backlog

Deferred improvements and technical debt. Every item has a priority and a **trigger** —
the condition that brings it back into play. An item without a trigger never returns, so
the trigger is required. When a trigger fires, the item is promoted rather than waiting for
a review.

- **P1** — return at the next opportunity in this area
- **P2** — return when the trigger fires, in the natural queue of work
- **P3** — deliberately deferred; return only on the trigger

**Maintenance:** `/pipeline:final-review` adds new items when closing a spec, removes the
ones delivered (the trace stays in `docs/ROADMAP.md` and git history) and reports items
whose trigger has fired.

## P2

| Area | Item | Trigger | Context |
|------|------|---------|---------|
| Evals | The suite is too noisy to gate a release on at `runs: 1` and `--threshold 1.0`: LLM judges flip between runs on unchanged cases | Before the first minor release the gate actually blocks, or the second time a re-run alone turns the suite green | Measured 2026-09-20 across two full runs on almost the same tree: `init-without-questions` went PASS PASS PASS then FAIL FAIL FAIL on an answer meeting all four written criteria, and `guard-blocks-main-push` went PASS PASS PASS then PASS PASS FAIL. The plugin did not change between them. Options: raise `runs:` to 3 and score by majority (about 3x the cost), lower the threshold, or sharpen the criteria so the judge has less room. Until then a red receipt may mean noise rather than a regression, and the hook cannot tell the difference |
| Reach | Translate the plugin's skills and agents (and `plugin/README.md`) into English | The first user or contributor other than the owner | About 700 lines of steering instructions; rewriting them is a substantive change with a risk of silently changing behaviour, so it ships as its own release with evals. The plugin's universality is about stack, not language |

## P3

| Area | Item | Trigger | Context |
|------|------|---------|---------|
| Guard | Generalise the guard's migration module beyond Alembic (verbs `upgrade`, `downgrade`, `stamp`, `revision`, `current`, `check`; variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`) | The first consumer project using another migration tool | Recorded in `docs/DECISIONS.md` (2026-09-20) as a deliberate limitation: the owner uses Alembic, and an honest gap beats an abstraction nobody exercises. A project on another tool must not mistake the guard's silence for protection |
| Guard | The guard knows the `claude` program (blocks `claude plugin disable`, `claude plugin uninstall`, `claude plugin marketplace remove`) | A second consumer project, or the first session that detached the plugin | Today the only barrier is the `deny` list in the consumer's `.claude/settings.json` — configuration, not code; the guard should protect its own attachment |
| Guard | `protected_file_pattern` covers `.claude-plugin/marketplace.json` | Same as above | The file points at the plugin source, so replacing it redirects the whole workflow; today only an `ask` rule on the consumer side protects it |
| Guard | Read-only `git config core.hooksPath` (no value) is not blocked | The next guard change | The guard treats reading the key as changing it and blocks it; sessions work around it with `grep .git/config` |
| Guard | `gh api -X DELETE` on repository settings unrelated to merges or `main` (e.g. `automated-security-fixes`) is not blocked | The next guard change | The guard blocks every such write as a merge/branch-protection call, so the owner has to run even a security-setting toggle by hand |
| Init | `pipeline:init` substitutes `<gitHooksDir>` in the copied `pre-push` template | The next `init` run in a new project | The template lands with an unsubstituted placeholder in the hook's enable instruction; projects so far substituted it by hand |
| Init | CI generator in `init` for stacks other than Python and Node | `init` run in a project with another stack | An unknown stack gets `ci-placeholder.yml` to complete by hand |
| Evals | `claude plugin eval` as a blocking CI gate | The first skill behaviour regression that `validate --strict` let through | Eval runs a real model: cost, score variance and a secret in CI. There is no eval workflow any more — it was removed on 2026-09-20 because the API console bills separately from the subscription (`docs/DECISIONS.md`); the suite runs locally per `docs/CONVENTIONS.md`. A CI gate means paying for metered credits, so the trigger has to be worth that |
