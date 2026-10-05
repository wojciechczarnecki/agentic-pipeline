#!/usr/bin/env python3
# Reads the fixed forms of SPEC.md and PLAN.md that `workflow_metrics.py --derive` counts.
# Section headings come from templates/sections.md at run time, so a spec written in either
# language is found; every other form is a code token, the same in both languages.
import re
from dataclasses import dataclass
from pathlib import Path

SECTIONS_FILE = Path(__file__).resolve().parent.parent / "templates" / "sections.md"
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(SPEC|PLAN)\s*\|\s*`([^`]*)`\s*\|\s*`([^`]*)`\s*\|\s*$")
HEADING = re.compile(r"^(#+) ")
STAGES = ("plan", "plan-review", "implement", "final-review")
KINDS = ("decision", "permission", "tooling", "gate")


def section_map() -> dict[tuple[str, str], tuple[str, str]]:
    rows = {}
    for line in SECTIONS_FILE.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            rows[(match.group(2), match.group(1))] = (match.group(3), match.group(4))
    return rows


def literals(document: str, key: str) -> tuple[str, str]:
    return section_map()[(document, key)]


# The lines under the heading whose literal is one of the key's two, down to the next heading
# of the same or a higher level. A fenced block never holds a heading.
def section(text: str, document: str, key: str) -> str | None:
    wanted = set(literals(document, key))
    found, level, fenced, body = False, 0, False, []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            if found:
                body.append(line)
            continue
        heading = None if fenced else HEADING.match(line)
        if not found:
            if heading and line.rstrip() in wanted:
                found, level = True, len(heading.group(1))
            continue
        if heading and len(heading.group(1)) <= level:
            break
        body.append(line)
    return "\n".join(body) if found else None


# A section holds something when it has more than the template's one-line `_(…)_` placeholder.
def has_content(body: str | None) -> bool:
    if body is None:
        return False
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return bool(lines) and not all(re.fullmatch(r"_\(.*\)_", line) for line in lines)


def entries(body: str | None) -> list[str]:
    found: list[str] = []
    for line in (body or "").splitlines():
        if line.startswith("- "):
            found.append(line[2:].strip())
        elif found and line.startswith(" ") and line.strip():
            found[-1] += " " + line.strip()
    return found


STEP = re.compile(r"^- \[( |x|X)\] (\d+)\. (.*)")
NOTE = re.compile(r"`iterations: (\d+)`")


@dataclass
class Step:
    number: int
    ticked: bool
    iterations: int | None


# A step line of the template (`<what> …`, `…`) is a placeholder, not a step.
def steps(plan: str) -> list[Step]:
    blocks: list[tuple[int, bool, list[str]]] = []
    for line in (section(plan, "PLAN", "steps") or "").splitlines():
        match = STEP.match(line)
        if match:
            if match.group(3).startswith(("<", "…")):
                blocks.append((-1, False, []))
                continue
            blocks.append((int(match.group(2)), match.group(1) != " ", [match.group(3)]))
        elif blocks:
            blocks[-1][2].append(line)
    found = []
    for number, ticked, lines in blocks:
        if number < 0:
            continue
        note = NOTE.search("\n".join(lines))
        found.append(Step(number, ticked, int(note.group(1)) if note else None))
    return found


def deviations(plan: str) -> tuple[int, int] | None:
    body = section(plan, "PLAN", "deviations")
    if body is None:
        return None
    found = entries(body)
    major = sum(1 for entry in found if entry.startswith("`major`"))
    return len(found) - major, major


REVIEW_FINDING = re.compile(r"^(?:- |\d+\. )`(blocker|major|minor)`")
FINAL_FINDING = re.compile(r"^\s*- \*\*F(\d+)\*\*\s+`(blocker|worth-fixing|nit)`")


def review_log(plan: str, severity: str) -> int | None:
    body = section(plan, "PLAN", "review-log")
    if not has_content(body):
        return None
    return sum(
        1
        for line in (body or "").splitlines()
        if (match := REVIEW_FINDING.match(line)) and match.group(1) == severity
    )


def final_review(plan: str, severity: str) -> int | None:
    body = section(plan, "PLAN", "final-review")
    if not has_content(body):
        return None
    seen: dict[str, str] = {}
    for line in (body or "").splitlines():
        match = FINAL_FINDING.match(line)
        if match:
            seen.setdefault(match.group(1), match.group(2))
    return sum(1 for found in seen.values() if found == severity)


ENTRY = re.compile(
    rf"^(\d{{4}}-\d{{2}}-\d{{2}}) [—-] ({'|'.join(STAGES)}) [—-] `([a-z]+)`(?: [—-] (.*))?$"
)
IDS = r"(?:F\d+(?:\s*,\s*F\d+)*|none)"


@dataclass
class Decision:
    stage: str
    kind: str
    text: str


# The fixed-form entries of an `## Owner decisions` section, and the top-level entries that are
# not in that form (a kind outside the four counts as not in the form).
def decisions(text: str, document: str) -> tuple[list[Decision], list[str]]:
    formed: list[Decision] = []
    unformed: list[str] = []
    for entry in entries(section(text, document, "owner-decisions")):
        match = ENTRY.match(entry)
        if match and match.group(3) in KINDS:
            formed.append(Decision(match.group(2), match.group(3), match.group(4) or ""))
        else:
            unformed.append(entry)
    return formed, unformed


def gate_ids(decision: Decision) -> tuple[list[str], list[str]] | None:
    parsed = []
    for word in ("accepted", "rejected"):
        match = re.search(rf"`{word}`:\s*({IDS})", decision.text)
        if not match:
            return None
        parsed.append([] if match.group(1) == "none" else re.findall(r"F\d+", match.group(1)))
    return parsed[0], parsed[1]


ACS = re.compile(r"^\s*- \[[ xX]\] AC(\d+)\b", re.MULTILINE)


def spec_acs(spec_text: str) -> list[int]:
    return sorted({int(number) for number in ACS.findall(spec_text)})


def matrix_acs(plan: str | None) -> set[int]:
    found: set[int] = set()
    for line in (section(plan, "PLAN", "ac-matrix") or "").splitlines() if plan else []:
        cells = line.strip().strip("|").split("|")
        if line.lstrip().startswith("|") and cells:
            found.update(int(number) for number in re.findall(r"AC(\d+)", cells[0]))
    return found


# The items of `### Manual` that carry no pass-condition line. A section of the single line
# `n/a — <reason>` has no items to report.
def manual_without_pass(plan: str | None) -> list[str]:
    body = section(plan, "PLAN", "e2e-manual") if plan else None
    if body is None:
        return []
    lines = [line for line in body.splitlines() if line.strip()]
    if len(lines) == 1 and re.match(r"n/a\s+[—-]\s+\S", lines[0]):
        return []
    marks = literals("PLAN", "pass-condition")
    missing = []
    for item in _items(body):
        stripped = [re.sub(r"^(- )?", "", line.strip()) for line in item]
        if not any(line.startswith(marks) for line in stripped):
            missing.append(stripped[0])
    return missing


def _items(body: str) -> list[list[str]]:
    items: list[list[str]] = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append([line])
        elif items and line.strip():
            items[-1].append(line)
    return items
