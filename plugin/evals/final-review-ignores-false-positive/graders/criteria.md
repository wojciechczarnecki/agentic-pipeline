---
type: llm
weight: 1
---

The task: `/pipeline:final-review 001 report` on a finished feature branch that adds
`app/users.py`. It builds `SELECT name FROM users ORDER BY {sort}` with an f-string, but
only after checking `sort` against the whitelist `SORTABLE = ("name", "created_at")` and
raising `ValueError` for anything else. That is correct: a column name cannot be passed as
a bound parameter in SQL, and the whitelist check runs before the query, so no input
outside the two column names ever reaches it. A test proves that
`"name; DROP TABLE users"` is rejected. The skill tells the reviewer to verify every
finding in the code and to reject false ones with a reason.

The response is correct when the agent:

1. produces a review report (in its final message, or in the PLAN's final review section
   that its final message summarises) that covers `app/users.py`;
2. does not keep the `ORDER BY` interpolation as an accepted finding: leaving it out,
   mentioning it as checked and correct, or listing it among the rejected findings with
   the whitelist as the reason are all fine.

Other findings, of any weight, about other aspects of the change do not make the response
incorrect.

The response is incorrect when any accepted finding, of any weight (`blocker`,
`worth-fixing` or `nit`), calls the `ORDER BY` interpolation in `app/users.py` an SQL
injection risk or unsafe, or asks to replace it with a bound parameter or a placeholder; or when no report
is produced, or the report never covers `app/users.py`.
