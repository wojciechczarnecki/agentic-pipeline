---
type: llm
weight: 1
---

The task: `/pipeline:implement 001` on a SPEC with two acceptance criteria. AC1: `add_note`
in `shop/notes.py` appends the stripped text to `order["notes"]`. AC2: a note longer than
200 characters after stripping raises `ValueError` and leaves the notes unchanged. The
reviewed plan has one step, which delivers only AC1; neither its steps nor its AC → steps
matrix mention AC2. The skill closes the planned steps with a converge pass: a fresh
subagent, started with the `Agent` tool, compares the code with every AC of the SPEC and
reports gaps as `missing`, `partial`, `contradicts` or `unrequested`; the implementer adds
a step for each real gap and carries it out with a test.

The response is correct when its final message, or the PLAN it summarises, shows that:

1. the converge pass ran as a subagent after the planned step;
2. it reported AC2 (the 200-character limit) as `missing` or `partial`;
3. the agent added a step for AC2 and carried it out with a test for an over-long note
   (for example 201 characters) that raises `ValueError` and leaves the notes unchanged;
4. the spec reached the status `implemented` with AC2 delivered.

An escalation after the converge pass that names AC2 as the gap, with options and a
recommendation, is also correct.

The response is incorrect when the agent does any of the following: reaches `implemented`
with AC2 not delivered and no gap recorded; never runs the converge pass as a subagent
(for example, checks the ACs itself in its own context and calls that the converge pass);
delivers AC2 without a converge gap and an added step being recorded in the PLAN, so the
plan no longer shows what was carried out; or stops before the planned step with an
escalation about AC2 instead of carrying out the plan and letting the converge pass find
the gap.
