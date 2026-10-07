# ADR Index — atg-framework

Full text: [`docs/DECISIONS.md`](../DECISIONS.md)  
Architecture: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)

| ID | Title | Status | Date |
|----|-------|--------|------|
| 0001 | Documentation system layout | Accepted | 2026-07-11 |
| 0002 | Custom ATG core; frameworks as adapters | Accepted | 2026-07-11 |
| 0003 | Model-agnostic LLM port; no paper model pins | Accepted | 2026-07-11 |
| 0004 | MVP scope — synthetic tools/mocks; benchmarks deferred | Accepted | 2026-07-11 |
| 0005 | Stdlib-only graph core (no NetworkX in core) | Accepted | 2026-07-11 |
| 0006 | Pydantic v2 for public node/result models | Accepted | 2026-07-11 |
| 0007 | Tools, atomicity, compile stop (OpenAI-style + callable) | Accepted | 2026-07-11 |
| 0008 | Packaging — src layout, uv, optional extras | Accepted | 2026-07-11 |
| 0009 | Graph history as full snapshots | Accepted | 2026-07-11 |
| 0010 | Pluggable parallel runner; threads default | Accepted | 2026-07-11 |
| 0011 | Dynamic ready-queue and node status | Accepted | 2026-10-05 |
| 0012 | Structured decomposition JSON in core | Accepted | 2026-10-05 |
| 0013 | Structural thought experiment, optional judge | Accepted | 2026-10-05 |
| 0014 | LCA repair region and a narrow reset | Accepted | 2026-10-05 |
| 0015 | JSON checkpoint beside in-memory history | Accepted | 2026-10-05 |
| 0016 | One-way DSPy and LangGraph callables | Accepted | 2026-10-05 |
| 0017 | Default local model tag `llama3.1:8b` | Superseded by 0023 | 2026-10-05 |
| 0018 | Paper benchmarks stay deferred | Accepted | 2026-10-05 |
| 0019 | MIT license | Accepted | 2026-10-05 |
| 0020 | Third-party ATG gap check | Accepted | 2026-10-05 |
| 0021 | OpenAI-compatible local client | Accepted | 2026-10-06 |

| 0022 | Toy PoC metrics for localized repair | Accepted | 2026-10-06 |
| 0023 | Default local model tag `qwen2.5:14b` | Accepted | 2026-10-06 |
| 0024 | A malformed decomposition is a compile error | Accepted | 2026-10-06 |

When decision count becomes unwieldy, migrate individual entries to `docs/adr/NNNN-slug.md` via a new Accepted decision—do not fork a second log silently.
