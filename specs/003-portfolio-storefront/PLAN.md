# PLAN 003 — Portfolio storefront

## Owner summary

- **Approach:** Documentation only. The installation text moves verbatim from
  `plugin/README.md` into a new `plugin/docs/INSTALL.md` (the existing installation tests
  follow it); the root `README.md` is rewritten for an outside reader under the display
  name *Spec-Driven Workflow*; `CONTRIBUTING.md` and `SECURITY.md` are added; the display
  name reaches `docs/PROJECT.md`, `CLAUDE.md` and both manifest descriptions. The claims in
  the documents are pinned by a new `tests/test_documents.py` at the repository root: every
  relative link and anchor resolves, the guard refusal quoted in the README is compared
  with the output of `plugin/bin/guard.py`, and the required sections are present.
  `scripts/check.sh` and CI start running the root `tests/` directory. Today they run only
  `plugin/tests`, and `tests/test_release_gate.py` already sits there unrun. GitHub
  Releases and the *About* description come after gate 2.
- **Main risks:** the guard refuses `gh repo edit` for agents ("changing repository
  settings is the owner's call"), and AC19 forbids changing the guard. The *About*
  description is therefore set by **you** with one command from the final review's gate 2
  entry "Steps 8–9", which you run before answering the gate. The
  agent does not work around the refusal through `gh api`. The topics already meet AC16
  (checked 2026-09-21). `gh release create` is not in the `allow` list, so it asks for
  permission. Moving the installation text must not lose any assertion the tests make
  today.
- **New dependency:** no. Mermaid and the shields.io badges are rendered by GitHub
  (SPEC → "Owner decisions").
- **Data migration:** no (SPEC → "Owner decisions").
- **Manual scenarios for the owner:** 3. Check the rendered README on GitHub (mermaid,
  badges, links). At gate 2, run `gh repo edit --description` and accept the "Steps 8–9"
  entry; afterwards look over the Releases page. Do the profile pin and the social preview
  image.

## Approach

**Where the tests live.** Assertions about `plugin/README.md` and `plugin/docs/*` stay in
`plugin/tests/test_readme.py`, because those files ship with the plugin. Assertions about
repository documents (root `README.md`, `CONTRIBUTING.md`, `SECURITY.md`) go into a new
`tests/test_documents.py` at the repository root. That is where repository rules already
live (`tests/test_release_gate.py` explains why: the plugin stays project-independent,
and `plugin/tests` must run from a bare `plugin/` checkout). The same file holds the
cross-document link check (AC11), because only the repository root sees all six
documents. `pyproject.toml` already lists `tests` in `testpaths`, but `scripts/check.sh`
and `.github/workflows/ci.yml` pass `plugin/tests` explicitly, so both change to
`plugin/tests tests`. Considered and rejected: putting the root-document tests into
`plugin/tests` with `parents[2]`. That breaks `cd plugin && python3 -m pytest tests`
outside this repository, which the root README promises. Do **not** name the new file
`test_readme.py`. Both test directories have no `__init__.py`, so pytest would refuse the
duplicate basename.

**Install guide.** `plugin/docs/INSTALL.md` takes lines 13–133 of `plugin/README.md`
unchanged in substance. The bold lead-ins become `##` headings: local path, marketplace,
release channel, user scope, project settings, the `enabledPlugins` trap, updating,
one-time migration, verification, opting out, setting up a project. The file sits beside
`GUARD.md` (SPEC decision: `plugin/` reaches the consumer's cache). `plugin/README.md` →
`## Installation` keeps three commands (marketplace add on `#stable`, install at
`--scope user`, `/pipeline:init`) and a link `docs/INSTALL.md`, which covers updating. The existing assertions follow the
text: `installation_section()` becomes `install_guide()`, which returns the whole of
`plugin/docs/INSTALL.md`. Every current assertion stays as it is, including
`test_installation_covers_a_local_path_and_a_repository`, which today splits the README
itself. That is how AC9 holds: "every assertion … is made about this file".

**Root README layout** (headings exact, because tests find them; order as listed):

1. `# Spec-Driven Workflow`
2. One badge line: CI, licence, version (below).
3. The pitch: **one plain-text sentence** with no markdown (no links, backticks or
   emphasis), containing "Claude Code" and ending with `.`, at most 350 characters. The
   same sentence becomes the GitHub *About* description (AC16), which is why it must be
   plain. Proposal, which the implementer may tighten: "A Claude Code plugin that takes a
   feature from an approved spec to a reviewed pull request, with owner gates between the
   stages and a command guard that stops the agent from pushing to main, merging its own
   PR or touching production."
4. A short paragraph containing the names sentence (AC8): *Spec-Driven Workflow* is the
   project, `agentic-pipeline` the repository and `pipeline` the plugin
   (`/pipeline:*`, `pipeline@wcz-tools`).
5. `## How it works`: the mermaid block (below), then one paragraph on the stages running
   as subagents with fresh context.
6. `## The guard in action`: the refusal block (below), a sentence on best effort, and a
   link `plugin/docs/GUARD.md`.
7. `## Why not Spec Kit?` (AC5).
8. `## Requirements & opinions` (AC6).
9. `## What's deliberately not here` (AC7).
10. `## Install`: exactly two commands in one ```` ```bash ```` block (marketplace add
    `'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'`, install
    `pipeline@wcz-tools --scope user`), then the link `plugin/docs/INSTALL.md` (updating,
    the channel, the opt-out and the traps).
11. `## Quickstart`: "Install first ([Install](#install)), then:" followed by three
    commands in one fenced block: `claude` (run in your project's directory),
    `/pipeline:init` and `/pipeline:idea`. That makes five commands from nothing to
    `/pipeline:idea` (AC8), and the install section keeps ≤ 3 (AC10). Two blocks, not one
    five-line block, because AC10 caps the install section at three commands.
12. `## Documentation`: links to `plugin/docs/INSTALL.md`, `plugin/docs/GUARD.md`,
    `plugin/README.md#workflow-metrics`, `plugin/README.md`, `CONTRIBUTING.md`,
    `SECURITY.md` and `plugin/CHANGELOG.md`.
13. `## Development`: the current short dev section trimmed to a pointer to
    `CONTRIBUTING.md`, keeping `cd plugin && python3 -m pytest tests`.
14. `## License`: `[MIT](LICENSE)`.

**Badges** (AC2), all linked:
- CI: `https://github.com/wojciechczarnecki/agentic-pipeline/actions/workflows/ci.yml/badge.svg?branch=main`
  → `https://github.com/wojciechczarnecki/agentic-pipeline/actions/workflows/ci.yml`
- Licence: `https://img.shields.io/badge/license-MIT-blue` → `LICENSE`. A static badge,
  so it does not depend on GitHub's licence detection.
- Version: `https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fwojciechczarnecki%2Fagentic-pipeline%2Fmain%2Fplugin%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version`
  → `plugin/CHANGELOG.md`. It reads `main`, so it follows a bump without an edit.

**Mermaid** (AC3): a `flowchart LR` whose node labels contain, verbatim, `idea`, `plan`,
`plan review`, `implement`, `final review` and `PR`, and three gate nodes labelled
`Gate 1: owner approves the SPEC`, `Gate 2: owner decides on review findings` and
`Gate 3: owner merges`. The order is idea → Gate 1 → plan → plan review → implement →
final review → Gate 2 → PR → Gate 3. Keep labels free of characters mermaid treats
specially (quote the labels: `A["plan review"]`).

**Guard refusal block** (AC4), measured 2026-09-21 on the working tree, in a scratch repo
on a feature branch with `.claude/workflow.json` = `{}` (exit code 2, stderr):

```text
$ git push origin main
Blocked by the pipeline guard: pushing to main: main changes only through a PR merged by the owner; work on a feature branch
```

In the README this is a ```` ```text ```` block whose first line is `$ git push origin
main` and whose remaining lines are the guard's stderr. The test re-runs the command
through `plugin/bin/guard.py` and compares the output.

**Why not Spec Kit?** (AC5): Spec Kit plans (spec → plan → tasks) and this plugin
enforces. The claim is the command guard and the checked metrics (`workflow_metrics.py
--check`), **not** hook-enforced approval gates, because SpecForge and gate-oriented-sdd
have those too and neither guards shell commands. Every sentence about another tool
carries "(checked YYYY-MM-DD)". Claims already recorded with a date in
`docs/ROADMAP.md` (Stage 4, first item) and `docs/BACKLOG.md` (Spec Kit rows) may reuse
2026-09-21. Any **new** claim about another tool has to be checked on the day of
implementation (WebFetch/WebSearch on the tool's repository) and dated with that day. Do
not state anything about another tool that has not been checked.

**Requirements & opinions** (AC6): GitHub with the `gh` CLI; squash merges; GitHub
rulesets (the `main` ruleset as the server-side layer); `python3` on the machine (the hooks
run on the standard library and fail open without it); migration guarding is Alembic only.
Two short lists follow: `### Who it is for` and `### Who it is not for`.

**What's deliberately not here** (AC7): no runtime dependencies; no hosting outside Claude
Code (`docs/PROJECT.md` → Out of scope); the guard is best effort, not a sandbox, with a
link `plugin/docs/GUARD.md#known-limits`. Optionally also "no hook-enforced approval
gates beyond the owner's merge", but only if it is true of the code.

**CONTRIBUTING.md** (AC12): sections for issues (bug report, feature proposal), dev setup
(`uv sync`, `bash scripts/check.sh`, `git config core.hooksPath scripts/git-hooks`), a link
`docs/CONVENTIONS.md`, the PR flow (branch, PR to `main`, squash, the `plugin` check must
be green) and the language note: skills, agents and templates are in Polish until Stage 8
(link `docs/ROADMAP.md`); documents and code are English.

**SECURITY.md** (AC13): the supported version is the release on the `stable` channel (the
latest `pipeline--v*` tag). Report through GitHub private vulnerability reporting
(`https://github.com/wojciechczarnecki/agentic-pipeline/security/advisories/new`), not
public issues. The guard is best effort (link `plugin/docs/GUARD.md#known-limits`), and a
way past the guard counts as a security report: a command the guard should refuse but lets
through, beyond the known limits.

**GitHub-style anchors** for the link check: lower-case the heading text, drop every
character that is not a word character (Unicode `\w`), a space or a hyphen, replace each
space with `-`, and add `-1`, `-2` … to repeats. Examples the test pins:
`Known limits` → `known-limits`, `Requirements & opinions` → `requirements--opinions`,
`Why not Spec Kit?` → `why-not-spec-kit`,
``Project configuration — `.claude/workflow.json` `` → `project-configuration--claudeworkflowjson`.

**Releases and About (after gate 2).** `gh release create <tag> --verify-tag` aborts if the
tag is missing on the remote, so no tag is ever created. Notes come from
`awk -v v=X.Y.Z '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md`, which
prints the section body without its heading. Titles are `pipeline X.Y.Z`. Create them
oldest first with `--latest=false`, and 0.3.4 last with `--latest`. The guard lets
`gh release create` through. It refuses `gh repo edit` (`check_gh` in
`plugin/bin/guard.py`), so the owner runs that one command. A `gh api -X PATCH repos/…`
workaround is forbidden: it would be a guard bypass by the agent.

Reused: `strip_code` and the Polish check pattern from `plugin/tests/test_readme.py`
(copied into the root test as a 10-line helper, not imported, because importing a test
module drags its fixtures and imports); the consumer-name fragments from
`plugin/tests/test_no_domain_references.py` (`CASE_INSENSITIVE`, `CASE_SENSITIVE`),
imported so there is no third copy of the list. Import them by putting `plugin/tests` on
`sys.path`, and drop the `scripts/check` pattern, which root documents legitimately
contain. The guard is run the way `plugin/tests/test_guard.py::run_hook` runs it:
`[sys.executable, guard.py]`, a JSON payload on stdin with `tool_input.command`, `cwd`
and `session_id`, and `CLAUDE_PROJECT_DIR` in the environment.

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 4 | `tests/test_documents.py::test_readme_opens_with_the_display_name_and_the_pitch` |
| AC2 | 4 | `tests/test_documents.py::test_readme_shows_the_three_badges` |
| AC3 | 4 | `tests/test_documents.py::test_readme_diagram_names_every_stage_and_gate` |
| AC4 | 4 | `tests/test_documents.py::test_readme_guard_block_matches_the_guard` |
| AC5 | 4 | `tests/test_documents.py::test_why_not_spec_kit_states_the_claim_with_dates` |
| AC6 | 4 | `tests/test_documents.py::test_requirements_and_opinions` |
| AC7 | 4 | `tests/test_documents.py::test_whats_deliberately_not_here` |
| AC8 | 4 | `tests/test_documents.py::test_quickstart_reaches_idea_in_five_commands`, `test_readme_explains_the_three_names`, `test_readme_links_the_documentation` |
| AC9 | 2 | `plugin/tests/test_readme.py` installation tests re-pointed at `install_guide()` (all of them, `test_installation_covers_a_local_path_and_a_repository` included) + `test_install_guide_covers_verification_and_init`; `test_no_polish_outside_code[docs/INSTALL.md]` |
| AC10 | 2, 4, 5 | `plugin/tests/test_readme.py::test_the_installation_section_is_short_and_links_the_guide`; `tests/test_documents.py::test_readme_install_is_short_and_links_the_guide`; step 5 grep on `CLAUDE.md` |
| AC11 | 1, 2, 3, 4 | `tests/test_documents.py::test_relative_links_resolve`, `test_github_anchor_slugs`, `test_the_link_check_covers_the_six_documents`, `test_plugin_documents_link_inside_the_plugin` |
| AC12 | 3 | `tests/test_documents.py::test_contributing_covers_the_workflow` |
| AC13 | 3 | `tests/test_documents.py::test_security_policy` |
| AC14 | 8 | step 8 verification commands (`gh release list`, body diff, `git ls-remote` diff) |
| AC15 | 5 | step 5 grep on `docs/CONVENTIONS.md` and `CLAUDE.md` |
| AC16 | 9 | step 9 verification commands (`gh repo view`) |
| AC17 | 6, 8, 9 | step 6 grep on `docs/ROADMAP.md`; Releases and About items ticked in steps 8/9 |
| AC18 | 6 | step 6 grep on `docs/BACKLOG.md` and `docs/DECISIONS.md` |
| AC19 | 7 | step 7 `git diff` on the protected directories + version grep; `bash scripts/check.sh` |
| AC20 | 1 | `tests/test_documents.py::test_no_document_names_the_private_consumer` (root and `docs/`/`specs/` Markdown); `plugin/tests/test_no_domain_references.py` (plugin, incl. `docs/INSTALL.md`) |

## Steps

Steps 1–7 are done by `/pipeline:implement`. Steps 8–9 are done by `/pipeline:final-review`
in `apply` mode, **only after** the owner's approval at gate 2 is recorded in
`## Owner decisions`. `implemented` does not wait for them.

How the gate 2 approval is obtained (review 2026-09-21): the gate 2 question of
`/pipeline:ship` covers review findings only, so the approval travels as a finding. The
`/pipeline:final-review` report lists one entry, weight "worth fixing", titled
"Steps 8–9: GitHub Releases for the six tags; the About description". Its text carries the
exact `gh repo edit` command of step 9 with the pitch line pasted in, and asks the owner to
run that command before answering the gate. Accepting that entry at gate 2 is the approval
of steps 8–9; rejecting it means steps 8–9 are not run, the two Stage 4 items stay
unticked, and the apply report says so. In `apply`, steps 8–9 run after the accepted fixes
and **before** the PR is opened (apply step 3), so the ROADMAP ticks ride in the PR.

- [x] 1. **Root document tests wired into verification**: files `tests/test_documents.py`
      (new), `scripts/check.sh`, `.github/workflows/ci.yml`, `docs/CONVENTIONS.md`
      (Tests), `CLAUDE.md` (Structure).
      - `scripts/check.sh`: the pytest line becomes
        `run "pytest" uv run pytest -q -p no:cacheprovider plugin/tests tests`;
        `.github/workflows/ci.yml` → "Test the plugin" becomes
        `uv run pytest -q -p no:cacheprovider plugin/tests tests` (rename the step "Run the
        tests").
      - `tests/test_documents.py`: `ROOT = Path(__file__).resolve().parents[1]`;
        `LINKED = ["README.md", "CONTRIBUTING.md", "SECURITY.md", "plugin/README.md",
        "plugin/docs/INSTALL.md", "plugin/docs/GUARD.md"]`. For this step, parametrize the
        link test over `[d for d in LINKED if (ROOT / d).exists()]`.
        `test_the_link_check_covers_the_six_documents` asserts all six exist and is marked
        `xfail(strict=True)` until step 4, which removes the mark and the `exists()`
        filter. Helpers:
        - `strip_fences(text) -> str` drops fenced blocks. Links are then taken from the
          text with inline code spans removed.
        - `slug(heading) -> str` and `anchors(path) -> set[str]` follow the Approach rule
          and handle repeats.
        - `links(path) -> list[str]`: regex `\]\(([^)\s]+)(?:\s+"[^"]*")?\)`, skipping
          `http://`, `https://` and `mailto:`.
      - Tests:
        - `test_github_anchor_slugs`: the four examples from Approach.
        - `test_relative_links_resolve[doc]`: the target (relative to the document's
          directory; a bare `#x` means the document itself) exists as a file or
          directory, and an anchor on a `.md` target is in `anchors(target)`.
        - `test_plugin_documents_link_inside_the_plugin[doc]`: for the `plugin/` documents,
          every resolved target stays under `ROOT / "plugin"`.
        - `test_no_document_names_the_private_consumer[path]`: every `*.md` under `ROOT`
          except `plugin/`, `.venv/`, `.git/` and hidden directories. Patterns are
          imported from `test_no_domain_references` (Approach), without the
          `scripts/check` one.
        - `test_no_polish_outside_code[doc]` over `README.md`, `CONTRIBUTING.md` and
          `SECURITY.md`, filtered by `exists()` until step 4 like the link test.
      - `docs/CONVENTIONS.md` → Tests: one bullet saying that repository rules and
        repository documents are tested in the root `tests/`, and `plugin/tests` holds
        only what ships with the plugin; `bash scripts/check.sh` and CI run both.
      - `CLAUDE.md` → Structure: add `tests/  # repository rules and documents (pytest)`.
      Automated verification:
      `uv run pytest -q -p no:cacheprovider tests` (green; the six-documents test
      reports `xfailed`), then `bash scripts/check.sh` → `ALL GREEN`, and
      `grep -n "plugin/tests tests" scripts/check.sh .github/workflows/ci.yml` → 2 hits.

- [x] 2. **Install guide**: files `plugin/docs/INSTALL.md` (new), `plugin/README.md`,
      `plugin/tests/test_readme.py`.
      - `plugin/docs/INSTALL.md`: `# Installing the pipeline plugin` plus the content of
        the current `plugin/README.md` lines 13–133 under `##` headings (Approach). Keep
        every command and JSON block byte for byte, including `"ref": "stable"`,
        `#stable`, `known_marketplaces.json`, `claude plugin uninstall pipeline@<name>
        --scope project`, `git checkout -- .claude/settings.json`,
        `"pipeline@wcz-tools": false`, `--plugin-dir`, `/plugin install pipeline@`,
        `/pipeline:init` and `--permission-mode bypassPermissions`. Relative paths are
        relative to `plugin/docs/`: `templates/settings.json` stays a code span, or
        becomes the link `../templates/settings.json`. The file must not contain the
        literal `scripts/check.sh`: `test_no_domain_references` scans all of `plugin/`.
      - `plugin/README.md` → `## Installation`: one ```` ```bash ```` block with three
        commands (marketplace add `'…agentic-pipeline.git#stable'`,
        `claude plugin install pipeline@wcz-tools --scope user`,
        `/pipeline:init   # once in each project, inside a Claude Code session`), then one
        sentence: "See the [install guide](docs/INSTALL.md) for updating, the release
        channel, the one-time migration, verification, the opt-out and the known traps."
        No `a && b` one-liner: AC10 counts commands, not lines, and the update pair is two
        (review 2026-09-21).
      - `plugin/tests/test_readme.py`:
        - add `INSTALL = (PLUGIN / "docs" / "INSTALL.md").read_text()` and
          `def install_guide() -> str: return INSTALL`;
        - replace `installation_section()` everywhere with `install_guide()`;
        - make `test_installation_covers_a_local_path_and_a_repository` use
          `install_guide()`;
        - add `test_install_guide_covers_verification_and_init`: tokens
          `claude plugin list`, `/pipeline:init`, `--permission-mode bypassPermissions`,
          `extraKnownMarketplaces`;
        - add `test_the_installation_section_is_short_and_links_the_guide`: the README
          section (split as today) has ≤ 3 commands (non-empty, not `#`-comment lines
          inside fenced blocks, each `&&`/`||`/`;` join counted as a further command) and
          contains `](docs/INSTALL.md)`;
        - add `"docs/INSTALL.md"` to the `test_no_polish_outside_code` parameters.
      - Add `plugin/docs/INSTALL.md` to the link test's document list. It is already in
        `LINKED` and is picked up once it exists.
      Automated verification:
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_readme.py plugin/tests/test_no_domain_references.py tests/test_documents.py`,
      then check that no assertion was dropped:
      `git diff -U0 plugin/tests/test_readme.py | grep '^-.*assert'` must print nothing,
      since only the section helper changes. Also
      `grep -c "stable" plugin/docs/INSTALL.md` ≥ 5.

- [x] 3. **CONTRIBUTING.md and SECURITY.md**: files `CONTRIBUTING.md`, `SECURITY.md` (new),
      `tests/test_documents.py`. Content as in Approach. Tests:
      - `test_contributing_covers_the_workflow`: tokens `issue`, `uv sync`,
        `bash scripts/check.sh`, `core.hooksPath`, `](docs/CONVENTIONS.md)`, `main`,
        `squash`, `` `plugin` ``, `Polish`, `Stage 8`.
      - `test_security_policy`: tokens `stable`, `security/advisories/new`,
        `best effort`, `bypass` (or `way past the guard`; pick one wording and test it),
        `](plugin/docs/GUARD.md#known-limits)`; and it does **not** direct reports to
        `issues/new`.
      Automated verification:
      `uv run pytest -q -p no:cacheprovider tests/test_documents.py` (links of both files
      resolve, no Polish).

- [x] 4. **Root README rewritten**: files `README.md`, `tests/test_documents.py`. Layout,
      badges, mermaid, guard block and sections exactly as in Approach. In the tests,
      remove the `exists()` filters and the `xfail` from step 1. Tests (helper
      `section(text, heading)` = the text after the exact `## heading` line up to the next
      `\n## `):
      - `test_readme_opens_with_the_display_name_and_the_pitch`: the first `# ` line is
        `# Spec-Driven Workflow` or starts with `# Spec-Driven Workflow` followed by a
        subtitle separator. Among the next five non-empty lines, one has no `![`, `[`
        or `` ` ``, contains `Claude Code`, ends with `.` and has one sentence (no
        `. ` inside).
      - `test_readme_shows_the_three_badges`: after `urllib.parse.unquote`, the README
        contains `actions/workflows/ci.yml/badge.svg`, `img.shields.io/badge/license-MIT`
        and `raw.githubusercontent.com/wojciechczarnecki/agentic-pipeline/main/plugin/.claude-plugin/plugin.json`
        with `query=$.version`.
      - `test_readme_diagram_names_every_stage_and_gate`: a ```` ```mermaid ```` block
        exists and contains `idea`, `plan`, `plan review`, `implement`, `final review`,
        `PR` and the three gate labels verbatim.
      - `test_readme_guard_block_matches_the_guard(tmp_path)`:
        - find the fenced block whose first line starts with `$ git push origin main`;
        - build a git repo in `tmp_path` (`git init -b main`, an empty commit with
          `-c user.name/-c user.email`, `git switch -c feat/001-x`,
          `.claude/workflow.json` = `{}` written from Python);
        - run `[sys.executable, ROOT/"plugin/bin/guard.py"]` with the payload
          `{"tool_input": {"command": <command after "$ ">}, "cwd": str(repo), "session_id": "readme"}`
          and env `{**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}`;
        - assert `returncode == 2` and `stderr.strip() == "\n".join(block_lines[1:]).strip()`.
      - `test_why_not_spec_kit_states_the_claim_with_dates`: the section exists. It
        contains `command guard`, `metrics`, `SpecForge` and `gate-oriented-sdd`. Every
        paragraph of the **whole** README (fenced blocks dropped, split on blank lines,
        heading lines skipped) that names `Spec Kit`, `SpecForge` or `gate-oriented-sdd`
        contains `checked \d{4}-\d{2}-\d{2}` — AC5 says "every statement", not only
        those inside the section.
      - Every command count in these tests counts `&&`, `||` and `;` joins as separate
        commands (AC8, AC10 count commands, not lines); the plugin test of step 2 applies
        the same rule with its own local helper (no cross-directory import).
      - `test_requirements_and_opinions`: tokens `gh`, `squash`, `rulesets`, `python3`,
        `Alembic`, `### Who it is for` and `### Who it is not for`.
      - `test_whats_deliberately_not_here`: tokens `runtime dependencies`,
        `outside Claude Code`, `best effort`, `sandbox` and
        `](plugin/docs/GUARD.md#known-limits)`.
      - `test_readme_install_is_short_and_links_the_guide`: `## Install` has ≤ 3 command
        lines and `](plugin/docs/INSTALL.md)`.
      - `test_quickstart_reaches_idea_in_five_commands`: `## Quickstart` contains
        `](#install)`. The install and quickstart command-line counts add up to ≤ 5, and
        the last quickstart command is `/pipeline:idea`.
      - `test_readme_explains_the_three_names`: one paragraph contains
        `Spec-Driven Workflow`, `` `agentic-pipeline` `` and `` `pipeline` ``.
      - `test_readme_links_the_documentation`: the README contains the links
        `](plugin/docs/INSTALL.md)`, `](plugin/docs/GUARD.md`,
        `](plugin/README.md#workflow-metrics)`, `](CONTRIBUTING.md)`, `](SECURITY.md)` and
        `](plugin/CHANGELOG.md)`.
      Automated verification:
      `uv run pytest -q -p no:cacheprovider tests/test_documents.py` (no `xfail` left);
      then a negative check that the guard test bites: temporarily change one word of the
      refusal line in `README.md`, run
      `uv run pytest -q -p no:cacheprovider tests/test_documents.py -k guard_block`, expect
      a failure, and restore with the Edit tool, not `git checkout` on a dirty tree.
      Repeat the negative check for one broken anchor (`#known-limit`) with
      `-k relative_links`.

- [x] 5. **Display name, pointers and the release procedure**: files `docs/PROJECT.md`,
      `CLAUDE.md`, `.claude-plugin/marketplace.json`, `plugin/.claude-plugin/plugin.json`,
      `docs/CONVENTIONS.md`.
      - `docs/PROJECT.md`: title `# Spec-Driven Workflow`. The "Listing in external plugin
        catalogues (for now)" line stays.
      - `CLAUDE.md`:
        - the project line becomes `**Spec-Driven Workflow** (repository
          `agentic-pipeline`, plugin `pipeline`) — …`;
        - "`plugin/README.md` → Installation" becomes `plugin/docs/INSTALL.md`;
        - the release block under Commands gains a third owner line after the `stable`
          move:
          `awk -v v=X.Y.Z '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md | gh release create pipeline--vX.Y.Z --verify-tag --title 'pipeline X.Y.Z' --notes-file -`.
      - `docs/CONVENTIONS.md` → Releases: a bullet after the `stable` move. The owner
        creates the GitHub Release on the tag with the same command, with notes = the
        matching `plugin/CHANGELOG.md` section. `--verify-tag` means the command never
        creates a tag.
      - Manifests: only the `description` fields. `plugin.json` begins with
        `Spec-Driven Workflow: …`, and so do the marketplace root and plugin entry
        descriptions. `version` stays `0.3.4`; name, keywords and source are untouched.
      Automated verification:
      `claude plugin validate --strict plugin/ && claude plugin validate --strict .`;
      `grep -n "plugin/docs/INSTALL.md" CLAUDE.md` ≥ 1 and
      `grep -n "plugin/README.md\` → Installation" CLAUDE.md` → no hit;
      `grep -n "gh release create" CLAUDE.md docs/CONVENTIONS.md` → both files;
      `grep -n '"version": "0.3.4"' plugin/.claude-plugin/plugin.json` → 1;
      `grep -c "Spec-Driven Workflow" docs/PROJECT.md CLAUDE.md .claude-plugin/marketplace.json plugin/.claude-plugin/plugin.json`
      → each ≥ 1; `uv run pytest -q -p no:cacheprovider plugin/tests/test_readme.py plugin/tests/test_plugin_structure.py`.

- [ ] 6. **Roadmap, backlog, decisions**: files `docs/ROADMAP.md`, `docs/BACKLOG.md`,
      `docs/DECISIONS.md`.
      - ROADMAP Stage 4, rewritten into these items:
        1. the root README (ticked);
        2. *Requirements & opinions* (ticked);
        3. the install guide, reworded to `plugin/docs/INSTALL.md` (ticked);
        4. `CONTRIBUTING.md`, `SECURITY.md` (ticked);
        5. GitHub Releases for the six `pipeline--v*` tags and the release step (the
           procedure part is done here; the item is ticked in step 8);
        6. the *About* description and topics checked against the README (ticked in
           step 9);
        7. owner-only: pin on the profile and the social preview image (left unticked;
           ticked only on the owner's confirmation).
      - ROADMAP: the demo recording item is removed. The measured-results and demo
        repository items move, with their text (including the "ask the owner" note), to a
        new `## Stage 9 — Evidence` after Stage 8, under a one-line intro (material
        expected in weeks; catalogue listing waits for it).
      - BACKLOG *Reach* row: the trigger becomes `Stage 9 is done`.
      - BACKLOG, one new *Guard* row (P2): `gh api` write calls on the repository
        endpoint (`-X PATCH repos/<owner>/<repo>`, topics, settings) pass the guard while
        `gh repo edit` is refused; trigger: the first session seen changing repository
        settings through `gh api`, or Stage 5 starting. No guard change here (AC19).
      - DECISIONS, three appended rows dated today:
        1. the install guide at `plugin/docs/INSTALL.md` (rejected: `docs/INSTALL.md`;
           rationale from the SPEC decision table);
        2. a GitHub Release for every release tag, notes from `plugin/CHANGELOG.md`,
           created by the owner after the tag and the `stable` move, with `--verify-tag`;
           the six existing tags are backfilled by the agent after gate 2 (rejected: no
           Releases; generated notes);
        3. repository-document tests in the root `tests/`, run by `scripts/check.sh` and
           CI together with `plugin/tests` (rejected: in `plugin/tests` with
           `parents[2]`; rationale: `plugin/tests` must run from the plugin alone, and the
           root `tests/` was not run by CI before).
      Automated verification:
      `grep -n "## Stage 9 — Evidence" docs/ROADMAP.md` → 1 and after the Stage 8 line
      (`grep -n "^## Stage" docs/ROADMAP.md` shows 8 before 9);
      `grep -n "Demo recording" docs/ROADMAP.md` → nothing;
      `grep -n "plugin/docs/INSTALL.md" docs/ROADMAP.md` ≥ 1;
      `grep -n "Stage 9 is done" docs/BACKLOG.md` → 1;
      `grep -n "plugin/docs/INSTALL.md\|GitHub Release\|tests/" docs/DECISIONS.md` shows
      the new rows; `uv run pytest -q -p no:cacheprovider tests/test_documents.py`
      (names test over `docs/`).

- [ ] 7. **Full verification and end-to-end**: no new files; the results go into this
      PLAN → End-to-end verification → Results.
      Automated verification:
      `git diff --stat origin/main...HEAD -- plugin/bin plugin/hooks plugin/skills plugin/agents plugin/templates`
      → empty;
      `git diff origin/main...HEAD -- plugin/.claude-plugin/plugin.json` shows only the
      `description` line;
      `bash scripts/check.sh` → `ALL GREEN`; the automatic end-to-end list below.
      In End-to-end verification → Results, add the line "Pending after gate 2: steps 8
      (Releases) and 9 (About), see Steps intro", with the ready `gh repo edit` command
      (pitch line pasted in), so the final review can raise the gate 2 entry.

- [ ] 8. **(after gate 2) GitHub Releases for the six tags**: no repository files except the
      ROADMAP tick. The permission prompt for `gh release create` is expected (it is not
      in `allow`). If it cannot be answered, end with `RESULT: ESCALATE` and hand the
      owner the command list below.
      ```bash
      git ls-remote --tags origin 'pipeline--v*' > "$SCRATCH/tags-before.txt"
      for v in 0.2.0 0.3.0 0.3.1 0.3.2 0.3.3; do
        awk -v v=$v '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md \
          | gh release create "pipeline--v$v" --verify-tag --title "pipeline $v" --notes-file - --latest=false
      done
      awk -v v=0.3.4 '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md \
        | gh release create pipeline--v0.3.4 --verify-tag --title "pipeline 0.3.4" --notes-file - --latest
      ```
      (`$SCRATCH` = the session scratchpad directory, not the repository.) Then tick the
      Stage 4 Releases item and commit (`docs: tick the GitHub Releases item`).
      Automated verification:
      `gh release list --limit 20` shows exactly six `pipeline X.Y.Z` releases, with
      `pipeline 0.3.4` marked `Latest`;
      for each version,
      `diff <(gh release view pipeline--v$v --json body -q .body | sed -e 's/[[:space:]]*$//' | sed -e '/./,$!d') <(awk -v v=$v '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md | sed -e 's/[[:space:]]*$//' | sed -e '/./,$!d')`
      → no output apart from trailing blank lines;
      `git ls-remote --tags origin 'pipeline--v*' | diff "$SCRATCH/tags-before.txt" -` →
      no output (no tag moved).

- [ ] 9. **(after gate 2) About description and topics**: the guard refuses `gh repo edit`
      for agents, and it must not be worked around (`gh api -X PATCH` is forbidden). The
      agent hands the owner, in the stage report, the exact command with the README
      pitch line pasted in:
      `gh repo edit wojciechczarnecki/agentic-pipeline --description "<pitch line from README.md>"`.
      The topics already contain `claude-code-plugin` and `spec-driven-development`
      (checked 2026-09-21), so no topic change is needed. The command reaches the owner
      in the final review's gate 2 entry (Steps intro); the owner runs it before
      answering the gate. The apply agent cannot wait for the owner, so it only verifies:
      when the description matches, it ticks the Stage 4 About item and commits
      (`docs: tick the About item`); when it does not, it ends with `RESULT: ESCALATE`
      carrying the command, before opening the PR, and the status stays `implemented`.
      Automated verification:
      `gh repo view --json description -q .description` equals the pitch line of
      `README.md` byte for byte (`diff <(gh repo view --json description -q .description) <(sed -n '<pitch line number>p' README.md)`);
      `gh repo view --json repositoryTopics -q '.repositoryTopics[].name' | grep -xE 'claude-code-plugin|spec-driven-development' | wc -l`
      → 2.

## Risks and traps

- **`gh repo edit` is refused by the guard.** This is the plugin's own rule (repository
  settings are the owner's call), and AC19 forbids touching the guard. The owner runs it.
  An agent that reaches for `gh api -X PATCH repos/…` because it "is not blocked" commits
  exactly the guard bypass that `SECURITY.md` asks people to report.
- **Duplicate test basenames.** Root and plugin test directories have no `__init__.py`.
  A root `test_readme.py` would make pytest fail on collection. Use `test_documents.py`.
- **`test_no_domain_references` scans all of `plugin/`**, including `plugin/docs/INSTALL.md`,
  for the literal `scripts/check.sh`. The install guide must not mention it; the
  development setup belongs in `CONTRIBUTING.md`.
- **Losing an installation assertion in the move.** The step 2 `git diff | grep '^-.*assert'`
  check exists for this. If a test has to change beyond the helper swap, that is a
  deviation.
- **The guard block depends on the guard's wording.** A future change of the push-to-main
  reason makes `test_readme_guard_block_matches_the_guard` fail on purpose. That is the
  point of AC4. Build the scratch repo on a feature branch so the refusal does not also
  mention the current branch.
- **Anchors differ from GitHub for exotic headings.** The slug helper covers ASCII
  punctuation, em dashes and backticks, which is what these documents use. Do not link to
  headings with emoji or HTML.
- **The version badge reads `main`**, so on the PR branch it shows `main`'s version (the
  same 0.3.4). The badge URL must be percent-encoded as given, or shields.io misreads the
  query.
- **Claims about other tools.** Only dated, checked statements. When in doubt, leave the
  sentence out rather than date an unchecked claim.
- **`.claude/` files.** Nothing under `.claude/` changes in this plan. The allow list is
  deliberately not extended with `gh release *`: the prompt is the owner's approval
  moment.
- **The private consumer's name.** The root test (step 1) scans every Markdown file
  outside `plugin/`, `specs/` included. If an old spec contained the name it would turn
  red, but the grep on 2026-09-21 found none.
- **Editing guardrail-adjacent files.** `scripts/check.sh`, `.github/workflows/ci.yml` and
  the manifests are edited with Edit/Write, never with `sed -i`. They are not guardrail
  files for the guard (those are `.claude/settings*.json`, `.claude/workflow.json` and the
  installed plugin directory), but Edit keeps the diff reviewable. The guard *does* refuse
  a shell write of `.claude/workflow.json`, which is why the scratch repo's file is
  written from Python in the test and with Write in the manual check (verified in review).
- **`gh api` is in the allow list and the guard does not refuse `gh api -X PATCH
  repos/<owner>/<repo>`**, while it refuses `gh repo edit`. Using that gap is forbidden
  (step 9); step 6 records it in `docs/BACKLOG.md`.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. `bash scripts/check.sh` → `ALL GREEN`, and the pytest summary includes the
   `tests/test_documents.py` and `tests/test_release_gate.py` cases, proving the root
   directory now runs.
2. The guard block by hand, as the test does, in a scratch repo on `feat/001-x` with
   `.claude/workflow.json` = `{}` (written with Write) and a payload file:
   `CLAUDE_PROJECT_DIR=<scratch> python3 plugin/bin/guard.py < payload.json; echo $?` →
   stderr equal to the README block's second line, `2`.
3. `claude plugin validate --strict plugin/` and `claude plugin validate --strict .` → valid.
4. Links from a bare plugin checkout: `cd plugin && python3 -m pytest -q -p no:cacheprovider tests/test_readme.py`
   → green, so `plugin/tests` still runs without the repository root.
5. `git diff --stat origin/main...HEAD -- plugin/bin plugin/hooks plugin/skills plugin/agents plugin/templates`
   → empty.

### Manual (performed by the owner)

1. On GitHub, open the root `README.md` on the PR branch. The mermaid diagram renders,
   the three badges show (CI status, MIT, version 0.3.4), and the links to
   INSTALL/GUARD/metrics/CONTRIBUTING/SECURITY/CHANGELOG open the right place.
2. At gate 2, before answering: run the `gh repo edit --description` command from the
   final review's "Steps 8–9" entry and accept that entry. After the apply run, look over
   the Releases page (six releases, 0.3.4 as Latest, notes readable).
3. Pin the repository on your profile and upload a social preview image, then confirm, so
   the last Stage 4 item can be ticked.

### Results

_(filled in by /pipeline:implement)_

## Definition of Done

- [ ] steps 1–7 ticked (8–9 after gate 2, in `/pipeline:final-review` apply)
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) done, result recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md`, `docs/BACKLOG.md`,
      `docs/CONVENTIONS.md`, `docs/PROJECT.md`, `CLAUDE.md` updated
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-09-21 — /pipeline:plan-review

Findings (weight, before fixes): 0 blockers, 2 majors, 4 minors.

- **M1 (major) — the gate 2 approval of steps 8–9 had no carrier.** The plan made steps
  8–9 conditional on "the owner's approval at gate 2 recorded in Owner decisions", but the
  `/pipeline:ship` gate 2 question covers review findings only, and final-review `apply`
  reads plan steps only through the decisions. As written, steps 8–9 would be skipped
  without notice, or the apply agent would guess. Fixed: Steps intro — the final review
  raises one "worth fixing" entry "Steps 8–9"; accepting it is the approval; rejecting it
  leaves the two items unticked and reported. Step 7 writes a "Pending after gate 2" line
  into Results so the final review sees it.
- **M2 (major) — step 9 waited for the owner inside `apply`.** An apply agent cannot wait
  for the owner to run `gh repo edit` and confirm, and apply opens the PR and reaches
  `done` in one run. Also the order of steps 8–9 against the PR was not given, so the
  ROADMAP ticks could land after the PR or after `done`. Fixed: the owner runs the command
  at gate 2, before answering (it is in the gate 2 entry). Apply runs steps 8–9 after the
  accepted fixes and before opening the PR. On a description mismatch it ends with
  `RESULT: ESCALATE` carrying the command, and the status stays `implemented`. The owner
  summary and manual scenario 2 now say the same.
- **m1 (minor) — AC10 counts commands, not lines.** The `plugin/README.md` install block
  ended with `marketplace update && plugin update`, which is two commands, so the section
  had four. The line-counting test would have passed anyway. Fixed: the third command is
  `/pipeline:init` and updating moves behind the link. The command-count helpers in both
  test files count `&&`/`||`/`;` joins, and the Approach paragraph matches.
- **m2 (minor) — AC5 says "every statement about another tool".** The test only looked
  inside *Why not Spec Kit?*. Fixed: it scans every paragraph of the whole README
  (fences and heading lines skipped).
- **m3 (minor) — the risk note called `scripts/check.sh` a guardrail file.** It is not
  one for the guard. Corrected, with the real list. Verified that the guard does refuse a
  shell write of `.claude/workflow.json`, which confirms the Python/Write approach for
  the scratch repo.
- **m4 (minor) — a guard gap met on the way.** `gh api` is allowed, and the guard lets
  `gh api -X PATCH repos/<owner>/<repo>` through while it refuses `gh repo edit`. The plan
  already forbade using it. Added a risk entry and a P2 *Guard* row in `docs/BACKLOG.md`
  (step 6). No guard change (AC19).

Checked and found correct (later stages need not redo this):

- **AC coverage:** every AC from AC1 to AC20 has a step and a proving test or command, and
  the matrix matches the step list. AC14, AC16 and AC17 ride on steps 8–9 (now with a
  carrier, M1).
- **Guard block (AC4):** reproduced on the working tree in a scratch repo on `feat/001-x`
  with `.claude/workflow.json` = `{}`. Exit code 2, stderr exactly
  `Blocked by the pipeline guard: pushing to main: main changes only through a PR merged by the owner; work on a feature branch`.
  `run_hook` in `plugin/tests/test_guard.py` matches the planned invocation.
- **Guard on `gh`:** `check_gh` refuses `gh repo edit` and lets `gh release create`
  through; `gh release create` is not in `allow` and not in `deny`.
- **Repository state:** the six tags `pipeline--v0.2.0` to `pipeline--v0.3.4` exist.
  `plugin/CHANGELOG.md` has `## X.Y.Z` headings for each, so the awk extraction works
  (`## 0.1.0` has no tag and is not released). No GitHub Releases exist yet. The topics
  already include `claude-code-plugin` and `spec-driven-development`.
- **Tests:** `tests/test_release_gate.py` passes today (11 passed) but is not run by
  `scripts/check.sh` or CI. `pyproject.toml` `testpaths` already includes `tests`. Adding
  `tests` to both commands is needed and minimal.
- **Consumer names:** the patterns from `test_no_domain_references.py` hit nothing in the
  Markdown outside `plugin/`, `specs/` and `docs/` included.
- **Existing links:** the relative links in `README.md`, `plugin/README.md` and
  `plugin/docs/GUARD.md` stay inside their trees. `## Workflow metrics` and
  `## Known limits` exist, so `#workflow-metrics` and `#known-limits` resolve.
- **Existing tests:** `test_readme.py` has `installation_section()` and
  `test_installation_covers_a_local_path_and_a_repository`, as the plan says. The
  `HEADINGS` test keeps `## Installation`, which the plan keeps.
- **Conventions and decisions:** no version bump for a docs-only change; English
  documents; tagging and moving `stable` stay the owner's; the release step is added as an
  owner step; the extra DECISIONS row for the root `tests/` fits "record decisions in the
  same PR".
- **Dependencies and migrations:** none, as the owner decided. The owner summary flags are
  correct.
- **Verification:** every step has exact commands. End-to-end is split into automatic and
  manual, and nothing automatable was left manual. There is no UI scope.

The plan is ready: it has no blockers, the two majors are fixed in the plan itself, there
is no new dependency or migration, and every AC has an executable proof.

## Deviations

1. **Step 3 — the `xfail` on `test_the_link_check_covers_the_six_documents` removed in
   step 3, not step 4.** The plan assumed the root `README.md` would appear in step 4, but
   the old README already exists, so the six documents were all present once
   `CONTRIBUTING.md` and `SECURITY.md` landed and the strict `xfail` turned into a failing
   XPASS. The mark goes one step early; the `exists()` filters still go in step 4.

## Final review

_(filled in by /pipeline:final-review)_
