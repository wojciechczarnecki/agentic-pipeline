---
type: llm
weight: 1
---

The response is correct when the agent:

1. does NOT stop on a question to the user and does not declare that without an answer
   it cannot continue;
2. creates the project scaffold within the allowed scope (`.claude/`, `CLAUDE.md`, `docs/`,
   `scripts/`, `.github/`) — a file it could not write it names with the content
   to paste instead of skipping it in silence;
3. writes values confirmed neither by the user nor by the code as `TODO:`
   instead of guessing them — with one exception: `language` without an indication in the
   argument is `"en"` without a `TODO:` marker, because `en` is the default value;
4. finishes with success: prints the list of files, the list of `TODO:` and the instruction
   for enabling the git hook;
5. generates `CLAUDE.md` and the files in `docs/` in English (the first lines shown are
   English, e.g. the title `# Roadmap`, the backlog column `Priority`) and sets `language`
   to `"en"` — the language of this prompt does not indicate the language of the documents.

The response is incorrect when the agent waits for an answer, stops working because there is
none, guesses values without a `TODO:` marker, writes files outside the allowed scope,
generates the documents in Polish, sets `language` to `"pl"` because the conversation is in
Polish, or leaves a `TODO` marker at `language`.

The eval run blocks writes in `.claude/` regardless of the permission rules, so the absence
of `.claude/settings.json` and `.claude/workflow.json` is a limitation of the environment,
and NOT a behaviour of the skill. Naming them with the content to paste satisfies point 2 in
full, and the response may not be judged incorrect for that reason.
