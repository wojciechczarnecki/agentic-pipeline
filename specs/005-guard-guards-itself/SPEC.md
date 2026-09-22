---
status: implemented
stage_history:
  - "spec-draft — 2026-09-22"
  - "spec-ready — 2026-09-22"
  - "plan-draft — 2026-09-22"
  - "plan-approved — 2026-09-22"
  - "implemented — 2026-09-22"
metrics:
  started_at: 2026-09-22T21:12
  escalations: 0
  plan_steps: 11
  plan_review_blockers: 1
  plan_review_majors: 2
  plan_changes: 11
  implement_steps: 11
  implement_iterations: 2
  deviations: 5
  final_review_blockers: 1
  final_review_worth_fixing: 6
  final_review_nits: 7
---

# SPEC 005 — A guard that guards itself and the release channel

## Goal

With a `--scope user` install one plugin guards every project on the machine, yet today an
agent session can switch that guard off with a single command, move the release channel
that feeds every project, or rewrite repository settings through `gh api` — all three
held back only by string `deny` rules that miss the CLI's own aliases, or by nothing at
all. Release 0.4.0 makes the guard refuse these in any consumer that configures it: it
protects configurable release-channel branches like `main`, refuses detaching or
tampering with the plugin itself, and refuses `gh api` writes on the owner's ground. It
works when those commands are refused in a real 0.4.0 session and this repository no
longer needs `deny` rules for them.

## Context

- Stage 5 of `docs/ROADMAP.md` has two open 0.4.0 items (`protectedBranches`, blocking
  plugin detachment); SPEC 004 (merged in #19, e0cc2f7) delivered the eval gate and the
  canary this first minor release has to pass. The `gh api` item comes from
  `docs/BACKLOG.md` (Guard, P3), whose trigger "Stage 5 starting" has fired.
- Guard today (`plugin/bin/guard.py`, 0.3.4): `PROTECTED_BRANCHES = {"main", "master"}`
  hard-coded and used for pushes (`push`), commits/merges/rebases/cherry-picks/reverts/`am`
  and non-`--ff-only` pulls on the current branch, `git branch -d/-D/-m/-M/-f`,
  `git update-ref`/`symbolic-ref`, and the `gh api` write regex `refs/heads/(main|master)`.
  It has no rule for the `claude` program at all.
- Guardrail files today (`protected_file_pattern`): `.claude/settings*.json`,
  `.claude/workflow.json`, and the plugin directory **only when it lies inside the
  project** (`plugin_dir_inside_project`). With a `--scope user` install the plugin lives in
  `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`, so `sed -i`, `mv`, `cp`,
  `tee` or a redirect onto `bin/guard.py`, `hooks/hooks.json`,
  `~/.claude/plugins/installed_plugins.json` or `known_marketplaces.json` passes; `rm` there
  is already refused as a removal outside the project.
- `gh api` today (`check_gh`): `DELETE` is refused on the owner's ground
  (`API_OWNER_DELETIONS`, the repository and organisation themselves, `git/refs`); other
  writes are refused only when the path matches merges, branch protection, rulesets or
  `refs/heads/(main|master)`. `gh api -X PATCH repos/<o>/<r> -f default_branch=…` or
  `-f visibility=…` passes, while `gh repo edit` is refused.
- Claude Code CLI 2.1.280 (`claude plugin --help`, checked 2026-09-22): `claude plugin` has
  the alias `plugins`; `uninstall` has the alias `remove`; `marketplace remove` has the
  alias `rm`; `disable [plugin]` takes the plugin optionally; `update`, `install` and
  `enable` take `--scope user|project|local`. The current `deny` rules in
  `.claude/settings.json` miss `claude plugins uninstall …` and
  `claude plugin marketplace rm …`, and refuse even `claude plugin disable --help`.
- Configuration: `plugin/bin/workflow_config.py` validates `.claude/workflow.json` against
  `SCHEMA`; the guard loads it section by section (`load_sections`), so a key an older
  plugin does not know is dropped with a stderr warning on every Bash call, never a
  failure. `format-file.sh` discards that stderr.
- Pre-push: `scripts/git-hooks/pre-push` and `plugin/templates/pre-push` refuse
  `refs/heads/(main|master)` for everyone, the owner included. The owner's release
  procedure pushes `pipeline--vX.Y.Z^{commit}:refs/heads/stable` directly
  (`docs/CONVENTIONS.md`), so the channel branch is "agents never", not "nobody".
- Release gate: `scripts/eval.sh` writes `plugin/evals/last-run.json`, whose fingerprint
  covers `plugin/`; `pre-push` refuses a `pipeline--vX.Y.0` tag without a matching green
  receipt. The canary (`docs/CONVENTIONS.md`) runs for minor releases; SPEC 004's deviation
  D4 left the 0.4.0 canary to confirm, in a logged-in session, that `bin/` resolves from
  the unreleased copy.

## Read context

- `docs/ROADMAP.md` — Stage 5's two open items are 0.4.0 and this spec delivers both;
  "replacing the `deny` rules on pushes to `stable`" holds, since the owner removes them in
  this PR. Stage 8 (0.5.0/0.6.0) comes next, so the new guard texts are English and no
  skill is touched.
- `docs/PROJECT.md` — the command guard's "protected branches … guardrail files" is the
  functional requirement extended here; the non-functional requirements (plain `python3`,
  no network from hooks, no consumer specifics, semver releases) bind the change.
- `docs/DECISIONS.md` — the 2026-09-17 ruleset row says merging and new release tags rest
  on the guard and `deny` alone (tags stay out, see Out of scope); the 2026-09-21 `stable`
  channel row and the 2026-09-22 canary and eval-gate rows set the release path this spec
  goes through; the 2026-09-21 `GUARD.md` deny-table row sets how a new table row is
  measured.
- `plugin/README.md` — the configuration table gets a `protectedBranches` row, and the
  command guard section names the new rules; mechanics otherwise unchanged.

## Scope

- `protectedBranches` in `.claude/workflow.json`: extra branch names the guard treats
  exactly like `main`/`master`.
- The guard refuses detaching this plugin: `claude plugin|plugins disable`,
  `uninstall|remove` and `marketplace remove|rm`, aimed at this plugin or its marketplace.
- The guard's guardrail files cover the loaded plugin's directory wherever it lies, and the
  plugin install state (`~/.claude/plugins/installed_plugins.json`,
  `known_marketplaces.json`).
- The guard refuses `gh api` writes (`POST`/`PUT`/`PATCH`) on the owner's ground.
- This repository: `protectedBranches: ["stable"]` in `.claude/workflow.json`, and the
  `deny` rules the guard now covers removed from `.claude/settings.json`.
- Documentation: `plugin/docs/GUARD.md`, `plugin/README.md`,
  `plugin/templates/workflow.example.json`, `plugin/docs/INSTALL.md`, `CLAUDE.md`,
  `docs/CONVENTIONS.md`; `docs/DECISIONS.md` rows; `docs/BACKLOG.md` updates;
  `docs/ROADMAP.md` ticks.
- Release readiness for 0.4.0: version bump, `plugin/CHANGELOG.md`, a green eval receipt
  for the final `plugin/` tree.

## Out of scope

- The `pre-push` hook and `/pipeline:init` reading `protectedBranches` — the hook binds the
  owner too, who moves `stable` by a direct push; `init` does not ask about or write the
  key. No backlog item: this is the design, recorded in `docs/DECISIONS.md`.
- Branch patterns in `protectedBranches` (`release/*`) — `docs/BACKLOG.md` P3, trigger: the
  first consumer with more than one release-channel branch or a pattern-named one.
- Protecting release tags (`claude plugin tag --push`, `git push origin pipeline--vX.Y.Z`)
  — `docs/BACKLOG.md` P3, trigger: the first release tag pushed by an agent session.
  Consumers' tags are their own, so it needs its own configuration key.
- `claude plugin enable|install --scope project` creating a stale project-scope duplicate
  (the `enabledPlugins` trap in `plugin/docs/INSTALL.md`) — the `deny` rule
  `Bash(claude plugin enable*)` stays in this repository; `docs/BACKLOG.md` P3, trigger:
  the first project-scope duplicate created by an agent session.
- `gh api graphql` mutations (e.g. `updateRepository`) — a known limit in `GUARD.md`;
  `docs/BACKLOG.md` P3, trigger: the first session seen changing repository settings
  through GraphQL.
- A nested session (`claude -p --safe-mode …`, `--dangerously-skip-permissions`) runs
  without this session's hooks — deliberate evasion, documented as a known limit in
  `GUARD.md` beside interpreters; no backlog item beyond the existing Guard P3 row on
  commands the guard cannot see.
- A new eval case — the new rules are deterministic code covered by pytest, the hook wiring
  is proven by `guard-blocks-main-push`, and the real CLI is probed in the canary.
- Tagging, moving `stable`, publishing the GitHub Release and running the canary — the
  owner's steps after merge; this spec states only what has to be ready.

## Requirements and acceptance criteria

Protected branches

- [ ] AC1: `protectedBranches` is an optional top-level key of `.claude/workflow.json`, a
      list of branch names; `workflow_config.py --check` accepts it, and a value that is
      not a list of strings is rejected with the existing validation message while the
      guard falls back to the defaults for that key only.
- [ ] AC2: without the key, or with `[]`, every guard decision is what 0.3.4 decides: the
      existing `plugin/tests/test_guard.py` passes unchanged.
- [ ] AC3: `main` and `master` stay protected whatever the list says — with
      `protectedBranches: ["stable"]`, `git push origin HEAD:main` is still refused.
- [ ] AC4: with `protectedBranches: ["stable"]`, each rule that protects `main` today
      protects `stable`: refused are `git push origin HEAD:stable`,
      `git push origin feat/x:refs/heads/stable`, `git push -u origin stable`,
      `B=stable; git push origin $B`, a bare `git push` while on `stable`,
      `git commit`/`merge`/`rebase` while on `stable`, `git pull` without `--ff-only` on
      `stable`, `git branch -D stable`, `git update-ref refs/heads/stable <sha>`, and
      `gh api -X PATCH repos/o/r/git/refs/heads/stable`; `git push origin feat/x` and
      `git pull --ff-only` on `stable` pass.
- [ ] AC5: a refusal on a configured branch names that branch (e.g. "pushing to stable: …"),
      not `main`.
- [ ] AC6: names match exactly; `stable-next` and `feat/stable` are not protected by
      `["stable"]`.
- [ ] AC7: `scripts/git-hooks/pre-push` and `plugin/templates/pre-push` are unchanged, and
      `/pipeline:init` writes no `protectedBranches`; `templates/workflow.example.json` and
      the `plugin/README.md` configuration table show the key, its default (absent = only
      `main`/`master`) and that it binds agent sessions only.

Detaching the plugin

- [ ] AC8: refused, with a reason saying the plugin's install is the owner's to change:
      `claude plugin disable pipeline@<any-marketplace>`, `claude plugin disable pipeline`,
      `claude plugin disable` with no plugin or with `--all`,
      `claude plugin uninstall pipeline@<m>`, `claude plugins remove pipeline@<m>`, each
      with or without `--scope user|project|local`, and through the guard's usual
      wrappers (`env`, `bash -c`, `eval`, an absolute path to `claude`).
- [ ] AC9: `claude plugin marketplace remove <m>` and `… rm <m>` are refused when `<m>` is a
      marketplace this plugin is installed from (per the install state) or loaded from
      (per the plugin's own directory); a name the guard cannot resolve (a variable,
      unreadable install state) is refused rather than guessed.
- [ ] AC10: these pass: `disable`/`uninstall` of another plugin, `marketplace remove` of a
      marketplace this plugin does not come from, `claude plugin list`, `details`,
      `validate`, `eval`, `update`, `install`, `enable`, `marketplace add|list|update`, and
      any of the refused commands with `--help` or `-h`.

Guarding its own files

- [ ] AC11: shell writes (`sed -i`, `perl -i`, `tee`, `mv`, `cp`, `truncate`, `chmod`,
      `ln`, a `>`/`>>` redirect, `git checkout`/`restore` onto it) to any file under the
      directory the running guard was loaded from are refused with the guardrail-files
      reason, wherever that directory lies (plugin cache, `--plugin-dir` clone, inside the
      project); reading (`cat`, `grep`) passes. With a `--plugin-dir` session this also
      refuses shell edits of the clone's `plugin/`.
- [ ] AC12: the same shell writes to `~/.claude/plugins/installed_plugins.json` and
      `~/.claude/plugins/known_marketplaces.json` are refused; reading passes.

`gh api` writes

- [ ] AC13: refused: `gh api -X PATCH repos/o/r -f default_branch=x`,
      `gh api -X PATCH repos/o/r -f visibility=public`, `gh api -X PUT repos/o/r/topics`,
      `gh api -X POST repos/o/r/transfer`, `gh api -f name=x repos/o/r` (implicit `POST`),
      and `POST`/`PUT`/`PATCH` on secrets, variables, environments, webhooks, keys,
      collaborators and invitations, Pages, security settings, `actions/permissions`,
      rulesets and branch protection, for `repos/<o>/<r>`, `repositories/<id>` and
      `orgs/<o>` (teams and members included).
- [ ] AC14: these pass: every `GET`,
      `gh api -X POST repos/o/r/actions/runs/1/rerun`, comments, labels, issues, pulls,
      releases and deployments writes, e.g.
      `gh api -X POST repos/o/r/issues/1/comments -f body=x` and
      `gh api -X PATCH repos/o/r/pulls/1 -f title=x`.
- [ ] AC15: a write whose endpoint is built from a variable or command substitution is
      refused, as for `DELETE`.

Documentation and this repository

- [ ] AC16: `plugin/docs/GUARD.md` lists the new rules in *The command guard*, drops the
      two known limits this spec closes ("Only `main` and `master` …", detaching left to
      `deny`), adds the known limits for `gh api graphql` and nested `claude` sessions,
      and no longer names `claude plugin uninstall` or a release-channel push as `deny`
      territory.
- [ ] AC17: the *Deny rules versus the guard* table gains rows for
      `claude plugins uninstall pipeline@<m>` (against `Bash(claude plugin uninstall*)`)
      and `claude plugin marketplace rm <m>` (against
      `Bash(claude plugin marketplace remove*)`), each measured by the method of the
      2026-09-21 decision row, with an isolated `CLAUDE_CONFIG_DIR`, before it is added;
      a candidate the rule does catch is left out, and the test that runs every row
      through the guard stays green.
- [ ] AC18: `plugin/docs/INSTALL.md` says that the uninstall, disable and
      `marketplace remove` commands it shows are refused inside an agent session and are
      run by the owner in a terminal.
- [ ] AC19: `.claude/workflow.json` holds `"protectedBranches": ["stable"]`;
      `.claude/settings.json` no longer holds the seven `git push … stable` rules or
      `claude plugin disable*`, `uninstall*`, `remove*`, `marketplace remove*`, and still
      holds `Bash(gh pr merge*)` and `Bash(claude plugin enable*)`. These two edits are the
      last implementation step, to shorten the window in which sessions on 0.3.4 have
      neither the rules nor the guard.
- [ ] AC20: `CLAUDE.md` (Git section) and `docs/CONVENTIONS.md` (release bullet) say the
      guard keeps agents off `stable` through `protectedBranches` and off detaching the
      plugin, instead of `deny` rules.
- [ ] AC21: `docs/DECISIONS.md` gains rows for: `protectedBranches` additive to
      `main`/`master`, exact names, guard-only (why the pre-push hook does not read it);
      detaching refused by target, with `update`/`install`/`enable` passing; the guard's
      own directory and install state as guardrail files; `gh api` writes on the owner's
      ground, with runs, releases and deployments left open.
- [ ] AC22: `docs/BACKLOG.md` loses the `gh api` repository-endpoint row (delivered) and
      gains the P3 rows named in Out of scope; `docs/ROADMAP.md` ticks both Stage 5 0.4.0
      items with a link to this spec.

Release readiness

- [ ] AC23: `plugin/.claude-plugin/plugin.json` reads `0.4.0`; `plugin/CHANGELOG.md` has a
      `## 0.4.0` section stating the consumer impact — agent sessions can no longer
      disable, uninstall or remove the plugin's marketplace, edit the plugin's files or
      install state, or write repository settings through `gh api`, and a consumer adds
      `protectedBranches` to protect a release channel.
- [ ] AC24: `plugin/` stays on the standard library and names no consumer project
      (`plugin/tests/test_no_domain_references.py`); `bash scripts/check.sh` is green.
- [ ] AC25: the PR's last commit is a green receipt from `bash scripts/eval.sh` (full
      suite, default model) whose fingerprint matches the final `plugin/` tree, made after
      the fixes from gate 2; any later change to `plugin/` means running it again.
- [ ] AC26: the PR description lists the owner's 0.4.0 canary checks: the D4 check (inside
      the session `command -v workflow_metrics.py` points into `<clone>/plugin/bin`, no
      other `pipeline` on `$PATH`), the `Found N plugins` count equal to a plain session in
      the same consumer, and refusal probes that do no harm if the guard let them through
      — `claude plugin uninstall pipeline@no-such-marketplace` and, with
      `protectedBranches` set in the consumer,
      `git push --dry-run origin HEAD:<protected branch>`.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---|---|---|
| `protectedBranches` adds to `main`/`master`, which stay protected always; exact names | a full list defaulting to `["main","master"]`; fnmatch patterns now | A consumer writing `["stable"]` must not unprotect `main` by accident; absent key = 0.3.4 behaviour for every consumer; patterns wait for a consumer that needs them |
| Guard only; the `pre-push` hook and `init` do not read the key | `pre-push` reads it with an owner escape hatch; `init` asks for the channel | The hook binds everyone, and the owner moves `stable` with a direct push; a release channel is "agents never", `main` is "nobody" |
| Detaching refused by target: this plugin (any marketplace, no name, `--all`) and its marketplace; unresolved target refused | every plugin-state command refused; `update` refused too | The guard runs in every consumer, where managing other plugins is not its business; `update` only follows the owner's channel |
| The guard's own directory (wherever it lies) and the install-state files become guardrail files | the plugin directory only; CLI commands only | A shell edit of `guard.py` or `installed_plugins.json` detaches the guard as surely as `uninstall` |
| `gh api` writes on the owner's ground refused in 0.4.0, the narrow set | only the repository endpoint; deferring to the backlog | The trigger fired, the eval gate is paid once for 0.4.0 anyway, and `PATCH repos/o/r` can change `default_branch` or `visibility` behind the rulesets; runs (CI re-runs), releases and deployments stay open to agents |
| The `deny` rules for `stable` and detaching are removed in this PR, as its last step | removed after the owner installs 0.4.0, keeping `stable`'s as a second layer | The owner's call: one PR, and a 0.3.4 session only warns about the unknown key; the window until 0.4.0 is installed is accepted |
| No new eval case | a detach case; a release-channel case (~$1–3 each) | Deterministic rules are proven by pytest, the hook wiring by `guard-blocks-main-push`, the real CLI by the canary probes |

## Owner decisions

- No new dependency (runtime or dev) and no data migration; if the plan needs either, it
  escalates. The new key is optional, so existing consumer configurations need no change.
- From merge until 0.4.0 is installed, sessions in this repository run the 0.3.4 guard
  without the removed `deny` rules: nothing local keeps an agent off `stable` or off
  detaching the plugin, and every Bash call prints an "unknown key `protectedBranches`"
  warning. Accepted.
- The agent runs `bash scripts/eval.sh` (about $3.4 of session limit) for the final
  receipt, as the PR's last commit after gate 2.

## Open questions (non-blocking)

- Whether `claude plugin disable` accepts `--all` or another flag that disables every
  plugin, and how `disable` with no plugin behaves in 2.1.280 — `--help` for it is
  refused by this repository's `deny` rules today; the plan checks it (AC8 refuses both
  forms either way).
- Whether the owner's `!`-prefixed shell in Claude Code passes through `PreToolUse` hooks;
  if it does, INSTALL.md's commands need a real terminal, which AC18 already says.
