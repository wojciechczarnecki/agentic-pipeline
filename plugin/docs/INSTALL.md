# Installing the pipeline plugin

The short version is in the [plugin README](../README.md#installation). This guide covers
the release channel, the install scope, the project settings, updating, the one-time
migration, verification, opting a repository out and the known traps.

The command guard refuses `claude plugin uninstall`, `disable` and
`marketplace remove` aimed at this plugin or its marketplace inside an agent session, and
shell edits of the plugin's files and install state: the owner runs those commands from
this guide in a terminal, outside an agent session.

## From a local path

For a preview, or for work on the plugin itself:

```bash
claude --plugin-dir ./plugin          # a one-off session with the plugin
claude plugin validate --strict ./plugin
```

## Through a marketplace — a local directory

```bash
claude plugin marketplace add /path/to/agentic-pipeline-clone
/plugin install pipeline@wcz-tools
```

## Through a marketplace — the GitHub repository

The repository is public and reached over HTTPS, with no SSH key; the release channel is
`stable`:

```bash
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'
claude plugin install pipeline@wcz-tools --scope user
```

## The release channel

`stable` is a branch the owner moves to every new release tag (`pipeline--vX.Y.Z`).
Without a `ref` a consumer tracks `main`, that is unreleased code. A marketplace's `ref` is
global per machine (`~/.claude/plugins/known_marketplaces.json`), and `install` and
`update` take no version — hence a channel rather than a pin on a tag: a pin would force
`marketplace remove` and a reinstall in every project on each release. Moving `stable` is
the owner's move; in the plugin's own repository the guard keeps agent sessions off it
through `"protectedBranches": ["stable"]` in `.claude/workflow.json`, not through `deny`
rules.

## The `user` scope — one install per machine

The plugin works in every directory, without installing it separately in each repository
and each clone. A `--scope project` install is tied to a directory (an entry with
`projectPath` in `~/.claude/plugins/installed_plugins.json`; in another repository
`claude plugin list` shows the plugin as `enabled`, yet the `/pipeline:*` commands are
missing) and `claude plugin update --scope user` does not lift it — do not use it; the only
install is `user`.

## Project settings

In the project's `.claude/settings.json` (shaped like `templates/settings.json` in the
plugin) declare only the source — that way a fresh clone on another machine learns where
the plugin comes from:

```json
{
  "extraKnownMarketplaces": {
    "wcz-tools": {
      "source": {
        "source": "git",
        "url": "https://github.com/wojciechczarnecki/agentic-pipeline.git",
        "ref": "stable"
      }
    }
  }
}
```

## Reading the plugin's templates

The stages read the SPEC and PLAN templates and the section map from the plugin's own
directory with `Read` at run time. A stage subagent under `/pipeline:ship` cannot answer
a permission prompt, so the project allows that directory up front in `permissions.allow`
of `.claude/settings.json` — `/pipeline:init` writes it, with the marketplace name of the
install:

```json
{
  "permissions": {
    "allow": ["Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)"]
  }
}
```

The rule covers every version of the install, so it survives `claude plugin update`. It may
live in `~/.claude/settings.json` instead, for every project on the machine; project settings
are what `init` writes, because the rule then travels with the repository and a fresh clone
works without an extra step.

A `--plugin-dir` session (a canary, work on the plugin) loads the plugin from a clone, which
the cache rule does not cover. Allow the clone with an absolute rule — `//` marks an
absolute path, while a single `/` is read relative to the settings file:

```json
{ "permissions": { "allow": ["Read(//home/me/agentic-pipeline/plugin/**)"] } }
```

Without a covering rule a stage stops at its first read: under `/pipeline:ship` with
`RESULT: ESCALATE` naming the file and the rule, in an interactive `idea` or `plan` with the
same message. The command guard warns about it once per session, before a stage gets there,
and names the exact rule to add.

## The `enabledPlugins` trap

**A project does NOT declare `"enabledPlugins": {"pipeline@<name>": true}`.** A session
starting in a directory that enables the plugin this way creates a `--scope project`
install on its own — even beside an existing `user` install — and `claude plugin update
--scope user` lifts only the `user` entry, so the `project` duplicate stays on its old
version for good (measured 2026-09-21: `claude plugin list` shows the plugin twice; without
`enabledPlugins`, with `extraKnownMarketplaces` alone, no `project` entry appears and the
plugin loads from the `user` install as usual). Remove an existing duplicate like this:
first commit `.claude/settings.json` without `enabledPlugins` (otherwise `git checkout`
restores the declaration and the next session creates the duplicate again), then, in the
repository directory:

```bash
claude plugin uninstall pipeline@<name> --scope project
git checkout -- .claude/settings.json   # the command can strip the marketplace block
```

Run it in a terminal: inside an agent session the guard refuses the `uninstall`.

## Updating

To a new release, without registering again:

```bash
claude plugin marketplace update wcz-tools && claude plugin update pipeline@wcz-tools --scope user
```

Then start a new session — a running one keeps what it loaded at startup.

## One-time migration from a registration on a tag

This applies to a marketplace added earlier as `'<url>#pipeline--vX.Y.Z'` or without a
`ref`. Check the marketplace entry in `~/.claude/plugins/known_marketplaces.json`: its
`source.ref` must read `"stable"`. If it does not:

```bash
claude plugin marketplace remove <name>
claude plugin marketplace add '<url>#stable'
claude plugin install pipeline@<name> --scope user
git checkout -- .claude/settings.json   # in EVERY repository with the plugin
```

**`remove` uninstalls the plugin in ALL projects** — the marketplace is the install's
source. **All three commands (`remove`, `add`, `install`) delete
`extraKnownMarketplaces` from `.claude/settings.json`** (the project's and
`~/.claude/settings.json`) and none of them restores it — hence `git checkout` in every
repository that has the block (without `enabledPlugins`, see above). Both effects are
silent: a session without the plugin has no command guard and reports nothing. The guard
refuses `marketplace remove` of this plugin's marketplace in an agent session, so the
migration is run in a terminal. After the migration start a new session.

## Verification

After an install, an update or a migration, in a new session: `claude plugin list` shows
the plugin at the released version in the `user` scope — and only there, with no `project`
entry — and a command the guard blocks — e.g. `sed -i` on `.claude/settings.json` — is
actually refused, with the version in the path it reports. Only the second test proves that
the plugin is loaded in this repository; the first proves only that the install is correct.

## Switching it off in a repository that does not want the plugin

With a `user` install the plugin — the command guard included — works everywhere, also
where commits go straight to `main` and the guard would block them. Switch it off in that
repository's `.claude/settings.json`:

```json
{ "enabledPlugins": { "pipeline@wcz-tools": false } }
```

This is the only legitimate project use of `enabledPlugins` — with the value `false` only.

## Setting up a project

In every project run `/pipeline:init` once to create `.claude/workflow.json` and the rest
of the scaffold. A non-interactive session (`claude -p`) needs
`--permission-mode bypassPermissions`: Claude Code treats files in `.claude/` as sensitive
and asks before writing them regardless of permission rules. In a weaker mode init writes
everything outside `.claude/` and prints the content of the files it skipped.
