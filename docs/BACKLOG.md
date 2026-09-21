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
| Idea | Wider ambiguity taxonomy in `idea` step 2: data volume and scale, performance, concurrent edits, observability, terminology drift, and "an adjective without a number is a gap" | The first final-review blocker traced to a question `idea` never asked | Spec Kit's `clarify` scans about ten categories; ours covers goals, scope, collisions, edge cases, roles, validation, texts, migrations, legal and testability. A few lines in the skill, deferred on 2026-09-21 to keep the Stage 6 spec small |
| Docs | Targeted reading needs findable decisions: an index at the top of `DECISIONS.md` in `templates/docs/`, and guidance on archiving superseded rows | The first finding that a stage broke a decision it did not read, after Stage 7 ships targeted reading | Search by topic misses a decision named in other words. The consumer's `DECISIONS.md` is 97 KB, which is why reading it whole in every stage was expensive in the first place |

## P3

| Area | Item | Trigger | Context |
|------|------|---------|---------|
| Spec | Acceptance criteria carry a priority (P1 = the smallest shippable slice), so an exhausted loop can escalate with "ship P1, the rest to the backlog" instead of only STOP | The first escalation where shipping part of a spec would have been the right answer | Spec Kit's user stories are prioritised and independently testable; our acceptance criteria are a flat list. Deferred on 2026-09-21 |
| Workflow | `/pipeline:fix` — the fast path from `CLAUDE.md` as a skill for bugs: root cause, fix, proof on the original symptom | The first bug that went through the fast path and came back, or the third bug that went through the full pipeline | Spec Kit ships a bug extension (`bug-assess` → `bug-fix` → `bug-test`); the fast path is prose in each consumer's `CLAUDE.md` today. Chosen over spec size tiers on 2026-09-21 as the simpler option, then deferred |
| Models | The final review's spec-compliance and tests perspectives on Sonnet | The Stage 7 comparison shows the implementer on Sonnet keeps quality | Those perspectives are checklist-like, but short, so the saving is small; deliberately left on the session model on 2026-09-21 |
| Guard | Generalise the guard's migration module beyond Alembic (verbs `upgrade`, `downgrade`, `stamp`, `revision`, `current`, `check`; variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`) | The first consumer project using another migration tool | Recorded in `docs/DECISIONS.md` (2026-09-20) as a deliberate limitation: the owner uses Alembic, and an honest gap beats an abstraction nobody exercises. A project on another tool must not mistake the guard's silence for protection |
| Guard | `protected_file_pattern` covers `.claude-plugin/marketplace.json` | The first consumer that hosts its own marketplace, or a session that edited the file from the shell | The file points at the plugin source, so replacing it redirects the whole workflow; today only an `ask` rule on the consumer side protects it. It matters only in repositories that are marketplaces, which is why it stayed out of Stage 5 |
| Guard | `gh api -X DELETE` matches an owner keyword (`releases`, `keys`, `hooks`, `secrets`, `protection` …) only at its structural position after `repos/<o>/<r>/`, `actions/`, `orgs/<o>/` or `user/`, not in any path segment | The first false refusal met in a session, e.g. removing a label or deleting a branch-scoped resource named like a keyword | 0.3.3 narrowed the rule from every DELETE to the owner's ground by segment name; `repos/o/r/issues/1/labels/releases` is refused as "deleting releases". A false refusal fails safe and is rare, so positional matching was deferred on 2026-09-21 |
| Guard | Commands the guard cannot see in a command string: scripts written to files and then run, interpreters (`python3 -c`, `node -e`), shell functions defined in earlier calls, and git configuration channels it does not parse (`--config-env`, `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_GLOBAL`, `include.path`/`includeIf`), an alias already present in a configuration file, and shell constructs it does not model (a brace group in a pipeline, `coproc`, arithmetic assignments) | The first session seen reaching a guarded action through one of them | Documented as known limits in `plugin/docs/GUARD.md` (SPEC 002); the guard is best effort, not a sandbox, and on `main` the `pre-push` hook and the rulesets stand behind it. Closing them means analysing file contents or process behaviour, not command strings |
| Init | `pipeline:init` substitutes `<gitHooksDir>` in the copied `pre-push` template | The next `init` run in a new project | The template lands with an unsubstituted placeholder in the hook's enable instruction; projects so far substituted it by hand |
| Init | CI generator in `init` for stacks other than Python and Node | `init` run in a project with another stack | An unknown stack gets `ci-placeholder.yml` to complete by hand |
| Evals | `claude plugin eval` as a blocking CI gate | The first skill behaviour regression that `validate --strict` let through | Eval runs a real model: cost, score variance and a secret in CI. There is no eval workflow any more — it was removed on 2026-09-20 because the API console bills separately from the subscription (`docs/DECISIONS.md`); the suite runs locally per `docs/CONVENTIONS.md`. A CI gate means paying for metered credits, so the trigger has to be worth that |
| Reach | Listing in plugin catalogues (claudemarketplaces.com, awesome-claude-plugins lists) | Stage 4 is done | Visibility is the only lever left once the storefront is in place (the write-up is scheduled in Stage 7); `docs/PROJECT.md` lists catalogues as out of scope "for now", so this also needs that line changed |
