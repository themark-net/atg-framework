# atg-framework

**Prototype implementation of Atomic Task Graph (ATG) concepts** for building more robust, efficient LLM-based agents.

This is an **independent reimplementation** of ideas from the research literature. It is **not** an official release from the paper authors.

## Citation & attribution

Core design is based on:

> Yue Zhang, Sihan Chen, Ziwen Huang, Hanyun Cui, Kangye Ji, and Zhi Wang.  
> **Atomic Task Graph: A Unified Framework for Agentic Planning and Execution.**  
> arXiv:2607.01942 \[cs.AI\], 2026.  
> https://doi.org/10.48550/arXiv.2607.01942 · https://arxiv.org/abs/2607.01942

**Authors** (equal contribution: Sihan Chen, Ziwen Huang): Yue Zhang, Sihan Chen, Ziwen Huang, Hanyun Cui, Kangye Ji, Zhi Wang.  
**Affiliations:** South China University of Technology; Tsinghua Shenzhen International Graduate School, Tsinghua University.

Machine-readable and policy artifacts:

| Artifact | Purpose |
|----------|---------|
| [`CITATION.cff`](CITATION.cff) | GitHub / CFF preferred citation (paper + software) |
| [`docs/citations.bib`](docs/citations.bib) | BibTeX (`zhang2026atg`) |
| [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) | What ideas come from the paper, what this repo may claim, code comment norms |
| `/attribution` skill | Agent checklist so future implementation keeps credit intact |

BibTeX:

```bibtex
@article{zhang2026atg,
  title   = {Atomic Task Graph: A Unified Framework for Agentic Planning and Execution},
  author  = {Zhang, Yue and Chen, Sihan and Huang, Ziwen and Cui, Hanyun and Ji, Kangye and Wang, Zhi},
  journal = {arXiv preprint arXiv:2607.01942},
  year    = {2026},
  eprint  = {2607.01942},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  doi     = {10.48550/arXiv.2607.01942},
  url     = {https://arxiv.org/abs/2607.01942}
}
```

This repository serves as the dedicated development and testing space for ATG ideas. It is linked as an untested prototype from the [local-llm-dev-tools catalog](https://github.com/themark-net/local-llm-dev-tools) (see the ATG entry in TOOLS.md for analysis, feasibility scoring, and distilled methodology).

**Current Status**: Initial skeleton / proof-of-concept. Untested implementation focused on core reusable components with emphasis on built-in testing and validation. Not production-ready — use for experimentation, rapid iteration, and validating concepts from the paper in a local LLM context (Ollama, LiteLLM, DSPy, LangGraph, etc.). Active space to deploy and test these ideas.

## Core Goals
- Reusable Python framework centered on explicit DAG-based task planning and execution.
- Support for dependency-driven parallelism and reuse of verified intermediate results.
- Localized failure detection and targeted repair using graph evolution history.
- Strong built-in testing, validation harnesses, and benchmarking tools from the start.
- Seamless integration points with popular local agent stacks.
- Focus on reliability and efficiency for complex agentic workflows, especially on smaller models and consumer hardware.

## High-Level Architecture (Initial Sketch - Subject to Refinement)
- `atg.graph`: Core DAG representation, dependency resolution, history/evolution tracking (NetworkX? custom? LangGraph integration?).
- `atg.planner`: Recursive decomposition of tasks into atomic nodes with explicit I/O dependencies.
- `atg.executor`: Parallel execution engine respecting dependencies; ready-node scheduling.
- `atg.repair`: Failure localization via graph history and minimal subgraph repair.
- `atg.validation`: Graph integrity checks, plan executability, result validators.
- `atg.testing`: Test harness (mock LLMs, property-based tests, benchmark runners), metrics collection.
- `atg.integrations`: Adapters for DSPy signatures/modules, LangGraph state graphs, tool calling schemas, memory backends (e.g., MCP-like persistent storage).
- `examples/`: Toy tasks and end-to-end demos.
- `tests/`: Comprehensive test suite.

## Documentation system

| Doc | Role |
|-----|------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Master design: goals, paper map, modernization of outdated paper stack, target layout |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | ADR log (choices + rejected paths) |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Parked questions (OQ-NNNN) |
| [`docs/TODO.md`](docs/TODO.md) | Backlog and phase gates |
| [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) | Paper credit |
| [`docs/README.md`](docs/README.md) | Doc map |

Workflow: **ARCHITECTURE** → park unknowns in **OPEN_QUESTIONS** → bind choices in **DECISIONS** → execute via **TODO**.

## Quick Start (Placeholder)
```bash
# Once packaged
pip install -e .
python -m atg.examples.simple_multi_step_task
```

Run tests:
```bash
pytest
```

## Integration Notes
Designed to complement and extend existing setups like DSPy + LiteLLM for orchestration, Ollama for local inference, and custom MCP-style code memory. The explicit graph structure aligns naturally with persistent memory of verified subtasks and dependencies.

## Links
- Paper (abs): https://arxiv.org/abs/2607.01942
- Paper (HTML): https://arxiv.org/html/2607.01942
- Paper (DOI): https://doi.org/10.48550/arXiv.2607.01942
- Attribution policy: [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md)
- Cite this repo: [CITATION.cff](CITATION.cff) · [docs/citations.bib](docs/citations.bib)
- Analysis & Tracking Repo: https://github.com/themark-net/local-llm-dev-tools (ATG section — feasibility ~75/100, distilled method, implementation guidance)
- Related Concepts: Your gom-jobbar-grok4 style agents, LangGraph workflows, etc.

**License**: To be determined (MIT or Apache-2.0 recommended for broad reusability). Software license is separate from the paper’s arXiv license.

Contributions, experiments, and feedback welcome. This is our sandbox to turn the paper's promising architecture into tested, reusable code — with correct credit to Zhang et al. (2026).