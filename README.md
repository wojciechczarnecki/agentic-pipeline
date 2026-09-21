# Spec-Driven Workflow

[![CI](https://github.com/wojciechczarnecki/agentic-pipeline/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/wojciechczarnecki/agentic-pipeline/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE) [![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fwojciechczarnecki%2Fagentic-pipeline%2Fmain%2Fplugin%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version)](plugin/CHANGELOG.md)

A Claude Code plugin that takes a feature from an approved spec to a reviewed pull request, with owner gates between the stages and a command guard that stops the agent from pushing to main, merging its own PR or touching production.

Three names, one thing: *Spec-Driven Workflow* is the project, `agentic-pipeline` is the
repository and `pipeline` is the plugin (the `/pipeline:*` commands, installed as
`pipeline@wcz-tools`).

## How it works

```mermaid
flowchart LR
    idea["idea"] --> G1{{"Gate 1: owner approves the SPEC"}}
    G1 --> plan["plan"]
    plan --> review["plan review"]
    review --> implement["implement"]
    implement --> final["final review"]
    final --> G2{{"Gate 2: owner decides on review findings"}}
    G2 --> pr["PR"]
    pr --> G3{{"Gate 3: owner merges"}}
```

You write the spec with the agent in a dialogue (`/pipeline:idea`) and approve it. From
there `/pipeline:ship` runs every stage as a subagent with fresh context: a plan, an
adversarial review of the plan, the implementation step by step in a self-correction loop,
and a final review from three perspectives. You come back when a stage escalates and when
the review findings are ready; the agent then applies your decisions, opens the pull
request and waits for green CI. The merge stays yours. Every spec keeps its state and
workflow metrics in its own frontmatter, checked by `workflow_metrics.py --check`.

## The guard in action

A `PreToolUse` hook reads every shell command the agent is about to run and refuses the
ones that belong to the owner:

```text
$ git push origin main
Blocked by the pipeline guard: pushing to main: main changes only through a PR merged by the owner; work on a feature branch
```

The guard is best effort, not a sandbox: it reads commands as text, and GitHub rulesets
and a `pre-push` hook stand behind it. Its three layers, the commands it stops that a
string `deny` rule lets through, and its known limits are in
[plugin/docs/GUARD.md](plugin/docs/GUARD.md).

## Why not Spec Kit?

Spec Kit plans and this plugin enforces. Spec Kit takes a feature through slash commands
from a constitution and a specification to a plan, tasks and the implementation, and its
README describes no mechanism that refuses a shell command such as a push to `main`
(checked 2026-09-21).

The claim here is narrower than "gates": it is the command guard and the checked metrics.
Approval gates enforced with hooks are not unique — SpecForge and gate-oriented-sdd enforce
them too, but neither guards shell commands (checked 2026-09-21). What this plugin adds is
an agent that cannot push to `main`, merge its own pull request, touch production hosts or
run a migration against a non-local database, and a `metrics:` block per spec that a script
refuses to accept when a stage left it incomplete.

## Requirements & opinions

The plugin is opinionated about the setup around it:

- **GitHub with the `gh` CLI** — the agent opens pull requests and reads CI with `gh`.
- **Squash merges** — pull requests are squash merged, so one pull request becomes one
  commit on `main`.
- **GitHub rulesets** — the server-side layer: the `main` ruleset requires a pull request
  and a green check, whatever happens on the machine.
- **`python3` on the machine** — the hooks run on the standard library alone; without
  `python3` they fail open, with a warning, and guard nothing.
- **Migration guarding is Alembic only** — a project on another migration tool gets no
  protection there.

### Who it is for

- A developer who owns a repository and wants Claude Code to deliver whole features while
  keeping the spec, the review decisions and the merge.
- Projects on GitHub where a pull request with green CI is already the way into `main`.

### Who it is not for

- Teams that want the agent to merge on its own or to deploy.
- Projects outside GitHub, or without `python3` where Claude Code runs.
- Anyone looking for a sandbox: the guard is a guardrail for a cooperative agent, not a
  security boundary.

## What's deliberately not here

- **No runtime dependencies** — hooks and scripts use the Python standard library only.
- **No hosting outside Claude Code** — the pipeline runs as a Claude Code plugin, not as a
  service or a CLI of its own.
- **No sandbox** — the guard is best effort; what it does not see is listed in
  [its known limits](plugin/docs/GUARD.md#known-limits).

## Install

```bash
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'
claude plugin install pipeline@wcz-tools --scope user
```

`#stable` is the release channel. Updating, the one-time migration, opting a repository out
and the known traps are in the [install guide](plugin/docs/INSTALL.md).

## Quickstart

Install first ([Install](#install)), then:

```bash
claude            # in your project's directory
/pipeline:init    # inside the session: configuration, documents, git hook, CI
/pipeline:idea    # describe the feature; the dialogue ends in an approved SPEC
```

After the SPEC is approved, `/pipeline:ship NNN` takes it to a pull request.

## Documentation

- [Install guide](plugin/docs/INSTALL.md) — channel, scope, updates, migration, traps
- [The command guard](plugin/docs/GUARD.md) — threat model, layers, known limits
- [Workflow metrics](plugin/README.md#workflow-metrics) — the `metrics:` block and `--check`
- [Plugin documentation](plugin/README.md) — configuration and pipeline mechanics
- [Contributing](CONTRIBUTING.md) and the [security policy](SECURITY.md)
- [Changelog](plugin/CHANGELOG.md) — releases are tagged `pipeline--vX.Y.Z`

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). The plugin's tests are plain pytest on the standard
library, so they also run outside this project's dev environment:

```bash
cd plugin && python3 -m pytest tests
```

## License

[MIT](LICENSE)
