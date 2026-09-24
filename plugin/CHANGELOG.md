# CHANGELOG

Semantic versioning. A release is tagged with `claude plugin tag`.

## 0.7.0

The skills and agents are reworded for Claude Opus 5.5 after a prompt audit
(`specs/009-prompt-audit-for-opus-5-5/AUDIT.md` in the repository): rules keep their words
and their reasons, stated at normal volume; a line that only raised the pressure or coached
a strategy the model follows unprompted is gone, and `idea` gains two guardrails.

**consumer impact:** none — no configuration change; update as usual.

### Changed

- Capitals used as emphasis are lowered across the skills and agents; capitals stay only
  for contract tokens and identifiers (`STOP`, `RESULT: ESCALATE`, `SPEC`, `PLAN`, …), and
  a test keeps them out (P1).
- `plan-review`: the role asks for the real review targets — an AC without steps or a
  test, a broken decision, a step whose verification cannot run — and a report of the
  findings with their severity next to what was checked and found sound, instead of
  telling the reviewer that its success is finding gaps; the `IMPORTANT` status heading is
  now `What the status triggers` (P2, P3).
- `implement`: the self-correction loop drops the hint to read the full error output from
  the first error; the gate says the next step starts only on green, that a suspected
  flaky test is still red and that a skipped test is not green (S1, S2).
- `final-review`: the line "Green tests ≠ correct code" is removed; the three perspectives
  and the check of every finding set the depth of the review (S3).
- `idea`: the stage ends at the handoff and never starts `/pipeline:ship` or a later stage,
  and it neither removes an `(assumption)` suffix nor sets `spec-ready` before the owner
  has answered on every such item (R1); a stage that ends with the SPEC still
  `spec-draft` hands off with the open items and does not point at `/pipeline:ship`.

## 0.6.1

The hook commands quote the plugin path, so the guard, the formatter and the notifications
run from a plugin directory whose path contains a space.

**consumer impact:** none — no configuration change; update as usual.

### Fixed

- `hooks/hooks.json` wraps `${CLAUDE_PLUGIN_ROOT}` in double quotes in all four commands.
  Unquoted, a path with a space split into several words: the hook exited 127, which
  Claude Code treats as a non-blocking error, so the guard did not run and every command
  passed. `claude plugin validate --strict` (Claude Code 2.1.281) also refuses the
  unquoted form.

## 0.6.0

Stages read their templates and the section map at run time: `idea` and `plan` read the one
SPEC or PLAN template for the current `language`, and every stage reads
`templates/sections.md` with `Read` from the plugin's directory, instead of carrying both
languages inline. The command guard warns once per session when no settings file allows
that read. Skills, agents, tests and eval graders are translated into English, one to one.

**consumer impact:** add `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` (for
this plugin's own marketplace: `Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)`) to
`permissions.allow` in the project's `.claude/settings.json`, or in
`~/.claude/settings.json` for every project on the machine; a `--plugin-dir` session needs
the absolute clone rule `Read(//<clone>/plugin/**)`. Without it every stage stops on its
first read — under `/pipeline:ship` with an escalation naming the file and the rule — and
the guard prints a notice with the exact rule once per session. `/pipeline:init` writes the
rule for new projects. The translation needs no configuration change: a
`"language": "pl"` consumer keeps Polish specs, plans and documents.

### Added

- `templates/sections.md`: the section map (key → Polish → English), read by every stage
  with `Read` before it looks for a section; a failed read of the map or a template ends the
  stage (`RESULT: ESCALATE` under `/pipeline:ship`, a stop with the same message when run
  on its own), naming the file and the allow rule to add.
- A once-per-session guard notice, in a project with `.claude/workflow.json`, when no
  user, project or project-local settings file holds a `Read` allow rule covering the
  plugin's directory: one JSON object on stdout, as `systemMessage` for the owner and
  `additionalContext` for the model, never blocking; on a refused call it follows the
  reason on stderr. It names the exact rule — the version-free cache form, or the absolute
  `//` form for a clone.
- `templates/settings.json` allows `Read(~/.claude/plugins/cache/TODO-marketplace/pipeline/**)`,
  and `/pipeline:init` fills the marketplace name into the rule and `extraKnownMarketplaces`
  alike.
- Eval case `plan-review-approves-polish-owner-decision`: a Polish consumer whose
  owner-decisions section, under its Polish heading, accepts a new dependency, approved
  without escalating; every stage eval scaffold writes the clone `Read` rule.

### Changed

- Skills, agents, tests and eval graders are English, translated one to one: a stage names
  a SPEC or PLAN section by its English heading and takes the Polish twin from
  `templates/sections.md`; Polish lives only there and in the `*.pl.md` templates.
- `idea` and `plan` read `templates/{SPEC,PLAN}.<language>.md` with `Read` (`en` for a
  missing or unsupported value); every stage skill carries one identical `## Section map`
  block.
- The install guide documents the rule, project versus user settings and the clone rule;
  the canary procedure includes the clone rule.

### Removed

- The inline SPEC and PLAN templates in `idea` and `plan`, and the section-map table in the
  README (the README links to `templates/sections.md` and carries no Polish).

## 0.5.0

Language made explicit: `language` decides what the pipeline writes into the repository,
commits and PR titles are English everywhere, and the conversation follows the session.
Skills and agents stay Polish until 0.6.0.

**consumer impact:** a consumer without `language` in `.claude/workflow.json` now gets
English specs, plans and PR descriptions — add `"language": "pl"` to keep Polish. A value
other than `en` or `pl` warns and falls back to `en`. `/pipeline:init` asks for the language
first and generates `CLAUDE.md` and `docs/*` in it. Commit messages, PR titles and branch
names are English whatever `language` says. Final-review findings use the severity token
`worth-fixing`. Existing specs and documents are not translated, and specs in either
language keep working.

### Added

- A language contract in the README: what follows `language` (every file the pipeline
  writes, PR descriptions), what is always English (commit messages, PR titles, branch
  names, `RESULT` and metric keys, severity tokens) and what follows the Claude Code
  session (questions, escalations, summaries). Every stage skill carries it as one
  identical `## Język` block; the stage contract gains a language bullet.
- SPEC and PLAN templates per language (`templates/{SPEC,PLAN}.{en,pl}.md`); `idea` and
  `plan` carry both inline, pinned byte for byte to those files, and pick one by
  `language`. PLAN is written in the current `language`, also over a SPEC in another one.
- A section map in the README (key → Polish → English); stages name sections by both
  headings and accept either. `plan-review` checks the plan's language.
- `/pipeline:init` templates per language (`CLAUDE.{en,pl}.md`, `docs/*.{en,pl}.md`); the
  language is the first question, unattended it comes from the argument, the existing
  `language` or `en`; a re-run recommends the configured language, and a re-run with
  another language changes only the key.
- Eval case `init-writes-the-chosen-language`.

### Changed

- `language` accepts `en` and `pl` only; the default is `en` (was `pl`).
- `workflow_metrics.py` reads `.claude/workflow.json` section by section, like the hooks: a
  faulty key warns and falls back to its default instead of stopping the report.
- Severities are the tokens `blocker` / `worth-fixing` / `nit` (final review) and
  `blocker` / `major` / `minor` (plan review), written as code in every language; the ship
  gate's options use them.
- `final-review` opens the PR with an English conventional-commit title and a body in
  `language`; `ship` asks the owner in the session language.
- `init-without-questions` also requires English documents and `"language": "en"`; the
  final-review eval criteria use the tokens.

## 0.4.0

The guard guards itself and the release channel: it protects configurable release-channel
branches like `main`, refuses detaching or tampering with the plugin, and refuses `gh api`
writes on the owner's ground. The first minor release, gated on the eval receipt and the
canary.

**consumer impact:** agent sessions can no longer disable, uninstall or remove the
plugin's marketplace (`claude plugin|plugins disable`, `uninstall|remove`,
`marketplace remove|rm` aimed at this plugin — the owner runs those in a terminal), edit
the plugin's files or its install state (`installed_plugins.json`,
`known_marketplaces.json`) from the shell, or write repository settings through `gh api`
(`POST`/`PUT`/`PATCH` on the repository or organisation itself, topics, transfer,
secrets, variables, environments, webhooks, keys, collaborators and invitations, teams and
members, Pages, security settings, Actions permissions, rulesets, branch protection; CI
re-runs, releases, deployments, comments, labels, issues and pulls stay open). A consumer
adds `"protectedBranches": ["<branch>"]` to `.claude/workflow.json` to protect a release
channel; without the key every decision is what 0.3.4 made. An older plugin reading a
configuration with the key only warns about an unknown key and keeps the other sections.

### Added

- `protectedBranches` in `.claude/workflow.json`: extra branch names (exact) the guard
  treats exactly like `main`/`master` — pushes, commits, merges, rebases, non-`--ff-only`
  pulls, `git branch -D`, `update-ref`, `gh api` ref writes — naming the branch in the
  refusal. `main` and `master` stay protected whatever the list says. The `pre-push` hook
  and `/pipeline:init` do not read or write it.
- Detaching the plugin is refused by target: `disable`/`uninstall`/`remove` of this plugin
  under any marketplace, `disable` with no plugin or `--all`, `marketplace remove|rm` of a
  marketplace it is installed or loaded from; a name built from variables or an unreadable
  install state is refused. Other plugins, `update`, `install`, `enable` and `--help` pass.
- The running guard's own directory, wherever it lies, and the plugin install state are
  guardrail files, judged by the real path a shell write reaches; `cp`, `install` and `ln`
  count only their destination (`-t` at the end of a cluster, `--target…` prefixes) and
  the path a copy into a directory lands on, so copying templates out of the plugin
  passes; `sed --in-place` counts as `sed -i`, also for the settings files.
- `gh api` writes on the owner's ground, judged by the endpoint after `repos/<o>/<r>`,
  `repositories/<id>` or `orgs/<o>`; a write endpoint built from variables is refused.
  Flags are read the way `gh` reads them, so `-X=DELETE`, `-iXPATCH` and an attached
  `-fkey=value` no longer read as `GET` — the 0.3.4 `DELETE` rule gains this too. On a
  configured channel a write under `branches/<branch>` or with a `branch=<branch>` field
  is refused as well.

## 0.3.4

The guard closes the known leaks around pushes and git aliases; the guard documentation
(`docs/GUARD.md`) and the plugin README are in English, and so is this changelog.

**consumer impact:** no migration steps. New guard refusals: a push whose refspec is built
from variables or command substitution that the guard cannot expand — for example
`git push origin HEAD:$(git branch --show-current)`, `git push $(git remote) <branch>`,
`git push origin $UNKNOWN`; a prefix assignment used for the same push's refspec
(`B=feat/x git push origin $B`); `git -c alias.*`; writing an alias to git configuration,
including `--unset` and `--rename-section … alias`; removing or renaming the `core`
section; `git push --all`/`--branches`, a refspec with a pattern or brace expansion (`*`,
`?`, `{a,b}`); writing or `-c`-setting push configuration (`remote.<name>.push`,
`remote.<name>.mirror`, `push.default`); `git config --edit`; a git configuration key built
from a variable; a push with a variable assigned in an `if`/`while`/`for`/`case` block,
through `read`/`declare`/`printf -v`/`unset` or through `B+=`. Spell the branch out in such
a push.

### Fixed

- A push refspec built from variables is expanded the same way as an `rm` path: variables
  from the session, earlier assignments and `export`; a result that names `main`/`master`
  is refused with the push-to-`main` reason (also `${B}`, `HEAD:$B`, `"$B"`,
  `refs/heads/$B`). Before, `B=main; git push origin $B` passed.
- A refspec that cannot be expanded (an unknown variable, `$(...)`, backticks, a
  conditional assignment after `||`/`&&`) is refused, and the reason names the refspec and
  asks for the branch to be spelled out. So is command substitution in place of the remote.
- Shell semantics: a prefix assignment does not expand the arguments of its own command,
  an empty value disappears (`E=; git push origin $E` pushes the current branch — refused
  on `main`), and a value with spaces splits into words (`B="feat/x main"`).
- A variable in place of the remote with literal refspecs passes
  (`git push $REMOTE feat/x`); `git push $REMOTE main` is still refused.
- Reading `core.hooksPath` without a value (`git config core.hooksPath`, with `--global`,
  `--local`, `--show-origin`, `--file`) passes; a write, `--unset`, `set`/`unset` and
  `-c core.hooksPath=…` are still refused. One parser tells a read from a write, in the
  classic form and in the git 2.46 subcommands.
- A git alias is refused: `git -c alias.*=…` (key matched case-insensitively) and writing
  an alias to configuration in any scope; reading an alias passes. Other `-c` keys (such
  as `user.name`) are unchanged.
- After the final review: the guard follows a variable only where its value is certain. An
  assignment in a subshell `( … )`, in a pipeline or in the background ends with them (so
  does `cd`); `bash -c` sees only exported variables (`export -n` removes the export); a
  conditional assignment (including a conditional `export`), one in an
  `if`/`while`/`for`/`case` block, one made by a builtin (`read`, `declare`, `local`,
  `unset`, `printf -v`, `mapfile` …), an append `B+=`, an element and an array give an
  unknown value; after `IFS` changes, every expansion in a refspec is unknown. Before,
  among others, `(B=feat/x); git push origin $B` and
  `B=feat/x; bash -c 'git push origin $B'` passed on `main`.
- A command after the keywords `if`, `while`, `until`, `elif` and `!` is checked — before,
  `if git push origin main; then :; fi` passed.
- Push options are read after variables are expanded: `B=-f; git push origin $B`, and
  `--delete`, `--mirror` and `--no-verify` from a variable, are refused. The value of
  `-o`/`--push-option`/`--repo`/`--receive-pack`/`--exec` is not taken for the remote
  (before, `git push -o ci.skip origin` passed on `main`); with `--repo`, every argument is
  a refspec.
- A push that reaches `main` without naming it is refused: `--all`, `--branches`,
  patterns and braces in a refspec, the short form `heads/main` (git completes it to
  `refs/heads/main`), push configuration through `-c` and writes of `remote.*.push`,
  `remote.*.mirror`, `push.default`, and section operations on `push` and `remote.*`.
- `git config --edit`/`-e`/`edit` is refused (an editor can change `core.hooksPath` or an
  alias), and so is a `git config` or `git -c` key built from a variable the guard does not
  know; a known variable is expanded before the key is checked.

### Added

- `docs/GUARD.md`: the threat model, the three layers (guard → `pre-push` → GitHub
  rulesets), a table of commands that get past a string-based `deny` rule and that the
  guard stops — measured with `claude -p --settings` and checked against the guard by a
  test — fail-open behaviour and known limits.

### Changed

- The plugin `README.md` is in English; its guard section is a summary with a link to
  `docs/GUARD.md`. Skills and agents stay in Polish until Stage 8.
- This changelog is in English, earlier releases included.

## 0.3.3

Fixes after the first full run of 0.3.2 in a consumer project.

**consumer impact:** no migration steps; `gh api -X DELETE` outside the owner's territory
is no longer refused.

### Fixed

- The guard refused every `gh api -X DELETE` with a message about merges and branch
  protection — including deleting Actions artifacts. DELETE is now refused only on paths
  that are the owner's decision: the repository itself and the organisation (also under a
  prefix, such as GitHub Enterprise Server's `api/v3`, and as `repositories/<id>`), branch
  and tag refs, merges, protection, rulesets, releases, workflow runs, secrets, variables,
  environments, hooks, keys, collaborator access, organisation teams and members, Pages,
  deployments and security settings; the message names the path and the rule that
  matched. A path built from variables is refused — it cannot be checked.
- `final-review` (mode `apply`) took the run link from `gh run list --workflow CI` — a
  workflow name from the source project that does not exist in a consumer project. The
  link now comes from `gh pr checks <nr> --json name,workflow,link`.
- The stage agent contract says that only the orchestrator increments the `escalations`
  counter — in the consumer run the reviewer incremented it in mode `apply`.

### Changed

- The guard's refusal of a compound command names the refused parts and says how many of
  the others passed, so the agent can run them in a separate call. A pipeline (`|`) is one
  part.
- `ship`: instead of "the stage agent runs in the foreground" — you wait for its result
  before moving on (the harness runs agents in the background; what matters is waiting,
  not the mode).

## 0.3.2

Projects stop enabling the plugin. A session starting in a directory whose
`.claude/settings.json` has `"enabledPlugins": {"pipeline@<marketplace>": true}` creates a
`--scope project` install on its own — also next to an existing `--scope user` install —
and `claude plugin update --scope user` updates only the `user` entry, so the `project`
duplicate stays on the old version forever (measured 2026-09-21 on an isolated
`CLAUDE_CONFIG_DIR` with a local marketplace). With `extraKnownMarketplaces` alone, no
`project` entry is created and the plugin from the `user` install loads normally.

**consumer impact:** remove `enabledPlugins` from your own `.claude/settings.json` (keep
`extraKnownMarketplaces`; an opt-out with the value `false` stays) and commit, then in
every repository with the plugin uninstall the duplicate: `claude plugin
uninstall pipeline@<name> --scope project` and `git checkout -- .claude/settings.json`
(the command can cut out the marketplace block). `claude plugin list` should show the
plugin once, in the `user` scope.

### Fixed

- `templates/settings.json` has no `enabledPlugins`; `/pipeline:init` does not write it.

### Changed

- README, Installation: the example declares only `extraKnownMarketplaces`, explains why
  a project does not declare `enabledPlugins: true` and how to remove an existing `project`
  duplicate; the migration from a tag-based registration does not bring `enabledPlugins`
  back, and the verification checks that there is no `project` entry. A `--scope project`
  install is no longer an option for version isolation — the only install is `user`.

## 0.3.1

Fixes the metrics check call from 0.3.0. Stage skills ran
`python3 "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" --check`, and the template allowed
it with a rule written with the same variable. The variable is substituted in a skill's
text but not in `permissions` rules, so the rule never matched, every `--check` ended in a
permission prompt that a stage subagent cannot answer, and `final-review` in mode `apply`
could not set `done`.

**consumer impact:** in `permissions.allow` of your own `.claude/settings.json`, replace
the entry with `"Bash(workflow_metrics.py *)"` (the template change applies only to new
projects). In `extraKnownMarketplaces` set `"ref": "stable"` instead of a release tag and,
once per machine, switch to the `stable` channel with a `--scope user` install: `claude
plugin marketplace remove <name>`, `claude plugin marketplace add '<url>#stable'`, `claude
plugin install pipeline@<name> --scope user`, then `git checkout -- .claude/settings.json`
in every repository with the plugin (these commands delete the plugin block from
`settings.json`). Later releases: `claude plugin marketplace update <name> && claude plugin
update pipeline@<name> --scope user`, without `remove`.

### Fixed

- The closing steps of `plan`, `plan-review`, `implement` and `final-review` (including the
  close in mode `apply`) call `workflow_metrics.py --check <spec-dir>` through `PATH` —
  Claude Code adds the plugin's `bin/` to the session `PATH`.
- `templates/settings.json` allows `Bash(workflow_metrics.py *)`.
- `templates/docs/CONVENTIONS.md` gives the call through `PATH` instead of
  `python3 <plugin>/bin/workflow_metrics.py`.

### Changed

- README: the report and `--check` in the `PATH` form, with an explanation of why not
  `${CLAUDE_PLUGIN_ROOT}`.
- A `stable` release channel instead of a tag pin: `templates/settings.json` has
  `"ref": "stable"` (instead of a `TODO:` with a tag), and `/pipeline:init` writes `stable`
  instead of deriving a tag from the version in `${CLAUDE_PLUGIN_ROOT}`. A marketplace's
  `ref` is global per machine, so a tag pin forced a `remove` on every release, which
  uninstalls the plugin in all projects.
- README, Installation: `--scope user` by default (one install per machine; `--scope
  project` as an option for isolation), updates through `marketplace update` + `plugin
  update`, a one-off migration from a tag-based registration (with a warning that `remove`
  uninstalls the plugin in all projects, and that `remove`, `add` and `install` delete the
  plugin block from `.claude/settings.json`) and disabling the plugin in a repository with
  `"enabledPlugins": {"pipeline@<marketplace>": false}`.

## 0.3.0

Rules go where the agent executes them and get a program that enforces them. The format of
the `metrics:` block is named in every stage skill and checked by
`workflow_metrics.py --check`, the stage agent contract lives in the `agents/*.md` files
(the harness loads them without a tool read), and the installation guide pins a release.

**consumer impact:** after updating, register the marketplace again with the new `ref`
(`claude plugin marketplace remove <name>` + `add '<url>#pipeline--v0.3.0'`) — without it
the pin in `.claude/settings.json` has no effect; add to `permissions.allow` in your own
`.claude/settings.json` the entry
`"Bash(python3 \"${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py\" *)"` (the template change
applies only to new projects); a spec started before this release may escalate once over
missing metrics keys — the owner fills them in, the agent does not make them up.

### Added

- `bin/workflow_metrics.py --check <spec-dir>` — the full set of keys due for the status
  reached, parseable timestamps and `findings_accepted + findings_rejected` matching the
  total of final review findings; exit code 1 and a readable message naming every gap.
  `--check` also reports a key outside the metrics list (a typo would lose the value
  silently) and names a frontmatter without `status` separately. The default call (the
  report) is unchanged, except that a missing specs directory ends with exit code 1 and a
  message instead of "no metrics", and the report skips an unreadable `SPEC.md` with a
  warning instead of a traceback.
- Structural tests `test_stage_skills.py` and `test_stage_contract.py`.
- The `init` skill checks for `AskUserQuestion` BEFORE the question step and without that
  tool asks nothing by any route — not in prose either — and does not end its reply with a
  request for a decision. Before, the rule stood only after the "ask the questions" step,
  so it was weighed rather than executed: two eval runs of the same commit diverged, one
  finished the skill, the other asked four questions in text and stopped.

### Changed

- Every stage skill names the format of the `metrics:` block and its own keys in its
  closing step and runs `--check` before reporting success; `final-review` in mode `apply`
  does not set `done` while `--check` fails. No skill refers to the README for the metrics
  format.
- `## Kontrakt agenta etapu` (stage agent contract) and `## Wyzwalacze eskalacji`
  (escalation triggers) live entirely in `agents/*.md`; agents no longer tell the reader to
  read the `ship` skill (a test keeps them identical to the character).
- The `## Konfiguracja projektu` (project configuration) section in the six stage skills is
  two points; the key table stays only in the README. The visual artifacts rule is one
  imperative sentence, conditional on a UI scope in `verify.scopes`, pointing to the
  project's conventions.
- `templates/settings.json` names a `git` source over HTTPS with a visible `ref` (TODO) and
  allows one specific call
  `Bash(python3 "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" *)` — the pattern is
  anchored on the whole literal, so it does not let any `python3` command through; `init`
  fills in the marketplace name and `ref` from the `${CLAUDE_PLUGIN_ROOT}` path, and leaves
  a `TODO:` when the path has another shape.
- `final-review` in mode `apply`: a finding deferred to the backlog counts as
  `findings_rejected`, so the `--check` balance adds up.
- README: a section on `--check` (exit codes, a table of keys due per status) and the call
  through `${CLAUDE_PLUGIN_ROOT}` instead of a relative path; a `ref` in the declarative
  example, a note about registering the marketplace again and a one-sentence scope of the
  migration module (Alembic only).

## 0.2.0

The first release in this repository — imported from a private project repository without
changing the behaviour of skills, agents, hooks or the guard.

Stage skills lead to domain documents through the document map in the project's
`CLAUDE.md`, and the SPEC shows what the agent read. A new SPEC section changes the output
of the `idea` stage, hence a minor release.

### Changed

- `idea`, `plan` and `implement` refer to the domain documents from the document map in
  `CLAUDE.md` (according to the conditions in the map) instead of a list in the code style
  document.
- Step 1 of `idea`: a ready scope or requirements in the prompt do not excuse the agent
  from gathering context.
- The SPEC template has a `## Przeczytany kontekst` section (context read) — one item each
  for the roadmap, the project description, the decision log and every domain document;
  the guardrail requires it for `spec-ready`.

## 0.1.0

The first version — the agentic workflow extracted into a standalone plugin.

### Added

- Seven skills: `init`, `idea`, `plan`, `plan-review`, `implement`, `final-review`, `ship`.
- Four stage agents: `planner`, `plan-reviewer`, `implementer`, `reviewer`.
- The command guard (`bin/guard`, `bin/guard.py`) with universal rules that work without
  configuration and production, worktree and migration modules driven by configuration.
- `PostToolUse` hooks (formatting according to the `format[]` map) and `PreToolUse:
  AskUserQuestion` / `Notification` (a notification when the owner is awaited).
- The `.claude/workflow.json` configuration layer (`bin/workflow_config.py`) with key
  validation and documented defaults.
- Workflow metrics report (`bin/workflow_metrics.py`).
- Project templates: `settings.json`, `workflow.example.json`, `CLAUDE.md`, `docs/`
  documents, the `pre-push` hook and CI variants (Python, Node, skeleton), a security
  audit and `dependabot.yml`.
