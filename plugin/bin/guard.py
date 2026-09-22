#!/usr/bin/env python3
# PreToolUse hook (Bash): deterministic guardrails that let agent sessions run without
# permission prompts. Exit code 2 blocks the call and hands the reason back to the agent.
# Best effort, not a sandbox: it stops mistakes and shortcuts, not deliberate evasion.
# Everything project-specific comes from .claude/workflow.json; without that file only the
# universal rules apply.
import glob as globbing
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_config  # noqa: E402

DEFAULT_PROTECTED = {"main", "master"}
DB_COMMANDS = {"upgrade", "downgrade", "stamp", "revision", "current", "check"}
NO_CONFIG = (
    "pipeline guard: no .claude/workflow.json found, so only the universal rules apply "
    "(production hosts, worktree directory and migrations stay unguarded) — "
    "run /pipeline:init to create one"
)
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# `B=x`, `B+=x`, `B[0]=x`: only the plain form gives the guard a value it can trust
ASSIGNMENT_LIKE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(\[[^\]]*\])?(\+?)=")
NAME_ARGUMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\[[^\]]*\])?(?:\+?=|$)")
ARRAY_START = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
HEREDOC_DELIMITER = re.compile(r"(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
PUNCTUATION = ";&|()<>"
OPERATOR = re.compile(r";;|&&|\|\||\|&|[;&|()]")

NETWORK_PROGRAMS = {
    "curl",
    "wget",
    "http",
    "https",
    "xh",
    "ssh",
    "scp",
    "sftp",
    "rsync",
    "psql",
    "pg_dump",
    "pg_restore",
    "nc",
    "ncat",
    "telnet",
    "openssl",
    "python",
    "python3",
    "node",
}
BASE_BLOCKED_PROGRAMS = {
    "sudo": "sudo is not available to agent sessions; ask the owner to run it",
}
REMOVAL_PROGRAMS = {"rm", "rmdir", "unlink", "shred"}
MUTATING_PROGRAMS = {"tee", "mv", "cp", "rm", "chmod", "chown", "truncate", "ln", "install", "dd"}
WRAPPERS = {"env", "command", "exec", "time", "nice", "nohup", "builtin", "stdbuf"}
SHELLS = {"bash", "sh", "zsh", "dash"}
# Control structures: the keywords are stripped so the command behind them is checked, and
# an assignment inside a block counts as conditional — the block may run never or twice.
BLOCK_OPENERS = {"if", "while", "until"}
WORD_LIST_OPENERS = {"for", "select", "case"}
BLOCK_CLOSERS = {"fi", "done", "esac"}
BLOCK_KEYWORDS = {"then", "else", "elif", "do", "!", "{", "}"}
# Builtins that assign the variables they name; the guard does not follow their values.
ASSIGNING_BUILTINS = {
    "read",
    "declare",
    "typeset",
    "local",
    "readonly",
    "unset",
    "mapfile",
    "readarray",
    "getopts",
    "let",
}
DEFAULT_IFS = " \t\n"
UV_RUN_OPTIONS = {
    "--project",
    "--directory",
    "--with",
    "--with-requirements",
    "--python",
    "-p",
    "--env-file",
    "--package",
    "--group",
    "--extra",
}
DOCKER_OPTIONS = {
    "-e",
    "--env",
    "--env-file",
    "-u",
    "--user",
    "-w",
    "--workdir",
    "--entrypoint",
    "--name",
    "-p",
    "--publish",
    "-v",
    "--volume",
}
BRANCH_REWRITE = {"-d", "-D", "--delete", "-m", "-M", "--move", "-f", "--force"}
MAIN_OWNER_ONLY = "main changes only through a PR merged by the owner; work on a feature branch"
CHANNEL_OWNER_ONLY = (
    "{branch} is listed in protectedBranches (.claude/workflow.json) and only the owner "
    "changes it; work on a feature branch"
)
HOOKS_PATH = "changing core.hooksPath would switch off the pre-push guard"
UNRESOLVED_REFSPEC = (
    "cannot verify a push refspec built from variables or command substitution: {}; "
    "spell the branch out"
)
ALIAS = "a git alias cannot be verified by the guard; run the git command itself"
PUSH_CONFIG = (
    "push configuration (remote.<name>.push, remote.<name>.mirror, push.default) decides "
    "which branches a push reaches and cannot be verified by the guard; name the branch "
    "in the push itself"
)
CONFIG_EDIT = (
    "`git config --edit` could change core.hooksPath or an alias unseen by the guard; "
    "set the key with `git config <key> <value>`"
)
CONFIG_VARIABLE = "cannot verify a git configuration key built from variables: {}; spell it out"
EVERY_BRANCH = (
    "a push of every branch (--all, --branches) includes main, and main changes only "
    "through a PR merged by the owner; push the feature branch by name"
)
PUSH_PATTERN = (
    "cannot verify a push refspec with a pattern or brace expansion: {}; spell the branch out"
)
PUSH_VALUE_OPTIONS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
PUSH_DESTRUCTIVE = {"--mirror", "--delete", "-d", "--prune"}
CONFIG_VALUE_OPTIONS = {"-f", "--file", "--blob", "--type", "--default", "--comment", "--value"}
CONFIG_READ_SUBCOMMANDS = {"get", "list"}
CONFIG_WRITE_SUBCOMMANDS = {"set", "unset", "rename-section", "remove-section", "edit"}
CONFIG_WRITE_FLAGS = {
    "--add",
    "--replace-all",
    "--unset",
    "--unset-all",
    "--rename-section",
    "--remove-section",
    "-e",
    "--edit",
}
CONFIG_READ_FLAGS = {
    "--get",
    "--get-all",
    "--get-regexp",
    "--get-urlmatch",
    "--get-color",
    "--get-colorbool",
    "-l",
    "--list",
}
CONFIG_SECTION_OPERATIONS = {
    "--rename-section",
    "--remove-section",
    "rename-section",
    "remove-section",
}
GUARDRAIL_FILES = (
    "guardrail files (.claude/settings*.json, .claude/workflow.json and the plugin "
    "directory) change only through Edit/Write with the owner's approval"
)
GIT_HOOKS = (
    "an existing git hook changes only through Edit/Write with the owner's approval; "
    "creating a missing hook (and making it executable) is allowed"
)
API_OWNER_DELETIONS = {
    "merges": "merges",
    "protection": "branch protection",
    "rulesets": "rulesets",
    "releases": "releases",
    "runs": "workflow runs",
    "secrets": "secrets",
    "variables": "variables",
    "environments": "environments",
    "hooks": "webhooks",
    "keys": "keys",
    "gpg_keys": "keys",
    "ssh_signing_keys": "keys",
    "collaborators": "collaborator access",
    "invitations": "collaborator access",
    "outside_collaborators": "collaborator access",
    "teams": "organization teams and members",
    "members": "organization teams and members",
    "memberships": "organization teams and members",
    "pages": "the Pages site",
    "deployments": "deployments",
    "vulnerability-alerts": "security settings",
    "automated-security-fixes": "security settings",
    "private-vulnerability-reporting": "security settings",
}
PLUGIN_INSTALL = (
    "the {name} plugin's install is the owner's to change — disabling or uninstalling it, "
    "or removing its marketplace, switches the guard off; the owner runs that in a terminal"
)
PLUGIN_VARIABLE = (
    "cannot verify a plugin or marketplace name built from variables: {}; spell it out"
)
PLUGIN_STATE_UNREADABLE = (
    "cannot read the plugin install state to tell whether {} is this plugin's marketplace; "
    "the owner runs that in a terminal"
)
CLAUDE_VALUE_OPTIONS = {"-s", "--scope"}
DEFAULT_PLUGIN_NAME = "pipeline"
DEFAULT_WORKTREE_DIR = "../worktrees"
GLOB_CHARACTERS = re.compile(r"[*?\[{]")
WORKTREE_ADD_OPTIONS = {"-b", "-B", "--reason"}
warned_worktree_dirs: set[str] = set()


class GuardError(Exception):
    pass


class Rules:
    def __init__(self, config: workflow_config.Config, env: dict[str, str], cwd: Path):
        self.config = config
        hosts = config.get("production.hosts") or []
        self.production_host = (
            re.compile("|".join(re.escape(host) for host in hosts), re.I) if hosts else None
        )
        self.blocked_programs = dict(BASE_BLOCKED_PROGRAMS)
        for program in config.get("production.commands") or []:
            self.blocked_programs[program] = (
                f"`{program}` operates production; ask the owner to run it"
            )
        self.worktree_dir = config.get("worktree.dir") or DEFAULT_WORKTREE_DIR
        # `git branch --show-current` prints "" on a detached HEAD, so an empty name would
        # protect every detached checkout
        configured = config.get("protectedBranches") or []
        self.protected_branches = DEFAULT_PROTECTED | {name for name in configured if name}
        channels = sorted(self.protected_branches - DEFAULT_PROTECTED)
        self.channel_ref = (
            re.compile(
                r"refs/heads/(" + "|".join(re.escape(name) for name in channels) + r")(?=$|[/?#])"
            )
            if channels
            else None
        )
        self.protected_file = protected_file_pattern(config, env, cwd)
        self.git_hooks = git_hooks_pattern(config)
        migrations = config.get("migrations") or {}
        self.migration_command = migrations.get("command", "")
        self.local_hosts = {host.lower() for host in migrations.get("localHosts") or []} | {""}


def protected_file_pattern(
    config: workflow_config.Config, env: dict[str, str], cwd: Path
) -> re.Pattern[str]:
    parts = [r"\.claude/settings[^/\s]*\.json", r"\.claude/workflow\.json"]
    inside = plugin_dir_inside_project(config, env, cwd)
    if inside:
        parts.append(rf"(?:^|/|\s){re.escape(inside)}(?:/|$)")
    return re.compile("|".join(parts))


def git_hooks_pattern(config: workflow_config.Config) -> re.Pattern[str] | None:
    hooks = (config.get("gitHooksDir") or "").strip("/")
    return re.compile(re.escape(hooks)) if hooks else None


def adds_execute_bit(args: list[str]) -> bool:
    for arg in args:
        if arg.startswith("-") and not re.fullmatch(r"-[rwxXstugo]+", arg):
            continue
        if re.fullmatch(r"[ugoa]*\+[rwxXst]*x[rwxXst]*", arg):
            return True
        if re.fullmatch(r"[0-7]{3,4}", arg):
            return all(int(digit) & 1 for digit in arg[-3:])
        return False
    return False


def plugin_dir_inside_project(
    config: workflow_config.Config, env: dict[str, str], cwd: Path
) -> str:
    raw = env.get("CLAUDE_PLUGIN_ROOT")
    if not raw:
        return ""
    root = config.root or Path(env.get("CLAUDE_PROJECT_DIR") or cwd)
    try:
        return Path(raw).resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError):
        return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    command = payload.get("tool_input", {}).get("command") or ""
    cwd = Path(payload.get("cwd") or os.getcwd())
    env = dict(os.environ)
    config = read_config(cwd, env, warn=True)
    if not config.found and not config.unreadable:
        warn_once(payload.get("session_id"))
    reason = evaluate(command, cwd, env, config)
    if reason is None:
        return 0
    print(f"Blocked by the pipeline guard: {reason}", file=sys.stderr)
    return 2


# A broken or missing configuration is never a reason to block: the session has to stay
# usable, so both states only warn and leave the universal rules in charge. A single bad
# key costs only its own section — the rest of the file keeps configuring the rules.
def read_config(cwd: Path, env: dict[str, str], warn: bool = False) -> workflow_config.Config:
    start = Path(env.get("CLAUDE_PROJECT_DIR") or cwd)
    try:
        config, problems = workflow_config.load_sections(start)
    except workflow_config.ConfigError as exc:
        if warn:
            print(f"pipeline guard: {exc}; falling back to the defaults", file=sys.stderr)
        return workflow_config.Config(workflow_config.defaults(), unreadable=True)
    if warn:
        for problem in problems:
            print(
                f"pipeline guard: {problem}; that section falls back to the defaults",
                file=sys.stderr,
            )
    return config


# The marker lives in a per-user directory and is created exclusively, so a symlink or a
# file planted by someone else neither silences the warning nor gets written through.
def warn_once(session_id: str | None) -> None:
    name = re.sub(r"[^A-Za-z0-9_.-]", "", session_id or "") or "session"
    directory = Path(tempfile.gettempdir()) / f"pipeline-guard-{os.getuid()}"
    try:
        directory.mkdir(mode=0o700, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
        os.close(os.open(directory / f"{name}.warned", flags, 0o600))
    except FileExistsError:
        return
    except OSError:
        pass
    print(NO_CONFIG, file=sys.stderr)


def evaluate(
    command: str, cwd: Path, env: dict[str, str], config: workflow_config.Config | None = None
) -> str | None:
    rules = Rules(config if config is not None else read_config(cwd, env), env, cwd)
    try:
        Analyzer(cwd, env, rules).run(command)
    except GuardError as exc:
        return str(exc)
    return None


Snapshot = tuple[dict[str, str], set[str], Path]
# (part number, kind: "run" | "(" | ")", words, behind && or ||, runs in a subshell)
Item = tuple[int, str, list[str], bool, bool]


class Analyzer:
    def __init__(
        self,
        cwd: Path,
        env: dict[str, str],
        rules: Rules,
        in_container: bool = False,
        exported: set[str] | None = None,
    ):
        self.cwd = cwd
        self.env = env
        self.rules = rules
        self.in_container = in_container
        # the process environment is exported; plain assignments in the call are not
        self.exported = set(env) if exported is None else exported
        self.blocks = 0
        self.scopes: list[Snapshot] = []

    def run(self, text: str, depth: int = 0) -> None:
        if depth > 5:
            raise GuardError("the command nests too deeply to verify; split it up")
        try:
            text, expanded = strip_heredocs(text)
        except ValueError:
            raise GuardError(
                "the command could not be parsed; split it into simpler ones"
            ) from None
        executable = f"{outside_single_quotes(text)}\n{expanded}"
        for dollar, backtick in re.findall(r"\$\(([^()]*)\)|`([^`]*)`", executable):
            nested = Analyzer(
                self.cwd, dict(self.env), self.rules, self.in_container, set(self.exported)
            )
            nested.run(dollar or backtick, depth + 1)
        try:
            tokens = tokenize(text)
        except ValueError:
            raise GuardError(
                "the command could not be parsed; split it into simpler ones"
            ) from None
        parts = split_parts(tokens)
        commands = [part for part in parts if any(item[1] == "run" for item in part)]
        if depth > 0 or len(commands) < 2:
            for part in parts:
                for item in part:
                    self.step(item, depth)
            return
        # The hook refuses the whole call, so every part is checked and the refusal names
        # the ones at fault — the agent can send the rest again on its own.
        blocked = []
        for part in parts:
            for index, item in enumerate(part):
                try:
                    self.step(item, depth)
                except GuardError as exc:
                    text = " | ".join(" ".join(words) for _, kind, words, _, _ in part if words)
                    blocked.append(f"`{text}`: {exc}")
                    # the rest of the part is refused with it; its scopes still open and close
                    for _, kind, _, _, _ in part[index + 1 :]:
                        if kind != "run":
                            self.step((0, kind, [], False, False), depth)
                    break
        if blocked:
            passed = len(commands) - len(blocked)
            rest = (
                f"; the other {passed} of {len(commands)} parts passed"
                " — run them as a separate call"
                if passed
                else ""
            )
            raise GuardError(f"the whole call is refused because of {'; '.join(blocked)}{rest}")

    def snapshot(self) -> Snapshot:
        return dict(self.env), set(self.exported), self.cwd

    def restore(self, saved: Snapshot) -> None:
        self.env, self.exported, self.cwd = saved[0], saved[1], saved[2]

    # A subshell — `( … )`, `$( … )`, a command in a pipeline or in the background — keeps
    # its assignments and its `cd` to itself.
    def step(self, item: Item, depth: int) -> None:
        _, kind, words, conditional, isolated = item
        if kind == "(":
            self.scopes.append(self.snapshot())
        elif kind == ")":
            if self.scopes:
                self.restore(self.scopes.pop())
        elif isolated:
            saved = self.snapshot()
            try:
                self.segment(words, depth, conditional)
            finally:
                self.restore(saved)
        else:
            self.segment(words, depth, conditional)

    def forget(self, names: list[str]) -> None:
        for name in names:
            self.env[name] = f"${name}"

    def control(self, words: list[str]) -> list[str]:
        while words:
            keyword = words[0]
            if keyword in BLOCK_OPENERS:
                self.blocks += 1
            elif keyword in WORD_LIST_OPENERS:
                self.blocks += 1
                if keyword != "case" and len(words) > 1 and NAME_ARGUMENT.match(words[1]):
                    self.forget([words[1]])
                return []
            elif keyword in BLOCK_CLOSERS:
                self.blocks = max(0, self.blocks - 1)
            elif keyword not in BLOCK_KEYWORDS:
                return words
            words = words[1:]
        return words

    def segment(self, tokens: list[str], depth: int, conditional: bool = False) -> None:
        words, redirects = split_redirects(tokens)
        words = self.control(words)
        # an assignment behind && or || or inside a block may never run (or run again), so
        # its value stays unverifiable
        conditional = conditional or self.blocks > 0
        env = dict(self.env)
        prefixed: set[str] = set()
        while words and ASSIGNMENT_LIKE.match(words[0]):
            key, value = assignment(words.pop(0), conditional)
            env[key] = value
            prefixed.add(key)
        if not words:
            self.env = env
            return
        words = unwrap(words, env, prefixed)
        if not words:
            return
        program, args = os.path.basename(words[0]), words[1:]
        if program in self.rules.blocked_programs:
            raise GuardError(self.rules.blocked_programs[program])
        self.check_guardrail_files(program, args, redirects)
        if program in SHELLS:
            if "-c" in args[:-1]:
                # a new shell process sees only exported variables and its own prefix
                child = {
                    key: value
                    for key, value in env.items()
                    if key in self.exported or key in prefixed
                }
                Analyzer(self.cwd, child, self.rules, self.in_container).run(
                    args[args.index("-c") + 1], depth + 1
                )
            return
        if program == "eval":
            self.run(" ".join(args), depth + 1)
            return
        if program == "cd":
            self.change_dir(args)
            return
        if program == "export":
            self.export(args, conditional)
            return
        if program in ASSIGNING_BUILTINS:
            self.forget([match.group(1) for arg in args if (match := NAME_ARGUMENT.match(arg))])
        if program == "printf" and "-v" in args[:-1]:
            self.forget([args[args.index("-v") + 1]])
        if program in NETWORK_PROGRAMS and self.rules.production_host:
            if any(self.rules.production_host.search(arg) for arg in args):
                raise GuardError("production is off limits to agent sessions; ask the owner")
        if program == "git":
            self.git(args)
        elif program == "gh":
            check_gh(args, self.rules)
        elif program == "claude":
            check_claude(args, self.env, env)
        elif program in REMOVAL_PROGRAMS:
            self.removal(args)
        elif program == "find":
            self.find(args)
        elif program == "docker":
            self.docker(args, depth)
        migration = self.rules.migration_command
        if migration and (
            program == migration or (program.startswith("python") and args[:2] == ["-m", migration])
        ):
            self.migrate(args, env)

    def export(self, args: list[str], conditional: bool) -> None:
        names = []
        for arg in args:
            if ASSIGNMENT_LIKE.match(arg):
                key, value = assignment(arg, conditional)
                self.env[key] = value
                names.append(key)
            elif NAME_ARGUMENT.match(arg):
                names.append(arg)
        if "-n" in args:
            self.exported.difference_update(names)
        else:
            self.exported.update(names)

    def migrate(self, args: list[str], env: dict[str, str]) -> None:
        if not DB_COMMANDS & set(args):
            return
        settings = {} if self.in_container else read_dotenv(self.cwd / ".env")
        settings.update({key.upper(): value for key, value in env.items()})
        if settings.get("ENVIRONMENT", "").lower() == "production":
            raise GuardError("a migration with ENVIRONMENT=production; ask the owner")
        url = settings.get("DATABASE_URL")
        if url and "$" in url:
            raise GuardError("a migration with a database URL built from variables; ask the owner")
        host = (urlparse(url).hostname or "") if url else settings.get("DB_HOST", "localhost")
        if "$" in host or host.lower() not in self.rules.local_hosts:
            raise GuardError(
                f"a migration against a non-local database ({host}); "
                "migrations outside dev and test need the owner"
            )

    def check_guardrail_files(self, program: str, args: list[str], redirects: list[str]) -> None:
        in_place = program in {"sed", "perl"} and any(re.match(r"^-\w*i", arg) for arg in args)
        touched = [*redirects, *args] if program in MUTATING_PROGRAMS or in_place else redirects
        creates_hook = program == "chmod" and adds_execute_bit(args)
        self.reject_guardrail_targets(touched, check_hooks=not creates_hook)

    def reject_guardrail_targets(self, touched: list[str], check_hooks: bool) -> None:
        if any(self.rules.protected_file.search(target) for target in touched):
            raise GuardError(GUARDRAIL_FILES)
        hooks = self.rules.git_hooks
        if hooks is None or not check_hooks:
            return
        for target in touched:
            if hooks.search(target) and self.hook_target_exists(target):
                raise GuardError(GIT_HOOKS)

    # Only an existing hook is protected, and "existing" has to survive shell patterns:
    # `scripts/git-hooks/pre-*` names no file, yet the shell hands it to the very hook the
    # rule defends. A pattern counts as existing when it matches anything, and a path the
    # guard cannot expand counts as existing too.
    def hook_target_exists(self, target: str) -> bool:
        expanded = expand_variables(target, self.env)
        if "$" in expanded or "{" in expanded:
            return True
        if GLOB_CHARACTERS.search(expanded):
            try:
                return bool(globbing.glob(expanded, root_dir=self.cwd))
            except OSError:
                return True
        return resolve(self.cwd, expanded).exists()

    def change_dir(self, args: list[str]) -> None:
        if args[:1] == ["-"]:
            return
        targets = [arg for arg in args if not arg.startswith("-")]
        if not targets:
            self.cwd = Path.home()
            return
        target = expand_variables(targets[0], self.env)
        if "$" in target:
            raise GuardError(f"cannot verify a directory built from variables: {targets[0]}")
        self.cwd = resolve(self.cwd, target)

    def git(self, args: list[str]) -> None:
        cwd, rest = self.cwd, list(args)
        while rest and rest[0].startswith("-"):
            option = rest.pop(0)
            if option in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"} and rest:
                value = rest.pop(0)
                if option == "-C":
                    cwd = resolve(cwd, value)
                elif option == "-c":
                    key = expand_variables(value, self.env).split("=", 1)[0]
                    if "$" in key or "`" in key:
                        raise GuardError(CONFIG_VARIABLE.format(value))
                    refusal = config_key_refusal(key.lower())
                    if refusal:
                        raise GuardError(refusal)
        if not rest:
            return
        sub, sub_args = rest[0], rest[1:]
        if "--no-verify" in sub_args:
            raise GuardError("skipping git hooks with --no-verify is off limits")
        if sub == "config":
            self.config(sub_args)
        if sub == "reset" and "--hard" in sub_args:
            raise GuardError("`git reset --hard` discards work irreversibly; ask the owner")
        if sub == "clean" and any(is_force_flag(arg) for arg in sub_args):
            raise GuardError("`git clean -f` deletes untracked files irreversibly; ask the owner")
        if sub == "branch" and BRANCH_REWRITE & set(sub_args):
            hit = self.rules.protected_branches & set(sub_args)
            if hit:
                raise GuardError(f"deleting, renaming or resetting {shown(hit)} is off limits")
        if sub in {"checkout", "restore"}:
            self.reject_guardrail_targets(
                [arg for arg in sub_args if not arg.startswith("-")], check_hooks=True
            )
        if sub == "worktree" and sub_args[:1] == ["add"]:
            self.worktree_add(sub_args[1:])
        if sub in {"update-ref", "symbolic-ref"}:
            hit = {ref_name(arg) for arg in sub_args} & self.rules.protected_branches
            if hit:
                raise GuardError(owner_only(shown(hit)))
        if sub not in {"push", "commit", "merge", "rebase", "cherry-pick", "revert", "am", "pull"}:
            return
        branch = git_output(cwd, "branch", "--show-current")
        on_protected = branch in self.rules.protected_branches
        if sub == "push":
            self.push(sub_args, branch)
        elif on_protected and sub == "pull":
            if "--ff-only" not in sub_args:
                raise GuardError(f"on {shown({branch})} only `git pull --ff-only` is allowed")
        elif on_protected:
            raise GuardError(f"`git {sub}` on {branch}: {owner_only(branch)}")

    def config(self, args: list[str]) -> None:
        expanded = [expand_variables(arg, self.env) for arg in args]
        names, writes, sections = config_access(expanded)
        if not writes:
            return
        if not names:
            # `--edit`, `-e`, `edit`: an editor changes whatever it likes
            raise GuardError(CONFIG_EDIT)
        for name in names:
            if "$" in name or "`" in name:
                raise GuardError(CONFIG_VARIABLE.format(name))
            refusal = section_refusal(name) if sections else config_key_refusal(name)
            if refusal:
                raise GuardError(refusal)

    # A push is judged on what the shell will run: arguments expand with the variables known
    # before the command (never its own prefix assignments), an expansion splits on
    # whitespace, and an empty value disappears. Options are read after expansion too.
    # Whatever stays unresolved is refused, like a removal path.
    def push(self, args: list[str], current: str) -> None:
        ifs = self.env.get("IFS")
        words = []
        for raw in args:
            # the lexer cut a `$(` off here, so the rest of the push landed in other segments
            if raw.endswith("$"):
                raise GuardError(UNRESOLVED_REFSPEC.format(f"{raw}(...)"))
            if "$" not in raw:
                words.append((raw, raw))
                continue
            if ifs is not None and ifs != DEFAULT_IFS:
                # a changed IFS splits the expansion where the guard would not
                raise GuardError(UNRESOLVED_REFSPEC.format(raw))
            words += [(raw, word) for word in expand_variables(raw, self.env).split()]
        for _, word in words:
            destructive = word in PUSH_DESTRUCTIVE or word.startswith("--force")
            if destructive or is_force_flag(word):
                raise GuardError("force, mirror and delete pushes are off limits; ask the owner")
            if word == "--no-verify":
                raise GuardError("skipping git hooks with --no-verify is off limits")
            if word in {"--all", "--branches"}:
                raise GuardError(EVERY_BRANCH)
        positionals, repository_option = [], False
        index = 0
        while index < len(words):
            raw, word = words[index]
            option = word.split("=", 1)[0]
            if option == "--repo":
                repository_option = True
            if word in PUSH_VALUE_OPTIONS:
                index += 1
            elif not word.startswith("-"):
                positionals.append((raw, word))
            index += 1
        # with --repo every positional is a refspec
        refspecs = positionals if repository_option else positionals[1:]
        for raw, word in refspecs:
            if "$" in word or "`" in word:
                raise GuardError(UNRESOLVED_REFSPEC.format(raw))
            if GLOB_CHARACTERS.search(word):
                raise GuardError(PUSH_PATTERN.format(raw))
        specs = [word for _, word in refspecs]
        if any(spec.startswith(("+", ":")) for spec in specs):
            raise GuardError("force and delete pushes are off limits; ask the owner")
        targets = {ref_name(spec) for spec in specs}
        pushes_current = not specs or bool(targets & {"HEAD", "@"})
        hit = targets & self.rules.protected_branches
        if pushes_current and current in self.rules.protected_branches:
            hit.add(current)
        if hit:
            name = shown(hit)
            raise GuardError(f"pushing to {name}: {owner_only(name)}")

    def worktree_add(self, args: list[str]) -> None:
        rest = skip_options(args, WORKTREE_ADD_OPTIONS)
        targets = [arg for arg in rest if not arg.startswith("-")]
        if not targets:
            return
        target = expand_variables(targets[0], self.env)
        if "$" in target:
            raise GuardError(f"cannot verify a worktree path built from variables: {targets[0]}")
        _, _, worktrees = workspace(self.env, self.cwd, self.rules.worktree_dir)
        if not is_within(resolve(self.cwd, target), worktrees):
            raise GuardError(
                f"a worktree outside the configured directory ({worktrees}); "
                "set worktree.dir in .claude/workflow.json or use that directory"
            )

    def removal(self, args: list[str]) -> None:
        if self.in_container:
            return
        if "--" in args:
            split = args.index("--")
            targets = [arg for arg in args[:split] if not arg.startswith("-")] + args[split + 1 :]
        else:
            targets = [arg for arg in args if not arg.startswith("-")]
        for target in targets:
            self.check_path(target, allow_root=False)

    def find(self, args: list[str]) -> None:
        deletes = "-delete" in args or any(
            arg in {"-exec", "-execdir", "-ok"}
            and index + 1 < len(args)
            and os.path.basename(args[index + 1]) in REMOVAL_PROGRAMS
            for index, arg in enumerate(args)
        )
        if not deletes or self.in_container:
            return
        starts = []
        for arg in args:
            if arg.startswith("-") or arg in {"(", "!"}:
                break
            starts.append(arg)
        for start in starts or ["."]:
            self.check_path(start, allow_root=True)

    def check_path(self, raw: str, allow_root: bool) -> None:
        expanded = expand_variables(raw, self.env)
        if "$" in expanded:
            raise GuardError(f"cannot verify a path built from variables: {raw}")
        literal = re.split(r"[*?\[{]", expanded, maxsplit=1)[0] or "."
        path = resolve(self.cwd, literal)
        projects, writable, _ = workspace(self.env, self.cwd, self.rules.worktree_dir)
        if any(is_within(path, project / ".git") for project in projects):
            raise GuardError("removing git internals is off limits")
        if not allow_root and path in projects:
            raise GuardError("removing the repository root is off limits")
        if not any(is_within(path, root) for root in writable):
            raise GuardError(f"removing files outside the project and scratch directories: {raw}")

    def docker(self, args: list[str], depth: int) -> None:
        rest = list(args)
        if rest[:1] == ["compose"]:
            compose_options = {"-f", "--file", "-p", "--project-name", "--env-file", "--profile"}
            rest = skip_options(rest[1:], compose_options)
        if rest[:1] not in (["exec"], ["run"]):
            return
        rest = skip_options(rest[1:], DOCKER_OPTIONS)
        if len(rest) > 1:
            Analyzer(self.cwd, {}, self.rules, in_container=True).segment(rest[1:], depth + 1)


# Heredoc bodies are data, not commands; only an unquoted delimiter lets the shell run
# substitutions inside the body, so those bodies are still scanned for $(...) and backticks.
# A `<<` counts only outside quotes, comments and $((...)) — anywhere else skipping lines
# would hide real commands — and a heredoc that never closes fails closed.
def strip_heredocs(text: str) -> tuple[str, str]:
    kept: list[str] = []
    expanded: list[str] = []
    pending: list[tuple[str, bool, bool]] = []
    state = ShellState()
    for line in text.split("\n"):
        if pending:
            delimiter, strip_tabs, expands = pending[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                pending.pop(0)
            elif expands:
                expanded.append(line)
            continue
        kept.append(line)
        pending.extend(state.heredocs_opened_by(line))
    if pending:
        raise ValueError("unterminated heredoc")
    return "\n".join(kept), "\n".join(expanded)


class ShellState:
    def __init__(self) -> None:
        self.quote = ""
        self.arithmetic = 0

    def heredocs_opened_by(self, line: str) -> list[tuple[str, bool, bool]]:
        opened = []
        index = 0
        while index < len(line):
            char = line[index]
            if self.quote == "'":
                self.quote = "" if char == "'" else self.quote
            elif self.quote == '"':
                if char == "\\":
                    index += 1
                elif char == '"':
                    self.quote = ""
            elif char == "\\":
                index += 1
            elif char in "'\"":
                self.quote = char
            elif char == "#" and (index == 0 or line[index - 1] in " \t;&|("):
                break
            elif line.startswith("$((", index):
                self.arithmetic += 1
                index += 2
            elif line.startswith("))", index) and self.arithmetic:
                self.arithmetic -= 1
                index += 1
            elif line.startswith("<<<", index):
                index += 2
            elif line.startswith("<<", index) and not self.arithmetic:
                match = HEREDOC_DELIMITER.match(line, index + 2)
                if match:
                    opened.append((match.group(3), match.group(1) == "-", not match.group(2)))
                    index = match.end() - 1
            index += 1
        return opened


# Variables assigned earlier in the same command (or exported in the session) are known, so
# a path built from them can still be verified; anything unknown stays blocked.
def expand_variables(raw: str, env: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        return env.get(name, match.group(0))

    return VARIABLE.sub(replace, raw)


def outside_single_quotes(text: str) -> str:
    kept: list[str] = []
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        if quote == "'":
            quote = "" if char == "'" else quote
        elif char == "\\":
            kept.append(text[index : index + 2])
            index += 1
        elif char == "'" and quote != '"':
            quote = "'"
        else:
            if char == '"':
                quote = "" if quote == '"' else '"'
            kept.append(char)
        index += 1
    return "".join(kept)


def tokenize(text: str) -> list[str]:
    lexer = shlex.shlex(text.replace("\n", " ; "), posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def assignment(word: str, conditional: bool) -> tuple[str, str]:
    match = ASSIGNMENT_LIKE.match(word)
    assert match is not None
    key = match.group(1)
    # an append or an array element changes a value the guard does not track
    known = not conditional and not match.group(2) and not match.group(3)
    return key, word[match.end() :] if known else f"${key}"


# Splits tokens into parts: a pipeline is one part (its commands run together, so it is
# offered back whole in a compound refusal), and every `(` and `)` becomes an item of its
# own so a subshell's assignments end with it.
def split_parts(tokens: list[str]) -> list[list[Item]]:
    items: list[Item] = []
    part, filled = 0, False
    words: list[str] = []
    conditional = after_pipe = False
    pieces = []
    for token in [*tokens, ";"]:
        if is_operator(token):
            # the lexer glues neighbouring punctuation: `);`, `|(`, `&&(`
            pieces.extend(OPERATOR.findall(token))
        else:
            pieces.append(token)
    for token in pieces:
        if not is_operator(token):
            words.append(token)
            continue
        piped = token in {"|", "|&"}
        if token == "(" and words and ARRAY_START.fullmatch(words[-1]):
            # `B=(main)` makes an array; its value is not tracked
            words[-1] = f"{words[-1].removesuffix('=').removesuffix('+')}+="
        if words:
            items.append((part, "run", words, conditional, after_pipe or piped or token == "&"))
            filled = True
        if not piped and filled:
            part, filled = part + 1, False
        if token in {"(", ")"}:
            items.append((part, token, [], False, False))
        conditional = token in {"&&", "||"}
        after_pipe = piped
        words = []
    parts: dict[int, list[Item]] = {}
    for item in items:
        parts.setdefault(item[0], []).append(item)
    return list(parts.values())


def is_operator(token: str) -> bool:
    return bool(token) and all(char in "&|;()" for char in token)


def split_redirects(tokens: list[str]) -> tuple[list[str], list[str]]:
    words, targets = [], []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token and all(char in PUNCTUATION for char in token) and ("<" in token or ">" in token):
            if ">" in token and index + 1 < len(tokens):
                targets.append(tokens[index + 1])
            index += 2
        else:
            words.append(token)
            index += 1
    return words, targets


def unwrap(words: list[str], env: dict[str, str], prefixed: set[str]) -> list[str]:
    while words:
        name = os.path.basename(words[0])
        if name in WRAPPERS:
            words = words[1:]
            while words and (words[0].startswith("-") or ASSIGNMENT.match(words[0])):
                if ASSIGNMENT.match(words[0]):
                    key, value = words[0].split("=", 1)
                    env[key] = value
                    prefixed.add(key)
                words = words[1:]
        elif name == "timeout":
            words = skip_options(words[1:], {"-s", "--signal", "-k", "--kill-after"})[1:]
        elif name == "uv" and words[1:2] == ["run"]:
            words = skip_options(words[2:], UV_RUN_OPTIONS)
        elif name in {"npx", "xargs"}:
            words = skip_options(words[1:], {"-p", "--package", "-I", "-n", "-P", "-d", "-L"})
        else:
            return words
    return words


def skip_options(words: list[str], with_value: set[str]) -> list[str]:
    while words and words[0].startswith("-"):
        words = words[2:] if words[0] in with_value else words[1:]
    return words


# Tells a read of `git config` from a write, in both the legacy form (`git config key value`,
# `--unset`) and the subcommand form of git 2.46 (`git config set key value`). A section
# operation names sections, not keys, so every one of its names is returned.
def config_access(args: list[str]) -> tuple[list[str], bool, bool]:
    flags, positionals = set(), []
    rest = list(args)
    while rest:
        arg = rest.pop(0)
        if arg in CONFIG_VALUE_OPTIONS:
            rest = rest[1:]
        elif arg.startswith("-"):
            flags.add(arg)
        else:
            positionals.append(arg)
    action = ""
    if positionals and positionals[0] in CONFIG_READ_SUBCOMMANDS | CONFIG_WRITE_SUBCOMMANDS:
        action = positionals.pop(0)
        writes = action in CONFIG_WRITE_SUBCOMMANDS
    elif flags & CONFIG_WRITE_FLAGS:
        writes = True
    elif flags & CONFIG_READ_FLAGS:
        writes = False
    else:
        writes = len(positionals) > 1
    if action in CONFIG_SECTION_OPERATIONS or flags & CONFIG_SECTION_OPERATIONS:
        return [name.lower() for name in positionals], writes, True
    return [name.lower() for name in positionals[:1]], writes, False


# Keys that switch off the pre-push hook, run git commands the guard never sees, or decide
# which branches a push reaches. `key` is lower case.
def config_key_refusal(key: str) -> str | None:
    if key == "core.hookspath":
        return HOOKS_PATH
    if key.startswith("alias."):
        return ALIAS
    if key == "push.default" or re.fullmatch(r"remote\..+\.(push|mirror)", key):
        return PUSH_CONFIG
    return None


def section_refusal(section: str) -> str | None:
    if section == "core":
        return HOOKS_PATH
    if section == "alias":
        return ALIAS
    if section == "push" or section.startswith("remote."):
        return PUSH_CONFIG
    return None


def check_gh(args: list[str], rules: Rules) -> None:
    if args[:2] == ["pr", "merge"]:
        raise GuardError("merging a PR is the owner's gate")
    if args[:1] == ["repo"] and set(args[1:2]) & {"delete", "archive", "rename", "edit"}:
        raise GuardError("changing repository settings is the owner's call")
    if args[:1] in (["secret"], ["variable"], ["ruleset"]):
        if set(args[1:2]) & {"set", "delete", "remove"}:
            raise GuardError("changing secrets, variables or rulesets is the owner's call")
    if args[:2] in (["release", "delete"], ["run", "delete"]):
        raise GuardError("deleting releases or workflow runs is the owner's call")
    if args[:1] == ["api"]:
        method = api_method(args[1:])
        if method == "DELETE":
            if any("$" in arg or "`" in arg for arg in args[1:]):
                raise GuardError(
                    "`gh api -X DELETE` on an endpoint built from variables cannot be "
                    "verified; spell the endpoint out"
                )
            for arg in args[1:]:
                owned = owner_deletion(arg)
                if owned:
                    raise GuardError(f"`gh api -X DELETE {arg}`: deleting {owned}")
            return
        sensitive = any(
            re.search(r"/merges?\b|/protection|/rulesets|refs/heads/(main|master)\b", arg)
            for arg in args[1:]
        )
        if sensitive and method != "GET":
            raise GuardError(
                "write calls to merges, branch protection or main are the owner's call"
            )
        if rules.channel_ref and method != "GET":
            for arg in args[1:]:
                match = rules.channel_ref.search(arg)
                if match:
                    name = match.group(1)
                    raise GuardError(f"write calls to {name}: {owner_only(name)}")


# Detaching is judged by target: this plugin (under any marketplace, or no plugin named at
# all, or --all) and the marketplaces it comes from. Managing other plugins, and `update`,
# `install`, `enable`, stay open. A target the guard cannot resolve is refused.
def check_claude(args: list[str], env: dict[str, str], segment_env: dict[str, str]) -> None:
    start = next((index for index, arg in enumerate(args) if arg in {"plugin", "plugins"}), None)
    if start is None:
        return
    rest = args[start + 1 :]
    if any(arg in {"-h", "--help"} for arg in rest):
        return
    positionals, every = [], False
    index = 0
    while index < len(rest):
        arg = rest[index]
        if arg in CLAUDE_VALUE_OPTIONS:
            index += 1
        elif arg == "--all" or (arg.startswith("-") and not arg.startswith("--") and "a" in arg):
            every = True
        elif not arg.startswith("-"):
            positionals.append(arg)
        index += 1
    if not positionals:
        return
    sub, targets = positionals[0], positionals[1:]
    plugin = PluginIdentity(segment_env)
    if sub == "disable" and (every or not targets):
        raise GuardError(PLUGIN_INSTALL.format(name=plugin.name))
    if sub in {"disable", "uninstall", "remove"}:
        for target in targets:
            if resolved_name(target, env).split("@", 1)[0] == plugin.name:
                raise GuardError(PLUGIN_INSTALL.format(name=plugin.name))
    if sub == "marketplace" and targets[:1] in (["remove"], ["rm"]):
        for target in targets[1:]:
            plugin.check_marketplace(resolved_name(target, env))


def resolved_name(raw: str, env: dict[str, str]) -> str:
    expanded = expand_variables(raw, env)
    if "$" in expanded or "`" in expanded:
        raise GuardError(PLUGIN_VARIABLE.format(raw))
    return expanded


class PluginIdentity:
    def __init__(self, env: dict[str, str]):
        self.roots = plugin_roots(env)
        self.name = plugin_name(self.roots)
        self.config_dir = Path(env.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")

    # The plugin's own layout answers first, so the install state is read only when needed.
    def check_marketplace(self, marketplace: str) -> None:
        if marketplace in self.layout_marketplaces():
            raise GuardError(PLUGIN_INSTALL.format(name=self.name))
        installed = self.installed_marketplaces()
        if installed is None:
            raise GuardError(PLUGIN_STATE_UNREADABLE.format(marketplace))
        if marketplace in installed:
            raise GuardError(PLUGIN_INSTALL.format(name=self.name))

    def layout_marketplaces(self) -> set[str]:
        found = set()
        for root in self.roots:
            # …/plugins/cache/<marketplace>/<plugin>/<version>
            parents = root.parents
            if len(parents) > 3 and parents[2].name == "cache" and parents[3].name == "plugins":
                found.add(parents[1].name)
            manifest = read_json(root.parent / ".claude-plugin" / "marketplace.json")
            if isinstance(manifest, dict) and isinstance(manifest.get("name"), str):
                entries = manifest.get("plugins")
                if isinstance(entries, list) and any(
                    isinstance(entry, dict) and entry.get("name") == self.name for entry in entries
                ):
                    found.add(manifest["name"])
        return found

    def installed_marketplaces(self) -> set[str] | None:
        path = self.config_dir / "plugins" / "installed_plugins.json"
        if not path.exists():
            return set()
        data = read_json(path)
        if not isinstance(data, dict) or not isinstance(data.get("plugins"), dict):
            return None
        return {
            key.split("@", 1)[1]
            for key in data["plugins"]
            if isinstance(key, str) and key.split("@", 1)[0] == self.name and "@" in key
        }


def plugin_roots(env: dict[str, str]) -> list[Path]:
    roots = [Path(os.path.realpath(Path(__file__).resolve().parents[1]))]
    raw = env.get("CLAUDE_PLUGIN_ROOT")
    if raw:
        root = Path(os.path.realpath(os.path.expanduser(raw)))
        if root not in roots:
            roots.append(root)
    return roots


def plugin_name(roots: list[Path]) -> str:
    for root in roots:
        manifest = read_json(root / ".claude-plugin" / "plugin.json")
        if isinstance(manifest, dict) and isinstance(manifest.get("name"), str):
            return manifest["name"]
    return DEFAULT_PLUGIN_NAME


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


# What an API DELETE may not touch: the same ground the gh subcommands above keep for the
# owner. Everything else — Actions artifacts and caches, comments, labels — goes through.
def owner_deletion(arg: str) -> str | None:
    path = urlparse(arg).path if "://" in arg else arg.split("?", 1)[0]
    parts = [part for part in path.split("/") if part]
    for index, part in enumerate(parts):
        # repos/<owner>/<repo>, repositories/<id>, orgs/<org> — also behind a prefix such as
        # the api/v3 of GitHub Enterprise Server
        width = {"repos": 3, "repositories": 2, "orgs": 2}.get(part)
        if width is None or len(parts) < index + width:
            continue
        rest = parts[index + width :]
        if not rest:
            return f"the {'organization' if part == 'orgs' else 'repository'} is the owner's call"
        if rest[:2] == ["git", "refs"]:
            return "branch and tag refs is the owner's call, like `git push --delete`"
        break
    for part in parts:
        if part in API_OWNER_DELETIONS:
            return f"{API_OWNER_DELETIONS[part]} is the owner's call"
    return None


def api_method(args: list[str]) -> str:
    for index, arg in enumerate(args):
        if arg in {"-X", "--method"} and index + 1 < len(args):
            return args[index + 1].upper()
        if arg.startswith("--method="):
            return arg.split("=", 1)[1].upper()
        if arg.startswith("-X") and len(arg) > 2:
            return arg[2:].upper()
    field_options = ("-f", "-F", "--field", "--raw-field", "--input")
    has_fields = any(arg.split("=", 1)[0] in field_options for arg in args)
    return "POST" if has_fields else "GET"


# main and master keep the 0.3.4 wording (a push to master names main); a configured
# branch is named itself, the first in sorted order when several are hit
def shown(branches: set[str]) -> str:
    return "main" if branches & DEFAULT_PROTECTED else sorted(branches)[0]


def owner_only(branch: str) -> str:
    return (
        MAIN_OWNER_ONLY if branch in DEFAULT_PROTECTED else CHANNEL_OWNER_ONLY.format(branch=branch)
    )


def is_force_flag(arg: str) -> bool:
    return arg == "--force" or (arg.startswith("-") and not arg.startswith("--") and "f" in arg)


# git completes `heads/main` to `refs/heads/main`, so both prefixes name a branch
def ref_name(spec: str) -> str:
    return spec.lstrip("+").split(":")[-1].removeprefix("refs/").removeprefix("heads/")


def resolve(base: Path, raw: str) -> Path:
    return Path(os.path.normpath(base / os.path.expanduser(raw)))


def is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def workspace(
    env: dict[str, str], cwd: Path, worktree_dir: str
) -> tuple[set[Path], list[Path], Path]:
    toplevel = git_output(cwd, "rev-parse", "--show-toplevel")
    project = Path(env.get("CLAUDE_PROJECT_DIR") or toplevel or cwd)
    common = git_output(project, "rev-parse", "--path-format=absolute", "--git-common-dir")
    main_root = Path(common).parent if common else project
    projects = {project, main_root}
    scratch = Path(f"/tmp/claude-{os.getuid()}")
    worktrees = worktree_root(main_root, worktree_dir)
    return projects, [*projects, worktrees, scratch], worktrees


# Configuration may point the worktree directory somewhere else, never at everything:
# an absolute path or one containing the repository would turn the whole filesystem — or
# the project root itself — into a place files may be deleted from.
def worktree_root(main_root: Path, worktree_dir: str) -> Path:
    candidate = Path(os.path.normpath(main_root / worktree_dir))
    if not os.path.isabs(worktree_dir) and not is_within(main_root, candidate):
        return candidate
    if worktree_dir not in warned_worktree_dirs:
        warned_worktree_dirs.add(worktree_dir)
        print(
            f"pipeline guard: worktree.dir `{worktree_dir}` would widen the rule to the "
            f"project or the whole filesystem; using {DEFAULT_WORKTREE_DIR} instead",
            file=sys.stderr,
        )
    return Path(os.path.normpath(main_root / DEFAULT_WORKTREE_DIR))


def git_output(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def read_dotenv(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return {}
    values = {}
    for line in lines:
        line = line.strip().removeprefix("export ").strip()
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip().upper()] = value.strip().strip("'\"")
    return values


if __name__ == "__main__":
    sys.exit(main())
