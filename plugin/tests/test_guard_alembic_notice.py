import json

import pytest
from test_guard import WORKFLOW
from test_guard_read_rule import NOTICE as READ_NOTICE
from test_guard_read_rule import Setup, allow, notice_of, write_settings

NOTICE = "alembic.ini"


@pytest.fixture
def setup(tmp_path):
    setup = Setup(tmp_path)
    covered = allow("Read(~/.claude/plugins/cache/mkt/pipeline/**)")
    write_settings(setup.repo / ".claude" / "settings.json", covered)
    without_migrations(setup)
    return setup


def without_migrations(setup, **extra):
    workflow = {key: value for key, value in WORKFLOW.items() if key != "migrations"}
    workflow.update(extra)
    (setup.repo / ".claude" / "workflow.json").write_text(json.dumps(workflow))


def add_file(setup, relative):
    path = setup.repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[alembic]\n")


def test_a_root_alembic_ini_without_migrations_is_noticed(setup):
    add_file(setup, "alembic.ini")
    result = setup.run()
    assert result.returncode == 0
    notice = notice_of(result)
    assert NOTICE in notice["systemMessage"] and "migrations" in notice["systemMessage"]
    assert NOTICE in notice["hookSpecificOutput"]["additionalContext"]
    assert "permissionDecision" not in notice["hookSpecificOutput"]


def test_the_notice_comes_once_per_session(setup):
    add_file(setup, "alembic.ini")
    first, second = setup.run(), setup.run()
    assert NOTICE in notice_of(first)["systemMessage"]
    assert second.returncode == 0 and second.stdout == ""


def test_a_subdirectory_alembic_ini_is_named_with_its_path(setup):
    add_file(setup, "backend/alembic.ini")
    message = notice_of(setup.run())["systemMessage"]
    assert "backend/alembic.ini" in message
    assert '"migrations"' in message


def test_a_migrations_section_silences_the_notice(setup):
    add_file(setup, "alembic.ini")
    (setup.repo / ".claude" / "workflow.json").write_text(json.dumps(WORKFLOW))
    assert setup.run().stdout == ""


def test_alembic_ini_two_levels_down_is_not_seen(setup):
    add_file(setup, "a/b/alembic.ini")
    assert setup.run().stdout == ""


def test_hidden_and_node_modules_directories_are_skipped(setup):
    add_file(setup, ".venv/alembic.ini")
    add_file(setup, "node_modules/alembic.ini")
    assert setup.run().stdout == ""


def test_a_repository_without_a_workflow_file_gets_no_alembic_notice(setup):
    add_file(setup, "alembic.ini")
    (setup.repo / ".claude" / "workflow.json").unlink()
    result = setup.run()
    assert NOTICE not in result.stdout and NOTICE not in result.stderr


def test_a_refused_call_carries_the_notice_after_the_reason(setup):
    add_file(setup, "alembic.ini")
    result = setup.run("gh pr merge 1")
    assert result.returncode == 2
    assert result.stderr.index("owner's gate") < result.stderr.index(NOTICE)


def test_both_notices_share_one_message(tmp_path):
    setup = Setup(tmp_path)
    without_migrations(setup)
    add_file(setup, "alembic.ini")
    message = notice_of(setup.run())["systemMessage"]
    assert READ_NOTICE in message and NOTICE in message
