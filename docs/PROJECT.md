# Spec-Driven Workflow

## Problem

Coding agents are fast but unreliable without structure: they skip planning, grade their
own work by how it looks, touch `main` and production, and leave no trace of why a change
was made. This plugin gives a Claude Code project a repeatable feature pipeline with owner
gates and guardrails enforced by code rather than by prompt.

## Users and roles

| Role | Does | Cannot |
|---|---|---|
| Owner | writes and approves specs, decides on review findings, merges PRs, tags releases | — |
| Agent (pipeline stages) | plans, reviews plans, implements, reviews code, opens PRs | push to `main`, merge PRs, touch production, run non-local migrations |
| Consumer project | installs the plugin from the marketplace and describes itself in `.claude/workflow.json` | — |

## Functional requirements

- Stage skills and agents: `idea`, `plan`, `plan-review`, `implement`, `final-review`,
  orchestrated by `ship`, with spec state kept in `SPEC.md` frontmatter so every stage resumes.
- `init` scaffolds a consumer project: configuration, documents, permissions, git hook, CI.
- Command guard (`PreToolUse` hook): protected branches, production hosts and CLIs,
  migrations against non-local databases, deletions outside the project, guardrail files.
- Formatting and notification hooks; workflow metrics report across specs.

## Non-functional requirements

- Runtime on plain `python3` (standard library), no network access from hooks.
- Project and domain agnostic: no consumer specifics inside the plugin.
- `claude plugin validate --strict` passes for the plugin and the marketplace.
- Behaviour changes are released as tagged semver versions.

## Architecture

`plugin/` holds the plugin (skills, agents, hooks, `bin/` scripts, templates, evals, tests);
the repository root is the `wcz-tools` marketplace pointing at `./plugin`. Consumers install
it over git + HTTPS; configuration is read from the consumer's `.claude/workflow.json`
(`plugin/bin/workflow_config.py`). Documentation of the mechanics: `plugin/README.md`.

## Out of scope

- Hosting the pipeline outside Claude Code.
- Listing in external plugin catalogues (for now).
