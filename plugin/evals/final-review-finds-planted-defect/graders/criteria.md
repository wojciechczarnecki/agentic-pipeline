---
type: llm
weight: 1
---

The task: `/pipeline:final-review 001 report` on a finished feature branch. The SPEC says
orders whose subtotal is 100.00 or more ship free. `shop/shipping.py` implements it as
`if subtotal_cents > FREE_FROM_CENTS: return 0` with `FREE_FROM_CENTS = 10000`, so an
order of exactly 100.00 is still charged shipping. The tests cover 150.00 and 50.00 only,
so the suite is green and the defect hides behind it.

The response is correct when the agent produces a review report (in its final message,
or in the PLAN's final review section that its final message summarises) that contains
a finding which:

1. points at `shop/shipping.py` (a line number is welcome but not required);
2. says that an order of exactly 100.00 (10000 cents) is charged shipping although the
   SPEC makes it free, because the comparison is `>` where it must be `>=`;
3. carries a weight above a nit: `blocker`, `worth fixing`, the skill's Polish label for
   worth fixing (it starts `warto popraw`), "should fix", "major" or an equivalent label
   are all acceptable; the wording of the label does not matter, only that the finding is
   not filed as a cosmetic nit.

Suggesting a boundary test for 10000 cents alongside the fix is welcome but not required.

The response is incorrect when the boundary defect is missing from the report; when it
is filed only as a `nit`; when it is listed among the rejected or dismissed findings;
when the agent changes `shop/shipping.py` or its tests during report mode instead of only
reporting; or when no report is produced at all.
