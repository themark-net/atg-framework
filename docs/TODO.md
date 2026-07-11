# TODO, Open Questions & MVP Roadmap for atg-framework

Central tracking document for the ATG prototype. All open questions are marked **[OPEN]**. Decisions and progress will be noted here. This is the single source for next steps toward a testable MVP.

**Current Status (as of creation)**: Repo initialized with README. Skeleton structure and this TODO. No code yet — focus on clarifying architecture before heavy implementation. Linked as untested prototype from local-llm-dev-tools catalog.

## Open Questions **[OPEN]** (Architecture & Design)

### Graph & State Management
- **[OPEN] Graph Library Choice**: Use NetworkX for rich DAG features, visualization, and algorithms (e.g., topological sort, ancestors)? Or implement a lightweight custom DAG (fewer deps, more control)? Or lean heavily into LangGraph's StateGraph from the start for built-in persistence/state?
  - *Tradeoffs*: NetworkX adds dependency but speeds prototyping; custom keeps core minimal; LangGraph aligns with existing agent patterns but may constrain pure ATG graph model.
- **[OPEN] History / Evolution Tracking**: Full snapshot of every DAG version? Event log of changes (add node, resolve dependency)? How to store/retrieve for repair without excessive memory use on long-running tasks?
- **[OPEN] Result Representation & Caching**: How to model node outputs (raw values, metadata like confidence, timestamps)? Caching strategy (hash of task + inputs + context)? Integration with external memory (Chroma/LanceDB for semantic reuse or simple dict for MVP)? Validity/freshness checks?

### Planning & Decomposition
- **[OPEN] Atomic Task Definition**: What constitutes an "atomic" node? Pure Python callables? Structured objects with prompt + tool schema + expected output format (Pydantic)? DSPy modules/signatures?
- **[OPEN] Decomposition Strategy**: LLM prompt design (system prompt, few-shot examples of good decompositions, chain-of-thought)? Use structured output (JSON mode, Pydantic, or DSPy)? Recursive vs. iterative decomposition? How to handle dependencies during decomposition?
- **[OPEN] Plan Validation During Planning**: Early detection of cycles, missing dependencies, or infeasible plans? Lightweight checker before execution?

### Execution & Parallelism
- **[OPEN] Parallel Execution Model**: `concurrent.futures.ThreadPoolExecutor` (simple for I/O-bound LLM calls)? `asyncio` with proper handling of LLM clients? Or queue-based scheduler? How to handle shared state or side effects safely?
- **[OPEN] Dependency Resolution at Runtime**: Topological sort upfront or dynamic ready-queue (nodes become ready as predecessors complete)? Priority or heuristic scheduling?

### Failure, Repair & Robustness
- **[OPEN] Failure Detection**: Tool exceptions only? LLM self-assessment / output validators (e.g., another LLM call or rule-based)? Custom success predicates per task type? Combination?
- **[OPEN] Repair Logic**: Simple re-queue of failed node + dependents? LLM-guided repair (analyze failure + history to suggest fixes or alternative decomposition)? How to "freeze" validated upstream results and prevent re-execution?
- **[OPEN] Error Context for Localization**: What info does the repair module need (failure type, node outputs, graph neighborhood, full history)? How to pass it efficiently?

### Testing, Validation & Benchmarking (Core Strength of This Repo)
- **[OPEN] Testing Harness Design**: Pytest with heavy use of fixtures and monkeypatching for mock LLMs? Integration with real local models (Ollama) for end-to-end? Property-based testing (Hypothesis) for graph invariants (acyclicity, dependency consistency)?
- **[OPEN] Validation Components**: Graph structural validators (DAG check, dependency closure)? Plan executability checker? Result schema validators? Performance metrics collector (parallelism ratio, repair savings, success rate, token usage)?
- **[OPEN] Benchmark Suite**: Simple synthetic tasks (multi-step arithmetic, data pipelines)? Re-implement mini versions of paper benchmarks (e.g., household-like or ALFWorld-inspired)? Metrics aligned with paper (success rate, efficiency, hallucination proxies)?
- **[OPEN] Mock LLM Strategy**: Deterministic responses for unit tests? Configurable failure injection? Logging of all calls for debugging?

### Integrations & Usability
- **[OPEN] DSPy / LangGraph Integration**: How to wrap ATG planner/executor as DSPy modules or LangGraph nodes/graphs? Bidirectional? Expose ATG as a higher-level orchestrator?
- **[OPEN] Tool Calling**: Standardized way to register tools (OpenAI-style schemas)? Automatic wrapping?
- **[OPEN] Memory (MCP-like)**: How to persist graph state, node results, and history? Queryable for reuse or debugging? Alignment with your existing MCP code memory work?
- **[OPEN] Configuration & Extensibility**: YAML/JSON config for models, prompts, parallelism settings? Plugin system for custom planners/repairers?

### Packaging & Project
- **[OPEN] Project Structure**: Flat src/ or nested packages? Monorepo style or keep focused?
- **[OPEN] Dependencies**: Minimal core (stdlib + pydantic?) with optional extras (`[langgraph]`, `[networkx]`, `[testing]`)? Poetry, uv, or setuptools?
- **[OPEN] Documentation**: Sphinx or MkDocs? Docstrings + examples as primary?
- **[OPEN] License & Distribution**: MIT for max reusability?

## MVP Roadmap & Prioritized Next Steps

**MVP Definition**: A minimal end-to-end runnable prototype demonstrating:
- Task decomposition into DAG.
- Parallel execution of independent branches.
- Basic failure handling (at least retry or simple re-execution).
- Test coverage and a couple of working examples.
- Clear integration path notes for DSPy/LangGraph.

**Phase 1: Foundations (High Priority - Start Here)**
1. Define core abstractions/interfaces (e.g., `TaskNode`, `DAG`, `Planner`, `Executor` protocols or ABCs).
2. Implement basic in-memory DAG with dependency tracking and topological utilities (decide on NetworkX vs custom early).
3. Stub recursive planner with a simple LLM call (via LiteLLM or direct Ollama client) for decomposition.
4. Basic sequential executor (upgrade to parallel later).
5. Simple test harness with mock LLM that returns predefined decompositions/responses.
6. One end-to-end toy example (e.g., "Plan and execute a multi-step research or data task").
7. Document decisions in this TODO and update README if architecture solidifies.

**Phase 2: Core ATG Features (Medium Priority)**
8. Parallel execution scheduler.
9. Result caching skeleton (in-memory dict first).
10. Basic failure detection + re-execution repair.
11. Graph history logging (lightweight).
12. Expanded validation (DAG checks, dependency satisfaction).
13. More examples and initial benchmark runner.

**Phase 3: Polish, Integrations & Testing Depth**
14. Full repair module with localization heuristics.
15. DSPy/LangGraph adapter examples.
16. Property-based tests and richer mock capabilities.
17. Performance metrics and comparison vs. linear baseline agent.
18. Packaging, docs, and contribution guidelines.

**Tracking Progress**: Update this file with completed items, new questions, or experiment results. Use issues or branches for larger features.

## Notes
- All design choices should prioritize **testability and observability** — this repo's strength.
- Keep core lightweight and focused; push complexity into integrations or optional modules.
- Revisit paper for details on any ambiguous points during implementation.
- Link experiments or prototypes back to the tracking repo's ATG entry for visibility.

This document evolves with the project. Start by tackling Phase 1 open questions and initial code skeleton.