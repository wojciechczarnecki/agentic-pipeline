---
type: llm
weight: 1
---

The task: `/pipeline:plan-review 001` on a plan in status `plan-draft`, in a consumer whose
`.claude/workflow.json` sets `"language": "pl"`, so the SPEC and the PLAN use the Polish
section headings. Step 2 of the plan adds `PyYAML==6.0.2` to `requirements.txt` and reads
`settings.yaml` with `yaml.safe_load`; the plan's owner summary says the new dependency is
PyYAML, accepted in the SPEC. The SPEC's owner decisions section — under its Polish
heading, the twin of `## Owner decisions` in the plugin's section map — accepts exactly that
dependency. The plan is otherwise complete: every acceptance criterion has a step and a
proving test, every step has exact verification commands, and the end-to-end verification
is split into automatic and manual parts. The review skill escalates only on a dependency the owner has
not accepted, so the correct outcome is approval.

The response is correct when the agent:

1. reviews the plan and identifies `PyYAML` as a new dependency;
2. recognises that the owner accepted it in the SPEC's owner decisions section (the Polish
   heading of `## Owner decisions`);
3. does not escalate on the dependency;
4. ends with the spec status `plan-approved`.

Fixing minor things in the plan in place and writing a review log is fine, in either
language.

Escalating means that this review stops and hands a question to the owner now, instead of
approving. A plan step, fixed by the reviewer, that tells the implementer to stop or
escalate later if a check fails (for example, when `import yaml` fails on the target
machine) is not an escalation on the dependency; neither are notes about follow-up work
outside the SPEC (how PyYAML reaches the hosts, wiring the settings path to a command line).
Judge the reviewer's own outcome: approved with `plan-approved`, or not.

The response is incorrect when the agent escalates on the dependency or asks the owner to
accept it; when it claims the owner has not accepted `PyYAML`, or that the SPEC has no
owner decisions section; when it leaves the status `plan-draft`; or when it rewrites the
plan to drop `PyYAML` (a hand-written or standard-library parser, another file format).
