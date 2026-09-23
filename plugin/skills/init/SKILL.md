---
name: init
description: Sets up the pipeline scaffold in a repository — .claude/workflow.json, permissions, CLAUDE.md, project documents, the pre-push hook and CI templates. Use in a new repository or when the guard reports a missing .claude/workflow.json.
argument-hint: <optional: the project name and the problem it solves>
---

# /pipeline:init — the project scaffold for the pipeline

Role: installer, not architect. You set up the minimum the pipeline runs on: the
configuration, documents to fill in, permissions, a git hook and CI. The full vision and the
requirements belong to `/pipeline:idea` at the first feature — do not turn the
initialisation into a design interview.

## Input / output

- Input: a repository (also an empty one, right after `git init`).
- Output: the files from the list below + the printed instruction for enabling the git hook.

## Write scope (absolute)

You write ONLY in: `.claude/`, `CLAUDE.md`, `docs/`, `scripts/`, `.github/`.
Nothing outside these prefixes — no source files, no tool configuration and no
`.gitignore`. You do not commit; the commit belongs to the owner.

## Steps

1. **Survey the ground.** Check whether the directory is a git repository (`git rev-parse
   --is-inside-work-tree`) and which of the files on the list already exist. Autodetect the
   stack: `pyproject.toml` → Python, `package.json` → Node, both → both, neither → unknown.
   Look into the detected files for the script names (`scripts` in `package.json`, the lint
   and test tools in `pyproject.toml`) — that fills `verify` and `format` without asking.
2. **Check whether you have `AskUserQuestion`. If you do not — skip this step and go to
   step 3.** You then ask no questions BY ANY route: neither with the tool nor in plain
   text, and you do not wait for an answer, because there is no one to get it from.
   With `AskUserQuestion` — **ask the questions: one round, at most 4** (every question
   with a recommendation: the first option with the suffix "(Recommended)" in the label):
   1. the language of the project files (`language`): `en` "(Recommended)" or `pl` — you
      recommend `en`, because it is the default value and the language readers from outside
      the project expect; when `.claude/workflow.json` already has a supported `language`
      (`en` or `pl`), you recommend that existing value — accepting the recommendation does
      not change the project's language; the answer decides the documents, specs, plans and
      the PR description;
   2. the project name and the problem it solves (one sentence);
   3. confirmation of the detected stack and of the full verification command;
   4. production out of the agent's reach — hosts and CLI commands (or "no production").
   You ask the questions in the Claude Code session language — the answer about `language`
   governs the files, not the conversation.
   **A second round only when the stack autodetection failed** — you then ask
   for the verification command, the formatting commands and the git hooks directory. In no
   other case is there a second round.
3. **Non-interactive mode** (`claude -p`, no `AskUserQuestion`): you do NOT ask and do NOT
   block. A question asked in prose and ending the reply with a request for a decision is a
   block too — you finish the task to the end on the values you have, not with a question.
   Claude Code treats files in `.claude/` as sensitive and asks for consent to write them
   regardless of the permission rules, so the full set of files is created only in a session
   started with `--permission-mode bypassPermissions`; with a weaker mode you write
   everything outside `.claude/`, and you list the skipped files with their content to paste
   and finish with success. Missing values you write as `TODO:` — in `.claude/workflow.json`
   (e.g. `"command": "TODO: <verify command>"`, with the description after `TODO:` in the
   language from `language`) and in the headers of the documents.
   Exception — `language`: you take it from the argument, when the argument names a language
   (`en`, `pl` or its name: English, Polish); without such an argument
   you keep the supported `language` from the existing `.claude/workflow.json`, and when
   there is none — you set `en`; never with a `TODO:` marker, because `en` is the default
   value. The language the prompt is written in is not such an indication.
   You finish with success, listing the values to fill in.
4. **Generate the files** from `${CLAUDE_PLUGIN_ROOT}/templates/`, substituting the answers.
   **Move the templates with the shell** (`cp`, `cat`, `sed`), not with the Read/Glob tools:
   the plugin directory lies outside the session's working directory, so a read with a tool
   may be blocked there or wait for a consent that does not exist in non-interactive mode.
   First copy the file into the project, only then edit it with the Edit tool. Should the
   shell not reach the plugin directory either — stop without writing and ask for `--add-dir
   ${CLAUDE_PLUGIN_ROOT}`; do NOT rebuild the templates from memory.
   **Exception — files in `.claude/`:** the guard does not let their write from the shell
   through (they are guard files). READ the template's content with the shell (`cat`), and
   write the target file with the Write tool — the only sanctioned route. A block from the
   shell is not a reason to give up the file.
   The list of files:
   - `.claude/settings.json` — from `templates/settings.json` (permissions allow/ask/deny,
     `extraKnownMarketplaces`). **No `hooks` section** — the hooks
     are provided by the plugin; duplicating them here would run the guard twice.
     **No `enabledPlugins`** — a session in a directory that enables the plugin in
     `.claude/settings.json` sets up a `--scope project` install by itself beside the
     `user` install, and `claude plugin update --scope user` does not raise it.
     Substitute two things: in the `ask` rule the git hooks directory path with this
     project's `gitHooksDir` (a rule with another path guards emptiness) and the marketplace
     source. Read the marketplace name from the path `${CLAUDE_PLUGIN_ROOT}`
     (`…/<marketplace>/<plugin>/<version>/`): the same value goes into the key
     `extraKnownMarketplaces` and into the rule
     `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` in `permissions.allow` —
     without this rule the stages cannot load the plugin's templates or section map.
     `ref` is always `"stable"` — the release channel, a branch moved
     to every new tag; do not derive it from the version in the path, because a tag pin
     forces the marketplace to be registered again on every release. Take the `url` from the
     session's list of marketplaces. When the path has another shape or the url is unknown —
     leave `TODO:` at that value (in both places) and name it on the list of values to fill
     in from step 7.
     This is the only generated file whose write needs the owner's consent; when a
     non-interactive session does not get it, put the file on the list to add by hand
     (with its content) and finish with success — the rest of the scaffold stands anyway;
   - `.claude/workflow.json` — from `templates/workflow.example.json`, trimmed to this
     project: the `migrations` section stays only when the project has a migration tool;
     `production`, `verify`, `format`, `docs`, `gitHooksDir` filled with the answers
     or `TODO:`; `language` is always `en` or `pl` (the answer, the argument, the existing
     value or `en`), never `TODO:`; you do not write the `protectedBranches` key (the
     release channel is protected by the owner by hand, after `/pipeline:init`);
   - `CLAUDE.md` — from `templates/CLAUDE.<language>.md` (the template in the language from
     `language`), with the document map rewritten to the paths from `docs.*` (otherwise the
     instructions for agents point at other files than the configuration);
   - `docs/PROJECT.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`, `docs/DECISIONS.md`,
     `docs/CONVENTIONS.md` — each from `templates/docs/<NAME>.<language>.md`, written under
     the target name without the language suffix;
   - `scripts/git-hooks/pre-push` — from `templates/pre-push`, **with the executable bit**
     (`chmod +x`); the directory path matching `gitHooksDir`;
   - `.github/workflows/ci.yml` — assembled from variants by the detected stack:
     Python → the job from `templates/github/workflows/ci-python.yml`, Node → the job
     from `ci-node.yml`, both → BOTH jobs in one file, neither → `ci-placeholder.yml`;
   - `.github/workflows/security.yml` — the same from `security-python.yml` /
     `security-node.yml`; with an unknown stack a file with one job to fill in;
   - `.github/dependabot.yml` — from `templates/github/dependabot.yml`, with entries
     for the ecosystems of the detected stack; the `github-actions` entry stays ALWAYS,
     whatever the stack.
5. **Existing files.**
   - interactive mode: show the difference (what you add / change) and ASK before
     overwriting — separately for every file;
   - non-interactive mode: you NEVER overwrite an existing file — you skip it
     and put it on the list of skipped files.
6. **Idempotence.** A second run does not force the template back: content added
   by the user (a new section in `CLAUDE.md`, a row in the decision register, an item
   in the backlog) stays untouched. You change only what follows from NEW answers;
   files the new answers do not concern you do not write at all — `git status`
   has to stay silent about them after such a run. An answer on the language other than the
   existing `language` changes only `language` in `.claude/workflow.json`: you do not
   translate or replace existing documents with the template in the new language (only a
   file that was missing is created in the new one), and at the closing you tell the owner
   that they stay in their previous language.
7. **Closing.** List for the owner:
   - the list of created, updated and skipped files;
   - the `TODO:` values to fill in;
   - on a change of `language` — that existing documents stayed in their previous language;
   - the instruction for enabling the git hook: `git config core.hooksPath <gitHooksDir>`
     (once per clone — otherwise `pre-push` does not work);
   - the next step: `/pipeline:idea` for the first feature.

## Guardrails

- Do not guess values that neither the owner nor the code confirmed — that is what `TODO:`
  is for.
- Do not add to `.claude/settings.json` a `hooks` section or permission entries specific
  to tools that cannot be seen in the repository.
- Do not create the specs directory with a sample spec — the first spec is created by
  `/pipeline:idea`.
- Do not run `git config core.hooksPath` yourself — it is a change to the clone's
  configuration, which the owner makes (and which the guard blocks).
- You do not commit and do not push.
