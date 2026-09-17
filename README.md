# agentic-pipeline

An agentic feature pipeline plugin for [Claude Code](https://claude.com/claude-code):
idea → plan → plan review → implementation → final review → pull request, with a command
guard (protected `main`, production, migrations, file deletion), formatting and
notification hooks, workflow metrics and a project scaffold skill.

The plugin lives in [`plugin/`](plugin/); this repository root is its marketplace
(`wcz-tools`).

## Install

```bash
claude plugin marketplace add https://github.com/wojciechczarnecki/agentic-pipeline.git
/plugin install pipeline@wcz-tools
/pipeline:init
```

Documentation (currently in Polish): [plugin/README.md](plugin/README.md).
Releases are tagged `pipeline--vX.Y.Z`; see [plugin/CHANGELOG.md](plugin/CHANGELOG.md).

## License

[MIT](LICENSE)
