---
type: llm
weight: 1
---

The task: `/pipeline:init` runs unattended in an empty repository with an argument that
names the language `pl`. The prompt itself is in English on purpose, so Polish documents
can only come from the argument.

The response is correct when the agent:

1. finishes without stopping for a question and without saying it cannot continue without
   an answer;
2. sets `language` to `"pl"` in `.claude/workflow.json` — written to the file, or in the
   content it prints for pasting;
3. generates `CLAUDE.md` and the files in `docs/` in Polish: the first lines it shows are
   Polish (for example the roadmap title `# Roadmapa`, the backlog column `Priorytet`, the
   heading `## Projekt` in `CLAUDE.md`);
4. ends with the list of files and the `TODO:` values.

The response is incorrect when the documents it shows are English, when `language` is
`"en"` or left as a `TODO` marker, or when the agent stops to ask a question or waits for
an answer.

The evaluation run blocks writes to `.claude/` regardless of permission rules, so a missing
`.claude/settings.json` and `.claude/workflow.json` is a limit of the environment, NOT the
skill's behaviour. Listing them with their content for pasting fully satisfies point 2,
and the response must not be judged incorrect for it.
