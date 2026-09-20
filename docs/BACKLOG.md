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
| Evals | `init-question-cap` never gets its `pyproject.toml`: `scaffold_script` does not run, so the case cannot measure the question cap it exists for | The next change to the eval suite, or a `claude` release that documents the scaffold schema | Diagnosed 2026-09-20 with a throwaway probe plugin and a `file_exists` grader: with `--scaffold` passed and the CLI printing "runs each case's scaffold_script", the marker file appears nowhere — not in the agent's workspace (`sealed/home/cwd` under `--keep-temp`), not in the invoking cwd. The key is silently ignored both at the top level of `case.yaml` and under `execution:` (a wrong-typed value raises no validation error in either place), and `claude plugin validate --strict` does not look at eval case files at all. The case's own step 0 makes it fail loudly rather than silently mis-measure, so it is safe to leave red. Closing this needs the real schema, not another guess — each full-case attempt costs about $0.24 |
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
