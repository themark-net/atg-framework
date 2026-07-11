# Agent guide — atg-framework

Read before multi-step implementation work.

## Source of truth

| Need | Read |
|------|------|
| Goals, paper map, outdated stack notes, package design | `docs/ARCHITECTURE.md` |
| Binding decisions + rejected alternatives | `docs/DECISIONS.md` |
| Parked questions | `docs/OPEN_QUESTIONS.md` |
| What to do next | `docs/TODO.md` |
| Paper credit | `docs/ATTRIBUTION.md` · skill `/attribution` |

## Rules

1. **Do not re-propose Rejected ADR alternatives** without new evidence and a superseding decision.
2. **New design uncertainty** → add `OQ-NNNN` to `docs/OPEN_QUESTIONS.md` (and link from TODO). Do not leave P0–P2 only in chat or orphan `TODO` comments.
3. **Architectural answer** → promote OQ via ADR in `docs/DECISIONS.md` (`promoted-to-adr`).
4. **ATG method ideas** → credit Zhang et al. (2026), arXiv:2607.01942; never claim this repo “proposes ATG”.
5. **MVP** = synthetic tools + mocks + parallel execute + localized repair (Decision 0004). Paper benchmarks are deferred.
6. **Core** stays framework-agnostic (Decision 0002). No LangGraph/DSPy imports in core packages.

## Skills

- `/adr` — record or supersede decisions  
- `/open-questions` / `/oq` — manage OQs  
- `/attribution` — citation audit when touching planner/executor/repair  
- `/docs` — module docs after non-trivial code lands  
