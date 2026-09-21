---
status: implemented
stage_history:
  - "spec-draft — 2026-09-21"
  - "spec-ready — 2026-09-21"
  - "plan-draft — 2026-09-21"
  - "plan-approved — 2026-09-21"
  - "implemented — 2026-09-21"
metrics:
  started_at: 2026-09-21T21:48
  escalations: 1
  plan_steps: 9
  plan_review_blockers: 0
  plan_review_majors: 2
  plan_changes: 9
  implement_steps: 7
  implement_iterations: 2
  deviations: 1
  final_review_blockers: 0
  final_review_worth_fixing: 5
  final_review_nits: 5
  findings_accepted: 10
  findings_rejected: 0
---

# SPEC 003 — Portfolio storefront

## Goal

A reader who has never seen the project should understand from the root `README.md`, in
under a minute, what it does, how it differs from other spec-driven tools (it enforces
rather than only plans) and whether it fits their setup, and should be able to install it
from a single linked guide. We will know it works when every Stage 4 item is ticked, the
documents' links and quoted guard output are checked by tests, and the repository's GitHub
presentation (About, topics, Releases) matches the new README.

## Context

- Stage 4 of `docs/ROADMAP.md`; follows SPEC 002, which delivered `plugin/docs/GUARD.md`
  and the English `plugin/README.md`.
- Today the root `README.md` is a short developer note (pitch in one sentence, install,
  development, licence). Installation mechanics — the `stable` channel, the `user` scope,
  updates, the one-time migration, the `enabledPlugins` traps — live in the
  `## Installation` section of `plugin/README.md` (lines 11–133) and are asserted by
  `plugin/tests/test_readme.py` (`installation_section()` and the tests that use it).
- `CLAUDE.md` points the owner to `plugin/README.md` → Installation.
- The repository has six release tags (`pipeline--v0.2.0` … `pipeline--v0.3.4`), each with
  a `plugin/CHANGELOG.md` section, and no GitHub Releases. Private vulnerability reporting
  is already enabled on the repository (checked 2026-09-21).
- Naming: the repository slug is `agentic-pipeline`, the plugin is `pipeline`
  (`/pipeline:*`, `pipeline@wcz-tools`, `pipeline--v*`). The owner finds `agentic-pipeline`
  uninformative for an outside reader. A plugin rename would touch 133 `/pipeline:`
  references, the tag prefix and its ruleset, the install id and every consumer; a slug
  rename is cheap (GitHub redirects) but still leaves three names. The display name is
  independent of both.

## Read context

- `docs/ROADMAP.md` — Stage 4 lists eight items; this spec delivers the in-repository ones,
  changes the install guide's path, drops the demo recording, and moves the evidence items
  (public demo repository, consumer metrics) to a new Stage 9 because their material will
  not exist for weeks. "The claim is the command guard and the checked metrics, not
  hook-enforced gates" (SpecForge and gate-oriented-sdd, checked 2026-09-21) binds the
  comparison section.
- `docs/PROJECT.md` — the problem statement and roles feed the pitch and *Requirements &
  opinions*; its title changes to the display name; "Listing in external plugin catalogues
  (for now)" stays out of scope.
- `docs/DECISIONS.md` — the private consumer stays unnamed (2026-09-17); the `stable`
  channel, the `user` scope and `extraKnownMarketplaces`-only declarations (2026-09-21) are
  what the install guide must say; tagging and moving `stable` are the owner's alone, so
  Releases are created on existing tags only; the version grows with behaviour, not docs;
  `plugin/README.md` and `plugin/docs/` are English (2026-09-21); documents nothing checks
  drift, so quoted behaviour is tested (2026-09-21, the `GUARD.md` table).
- `docs/BACKLOG.md` — the P3 *Reach* item (catalogue listing) has the trigger "Stage 4 is
  done"; its trigger moves to Stage 9.
- `docs/CONVENTIONS.md` — project documents in English; the release procedure (tag, move
  `stable`) gains the GitHub Release step.
- `plugin/README.md` — its `## Installation` section moves to the new install guide and
  shrinks to a short install plus a link.

## Scope

- Display name **Spec-Driven Workflow** in document titles and descriptions: root
  `README.md`, `docs/PROJECT.md`, `CLAUDE.md` (project line), the descriptions in
  `.claude-plugin/marketplace.json` and `plugin/.claude-plugin/plugin.json`, and the
  GitHub *About* description. The repository slug stays `agentic-pipeline`; the plugin,
  its commands, install id and tags stay `pipeline`.
- Root `README.md` rewritten for an outside reader: one-line pitch; badges (CI, licence,
  version from `plugin/.claude-plugin/plugin.json`); a mermaid diagram of the pipeline and
  its three owner gates; a real guard refusal shown as a text block; *Why not Spec Kit?*;
  a quickstart; *Requirements & opinions*; *What's deliberately not here*; links to
  `plugin/docs/GUARD.md`, the metrics documentation and the install guide; one sentence
  explaining the three names (display name, repository, plugin).
- `plugin/docs/INSTALL.md`: installation, the `stable` channel, updates, the one-time
  migration, verification, the opt-out and the known traps (scope, `enabledPlugins`,
  commands stripping `.claude/settings.json`), moved out of `plugin/README.md`; both
  READMEs keep a short install and a link.
- `CONTRIBUTING.md` and `SECURITY.md` at the repository root.
- GitHub Releases for the six existing `pipeline--v*` tags, notes taken from the matching
  `plugin/CHANGELOG.md` section; the GitHub Release step added to the release procedure.
- GitHub *About* description and topics set with `gh repo edit` to match the new README.
- Documentation tests: relative links resolve, the guard refusal block matches the guard's
  actual output, and the installation assertions follow the moved content.
- `docs/ROADMAP.md`: Stage 4 items updated and ticked; a new Stage 9 with the deferred
  evidence items; `docs/BACKLOG.md` *Reach* trigger re-pointed; `docs/DECISIONS.md` rows.

## Out of scope

- Renaming the repository slug — not needed for the display name; a slug rename stays
  cheap later (GitHub redirects) and needs no spec of its own beyond URL updates.
- Renaming the plugin — never (owner decision, recorded in `docs/DECISIONS.md`).
- Demo recording (animated terminal capture of the guard and a `/pipeline:ship` run) —
  dropped from the roadmap by the owner; the tested text block replaces the guard part.
- Evidence from the owner's public demo repository and anonymised metrics from the
  private consumer — moved to the new Stage 9 (*Evidence*); material expected in a few
  weeks.
- Pinning the repository on the owner's profile and the social preview image — UI-only
  settings, done by the owner from the list in the final report.
- Listing in plugin catalogues — backlog P3, trigger now Stage 9 done.
- Translating skills, agents or templates — Stage 8.

## Requirements and acceptance criteria

- [ ] AC1: The first heading of the root `README.md` is `Spec-Driven Workflow` (optionally
  followed by a subtitle), and within its first five non-empty lines below the heading it
  states in one sentence what the plugin does for Claude Code.
- [ ] AC2: The root `README.md` shows three badges — CI status of `ci.yml`, the MIT
  licence, and the plugin version read from `plugin/.claude-plugin/plugin.json` on `main`
  (so the badge follows a version bump without an edit).
- [ ] AC3: The root `README.md` contains a ```` ```mermaid ```` block naming every stage
  (`idea`, `plan`, `plan review`, `implement`, `final review`, PR) and the three owner
  gates (SPEC approval, decisions on review findings, merge).
- [ ] AC4: The root `README.md` contains a text block with a command the guard refuses
  (a push to `main`) and the guard's refusal message; a test runs that command through
  `plugin/bin/guard.py` and fails if the message in the block differs from the guard's
  output.
- [ ] AC5: A section titled *Why not Spec Kit?* states that Spec Kit plans and this plugin
  enforces, and that the claim is the command guard and the checked metrics — not
  hook-enforced approval gates, which SpecForge and gate-oriented-sdd also have; every
  statement about another tool carries the date it was checked.
- [ ] AC6: A *Requirements & opinions* section names: GitHub with `gh`, squash merges,
  GitHub rulesets, `python3` on the machine, Alembic-only migration guarding — and says who
  the plugin is for and who it is not for.
- [ ] AC7: A *What's deliberately not here* section lists at least: no runtime
  dependencies, no hosting outside Claude Code, the guard is best effort rather than a
  sandbox (with a link to `plugin/docs/GUARD.md` → Known limits).
- [ ] AC8: The root `README.md` has a quickstart of at most five commands from nothing to
  `/pipeline:idea`, one sentence explaining that the project is *Spec-Driven Workflow*,
  the repository `agentic-pipeline` and the plugin `pipeline`, and links to
  `plugin/docs/INSTALL.md`, `plugin/docs/GUARD.md`, the metrics section of
  `plugin/README.md`, `CONTRIBUTING.md`, `SECURITY.md` and `plugin/CHANGELOG.md`.
- [ ] AC9: `plugin/docs/INSTALL.md` exists and carries everything that was in the
  `## Installation` section of `plugin/README.md` (channel, user scope, project settings
  declaring only the marketplace, the `enabledPlugins` duplicate trap and its removal,
  updating, the one-time migration, verification, the opt-out, `/pipeline:init` and the
  non-interactive note); every assertion `plugin/tests/test_readme.py` made about the
  installation section is made about this file and passes.
- [ ] AC10: The `## Installation` section of `plugin/README.md` and the install section of
  the root `README.md` each have at most three commands and a link to
  `plugin/docs/INSTALL.md`; `CLAUDE.md` points the owner to `plugin/docs/INSTALL.md`
  instead of `plugin/README.md` → Installation.
- [ ] AC11: A test resolves every relative Markdown link (and `#anchor`, where given) in
  the root `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `plugin/README.md`,
  `plugin/docs/INSTALL.md` and `plugin/docs/GUARD.md`, and fails on a missing target.
- [ ] AC12: `CONTRIBUTING.md` covers: how to report a bug or propose a feature (issues),
  the dev setup (`uv sync`, `bash scripts/check.sh`, `core.hooksPath`), a link to
  `docs/CONVENTIONS.md`, that changes go through a PR to `main` with a green `plugin`
  check, and that skills are in Polish until Stage 8.
- [ ] AC13: `SECURITY.md` names the supported version (the release on the `stable`
  channel), directs reports to GitHub private vulnerability reporting (not public issues),
  and states that the guard is best effort and that a guard bypass counts as a security
  report.
- [ ] AC14: `gh release list` shows six releases, one per `pipeline--v*` tag from 0.2.0 to
  0.3.4, each titled with its version, with the body of the matching `plugin/CHANGELOG.md`
  section; `pipeline--v0.3.4` is marked latest; no tag has moved (`git ls-remote --tags`
  shows the same shas before and after). Created only after the owner's approval at gate 2.
- [ ] AC15: The release procedure in `docs/CONVENTIONS.md` and the release commands in
  `CLAUDE.md` include creating the GitHub Release from the `plugin/CHANGELOG.md` section,
  as an owner step after the tag and the `stable` move.
- [ ] AC16: `gh repo view --json description,repositoryTopics` shows a description that
  begins with the display name's one-line pitch and topics that include
  `claude-code-plugin` and `spec-driven-development`; set with `gh repo edit` only after
  the owner's approval at gate 2.
- [ ] AC17: `docs/ROADMAP.md`: the install-guide item names `plugin/docs/INSTALL.md`; the
  demo recording item is removed; the public demo repository and consumer metrics items
  sit in a new `## Stage 9 — Evidence` after Stage 8; the remaining Stage 4 items are
  ticked, with the owner-only profile settings (pin, social preview) as a separate item
  ticked only after the owner confirms them.
- [ ] AC18: `docs/BACKLOG.md` *Reach* item's trigger reads "Stage 9 is done";
  `docs/DECISIONS.md` gains rows for: the install guide in `plugin/docs/`; GitHub Releases
  for every release tag (the naming row was added with this SPEC).
- [ ] AC19: No behaviour change: nothing under `plugin/bin/`, `plugin/hooks/`,
  `plugin/skills/`, `plugin/agents/` or `plugin/templates/` changes, and the version in
  `plugin/.claude-plugin/plugin.json` stays 0.3.4 (only its `description` changes);
  `bash scripts/check.sh` is green.
- [ ] AC20: No document names the private consumer project.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---------|-----------------------|--------------|
| Display name *Spec-Driven Workflow*; slug `agentic-pipeline` and plugin `pipeline` unchanged | renaming the slug to `pipeline`, `guarded-spec-workflow` or `spec-driven-workflow`; renaming the plugin | The owner wants a name that tells an outsider what happens, with the least invasive change; the display name is what a reader meets, the slug appears only in URLs. A slug rename stays cheap later. Noted: about ten repositories use the slug `spec-driven-workflow`, and `claude-code-spec-workflow` is a popular Claude Code tool, so the name alone does not differentiate — the pitch and *Why not Spec Kit?* must |
| Plugin name `pipeline` is permanent | renaming at Stage 8 when every skill is rewritten anyway | Owner decision; the namespace is typed in every command and a rename migrates every consumer |
| Install guide at `plugin/docs/INSTALL.md` | `docs/INSTALL.md` (the roadmap's path) | `plugin/` is what reaches the consumer's cache, next to `GUARD.md`; `docs/` holds project documents and a link from `plugin/README.md` into it breaks outside GitHub |
| The guard refusal as a tested text block; no animated recording | a GIF/asciinema of the guard and a `ship` run | Owner dropped the recording; a text block checked against `guard.py` cannot drift and needs no tooling |
| Evidence items moved to a new Stage 9 | leaving them open in Stage 4 | The material arrives in weeks; Stage 4 can close, and catalogue listing waits for evidence |
| Releases created by the agent on existing tags after gate 2; About and topics likewise | the owner runs every `gh` command | Tags do not move and a Release is reversible; creating tags and moving `stable` stay the owner's |

## Owner decisions

- No new dependencies (runtime or dev) and no data migration — accepted; mermaid and
  shields.io badges are rendered by GitHub.
- The agent may run `gh release create` for the six existing tags and `gh repo edit` for
  the description and topics, only after the owner's approval at gate 2.
- Profile pin and social preview are done by the owner.

## Open questions (non-blocking)

- none
