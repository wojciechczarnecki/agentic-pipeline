import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin"
HOOK = BIN / "format-file.sh"
BASH = shutil.which("bash") or "/bin/bash"


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    return tmp_path


def configure(repo: Path, entries: list[dict]) -> None:
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "workflow.json").write_text(json.dumps({"format": entries}))


def run(repo: Path, payload: dict, path: str | None = None) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ["PATH"] if path is None else path, "CLAUDE_PROJECT_DIR": str(repo)}
    return subprocess.run(
        [BASH, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(repo),
        env=env,
    )


def edit_of(repo: Path, relative: str) -> dict:
    return {"tool_input": {"file_path": str(repo / relative)}}


def test_matching_file_is_formatted(repo):
    configure(repo, [{"match": "src/*.py", "command": "cp {file} formatted.txt"}])
    result = run(repo, edit_of(repo, "src/a.py"))
    assert result.returncode == 0
    assert (repo / "formatted.txt").read_text() == "x = 1\n"


def test_command_without_a_placeholder_gets_the_path_appended(repo):
    configure(repo, [{"match": "src/*.py", "command": "cp -t . "}])
    assert run(repo, edit_of(repo, "src/a.py")).returncode == 0
    assert (repo / "a.py").read_text() == "x = 1\n"


def test_a_path_with_a_space_stays_one_argument(repo):
    (repo / "src" / "a b.py").write_text("x = 2\n")
    configure(repo, [{"match": "src/*.py", "command": "cp {file} formatted.txt"}])
    assert run(repo, edit_of(repo, "src/a b.py")).returncode == 0
    assert (repo / "formatted.txt").read_text() == "x = 2\n"


@pytest.mark.parametrize("command", ["cp {file} formatted.txt", "cp -t . "])
def test_a_path_cannot_inject_a_second_command(repo, command):
    (repo / "src" / "a; touch pwned.py").write_text("x = 3\n")
    configure(repo, [{"match": "src/*.py", "command": command}])
    assert run(repo, edit_of(repo, "src/a; touch pwned.py")).returncode == 0
    assert not (repo / "pwned.py").exists()


def test_unmatched_file_is_left_alone(repo):
    configure(repo, [{"match": "backend/*.py", "command": "cp {file} formatted.txt"}])
    assert run(repo, edit_of(repo, "src/a.py")).returncode == 0
    assert not (repo / "formatted.txt").exists()


def test_no_config_means_no_formatting(repo):
    assert run(repo, edit_of(repo, "src/a.py")).returncode == 0
    assert not (repo / "formatted.txt").exists()


def test_broken_config_never_blocks(repo):
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / "workflow.json").write_text('{"nope": 1}')
    assert run(repo, edit_of(repo, "src/a.py")).returncode == 0


def test_a_failing_formatter_still_exits_zero(repo):
    configure(repo, [{"match": "src/*.py", "command": "false {file}"}])
    assert run(repo, edit_of(repo, "src/a.py")).returncode == 0


def test_payload_without_a_file_path_exits_zero(repo):
    configure(repo, [{"match": "src/*.py", "command": "cp {file} formatted.txt"}])
    assert run(repo, {"tool_input": {}}).returncode == 0
    assert not (repo / "formatted.txt").exists()


def test_missing_file_exits_zero(repo):
    configure(repo, [{"match": "src/*.py", "command": "cp {file} formatted.txt"}])
    assert run(repo, edit_of(repo, "src/gone.py")).returncode == 0
    assert not (repo / "formatted.txt").exists()


def test_malformed_payload_exits_zero(repo):
    configure(repo, [{"match": "src/*.py", "command": "cp {file} formatted.txt"}])
    result = subprocess.run(
        [BASH, str(HOOK)], input="not json", text=True, capture_output=True, cwd=str(repo)
    )
    assert result.returncode == 0


def test_without_python_nothing_is_formatted(repo):
    configure(repo, [{"match": "src/*.py", "command": "cp {file} formatted.txt"}])
    result = run(repo, edit_of(repo, "src/a.py"), path="/nonexistent")
    assert result.returncode == 0
    assert not (repo / "formatted.txt").exists()
