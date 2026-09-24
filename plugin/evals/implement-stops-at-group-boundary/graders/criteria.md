---
type: llm
weight: 1
---

The task: `/pipeline:implement 001` in a project whose `.claude/workflow.json` has
`"implement": {"chunked": true}`. The reviewed plan of SPEC 001 has two step groups under
`## Steps`: `### Group 1 — Tags` with step 1 (`add_tag` in `shop/tags.py`, which appends the
lower-cased tag) and step 2 (a duplicate tag is ignored), and `### Group 2 — Label` with
step 3 (`tags_line` in `shop/labels.py`). With chunking on and more than one group, the
skill carries out only the group that holds the first unticked step, then appends an entry
to `## Chunk notes`, commits, pushes and ends with the spec status left at `plan-approved`.
The converge pass and the Definition of Done belong to the chunk with the last group, not
to this one.

The response is correct when its final message, or the PLAN it summarises, shows that:

1. steps 1 and 2 were carried out, ticked and committed;
2. step 3 was not started, and `shop/labels.py` was not written;
3. `## Chunk notes` has an entry for group 1 that gives the running `implement_iterations`
   total;
4. the spec status is still `plan-approved`;
5. the final message says the chunk ended at the group boundary, and that the next group
   is carried out by running the skill again.

The response is incorrect when the agent does any of the following: carries out step 3 or
any other part of group 2; sets the status to `implemented`; runs the converge pass or the
Definition of Done in this chunk; ends without a `## Chunk notes` entry; or stops inside
group 1, before step 2 is ticked and committed, without an escalation that explains why.
