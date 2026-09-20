# Roadmap

Tick an item in the same PR that delivers it, after green verification — the merge makes it
true, and the roadmap must not lie.

## Stage 1 — Standalone public repository

- [x] Import of the plugin 0.2.0 from the owner's private project repository (tag `pipeline--v0.2.0`)
- [x] Project scaffold: documents, configuration, dev tools, CI and the manual eval workflow
- [x] Post-import cleanup: the marketplace source declares the release tag, what the GitHub
      rulesets do and do not enforce is written down, project documents de-duplicated
      (each machine still needs the one-time marketplace re-registration from `CLAUDE.md`)

## Stage 2 — Rules the agent executes

- [x] Rules where the agent executes them, and install instructions that match reality:
      the metrics format in every stage skill plus `workflow_metrics.py --check`, the stage
      contract in `plugin/agents/*.md`, slimmed configuration and visual-artifact prose, and
      a git + HTTPS marketplace source pinned with `ref`
      (`specs/001-executable-rules-and-release-pinning/SPEC.md`)

## Later

### Reach

- [ ] Translate skills and agents into English (`docs/BACKLOG.md`, P2)
