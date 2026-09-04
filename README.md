# atg-framework

**Prototype implementation of Atomic Task Graph (ATG) concepts** for building more robust, efficient LLM-based agents.

This is an **independent reimplementation** of ideas from the research literature. It is **not** an official release from the paper authors.

## Citation & attribution

Core design is based on Zhang et al. (2026), *Atomic Task Graph*, arXiv:2607.01942. See `docs/ATTRIBUTION.md` and `CITATION.cff`.

**Current status:** Phase 1 skeleton on `main` — installable `src/atg` with graph/types/history/tools/validation. `pytest` green, no LLM. Not production-ready.

## Quick Start

```bash
pip install -e ".[dev]"
pytest
# or: PYTHONPATH=src pytest
```

Later examples read `ATG_MODEL` (placeholder `ollama/<current-small-instruct>`).

## Documentation system

| Doc | Role |
|-----|------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Master design |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | ADR log |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Parked questions |
| [`docs/TODO.md`](docs/TODO.md) | Phase gates |
| [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) | Paper credit |

**License:** [MIT](LICENSE). Separate from the paper’s arXiv license.
