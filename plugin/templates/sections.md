# Section map

The SPEC and PLAN section literals in both languages. Every pipeline stage reads this file
with `Read` at run time before it looks for a section, names a section by its English
literal and accepts either when reading, so a spec written in either language, or before
0.5.0, is found. The templates `SPEC.<language>.md` and `PLAN.<language>.md` beside this
file carry exactly these literals; the H1 lines (`# SPEC NNN — `, `# PLAN NNN — `) are
shared by both languages.

| key | document | Polish | English |
|---|---|---|---|
| `goal` | SPEC | `## Cel` | `## Goal` |
| `context` | SPEC | `## Kontekst` | `## Context` |
| `read-context` | SPEC | `## Przeczytany kontekst` | `## Read context` |
| `scope` | SPEC | `## Zakres` | `## Scope` |
| `out-of-scope` | SPEC | `## Poza zakresem` | `## Out of scope` |
| `requirements` | SPEC | `## Wymagania i kryteria akceptacji` | `## Requirements and acceptance criteria` |
| `decisions` | SPEC | `## Decyzje i odrzucone alternatywy` | `## Decisions and rejected alternatives` |
| `owner-decisions` | SPEC | `## Decyzje właściciela` | `## Owner decisions` |
| `open-questions` | SPEC | `## Pytania otwarte (nieblokujące)` | `## Open questions (non-blocking)` |
| `assumption` | SPEC | `(założenie)` | `(assumption)` |
| `owner-summary` | PLAN | `## Streszczenie dla właściciela` | `## Owner summary` |
| `summary-approach` | PLAN | `**Podejście:**` | `**Approach:**` |
| `summary-risks` | PLAN | `**Główne ryzyka:**` | `**Main risks:**` |
| `summary-dependency` | PLAN | `**Nowa zależność:**` | `**New dependency:**` |
| `summary-migration` | PLAN | `**Migracja danych:**` | `**Data migration:**` |
| `summary-manual` | PLAN | `**Scenariusze ręczne dla właściciela:**` | `**Manual scenarios for the owner:**` |
| `approach` | PLAN | `## Podejście` | `## Approach` |
| `ac-matrix` | PLAN | `## Macierz AC → kroki` | `## AC → steps matrix` |
| `steps` | PLAN | `## Kroki` | `## Steps` |
| `step-group` | PLAN | `### Grupa N — ` | `### Group N — ` |
| `step-verification` | PLAN | `Weryfikacja automatyczna:` | `Automatic verification:` |
| `risks` | PLAN | `## Ryzyka i pułapki` | `## Risks and traps` |
| `e2e` | PLAN | `## Weryfikacja end-to-end` | `## End-to-end verification` |
| `e2e-automatic` | PLAN | `### Automatyczna (wykonuje /pipeline:implement)` | `### Automatic (performed by /pipeline:implement)` |
| `e2e-manual` | PLAN | `### Ręczna (wykonuje właściciel)` | `### Manual (performed by the owner)` |
| `definition-of-done` | PLAN | `## Definition of Done` | `## Definition of Done` |
| `owner-decisions` | PLAN | `## Decyzje właściciela` | `## Owner decisions` |
| `review-log` | PLAN | `## Review log` | `## Review log` |
| `chunk-notes` | PLAN | `## Notatki chunków` | `## Chunk notes` |
| `deviations` | PLAN | `## Deviations` | `## Deviations` |
| `final-review` | PLAN | `## Final review` | `## Final review` |
