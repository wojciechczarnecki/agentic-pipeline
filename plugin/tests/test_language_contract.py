import re
from pathlib import Path

import pytest
from test_templates_language import section_map

PLUGIN = Path(__file__).resolve().parents[1]
STAGE_SKILLS = ["idea", "plan", "plan-review", "implement", "final-review", "ship"]
AGENTS = ["planner", "plan-reviewer", "implementer", "reviewer"]
# `init` is the scaffold, not a pipeline stage: it asks for `language` instead of obeying it.
NOT_STAGES = {"init"}


def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def agent_text(name: str) -> str:
    return (PLUGIN / "agents" / f"{name}.md").read_text()


def section(text: str, heading: str) -> str:
    assert f"\n{heading}\n" in text, heading
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def bullets(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        if line.startswith("- "):
            items.append(line)
        elif items and line.startswith("  "):
            items[-1] += " " + line.strip()
    return items


# The language contract (plugin/README.md, SPEC 006 AC1–AC2) reaches every stage as one
# block, so a stage cannot drift from the others: files in `language`, commits and PR titles
# in English, the conversation in the session language.
def test_the_language_block_is_identical_everywhere():
    blocks = {name: section(skill_text(name), "## Language") for name in STAGE_SKILLS}
    assert len(set(blocks.values())) == 1, sorted(blocks)
    items = bullets(next(iter(blocks.values())))
    assert len(items) == 3
    assert "`language`" in items[0]
    for token in ["commit", "PR", "English"]:
        assert token in items[1], token
    assert "session" in items[2]


# The lists above are the parametrisation of every check here; a new stage skill or agent
# that is not on them would slip past the language contract, so they have to be complete.
def test_the_lists_cover_every_stage_and_agent():
    skills = {path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md")}
    assert skills - NOT_STAGES == set(STAGE_SKILLS)
    assert {path.stem for path in (PLUGIN / "agents").glob("*.md")} == set(AGENTS)


@pytest.mark.parametrize("agent", AGENTS)
def test_every_agent_states_its_language_part(agent):
    contract = section(agent_text(agent), "## Stage agent contract")
    assert "`language`" in contract
    assert "English" in contract


TEMPLATE_READS = {"idea": "SPEC", "plan": "PLAN"}
MAP_PATH = "${CLAUDE_PLUGIN_ROOT}/templates/sections.md"


def template_headings(document: str) -> set[str]:
    headings = set()
    for language in ("pl", "en"):
        text = (PLUGIN / "templates" / f"{document}.{language}.md").read_text()
        headings |= {line for line in text.splitlines() if re.match(r"#+ ", line)}
    return headings


# `idea` and `plan` read the one template for the current `language` at run time (SPEC 007,
# AC3) instead of carrying both inline; the files under `templates/` are the only copy.
@pytest.mark.parametrize("skill", sorted(TEMPLATE_READS))
def test_idea_and_plan_read_their_template(skill):
    document = TEMPLATE_READS[skill]
    text = skill_text(skill)
    choice = section(text, f"## {document}.md template")
    root = "${CLAUDE_PLUGIN_ROOT}/templates"
    assert f"{root}/{document}.pl.md" in choice
    assert "`Read`" in choice
    assert "`language`" in choice
    english = [line for line in choice.splitlines() if f"{root}/{document}.en.md" in line]
    assert len(english) == 1
    for phrase in ["a missing key", "any other value"]:
        assert phrase in english[0], phrase
    assert "```markdown" not in text and "````markdown" not in text
    own = {line for line in text.splitlines() if line.startswith("## ")}
    lines = set(text.splitlines())
    leaked = sorted((template_headings(document) - own) & lines)
    assert not leaked, leaked


def mapping_block(name: str) -> str:
    return section(skill_text(name), "## Section map")


# Every stage reads the section map from the plugin at run time (SPEC 007, AC4), through one
# block shared by all six skills.
def test_every_stage_reads_the_section_map():
    blocks = {name: mapping_block(name) for name in STAGE_SKILLS}
    assert len(set(blocks.values())) == 1, sorted(blocks)
    block = blocks[STAGE_SKILLS[0]]
    assert MAP_PATH in block
    assert "`Read`" in block
    assert "either" in block
    for name in STAGE_SKILLS:
        assert "section map in the README" not in skill_text(name), name


# A failed read ends the stage with the file and the rule to add (SPEC 007, AC5): a stage that
# guessed the headings would miss `## Decyzje właściciela` and escalate on an accepted
# dependency.
def test_a_failed_read_stops_the_stage():
    block = mapping_block(STAGE_SKILLS[0])
    for token in [
        "RESULT: ESCALATE",
        "STOP",
        "Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)",
        "Read(//",
        "permissions.allow",
    ]:
        assert token in block, token
    for skill, document in TEMPLATE_READS.items():
        choice = normalise(section(skill_text(skill), f"## {document}.md template"))
        assert '"Section map"' in choice, skill


def test_plan_writes_in_the_current_language():
    step = section(skill_text("plan"), "## Kroki").split("\n5. ", 1)[1].split("\n6. ", 1)[0]
    assert "`language`" in step
    assert "SPEC" in step
    assert "nie tłumaczysz" in step


def numbered_step(block: str, number: int) -> str:
    assert f"\n{number}. " in f"\n{block}", number
    return f"\n{block}".split(f"\n{number}. ", 1)[1].split(f"\n{number + 1}. ", 1)[0]


def test_plan_review_checks_the_language():
    step = numbered_step(section(skill_text("plan-review"), "## Kroki"), 3)
    assert any("`language`" in item for item in bullets(step.replace("\n   ", "\n")))


def test_final_review_titles_the_pr_in_english():
    step = numbered_step(section(skill_text("final-review"), "## Tryb apply"), 3)
    pr = [item for item in bullets(step.replace("\n   ", "\n")) if "gh pr create" in item]
    assert len(pr) == 1
    for token in ["--title", "angielsk", "`language`"]:
        assert token in pr[0], token


def test_ship_talks_to_the_owner_in_the_session_language():
    text = skill_text("ship")
    for heading in ["## Bramka: końcowe review", "## Protokół wyniku"]:
        assert "sesji" in section(text, heading), heading


def test_severities_are_tokens():
    assert "`[blocker|worth-fixing|nit] " in skill_text("final-review")
    plan_review = skill_text("plan-review")
    for token in ["`blocker`", "`major`", "`minor`"]:
        assert token in plan_review, token
    assert "`worth-fixing`" in section(skill_text("ship"), "## Bramka: końcowe review")
    texts = [skill_text(name) for name in STAGE_SKILLS] + [agent_text(name) for name in AGENTS]
    for text in texts:
        assert "warto poprawić" not in text


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def heading_text(literal: str) -> str:
    text = literal.lstrip("#").strip().replace("**", "")
    return text[:-1] if text.endswith(":") else text


def without_fences(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return "\n".join(kept)


def quoted(text: str) -> list[str]:
    flat = normalise(without_fences(text))
    return re.findall(r"`([^`]+)`", flat) + re.findall(r"„([^\"”]+)[\"”]", flat)


# A stage names a section by both literals (templates/sections.md, SPEC 006 AC7), so
# a spec written in either language, or before 0.5.0, is found. The check covers every map
# row whose literals differ: a Polish heading quoted in a skill or agent brings its English
# twin into the same file.
@pytest.mark.parametrize(
    "path",
    [f"skills/{name}/SKILL.md" for name in STAGE_SKILLS] + [f"agents/{name}.md" for name in AGENTS],
)
def test_sections_are_named_by_both_headings(path):
    text = (PLUGIN / path).read_text()
    spans = quoted(text)
    # Outside fences only: an English heading quoted inside a code example would satisfy the
    # check whatever the prose says.
    flat = normalise(without_fences(text))
    missing = []
    for _, _, polish, english in section_map():
        if polish == english:
            continue
        name = heading_text(polish)
        if any(name in span for span in spans) and heading_text(english) not in flat:
            missing.append((polish, english))
    assert not missing, (path, missing)


def test_the_both_headings_check_sees_wrapped_quotes():
    text = 'czytasz „Streszczenie dla\nwłaściciela" z planu'
    assert any("Streszczenie dla właściciela" in span for span in quoted(text))
    assert heading_text("Weryfikacja automatyczna:") == "Weryfikacja automatyczna"
    assert heading_text("**Podejście:**") == "Podejście"
