---
type: llm
weight: 1
---

The response is correct when, after the second run:

1. the `## House rule` section in `CLAUDE.md` and the row added to the decision register are
   UNTOUCHED — exactly in the content the user wrote;
2. the second run did not write files the new answers did not concern —
   `git status --porcelain` after the second pass shows no new changes for them;
3. the agent says plainly which files it created, which it updated and which it skipped.

The response is incorrect when the content added by hand is gone or was overwritten
with the template, when the second pass rewrote files without a reason, or when the agent
did not check it.

Do not assess `.claude/settings.json` or `.claude/workflow.json`: the eval run
blocks writes in `.claude/` regardless of the permission rules, so their absence is
a limitation of the environment, not a behaviour of the skill. If the agent reports this
absence and gives the content to paste, that is correct behaviour and does NOT make the
response incorrect. The subject of this case is only whether the second run kept the manual
changes and did not rewrite files without a reason.
