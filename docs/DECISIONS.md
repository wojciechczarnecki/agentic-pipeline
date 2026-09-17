# Design decisions

Binding architectural and process decisions. Append rows at the end (append-only) — parallel
lanes then merge trivially. Record a decision in the same PR in which it takes effect.

| Date | Decision | Rejected alternatives | Rationale |
|---|---|---|---|
| 2026-09-17 | The plugin was developed inside the owner's private project repository and imported here as release 0.2.0 in a single commit; its earlier history stays private | `git subtree split` with full history | Squash merges had left only a few aggregate commits for the plugin, and the private repository's name must not appear in public history |
| 2026-09-17 | Repository is public, licensed MIT | private repository; Apache-2.0; no licence | The project is meant to be shown and installed from outside; MIT is the simplest permissive licence for developer tools |
| 2026-09-17 | Layout: plugin in `plugin/`, marketplace `wcz-tools` in `.claude-plugin/marketplace.json` at the root with `"source": "./plugin"` | plugin at the root with `"source": "./"` | Project files (`CLAUDE.md`, `docs/`, `scripts/`, CI) live at the root; with `./` they would land in every installer's plugin cache |
| 2026-09-17 | Releases are tagged with `claude plugin tag` (`pipeline--vX.Y.Z`); the version grows with behaviour, not with docs or tests; the owner pushes tags | untagged `main`; version bump on every change | Consumers and rollbacks need stable references; the tag format is the one Claude Code tooling understands |
| 2026-09-17 | Consumers install the marketplace from git over HTTPS (`{"source": "git", "url": "https://github.com/wojciechczarnecki/agentic-pipeline.git"}`) | `github` source (SSH) | The repository is public: background updates need no SSH key or agent, and the README instruction works for anyone |
| 2026-09-17 | Sessions working on this repository use the released plugin from GitHub, not the working tree (`directory: "."`) | `directory` source pointing at this checkout | A stable release guards work on unstable code; with the working tree the guard would also block shell writes to `plugin/` |
| 2026-09-17 | Dev tools (ruff, black, pytest) pinned in `pyproject.toml` `[dependency-groups] dev` with `uv.lock` committed; the plugin keeps zero runtime dependencies | `uvx` without a lock | Reproducible CI and Dependabot updates; hooks run on plain `python3` in any consumer |
| 2026-09-17 | Project documents are in English (`language: "en"`); skills, agents and `plugin/README.md` stay in Polish until translated (`docs/BACKLOG.md`, P2) | Polish project documents; translating in the import | Public repository; `language` is independent of the skills' language, and the import must not change behaviour |
| 2026-09-17 | CI runs `claude plugin validate --strict` for the plugin and the marketplace, ruff, black and pytest on every PR; `claude plugin eval` is manual only | eval as a PR gate | Eval runs a real model: cost, variance and a secret |
