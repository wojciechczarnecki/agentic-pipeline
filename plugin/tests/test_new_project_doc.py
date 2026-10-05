import re
from pathlib import Path

DOC = (Path(__file__).resolve().parents[1] / "docs" / "NEW-PROJECT.md").read_text()


def section(number: int) -> str:
    start = DOC.index(f"\n## {number}. ")
    end = DOC.find("\n## ", start + 1)
    return DOC[start : end if end != -1 else len(DOC)]


# SPEC 015, AC8: the first push to `main` comes before the hook, because the hook refuses it.
def test_the_first_push_comes_before_the_hook():
    after = section(3)
    push = after.index("git push -u origin main")
    hook = after.index("git config core.hooksPath")
    assert push < hook
    reason = after[:hook]
    assert "pre-push" in reason and "refuses" in reason


def test_the_scaffold_through_a_pr_path():
    after = " ".join(section(3).split())
    assert "git commit --allow-empty" in after
    assert "gh pr create" in after


def test_the_repository_settings_commands():
    after = section(3)
    for command in [
        "gh api -X POST repos/{owner}/{repo}/rulesets --input .github/repository/ruleset.json",
        "gh api -X PATCH repos/{owner}/{repo} --input .github/repository/settings.json",
        "gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts",
        "gh api -X PUT repos/{owner}/{repo}/automated-security-fixes",
        "gh api -X PUT repos/{owner}/{repo}/private-vulnerability-reporting",
    ]:
        assert command in after, command


def test_the_required_check_appears_after_the_first_run():
    after = " ".join(section(3).split())
    assert re.search(r"offers a required check only after the workflow has run once", after)


def test_the_adr_template_is_described():
    assert "templates/docs/adr/" in DOC and "docs/adr/" in DOC


def test_layers_in_subdirectories_are_described():
    first = " ".join(section(1).split())
    assert "backend/pyproject.toml" in first and "one level down" in first
    assert "named after the directory" in first
