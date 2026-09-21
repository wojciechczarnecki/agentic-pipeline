# agentic-pipeline

An agentic feature pipeline plugin for [Claude Code](https://claude.com/claude-code):
idea → plan → plan review → implementation → final review → pull request, with a command
guard (protected `main`, production, migrations, file deletion), formatting and
notification hooks, workflow metrics and a project scaffold skill.

The plugin lives in [`plugin/`](plugin/); this repository root is its marketplace
(`wcz-tools`).

## Install

```bash
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'
claude plugin install pipeline@wcz-tools --scope user
/pipeline:init   # once in each project, inside a Claude Code session
```

`#stable` is the release channel, moved to each release; without it you track `main`,
which is unreleased code. Update to a new release:

```bash
claude plugin marketplace update wcz-tools && claude plugin update pipeline@wcz-tools --scope user
```

Documentation: [plugin/README.md](plugin/README.md); the command guard, its layers and its limits: [plugin/docs/GUARD.md](plugin/docs/GUARD.md).
Releases are tagged `pipeline--vX.Y.Z`; see [plugin/CHANGELOG.md](plugin/CHANGELOG.md).

## Development

```bash
uv sync
bash scripts/check.sh   # claude plugin validate --strict, ruff, black, pytest
```

The plugin's tests are plain pytest on the standard library, so they also run outside this
project's dev environment, on any interpreter that has pytest:

```bash
cd plugin && python3 -m pytest tests
```

Conventions for code, tests, commits and releases: [docs/CONVENTIONS.md](docs/CONVENTIONS.md).

## License

[MIT](LICENSE)
