# Roadmap

Tick an item in the same PR that delivers it, after green verification — the merge makes it
true, and the roadmap must not lie.

## Stage 1 — Standalone public repository

- [x] Import of the plugin 0.2.0 from the owner's private project repository (tag `pipeline--v0.2.0`)
- [x] Project scaffold: documents, configuration, dev tools and CI (the manual eval workflow was removed on 2026-09-20; `claude plugin eval` runs locally — `docs/DECISIONS.md`)
- [x] Post-import cleanup: the marketplace source declares the release tag, what the GitHub
      rulesets do and do not enforce is written down, project documents de-duplicated
      (each machine still needs the one-time marketplace re-registration from `CLAUDE.md`)

## Stage 2 — Rules the agent executes

- [x] Rules where the agent executes them, and install instructions that match reality:
      the metrics format in every stage skill plus `workflow_metrics.py --check`, the stage
      contract in `plugin/agents/*.md`, slimmed configuration and visual-artifact prose, and
      a git + HTTPS marketplace source pinned with `ref`
      (`specs/001-executable-rules-and-release-pinning/SPEC.md`)
- [x] 0.3.1: the checker runs without a permission prompt — stage skills call it through
      `PATH` and the allow rule is `Bash(workflow_metrics.py *)`, since permission rules do
      not substitute `${CLAUDE_PLUGIN_ROOT}` (`docs/DECISIONS.md`, 2026-09-21)
- [x] 0.3.1: releases reach consumers through the `stable` channel and a single
      `--scope user` install, updated without re-registering the marketplace
      (`docs/DECISIONS.md`, 2026-09-21)

## Later

### Reach

- [ ] Translate skills and agents into English (`docs/BACKLOG.md`, P2)
