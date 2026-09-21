# The pipeline guard

The `pipeline` plugin lets agent sessions run long stretches of work without permission
prompts. What makes that acceptable is a command guard: a `PreToolUse` hook on the Bash
tool that refuses the commands an agent must never run on its own, and tells the agent
why and what to do instead. This document states what the guard defends against, which
other layers stand behind it, where a plain `deny` rule is not enough, and where the guard
stops.

## Threat model

The guard defends against **agent mistakes and shortcuts**: a session that pushes to
`main` because that is where the fix "belongs", force-pushes over a rejected push, runs
`git reset --hard` to get a clean tree, skips a failing hook with `--no-verify`, deletes a
directory outside the project, points a migration at a production database, merges its own
pull request or edits the very settings that constrain it. These are the actions of a
capable, well-meaning agent that optimises for finishing the task — the common case, and
the one that does damage in practice.

It does **not** defend against deliberate evasion. An agent (or a prompt injection) set on
getting past it can write a script to a file and run it, call an interpreter, or reach git
through a channel the guard does not parse; see [Known limits](#known-limits). The guard is
best effort, not a sandbox: it reads a command string and judges what the shell would run,
it does not confine the process. Where a mistake would be irreversible — a push to `main`,
a moved release tag — a server-side layer stands behind it.

## Three layers

Each layer covers ground the one before it cannot, and each has its own way around it.

### The command guard

- **Covers:** every Bash tool call of an agent session. Universal rules, with no
  configuration: pushes, commits, merges, rebases and cherry-picks on `main`/`master`
  (only `git pull --ff-only` passes there); force, mirror and delete pushes, also when the
  option comes from a variable; a push refspec built from variables or command
  substitution that the guard cannot resolve; a push of every branch (`--all`,
  `--branches`) or of a refspec pattern or brace expansion; push configuration that
  decides where a push lands (`remote.<name>.push`, `remote.<name>.mirror`,
  `push.default`, on the command line or written); `--no-verify`; `git reset --hard`;
  `git clean -f`; `git branch -D main` and friends; `git update-ref`/`git symbolic-ref` on
  `main`; changing `core.hooksPath` (reading it is fine); defining a git alias, on the
  command line (`git -c alias.*`) or with `git config`; `git config --edit`, which could
  write either; `gh pr merge`; changes to repository settings, secrets, variables
  and rulesets; `sudo`; removals outside the project, its worktree directory and the
  session's scratch directory, and of the repository root or `.git`; shell edits of
  guardrail files (`.claude/settings*.json`, `.claude/workflow.json`, the plugin directory
  when it sits inside the project, and an existing git hook in `gitHooksDir` — creating a
  missing hook and making it executable is allowed). The project's
  `.claude/workflow.json` adds production hosts and commands, the worktree directory and
  the migration module.
- **Runs:** before every Bash tool call, in the session that loaded the plugin, on plain
  `python3` with no network. It sees through `bash -c`, `eval`, `$(...)`, backticks,
  heredoc bodies that expand, wrappers such as `env`, `command`, `nohup`, `timeout`,
  `uv run` and `xargs`, `docker compose exec`, and variables assigned earlier in the same
  call or exported in the session. It follows a variable only where its value is
  certain: a prefix assignment (`B=x git push origin $B`) does not count for the
  command's own arguments, an empty value disappears, an assignment inside a subshell,
  a pipeline or a background command ends with it, and a new shell (`bash -c`) sees only
  exported names. A value it does not follow — assigned behind `&&`/`||` or inside
  `if`/`while`/`for`/`case`, by `read`, `declare`, `printf -v`, `unset` and similar
  builtins, appended (`B+=x`), an array — counts as unknown, and so does every expansion
  once `IFS` changes; an unknown value in a push refspec is refused.
- **How the refusal reads:** exit code 2 and a reason naming the rule and the way out. A
  refusal always covers the whole call; in a compound command the reason names the parts
  at fault (a pipeline is one part) and says how many of the others passed, so the agent
  can send those again on their own.
- **`gh api -X DELETE`** is refused only on the owner's ground — the same ground the `gh`
  subcommands keep: the repository and the organisation themselves, branch and tag refs,
  merges, branch protection, rulesets, releases, workflow runs, secrets, variables,
  environments, webhooks, keys, collaborator access, organisation teams and members,
  Pages, deployments and security settings. An endpoint built from variables is always
  refused. Everything else (Actions artifacts and caches, comments, labels) passes.
- **Bypassed by:** a session without the plugin (nothing reports its absence), the Edit
  and Write tools, a person at the terminal, and everything in [Known
  limits](#known-limits).

### The pre-push hook

- **Covers:** every `git push` from a clone, whoever runs it — the agent, the owner, an
  IDE. It refuses a push whose remote ref is `refs/heads/main` or `refs/heads/master`,
  however the command line spelled it: git resolves the refspec before the hook sees it,
  so aliases, variables and scripts end up here too. `/pipeline:init` installs it from
  `templates/pre-push` into `gitHooksDir`.
- **Runs:** inside git, after the refspec is resolved and before anything goes over the
  network — only in a clone where `core.hooksPath` points at `gitHooksDir`, set once per
  clone with `git config core.hooksPath <gitHooksDir>`.
- **Bypassed by:** `git push --no-verify`, a clone where `core.hooksPath` was never set or
  was changed, and any client other than git. The guard refuses `--no-verify` and changes
  to `core.hooksPath` in agent sessions, which is why those two rules exist.

### GitHub rulesets

- **Covers:** everyone, server side. The setup this plugin is built for: a ruleset on the
  default branch requiring a pull request, squash merges only, a green CI check, and no
  deletion or non-fast-forward push; a ruleset on release tags (`refs/tags/pipeline--v*`
  for this plugin) that forbids deleting, moving or force-updating an existing tag. With
  no bypass actors they hold for the owner too.
- **Runs:** on GitHub, when the push or the merge arrives.
- **Does not cover:** creating a *new* release tag (a tag ruleset without a `creation`
  rule accepts it from anyone who can push), merging a pull request when the required
  approvals are zero, and a branch whose ruleset lets an Admin bypass it — an agent
  pushing with the owner's credentials gets through such a bypass. Those rest on the
  guard and on `deny` rules alone. Rulesets also need a plan that offers them for the
  repository's visibility; where they are missing, the pre-push hook is the local stand-in.

## Deny rules versus the guard

Claude Code's `permissions.deny` rules match the command string. They are the right tool
for a command that has one spelling, and a weak one for anything with many. The table
lists commands that get past a string `deny` rule written for exactly that action and that
the guard refuses; every row was run through `claude -p --safe-mode --settings` (plugins
and hooks off, the rule in `--settings`, a local sandbox repository) once without and once
with the rule, and ran both times. A command the rule did catch — for example
`env gh pr merge 12 --squash`, `echo $(gh pr merge 12)` or `B=main; git push origin $B`
against their rules — is not listed. A test runs every command in the table through the
guard and fails if one of them passes.

Measured on 2026-09-21 with Claude Code 2.1.272 (claude -p --settings).

| Command | Deny rule it gets past | Guard's reason |
|---|---|---|
| `bash -c 'gh pr merge 12 --squash'` | `Bash(gh pr merge*)` | `merging a PR is the owner's gate` |
| `git push origin HEAD:main` | `Bash(git push origin main*)` | `pushing to main` |
| `git push origin feat/x:main` | `Bash(git push origin main*)` | `pushing to main` |
| `git push origin refs/heads/main` | `Bash(git push origin main*)` | `pushing to main` |
| `git push -u origin main` | `Bash(git push origin main*)` | `pushing to main` |
| `git -C . push origin main` | `Bash(git push origin main*)` | `pushing to main` |
| `git -c alias.p=push p origin main` | `Bash(git push origin main*)` | `a git alias cannot be verified` |
| `git push -f origin feat/x` | `Bash(git push --force*)` | `force, mirror and delete pushes` |
| `git push origin +feat/x` | `Bash(git push --force*)` | `force and delete pushes` |
| `git push origin feat/x --no-verify` | `Bash(git push --no-verify*)` | `skipping git hooks with --no-verify` |
| `eval 'git reset --hard HEAD~1'` | `Bash(git reset --hard*)` | `discards work irreversibly` |
| `git reset -q --hard HEAD~1` | `Bash(git reset --hard*)` | `discards work irreversibly` |
| `git clean -xdf` | `Bash(git clean -f*)` | `deletes untracked files irreversibly` |
| `git -c core.hooksPath=/dev/null push origin feat/x` | `Bash(git config core.hooksPath*)` | `would switch off the pre-push guard` |

The two layers complement each other: a `deny` rule is cheap, needs no plugin and suits
actions with one spelling (`gh pr merge`, `claude plugin uninstall`, a push to a
release-channel branch until the guard protects it); the guard reads the command the way
the shell will run it.

## Fail-open by design

The guard never stops a session from working because of its own state. A missing
`.claude/workflow.json` leaves the universal rules in charge and prints a warning on
stderr once per session; an invalid configuration prints the validation error, and only
the faulty section falls back to its defaults; a missing `python3` makes the `bin/guard`
wrapper print a warning on stderr and exit 0. In all three cases the command runs. A
guard that failed closed would lock the owner out of an agent session over a typo, and the
layers behind it do not depend on it.

## Known limits

- **Migrations are Alembic only.** The migration module recognises Alembic's verbs
  (`upgrade`, `downgrade`, `stamp`, `revision`, `current`, `check`) and the variables
  `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`; only `migrations.command` and
  `migrations.localHosts` are configurable. A project on another migration tool is not
  protected, and the guard's silence is not protection. Generalising it waits in
  `docs/BACKLOG.md` (Guard, P3).
- **Only `main` and `master` are protected branches.** A release-channel branch such as
  `stable` is kept off by `deny` rules in `.claude/settings.json` until the guard gets
  configurable protected branches (`docs/ROADMAP.md`, Stage 5, 0.4.0). Detaching the
  plugin (`claude plugin disable`, `uninstall`, `marketplace remove`) is left to `deny`
  rules until the same stage.
- **The guard sees only the Bash tool.** Edits through the Edit and Write tools never
  reach it; guardrail files are protected there by Claude Code's own `ask` rules in the
  project's settings, not by the guard.
- **Scripts, interpreters and shell functions.** A script written to a file and then run
  (`bash /tmp/x.sh`), an interpreter (`python3 -c`, `node -e`) and a shell function defined
  in an earlier call run commands the guard never sees as a command string. The pre-push
  hook and the rulesets still stop a push to `main`; nothing local stops the rest.
  Tracked in `docs/BACKLOG.md` (Guard, P3).
- **Git configuration channels the guard does not parse:** `--config-env`, the
  `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_PARAMETERS` variables,
  `GIT_CONFIG_GLOBAL`, and an `include.path` or `includeIf` entry pointing at another
  file can set `core.hooksPath` or an alias without the guard noticing. Tracked with the
  previous item in `docs/BACKLOG.md`.
- **`gh api -X DELETE` is matched by segment name.** An owner keyword anywhere in the path
  refuses the call, so `repos/o/r/issues/1/labels/releases` is refused as deleting
  releases. It fails safe; positional matching waits in `docs/BACKLOG.md` (Guard, P3).
- **An alias that already exists runs unchecked.** The guard refuses defining an alias,
  not using one: with `alias.p=push` already in a configuration file — set by the owner
  before the session, or written into the file directly — `git p origin main` passes the
  guard. On `main` the pre-push hook and the rulesets stop that push; the other guarded
  git actions have nothing local behind them. Keep aliases for guarded git actions out of
  the configuration of a clone agents work in.
- **Shell constructs the guard does not model** — a brace group in a pipeline
  (`{ B=x; } | cat`), `coproc`, arithmetic assignments and anything else it does not
  parse — may hide an assignment from it. A push refspec built from a variable is then
  judged by the value the guard last saw; write the branch out when it matters.
- **Removing an alias is refused too.** `git config --unset alias.p` counts as an alias
  write; the owner removes aliases by hand.
- **Variables come from the hook's environment.** The guard resolves `$NAME` from the
  Claude Code process environment and from assignments in the same call, which may differ
  from the Bash tool's shell; a name it cannot resolve in a push refspec, a removal path,
  a `cd` or a `gh api -X DELETE` endpoint is refused rather than guessed.
