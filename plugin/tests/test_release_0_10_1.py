import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()


# 0.10.1: the output estimate. A later bump keeps this green; the section for the manifest
# version is pinned in test_readme.py.
def test_the_manifest_is_at_least_0_10_1():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert tuple(int(part) for part in manifest["version"].split(".")) >= (0, 10, 1)


def test_the_changelog_records_the_output_estimate():
    assert "\n## 0.10.1\n" in CHANGELOG
    section = CHANGELOG.split("\n## 0.10.1\n", 1)[1].split("\n## ", 1)[0]
    for token in ["`stop_reason`", "`signature`", "`ESTIMATES`", "partly estimated", "20"]:
        assert token in section, token
    assert "**consumer impact:**" in section
