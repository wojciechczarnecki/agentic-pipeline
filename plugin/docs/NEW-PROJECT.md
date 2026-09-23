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
   `npm init`. Init detects the stack from `pyproject.toml` and `package.json`, fills
   `verify` and `format` from them without asking, and picks the matching CI, security and
   dependabot templates. In an empty directory it asks a second round of questions about
   the commands instead, or writes `TODO:` values and a placeholder CI job.

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
3. **The detected stack and the full verification command.**
4. **Production out of the agent's reach** — the hosts and CLI commands the command guard
   refuses, or "no production".

Claude Code asks for consent before every write into `.claude/`, whatever the permission
rules say — approve those prompts. Init creates `.claude/settings.json`,
`.claude/workflow.json`, `CLAUDE.md`, the documents in `docs/`, `scripts/git-hooks/pre-push`
and `.github/` (CI, security, dependabot), and it does not commit.

## 3. The owner's steps after init

- Enable the git hook, once per clone: `git config core.hooksPath scripts/git-hooks`.
- Fill in the `TODO:` values init lists at the end.
- Make the first commit and push to `main` yourself, in a terminal — the command guard
  refuses commits and pushes on `main` in an agent session.
- On GitHub, add a ruleset for the default branch: a pull request required, squash merges
  only, the CI check green, no deletion and no force-push. The check's name is the CI job's
  name (`python`, `node` or `verify` in the templates), and GitHub offers it only after the
  workflow has run once.

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
