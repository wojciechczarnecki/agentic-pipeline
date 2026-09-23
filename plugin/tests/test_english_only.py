import ast
import io
import tokenize
from fnmatch import fnmatch
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
# Escapes, so that this module carries no Polish letter of its own.
POLISH_LOWER = "\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c"
POLISH_LETTERS = set(POLISH_LOWER + POLISH_LOWER.upper())

# Polish survives only where a Polish consumer needs it (SPEC 008): the Polish templates,
# the section map, the Polish mirror fixture, the prompt whose Polish is the behaviour under
# test, and the test modules that pin those files as data.
ALLOWLIST = [
    "templates/*.pl.md",
    "templates/docs/*.pl.md",
    "templates/sections.md",
    "evals/plan-review-approves-polish-owner-decision/scaffold.sh",
    "evals/init-without-questions/case.yaml",
    "tests/test_templates_language.py",
    "tests/test_eval_cases.py",
    "tests/test_init_templates.py",
    # Released entries quote the Polish literals of their time, inside code spans only
    # (test_readme.py, test_no_polish_outside_code).
    "CHANGELOG.md",
]
# Generated eval reports quote past runs, which may be Polish.
SKIPPED = ("evals/results/",)


def has_polish(text: str) -> bool:
    return bool(POLISH_LETTERS & set(text))


def matches(relative: str, pattern: str) -> bool:
    parts, wanted = relative.split("/"), pattern.split("/")
    return len(parts) == len(wanted) and all(map(fnmatch, parts, wanted))


def polish_files(root: Path, skip: tuple[str, ...] = ()) -> list[str]:
    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(skip):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if has_polish(text):
            found.append(relative)
    return found


def polish_in_python_names(path: Path) -> list[str]:
    source = path.read_text()
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT and has_polish(token.string):
            found.append(f"comment on line {token.start[0]}")
    tree = ast.parse(source)
    named = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in [tree, *(node for node in ast.walk(tree) if isinstance(node, named))]:
        docstring = ast.get_docstring(node)
        where = "module" if isinstance(node, ast.Module) else node.name
        if docstring and has_polish(docstring):
            found.append(f"docstring of {where}")
        if isinstance(node, named) and has_polish(node.name):
            found.append(f"name {node.name}")
    return found


def stage_files() -> list[Path]:
    return sorted((PLUGIN / "skills").rglob("*.md")) + sorted((PLUGIN / "agents").glob("*.md"))


@pytest.mark.parametrize("path", stage_files(), ids=lambda p: str(p.relative_to(PLUGIN)))
def test_skills_and_agents_have_no_polish(path):
    assert not has_polish(path.read_text())


def test_polish_lives_only_in_the_allowlist():
    outside = [
        relative
        for relative in polish_files(PLUGIN, SKIPPED)
        if not any(matches(relative, pattern) for pattern in ALLOWLIST)
    ]
    assert not outside, outside


# The allowlist cannot rot: an entry that no longer holds Polish, or a glob that matches
# nothing, is removed rather than left to excuse a future file.
@pytest.mark.parametrize("pattern", ALLOWLIST)
def test_the_allowlist_is_live(pattern):
    polish = polish_files(PLUGIN, SKIPPED)
    assert any(matches(relative, pattern) for relative in polish), pattern


@pytest.mark.parametrize("path", sorted((PLUGIN / "tests").glob("*.py")), ids=lambda p: p.name)
def test_test_code_is_english(path):
    assert not polish_in_python_names(path)


def test_the_checks_catch_a_planted_letter(tmp_path):
    letter = POLISH_LOWER[0]
    (tmp_path / "notes.md").write_text(f"a note with {letter}\n")
    (tmp_path / "clean.md").write_text("an English note\n")
    assert polish_files(tmp_path) == ["notes.md"]
    assert polish_files(tmp_path, ("notes",)) == []
    module = tmp_path / "planted.py"
    module.write_text(
        f'"""module {letter}"""\n\n\n'
        f"def check_{letter}():\n"
        f'    """function {letter}"""\n'
        f"    return 1  # comment {letter}\n"
    )
    found = polish_in_python_names(module)
    assert "docstring of module" in found
    assert f"docstring of check_{letter}" in found
    assert f"name check_{letter}" in found
    assert "comment on line 6" in found
    assert matches("templates/SPEC.pl.md", "templates/*.pl.md")
    assert not matches("templates/docs/PROJECT.pl.md", "templates/*.pl.md")
