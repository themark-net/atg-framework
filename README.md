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

**Current status:** The MVP loop is implemented and covered by unit tests: compile a task to a DAG, run independent tools together, and repair a failed region without re-running frozen nodes. An offline example prints a two-branch sum. A live Ollama path reads `ATG_MODEL` (default `llama3.1:8b`). On 2026-10-05 that live path exited 1 for `llama3.1:8b` (180s timeout), `qwen2.5:14b` (an edge named the parent id), and `gemma4:latest` (the sink omitted `value`). The compiler now drops edges that name an id outside the child set. Re-run `--live` when `ollama ps` is empty; the numbers are on Decision 0017. Not production-ready. The software license is MIT (Decision 0019).

## Core Goals
- Reusable Python framework centered on explicit DAG-based task planning and execution.
- Support for dependency-driven parallelism and reuse of verified intermediate results.
- Localized failure detection and targeted repair using graph evolution history.
- Strong built-in testing, validation harnesses, and benchmarking tools from the start.
- Seamless integration points with popular local agent stacks.
- Focus on reliability and efficiency for complex agentic workflows, especially on smaller models and consumer hardware.

## High-Level Architecture

Binding detail is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md).

- `atg.types` / `atg.graph`: stdlib DAG and frozen Pydantic nodes (Decisions 0005, 0006, 0011). No NetworkX in core.
- `atg.history`: full graph snapshots (Decision 0009).
- `atg.tools`: OpenAI-style JSON schema plus a same-name callable (Decision 0007).
- `atg.validation`: acyclicity, `$ref` checks, and parent/subgraph interface checks.
- `atg.planner`, `atg.executor`, `atg.thought`, `atg.repair`: the compile / run / check / repair loop (Decisions 0011–0014).
- `atg.integrations`: one-way callables for LangGraph and DSPy. They do not import those packages (Decision 0016).
- `examples/toy_parallel.py`: offline by default. `--live` calls Ollama.
- `tests/`: unit tests do not call a model. The integration mark is off unless `ATG_RUN_INTEGRATION=1`.

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

## Quick Start

```bash
uv sync --extra dev
uv run pytest
uv run python examples/toy_parallel.py
```

The offline example compiles a two-branch sum with a scripted model and prints `value=25`. A local Ollama run uses `ATG_MODEL` (default `llama3.1:8b`, Decision 0017):

```bash
uv run python examples/toy_parallel.py --live
```

`pip install -e .` also works. The optional `llm` extra installs LiteLLM. The software license is MIT.

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

**License**: MIT (`LICENSE`). The software license is separate from the paper’s arXiv license.

Contributions, experiments, and feedback welcome. This is our sandbox to turn the paper's promising architecture into tested, reusable code — with correct credit to Zhang et al. (2026).