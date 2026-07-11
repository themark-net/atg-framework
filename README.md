# atg-framework

**Prototype implementation of Atomic Task Graph (ATG) concepts** for building more robust, efficient LLM-based agents.

Based on the research paper: [Atomic Task Graph: A Unified Framework for Agentic Planning and Execution](https://arxiv.org/abs/2607.01942) by researchers from Tsinghua University and South China University of Technology.

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

See `docs/TODO.md` (or root TODO.md) for detailed open questions, architecture decisions, and prioritized roadmap to MVP.

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
- Paper: https://arxiv.org/abs/2607.01942 (and HTML version for reading)
- Analysis & Tracking Repo: https://github.com/themark-net/local-llm-dev-tools (ATG section — feasibility ~75/100, distilled method, implementation guidance)
- Related Concepts: Your gom-jobbar-grok4 style agents, LangGraph workflows, etc.

**License**: To be determined (MIT or Apache-2.0 recommended for broad reusability).

Contributions, experiments, and feedback welcome. This is our sandbox to turn the paper's promising architecture into tested, reusable code.