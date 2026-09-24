#!/usr/bin/env python3
# The one place a project tells the pipeline plugin about itself: .claude/workflow.json.
# A missing file means documented defaults, never a failure — the plugin has to stay usable
# in a repository that has not been initialised yet.
import fnmatch
import json
import shlex
import sys
from pathlib import Path

CONFIG_RELATIVE = Path(".claude") / "workflow.json"

SCHEMA: dict[str, object] = {
    "production": {"hosts": list, "commands": list},
    "worktree": {"dir": str},
    "verify": {"command": str, "scopes": list},
    "format": list,
    "docs": {
        "roadmap": str,
        "backlog": str,
        "decisions": str,
        "conventions": str,
        "project": str,
        "specsDir": str,
    },
    "migrations": {"command": str, "localHosts": list},
    "gitHooksDir": str,
    "protectedBranches": list,
    "language": str,
    "models": {"plan": str, "plan-review": str, "implement": str, "final-review": str},
}


LANGUAGES = ("en", "pl")
MODEL_VALUES = ("inherit", "sonnet", "opus", "haiku", "fable")


class ConfigError(Exception):
    pass


def defaults() -> dict:
    return {
        "production": {"hosts": [], "commands": []},
        "worktree": {"dir": "../worktrees"},
        "verify": {"command": "bash scripts/verify.sh", "scopes": []},
        "format": [],
        "docs": {
            "roadmap": "docs/ROADMAP.md",
            "backlog": "docs/BACKLOG.md",
            "decisions": "docs/DECISIONS.md",
            "conventions": "docs/CONVENTIONS.md",
            "project": "docs/PROJECT.md",
            "specsDir": "specs",
        },
        "gitHooksDir": "scripts/git-hooks",
        "language": "en",
    }


class Config:
    def __init__(self, data: dict, path: Path | None = None, unreadable: bool = False):
        self.data = data
        self.path = path
        self.unreadable = unreadable

    @property
    def found(self) -> bool:
        return self.path is not None

    @property
    def root(self) -> Path | None:
        return self.path.parent.parent if self.path else None

    def get(self, dotted: str, fallback=None):
        node: object = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return fallback
            node = node[part]
        return node


def find_config(start: Path) -> Path | None:
    current = Path(start).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_RELATIVE
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            return None
    return None


def project_root(start: Path) -> Path:
    current = Path(start).resolve()
    for directory in [current, *current.parents]:
        if (directory / ".git").exists() or (directory / CONFIG_RELATIVE).is_file():
            return directory
    return current


def load(start: Path) -> Config:
    path = find_config(start)
    if path is None:
        return Config(defaults())
    raw = read_raw(path)
    validate(raw)
    return Config(merge(defaults(), raw), path)


def read_raw(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text())
    except OSError as exc:
        raise ConfigError(f"{path}: cannot be read ({exc})") from None
    except ValueError as exc:
        raise ConfigError(f"{path}: is not valid JSON ({exc})") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: the top level has to be an object")
    return raw


# Section-wise loading for the hooks: one bad key must not cost the project every rule it
# configured, so each top level section is validated on its own and only the faulty ones
# fall back to the defaults. The returned problems are meant to be warned about.
def load_sections(start: Path) -> tuple[Config, list[str]]:
    path = find_config(start)
    if path is None:
        return Config(defaults()), []
    raw = read_raw(path)
    kept: dict[str, object] = {}
    problems: list[str] = []
    for key, value in raw.items():
        if key == "models" and isinstance(value, dict):
            kept[key] = valid_entries(key, value, problems)
            continue
        try:
            validate({key: value})
        except ConfigError as exc:
            problems.append(str(exc))
            continue
        kept[key] = value
    return Config(merge(defaults(), kept), path), problems


# `models` is checked entry by entry: a bad entry sends only its own stage back to
# `inherit`, where dropping the section would reset every stage.
def valid_entries(key: str, section: dict, problems: list[str]) -> dict:
    kept = {}
    for entry, value in section.items():
        try:
            validate({key: {entry: value}})
        except ConfigError as exc:
            problems.append(str(exc))
            continue
        kept[entry] = value
    return kept


def stage_model(config: Config, stage: str) -> str:
    value = config.get(f"models.{stage}")
    return value if value in MODEL_VALUES else "inherit"


def validate(raw: dict, schema: dict | None = None, prefix: str = "") -> None:
    schema = SCHEMA if schema is None else schema
    for key, value in raw.items():
        dotted = f"{prefix}{key}"
        if key not in schema:
            known = ", ".join(sorted(schema))
            raise ConfigError(f"unknown key `{dotted}`; known keys here: {known}")
        expected = schema[key]
        if isinstance(expected, dict):
            if not isinstance(value, dict):
                raise ConfigError(f"`{dotted}` has to be an object")
            validate(value, expected, f"{dotted}.")
        elif not isinstance(value, expected) or isinstance(value, bool):
            raise ConfigError(f"`{dotted}` has to be {expected.__name__}")
        elif expected is list:
            check_list(dotted, value)
        elif dotted == "language" and value not in LANGUAGES:
            raise ConfigError(f"`language` has to be one of: {', '.join(LANGUAGES)}")
        elif prefix == "models." and value not in MODEL_VALUES:
            raise ConfigError(f"`{dotted}` has to be one of: {', '.join(MODEL_VALUES)}")


def check_list(dotted: str, value: list) -> None:
    if dotted != "format":
        for index, item in enumerate(value):
            if not isinstance(item, str):
                raise ConfigError(f"`{dotted}[{index}]` has to be str")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ConfigError(f"`format[{index}]` has to be an object")
        for field in ("match", "command"):
            if field not in item:
                raise ConfigError(f"`format[{index}]` is missing `{field}`")
            if not isinstance(item[field], str):
                raise ConfigError(f"`format[{index}].{field}` has to be str")
        for field in item:
            if field not in ("match", "command"):
                raise ConfigError(f"unknown key `format[{index}].{field}`")


def merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def format_command(config: Config, file_path: Path, root: Path) -> str | None:
    try:
        relative = Path(file_path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None
    quoted = shlex.quote(relative)
    for entry in config.get("format", []) or []:
        if not isinstance(entry, dict) or "match" not in entry or "command" not in entry:
            continue
        if fnmatch.fnmatch(relative, entry["match"]):
            command = entry["command"]
            if "{file}" in command:
                return command.replace("{file}", quoted)
            return f"{command} {quoted}"
    return None


def main(argv: list[str]) -> int:
    start = Path.cwd()
    if argv[1:2] == ["--check"]:
        try:
            config = load(start)
        except ConfigError as exc:
            print(f"workflow.json: {exc}", file=sys.stderr)
            return 1
        where = config.path if config.found else "not found — using defaults"
        print(f"workflow.json: {where}")
        return 0
    if argv[1:2] == ["--format-for"] and len(argv) > 2:
        try:
            config, problems = load_sections(start)
        except ConfigError as exc:
            print(f"workflow.json: {exc}", file=sys.stderr)
            return 1
        for problem in problems:
            print(f"workflow.json: {problem}", file=sys.stderr)
        root = config.root or project_root(start)
        command = format_command(config, Path(argv[2]), root)
        if command:
            print(command)
        return 0
    print("usage: workflow_config.py [--check | --format-for <path>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
