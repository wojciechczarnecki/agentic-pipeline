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

You write only in: `.claude/`, `CLAUDE.md`, `docs/`, `scripts/`, `.github/`, and in
`.gitignore`, which you only append to: you add the lines it lacks (creating the file when it
is missing), and you never reorder or remove a line. Nothing outside these — no source
files, no tool configuration, no `README.md` and no licence file. You do not commit; the
commit belongs to the owner.

## Steps

1. **Survey the ground.** Check whether the directory is a git repository (`git rev-parse
   --is-inside-work-tree`) and which of the files on the list already exist. Autodetect the
   layers: look for `pyproject.toml` and `package.json` at the repository root and in its
   direct subdirectories (depth 1), skipping hidden directories and `node_modules`. Each
   manifest is one layer. A layer at the root is named after its stack (`python`, `node`); a
   layer in a subdirectory is named after the directory (`backend`, `frontend`), and a
   directory holding both manifests gives the layers `<dir>-python` and `<dir>-node`, so
   job names stay unique. No manifest → unknown stack. A project deeper than depth 1
   (`apps/web`) is not detected: the owner names it in the stack question.
   Look into each manifest for the script names (`scripts` in `package.json`, the lint and
   test tools in `pyproject.toml`) — that fills `verify` and `format` without asking. Note
   for each layer whether it declares its lint and test tools, whether it has a test file
   (`test_*.py`, `*_test.py`, `*.test.*` or `*.spec.*` outside `.venv` and `node_modules`),
   and whether a compose file (`compose.yaml`, `compose.yml`, `docker-compose.yml` or
   `docker-compose.yaml`) or an `alembic.ini` sits at the root or in a layer directory. Note
   too whether `.gitignore`, `README.md` and a licence file exist.
2. **Check whether you have `AskUserQuestion`. If you do not — skip this step and go to
   step 3.** You then ask no questions by any route: neither with the tool nor in plain
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
   3. confirmation of the detected layers (name and directory of each), the stack and the
      full verification command;
   4. production out of the agent's reach — hosts and CLI commands (or "no production").
   You ask the questions in the Claude Code session language — the answer about `language`
   governs the files, not the conversation.
   **A second round only when the stack autodetection failed** — you then ask
   for the verification command, the formatting commands and the git hooks directory. In no
   other case is there a second round.
3. **Non-interactive mode** (`claude -p`, no `AskUserQuestion`): you do not ask and do not
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
   ${CLAUDE_PLUGIN_ROOT}`; do not rebuild the templates from memory.
   **Exception — files in `.claude/`:** the guard blocks writing them from the shell
   (they are guard files). Read the template's content with the shell (`cat`), and
   write the target file with the Write tool — the only sanctioned route. A block from the
   shell is not a reason to give up the file.
   The list of files:
   - `.claude/settings.json` — from `templates/settings.json` (permissions allow/ask/deny,
     `extraKnownMarketplaces`). **No `hooks` section** — the hooks
     are provided by the plugin; duplicating them here would run the guard twice.
     **No `enabledPlugins`** — a session in a directory that enables the plugin in
     `.claude/settings.json` sets up a `--scope project` install by itself beside the
     `user` install, and `claude plugin update --scope user` does not update it.
     Substitute two things: in the `ask` rule the git hooks directory path with this
     project's `gitHooksDir` (a rule with another path guards nothing) and the marketplace
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
     in from step 7. The template's `ask` and `deny` rules stay (an edit of
     `.claude/workflow.json` asks, and detaching the plugin is denied). Add `allow` rules
     for the stack you see in the repository, broad per tool: `Bash(uv *)` for a Python
     layer, `Bash(npm *)` for a Node layer and `Bash(docker compose *)` only when a compose
     file (`compose.yaml`, `compose.yml`, `docker-compose.yml` or `docker-compose.yaml`)
     exists at the root or in a layer directory; no rule for a tool the repository does not
     show.
     Like every file in `.claude/` (step 3), its write needs the owner's consent; when a
     non-interactive session does not get it, put the file on the list to add by hand
     (with its content) and finish with success — the rest of the scaffold stands anyway;
   - `.claude/workflow.json` — from `templates/workflow.example.json`, trimmed to this
     project: the `migrations` section stays only when the project has a migration tool;
     `production`, `verify`, `format`, `docs`, `gitHooksDir` filled with the answers
     or `TODO:`. `verify.command` runs the checks of every layer in the layer's directory:
     for a layer in `<dir>`, `cd <dir> && <the layer's checks>` (several layers: each `cd` and
     its checks in a subshell of their own, the subshells joined with `&&`; a root layer
     needs no `cd`), with the
     tools the manifest declares (`uv run ruff check .`, `uv run black --check .`,
     `uv run pytest -q`; the `npm run` scripts it has). Each `format[]` entry for a layer in
     `<dir>` matches `<dir>/…` files and runs its tool for the project in `<dir>`:
     `{"match": "<dir>/*.py", "command": "uv run --project <dir> black -q {file}"}` and the
     same with `ruff check -q --fix` — a Node tool is run from `<dir>/node_modules/.bin/`;
     a root layer keeps the plain form (`*.py`, `uv run black -q {file}`). The `migrations`
     section is also written when an `alembic.ini` sits at the root or in a layer
     directory; `language` is always `en` or `pl` (the answer, the argument, the existing
     value or `en`), never `TODO:`; you do not write the `protectedBranches` key (the
     release channel is protected by the owner by hand, after `/pipeline:init`), and
     you do not write the `implement` section (it was retired in 0.9.0);
     `models` is written as `"models": {"implement": "sonnet"}` and nothing else, so the
     implementer runs on Sonnet and every other stage on the session model — a guess not
     yet measured, which the plugin README marks as such;
   - `CLAUDE.md` — from `templates/CLAUDE.<language>.md` (the template in the language from
     `language`), with the document map rewritten to the paths from `docs.*` (otherwise the
     instructions for agents point at other files than the configuration), and the
     verification command in its commands block (the line under the `TODO` comment)
     set to the same string as `verify.command`;
   - `docs/PROJECT.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`, `docs/DECISIONS.md`,
     `docs/CONVENTIONS.md` — each from `templates/docs/<NAME>.<language>.md`, written under
     the target name without the language suffix. In `docs/CONVENTIONS.md` the "Full
     verification" line carries the same string as `verify.command` too, so `CLAUDE.md`,
     `docs/CONVENTIONS.md` and the configuration never disagree about the commands;
   - `scripts/git-hooks/pre-push` — from `templates/pre-push`, **with the executable bit**
     (`chmod +x`), in the directory `gitHooksDir` names. The template has the literal
     `<gitHooksDir>` in a comment: replace it while copying, with
     `sed 's|<gitHooksDir>|<the configured directory>|' templates/pre-push > <hook path>`
     and then `chmod +x`. Never edit the copied hook in place: the guard refuses a shell
     change to an existing hook. No `<gitHooksDir>` stays in any generated file;
   - `.github/workflows/ci.yml` — one job per layer, assembled into one file (a single
     `name: CI` and one trigger block). Per layer, write the real job (`ci-python.yml`,
     `ci-node.yml`) only when its manifest declares the lint and test tools — for Python
     `ruff` and `pytest` (the `black` step stays only when `black` is declared), for Node a
     `lint` and a test script (the build step stays only with a `build` script) — and the
     layer has a test file. Otherwise write the placeholder job (`ci-python-placeholder.yml`,
     `ci-node-placeholder.yml`): it passes, so the required check exists from the first
     push, and it lists the real steps as comments. Neither layer → `ci-placeholder.yml`
     (job `verify`). Render each template mechanically: for a root layer, delete the lines
     that end in `# subdirectory layer`, strip the ` # root layer` markers and replace
     `<layer>` with the stack name; for a subdirectory layer, delete the lines that end in
     `# root layer`, strip the ` # subdirectory layer` markers and replace `<layer>` and
     `<dir>` with the directory. The job is named after the layer, because the job name is
     the required check in the repository ruleset;
   - `.github/workflows/security.yml` — the same from `security-python.yml` /
     `security-node.yml`; with an unknown stack a file with one job to fill in;
   - `.github/dependabot.yml` — from `templates/github/dependabot.yml`, with one entry per
     layer for its ecosystem (`uv`, `npm`): the entry is copied once per layer with
     `directory: /<dir>` filled in — the layer's directory, nothing for a root layer, which
     gives `/`. The `github-actions` entry stays always, whatever the stack;
   - `.github/repository/ruleset.json` and `.github/repository/settings.json` — from
     `templates/github/repository/`. In the ruleset, replace the single `<job>` entry of
     `required_status_checks` with one `{"context": "<job name>"}` entry per job you wrote
     in `ci.yml`, so the required checks are the jobs that exist. The owner applies both
     files with `gh api --input` (the commands are in
     `${CLAUDE_PLUGIN_ROOT}/docs/NEW-PROJECT.md`): the guard refuses those writes to an
     agent;
   - `.gitignore` — append only the lines it lacks: always `.claude/settings.local.json`;
     for a Python layer `.venv/`, `__pycache__/`, `.pytest_cache/` and `.ruff_cache/`; for
     a Node layer `node_modules/`. Check each line with `grep -qxF`, add a newline first
     when the file does not end in one, and create the file when it is missing.
5. **Existing files.**
   - interactive mode: show the difference (what you add / change) and ask before
     overwriting — separately for every file;
   - non-interactive mode: you never overwrite an existing file — you skip it
     and put it on the list of skipped files.
6. **Idempotence.** A second run does not force the template back: content added
   by the user (a new section in `CLAUDE.md`, a row in the decision register, an item
   in the backlog) stays untouched. You change only what follows from new answers;
   files the new answers do not concern you do not write at all — `git status`
   has to stay silent about them after such a run. The files in `.github/repository/` are
   written only when missing — you never overwrite one, in interactive mode too, because the
   owner may have changed them or applied them already. `.gitignore` gets only the lines it
   lacks, so a second run adds nothing. An answer on the language other than the
   existing `language` changes only `language` in `.claude/workflow.json`: you do not
   translate or replace existing documents with the template in the new language (only a
   file that was missing is created in the new one), and at the closing you tell the owner
   that they stay in their previous language.
7. **Closing.** List for the owner:
   - the list of created, updated and skipped files;
   - the `TODO:` values to fill in;
   - for every placeholder job written into `ci.yml`: `TODO:` replace the job `<layer>`
     with the real steps (the comment in the job lists them) once the layer has tests and
     its tools — the job name stays, so the ruleset does not change;
   - when `production.hosts` stays empty: a warning that the production-host rule is
     inactive until hosts are added (the plugin README, configuration table); you offer no
     list of hosting providers;
   - when the repository has no `README.md`: `TODO:` add a `README.md`; when it has no
     licence file: `TODO:` add a licence file — you write neither;
   - the repository settings: the owner applies `.github/repository/ruleset.json` and
     `settings.json` with the `gh api --input` commands from
     `${CLAUDE_PLUGIN_ROOT}/docs/NEW-PROJECT.md`, after the first push (GitHub offers a
     required check only after the workflow has run once);
   - the architecture decision record template: `${CLAUDE_PLUGIN_ROOT}/templates/docs/adr/`
     holds one per language, and you do not copy it; when the project wants one decision
     record per file, copy `ADR.<language>.md` from there into `docs/adr/`;
   - on a change of `language` — that existing documents stayed in their previous language;
   - the instruction for enabling the git hook: `git config core.hooksPath <gitHooksDir>`
     (once per clone — otherwise `pre-push` does not work);
   - the next step: `/pipeline:idea` for the first feature.

## Guardrails

- Do not guess values that neither the owner nor the code confirmed — that is what `TODO:`
  is for.
- Do not add to `.claude/settings.json` a `hooks` section or permission entries specific
  to tools that cannot be seen in the repository.
- Do not write a `README.md`, a licence file, source files or a project skeleton (dev
  tools, a lock file, a smoke test): `init` is an installer, and the placeholder job keeps
  CI green until the project has tests.
- Do not create the specs directory with a sample spec — the first spec is created by
  `/pipeline:idea`.
- Do not run `git config core.hooksPath` yourself — it is a change to the clone's
  configuration, which the owner makes (and which the guard blocks).
- You do not commit and do not push.
