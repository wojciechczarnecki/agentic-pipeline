# Contributing

Thank you for looking at *Spec-Driven Workflow*. This file says how to report a problem,
how to set up the repository and how a change reaches `main`.

## Issues

- **A bug:** open an issue with the command or the stage that misbehaved, what you expected,
  what happened, and the plugin version (`claude plugin list`). For the guard, quote the
  command and its refusal (or the missing refusal).
- **A feature proposal:** open an issue that describes the problem first and the solution
  second. Larger changes go through the plugin's own pipeline (a SPEC, then a plan), so
  a short problem statement is the most useful start.
- **A security problem** — including a way past the command guard — does not go into a
  public issue: see [SECURITY.md](SECURITY.md).

## Development setup

The dev tools (ruff, black, pytest) come through [uv](https://docs.astral.sh/uv/); the
plugin itself runs on plain `python3` with the standard library only.

```bash
uv sync
bash scripts/check.sh                          # validate, ruff, black, pytest
git config core.hooksPath scripts/git-hooks    # once per clone: the pre-push rules
```

`bash scripts/check.sh` is the one verification command: it validates both manifests when
`claude` is on `PATH`, lints, checks formatting and runs `plugin/tests` and the root
`tests/`. Code style, tests, commit messages and the release procedure are in
[docs/CONVENTIONS.md](docs/CONVENTIONS.md); binding design decisions are in
[docs/DECISIONS.md](docs/DECISIONS.md).

## Pull requests

- Work on a branch (`feat/…`, `fix/…`, `docs/…`, `chore/…`) and open a pull request to
  `main`. Nobody pushes to `main` directly; the repository's rulesets enforce it.
- Pull requests are **squash** merged, so the PR title becomes the commit message: a type
  prefix and the imperative mood (`fix: refuse …`).
- The `plugin` check (CI) must be green before the merge.
- A change in behaviour comes with tests, bumps the version in
  `plugin/.claude-plugin/plugin.json` and gets a `plugin/CHANGELOG.md` entry; a
  documentation change does not bump the version.

## Language

Documents and code are English. The plugin's skills and agents are still in Polish until
Stage 8 of the [roadmap](docs/ROADMAP.md) translates them; a pull request that touches them
keeps them in Polish for now. Templates come in both languages (`*.en.md`, `*.pl.md`): a
change to one reaches its twin in the same pull request.
