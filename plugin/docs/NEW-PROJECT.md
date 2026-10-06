# Starting a new project

A walk-through from an empty directory to the first feature in the pipeline. It assumes the
plugin is already installed at `--scope user` ([install guide](INSTALL.md)); nothing is
installed per project.

What to expect: `/pipeline:init` is an installer, not a design interview. It sets up the
scaffold and asks at most four questions; the documents it writes are templates to fill in.
The project's vision and requirements come afterwards — in a conversation that fills the
documents, and at the first feature in `/pipeline:idea`.

## 1. Prepare the repository

1. Create an empty repository on GitHub — no README, no `.gitignore`, no licence, so the
   first push does not collide with a commit made on the server.
2. Clone it (or `mkdir`, `git init`, `git remote add origin <url>`).
3. If you already know the stack, set it up **before** init — e.g. `uv init` or
   `npm init`. Init detects the layers from `pyproject.toml` and `package.json` at the
   repository root and one level down (a `backend/pyproject.toml` is a layer too; hidden
   directories and `node_modules` are skipped, deeper projects such as `apps/web` are not
   detected). A layer at the root is named after its stack (`python`, `node`), a layer in a
   subdirectory is named after the directory (`backend`, `frontend`). Init fills `verify`
   and `format` for every layer, in its directory, without asking, and writes a CI job and
   a dependabot entry per layer — the job carries the layer's name, because that name is the
   required check in the repository ruleset. A layer that has no tests or dev tools yet gets
   a placeholder job that passes, so the first CI run is green; replace it with the real
   steps (listed in a comment in the job) once the layer has tests. The Security workflow
   is not covered: it still runs at the repository root and needs a lock file, so on a
   fresh project in a subdirectory, or one without a lock file, its first run is red — a
   known limit (`docs/BACKLOG.md` of the plugin's repository, Init); it is not a required
   check, so it does not block a pull request. In an empty directory
   init asks a second round of questions about the commands instead, or writes `TODO:`
   values and a placeholder CI job.

## 2. Run init

Start `claude` in the project directory and run:

```
/pipeline:init <ProjectName> — one sentence on the problem it solves
```

One round of at most four questions follows, each with a recommendation:

1. **The language of the project files** (`language`: `en` or `pl`) — the documents, specs,
   plans and PR descriptions.
2. **The project name and the problem it solves** — answered already when the argument
   carries them.
3. **The detected layers (name and directory of each), the stack and the full verification
   command.**
4. **Production out of the agent's reach** — the hosts and CLI commands the command guard
   refuses, or "no production".

Claude Code asks for consent before every write into `.claude/`, whatever the permission
rules say — approve those prompts. Init creates `.claude/settings.json`,
`.claude/workflow.json`, `CLAUDE.md`, the documents in `docs/`, `scripts/git-hooks/pre-push`
and `.github/` (CI, security, dependabot, and the repository settings in
`.github/repository/`), appends the missing lines to `.gitignore`, and it does not commit.
It writes no `README.md` and no licence: it lists both as `TODO:` when they are missing.

## 3. The owner's steps after init

1. Fill in the `TODO:` values init lists at the end, and replace each placeholder CI job
   once its layer has tests.
2. Make the first commit and push it to `main` yourself, in a terminal, **before** you enable
   the git hook: the `pre-push` hook refuses every push to `main`, so with the hook on, the
   scaffold could not land. The command guard also refuses commits and pushes on `main` in
   an agent session, so this step stays with you.

   ```
   git add -A && git commit -m "chore: add the project scaffold"
   git push -u origin main
   ```

3. Enable the git hook, once per clone: `git config core.hooksPath scripts/git-hooks`.
4. Apply the repository settings init copied into `.github/repository/` (the guard refuses
   these `gh api` writes to an agent, so they are yours). The ruleset requires a pull
   request, squash merges only and the CI jobs init wrote as checks, and blocks deletion and
   force-pushes; the settings file allows squash merges only and deletes merged branches.
   Then turn on Dependabot alerts, Dependabot security updates and private vulnerability
   reporting:

   ```
   gh api -X POST repos/{owner}/{repo}/rulesets --input .github/repository/ruleset.json
   gh api -X PATCH repos/{owner}/{repo} --input .github/repository/settings.json
   gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts
   gh api -X PUT repos/{owner}/{repo}/automated-security-fixes
   gh api -X PUT repos/{owner}/{repo}/private-vulnerability-reporting
   ```

   GitHub offers a required check only after the workflow has run once, so apply the ruleset
   after the first push has run CI. Renaming a CI job later means renaming it in the ruleset
   too (the file and on GitHub).

**Scaffold through a PR.** If you would rather have the scaffold reviewed like any change,
land only an empty initial commit on `main` and send everything else as a pull request. In
the clone, before you enable the hook, run `git commit --allow-empty -m "chore: initial
commit"` and `git push -u origin main`. Then `git switch -c chore/scaffold`, commit the
scaffold there, push the branch and open the PR with `gh pr create`; the hook can be on from
now on, because the branch is not `main`. Apply the repository settings after that PR's CI
run, as above.

**Decision records (optional).** The plugin ships an ADR template per language in
`templates/docs/adr/` (in the plugin directory, `ADR.en.md` and `ADR.pl.md`). Init does not
copy it; when the project wants one decision record per file, copy the template of your
language into `docs/adr/` and fill it in.

## 4. Fill the documents with the project

After init `docs/PROJECT.md` holds little more than the one-sentence problem. Two routes to
the real content:

- **The fast path** (the usual start): describe the project in the conversation — purpose,
  requirements, architecture, the first stages — and ask the agent to fill
  `docs/PROJECT.md` and `docs/ROADMAP.md`. It presents the intent, you approve, and it works
  on a branch and opens a pull request.
- **The first feature:** `/pipeline:idea` runs a real dialogue with a critical review of the
  idea and ends with a SPEC; after your approval `/pipeline:ship NNN` takes it through the
  plan, the reviews and the implementation to a pull request.

## Languages: the files and the conversation

Two independent settings (the [language contract](../README.md#language-contract)):

- `language` in `.claude/workflow.json` decides the files the pipeline writes and the PR
  descriptions.
- The language the agent talks in — questions, escalations, stage summaries — follows the
  Claude Code session language: the `language` setting in `/config` or in
  `~/.claude/settings.json` (e.g. `"language": "polish"`), set once per machine.
- Commit messages, PR titles, branch names and spec slugs are always English.

English files with a Polish conversation are therefore `"language": "en"` in the project and
`"language": "polish"` in the user settings.

## Worth knowing

- Keep the `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` rule init writes into
  `.claude/settings.json`: without it the stages cannot read the plugin's templates.
- Do not add `enabledPlugins` to the project settings — it creates a duplicate
  `--scope project` install ([the trap](INSTALL.md#the-enabledplugins-trap)).
- An unsure answer can stay a recommendation or a `TODO:` — a second run of init is
  idempotent and leaves your own edits untouched.
