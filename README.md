# atg-framework

**Prototype implementation of Atomic Task Graph (ATG) concepts** for building more robust, efficient LLM-based agents.

This is an **independent reimplementation** of ideas from the research literature. It is **not** an official release from the paper authors.

## Citation & attribution

Core design is based on Zhang et al. (2026), *Atomic Task Graph*, arXiv:2607.01942. See `docs/ATTRIBUTION.md` and `CITATION.cff`.

**Current status:** first-pass end-to-end loop — `compile → thought experiment → parallel execute → localized repair` — with a mock LLM. All MVP success criteria in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §3.3 are covered by `pytest` (no LLM, no GPU). Real-model path via LiteLLM is wired but unvalidated. Not production-ready.

## Quick Start

```bash
pip install -e ".[dev]"
pytest
python examples/weekend_trip.py          # offline demo with an injected tool failure
# optional real planner: pip install -e ".[llm]"; ATG_MODEL=ollama/<tag> python examples/weekend_trip.py --real
```

```python
from atg import ATGAgent, MockLLMClient, TaskSpec, ToolRegistry, ToolSpec

reg = ToolRegistry()
reg.register(ToolSpec(name="get_weather"), lambda city: {"forecast": f"sunny in {city}"})
agent = ATGAgent(reg, llm=MockLLMClient(structured={...}))   # or LiteLLMClient()
result = agent.run(TaskSpec(description="...", inputs={"city": "Paris"}, outputs={"itinerary": "text"}))
result.outputs, result.metrics, result.repairs, result.plan.history
```

| Module | ATG stage (Zhang et al. 2026) |
|--------|-------------------------------|
| `atg.planner` | §4.1 interface-preserving recursive compilation (structured JSON decompositions) |
| `atg.executor` | §4.2 dependency-aware ready-queue execution, parallel runner |
| `atg.thought` | §4.2 pre-execution thought experiment (rules + optional LLM judge) |
| `atg.repair` | §4.3 minimal subgraph repair via history LCA, frozen validated nodes |
| `atg.agent` | control loop tying the stages together |

Examples read the model tag from `ATG_MODEL`; nothing is pinned in library code.

## Documentation system

| Doc | Role |
|-----|------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Master design |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | ADR log |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Parked questions |
| [`docs/TODO.md`](docs/TODO.md) | Phase gates |
| [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) | Paper credit |

**License:** [MIT](LICENSE). Separate from the paper’s arXiv license.
