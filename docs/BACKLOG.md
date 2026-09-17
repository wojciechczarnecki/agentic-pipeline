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
| Init | `pipeline:init` substitutes `<gitHooksDir>` in the copied `pre-push` template | The next `init` run in a new project | The template lands with an unsubstituted placeholder in the hook's enable instruction; projects so far substituted it by hand |
| Init | CI generator in `init` for stacks other than Python and Node | `init` run in a project with another stack | An unknown stack gets `ci-placeholder.yml` to complete by hand |
| Evals | `claude plugin eval` as a blocking CI gate | The first skill behaviour regression that `validate --strict` let through | Eval runs a real model: cost, score variance and a secret in CI; today it lives in the manual `plugin-eval` workflow |
| Releases | Version pinning of the `pipeline` plugin in consumer projects, and keeping a consumer's pinned test version in step with the release its marketplace installs | A second consumer project, or the first drift between the two that broke a consumer | With one consumer pinning costs more than it gives; semver and `claude plugin tag` give a way back after a bad change. A consumer that tests its configuration against a pinned release (a version file bumped by PR) while the marketplace follows the latest release can drift after a new release — whether to check that automatically belongs here |
