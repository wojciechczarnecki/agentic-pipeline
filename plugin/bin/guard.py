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

PROTECTED_BRANCHES = {"main", "master"}
DB_COMMANDS = {"upgrade", "downgrade", "stamp", "revision", "current", "check"}
NO_CONFIG = (
    "pipeline guard: no .claude/workflow.json found, so only the universal rules apply "
    "(production hosts, worktree directory and migrations stay unguarded) — "
    "run /pipeline:init to create one"
)
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
HEREDOC_DELIMITER = re.compile(r"(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
PUNCTUATION = ";&|()<>"

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
LOOP_KEYWORDS = {"do", "then", "else", "elif", "{"}
SHELL_SYNTAX = {"for", "while", "until", "if", "case", "select", "done", "fi", "esac", "}"}
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
HOOKS_PATH = "changing core.hooksPath would switch off the pre-push guard"
CONFIG_READS = {"get", "list", "--get", "--get-all", "--get-regexp", "-l", "--list"}
GUARDRAIL_FILES = (
    "guardrail files (.claude/settings*.json, .claude/workflow.json and the plugin "
    "directory) change only through Edit/Write with the owner's approval"
)
GIT_HOOKS = (
    "an existing git hook changes only through Edit/Write with the owner's approval; "
    "creating a missing hook (and making it executable) is allowed"
)
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


class Analyzer:
    def __init__(self, cwd: Path, env: dict[str, str], rules: Rules, in_container: bool = False):
        self.cwd = cwd
        self.env = env
        self.rules = rules
        self.in_container = in_container

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
            nested = Analyzer(self.cwd, dict(self.env), self.rules, self.in_container)
            nested.run(dollar or backtick, depth + 1)
        try:
            tokens = tokenize(text)
        except ValueError:
            raise GuardError(
                "the command could not be parsed; split it into simpler ones"
            ) from None
        words: list[str] = []
        conditional = False
        for token in [*tokens, ";"]:
            if is_operator(token):
                if words:
                    self.segment(words, depth, conditional)
                conditional = token in {"&&", "||"}
                words = []
            else:
                words.append(token)

    def segment(self, tokens: list[str], depth: int, conditional: bool = False) -> None:
        words, redirects = split_redirects(tokens)
        env = dict(self.env)
        while words and ASSIGNMENT.match(words[0]):
            key, value = words.pop(0).split("=", 1)
            # an assignment behind && or || may never run, so the value stays unverifiable
            env[key] = f"${key}" if conditional else value
        if not words:
            self.env = env
            return
        keyword = os.path.basename(words[0])
        if keyword in LOOP_KEYWORDS:
            words = words[1:]
        if not words or os.path.basename(words[0]) in SHELL_SYNTAX:
            return
        words = unwrap(words, env)
        if not words:
            return
        program, args = os.path.basename(words[0]), words[1:]
        if program in self.rules.blocked_programs:
            raise GuardError(self.rules.blocked_programs[program])
        self.check_guardrail_files(program, args, redirects)
        if program in SHELLS:
            if "-c" in args[:-1]:
                self.run(args[args.index("-c") + 1], depth + 1)
            return
        if program == "eval":
            self.run(" ".join(args), depth + 1)
            return
        if program == "cd":
            self.change_dir(args)
            return
        if program == "export":
            for arg in args:
                if ASSIGNMENT.match(arg):
                    key, value = arg.split("=", 1)
                    self.env[key] = value
            return
        if program in NETWORK_PROGRAMS and self.rules.production_host:
            if any(self.rules.production_host.search(arg) for arg in args):
                raise GuardError("production is off limits to agent sessions; ask the owner")
        if program == "git":
            self.git(args)
        elif program == "gh":
            check_gh(args)
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
                elif option == "-c" and value.lower().startswith("core.hookspath"):
                    raise GuardError(HOOKS_PATH)
        if not rest:
            return
        sub, sub_args = rest[0], rest[1:]
        if "--no-verify" in sub_args:
            raise GuardError("skipping git hooks with --no-verify is off limits")
        if sub == "config" and any(arg.lower().startswith("core.hookspath") for arg in sub_args):
            if not CONFIG_READS & set(sub_args):
                raise GuardError(HOOKS_PATH)
        if sub == "reset" and "--hard" in sub_args:
            raise GuardError("`git reset --hard` discards work irreversibly; ask the owner")
        if sub == "clean" and any(is_force_flag(arg) for arg in sub_args):
            raise GuardError("`git clean -f` deletes untracked files irreversibly; ask the owner")
        if sub == "branch" and BRANCH_REWRITE & set(sub_args):
            if PROTECTED_BRANCHES & set(sub_args):
                raise GuardError("deleting, renaming or resetting main is off limits")
        if sub in {"checkout", "restore"}:
            self.reject_guardrail_targets(
                [arg for arg in sub_args if not arg.startswith("-")], check_hooks=True
            )
        if sub == "worktree" and sub_args[:1] == ["add"]:
            self.worktree_add(sub_args[1:])
        if sub in {"update-ref", "symbolic-ref"}:
            if any(ref_name(arg) in PROTECTED_BRANCHES for arg in sub_args):
                raise GuardError(MAIN_OWNER_ONLY)
        if sub not in {"push", "commit", "merge", "rebase", "cherry-pick", "revert", "am", "pull"}:
            return
        branch = git_output(cwd, "branch", "--show-current")
        on_protected = branch in PROTECTED_BRANCHES
        if sub == "push":
            check_push(sub_args, on_protected)
        elif on_protected and sub == "pull":
            if "--ff-only" not in sub_args:
                raise GuardError("on main only `git pull --ff-only` is allowed")
        elif on_protected:
            raise GuardError(f"`git {sub}` on {branch}: {MAIN_OWNER_ONLY}")

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


def unwrap(words: list[str], env: dict[str, str]) -> list[str]:
    while words:
        name = os.path.basename(words[0])
        if name in WRAPPERS:
            words = words[1:]
            while words and (words[0].startswith("-") or ASSIGNMENT.match(words[0])):
                if ASSIGNMENT.match(words[0]):
                    key, value = words[0].split("=", 1)
                    env[key] = value
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


def check_push(args: list[str], on_protected: bool) -> None:
    for arg in args:
        destructive = arg in {"--mirror", "--delete", "-d", "--prune"} or arg.startswith("--force")
        if destructive or is_force_flag(arg):
            raise GuardError("force, mirror and delete pushes are off limits; ask the owner")
    refspecs = [arg for arg in args if not arg.startswith("-")][1:]
    if any(spec.startswith(("+", ":")) for spec in refspecs):
        raise GuardError("force and delete pushes are off limits; ask the owner")
    targets = {ref_name(spec) for spec in refspecs}
    pushes_current = not refspecs or bool(targets & {"HEAD", "@"})
    if targets & PROTECTED_BRANCHES or (on_protected and pushes_current):
        raise GuardError(f"pushing to main: {MAIN_OWNER_ONLY}")


def check_gh(args: list[str]) -> None:
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
        sensitive = any(
            re.search(r"/merges?\b|/protection|/rulesets|refs/heads/(main|master)\b", arg)
            for arg in args[1:]
        )
        if method == "DELETE" or (sensitive and method != "GET"):
            raise GuardError(
                "write calls to merges, branch protection or main are the owner's call"
            )


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


def is_force_flag(arg: str) -> bool:
    return arg == "--force" or (arg.startswith("-") and not arg.startswith("--") and "f" in arg)


def ref_name(spec: str) -> str:
    return spec.lstrip("+").split(":")[-1].removeprefix("refs/heads/")


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
