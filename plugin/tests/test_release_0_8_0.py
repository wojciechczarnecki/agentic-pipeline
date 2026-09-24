import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CHANGELOG = (PLUGIN / "CHANGELOG.md").read_text()


# SPEC 011, AC20: the cost metrics, `models` and targeted reading ship as 0.8.0. A later
# bump keeps this green; a CHANGELOG section for the manifest version is pinned in
# test_readme.py.
def test_the_manifest_is_at_least_0_8_0():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert tuple(int(part) for part in manifest["version"].split(".")) >= (0, 8, 0)


def test_the_changelog_records_spec_011():
    assert "\n## 0.8.0\n" in CHANGELOG
    section = CHANGELOG.split("\n## 0.8.0\n", 1)[1].split("\n## ", 1)[0]
    impact = " ".join(section.split("**consumer impact:**", 1)[1].split("\n### ", 1)[0].split())
    for token in ["optional", "`models`", "inherit", "transcripts", "`/pipeline:init`"]:
        assert token in impact, token
    for token in ["--record-cost", "converge_gaps", "deviations_minor", "Reading section"]:
        assert token in section, token


# SPEC 012, AC16: the chunked implementer ships in 0.8.0, off by default.
def test_the_changelog_records_spec_012():
    section = CHANGELOG.split("\n## 0.8.0\n", 1)[1].split("\n## ", 1)[0]
    impact = " ".join(section.split("**consumer impact:**", 1)[1].split("\n### ", 1)[0].split())
    for token in ["`implement.chunked`", "off", "older skills", "ordinary headings"]:
        assert token in impact, token
    for token in [
        "`## Chunk notes`",
        "`CHUNK: ",
        "implement_chunks",
        "implement-stops-at-group-boundary",
    ]:
        assert token in section, token
