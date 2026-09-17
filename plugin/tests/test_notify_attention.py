import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "bin" / "notify-attention.sh"
BASH = shutil.which("bash") or "/bin/bash"


def stub(directory: Path, name: str, marker: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    script.write_text(f'#!/bin/sh\necho "$@" > "{marker}"\n')
    script.chmod(0o755)


def run(path: str) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, str(HOOK)], capture_output=True, text=True, env={"PATH": path})


@pytest.fixture
def tools(tmp_path):
    return tmp_path / "bin"


def test_linux_notification_tool_is_used(tools, tmp_path):
    marker = tmp_path / "notified.txt"
    stub(tools, "notify-send", marker)
    result = run(str(tools))
    assert result.returncode == 0
    assert "Agent waits for your reaction" in marker.read_text()


def test_macos_notification_tool_is_used(tools, tmp_path):
    marker = tmp_path / "notified.txt"
    stub(tools, "osascript", marker)
    result = run(str(tools))
    assert result.returncode == 0
    assert "display notification" in marker.read_text()


def test_linux_wins_when_both_are_available(tools, tmp_path):
    linux, mac = tmp_path / "linux.txt", tmp_path / "mac.txt"
    stub(tools, "notify-send", linux)
    stub(tools, "osascript", mac)
    assert run(str(tools)).returncode == 0
    assert linux.exists() and not mac.exists()


def test_without_any_tool_it_rings_the_terminal(tools):
    result = run("/nonexistent")
    assert result.returncode == 0
    assert result.stdout == "\a"
