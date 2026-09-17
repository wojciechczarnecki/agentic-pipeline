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
| Reach | Translate the plugin's skills and agents (and `plugin/README.md`) into English | The first user or contributor other than the owner | About 700 lines of steering instructions; rewriting them is a substantive change with a risk of silently changing behaviour, so it ships as its own release with evals. The plugin's universality is about stack, not language |

## P3

| Area | Item | Trigger | Context |
|------|------|---------|---------|
| Guard | The guard knows the `claude` program (blocks `claude plugin disable`, `claude plugin uninstall`, `claude plugin marketplace remove`) | A second consumer project, or the first session that detached the plugin | Today the only barrier is the `deny` list in the consumer's `.claude/settings.json` — configuration, not code; the guard should protect its own attachment |
| Guard | `protected_file_pattern` covers `.claude-plugin/marketplace.json` | Same as above | The file points at the plugin source, so replacing it redirects the whole workflow; today only an `ask` rule on the consumer side protects it |
| Guard | Read-only `git config core.hooksPath` (no value) is not blocked | The next guard change | The guard treats reading the key as changing it and blocks it; sessions work around it with `grep .git/config` |
| Guard | `gh api -X DELETE` on repository settings unrelated to merges or `main` (e.g. `automated-security-fixes`) is not blocked | The next guard change | The guard blocks every such write as a merge/branch-protection call, so the owner has to run even a security-setting toggle by hand |
| Init | Cover the cap on `init`'s first question round (one round, at most 4 questions) with a grader in `plugin/evals` | The next change to the `init` skill, or its translation | The assertion that covered it read the skill's Polish prose and was dropped with the other prose assertions; `init-without-questions` grades the non-interactive path only, so a rewrite that asks six questions in three rounds now passes CI |
| Init | `pipeline:init` substitutes `<gitHooksDir>` in the copied `pre-push` template | The next `init` run in a new project | The template lands with an unsubstituted placeholder in the hook's enable instruction; projects so far substituted it by hand |
| Init | CI generator in `init` for stacks other than Python and Node | `init` run in a project with another stack | An unknown stack gets `ci-placeholder.yml` to complete by hand |
| Evals | `claude plugin eval` as a blocking CI gate | The first skill behaviour regression that `validate --strict` let through | Eval runs a real model: cost, score variance and a secret in CI; today it lives in the manual `plugin-eval` workflow |
| Releases | Document release pinning for consumers: `"ref": "pipeline--vX.Y.Z"` in the marketplace source in `plugin/README.md`, `plugin/templates/settings.json` and `pipeline:init` | A second consumer project, or the next release | Without `ref` a consumer installs `main`, so every merge here changes skills and the guard in its next session. The first consumer already pins the marketplace to the release tag and checks it against its version file in a test; the plugin's own install instructions still show the unpinned source |
