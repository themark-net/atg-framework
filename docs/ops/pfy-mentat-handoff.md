# Handoff: decide how pfy-mentat couples to atg-framework

**Status:** procedure for a later session. This file does not change pfy-mentat.  
**Prototype:** https://github.com/themark-net/atg-framework  
**Catalog repo:** `/home/mark/DEVELOP/pfy-mentat` (GitHub `themark-net/pfy-mentat`)  
**Paper:** Zhang, Chen, Huang, Cui, Ji, and Wang (2026), arXiv:2607.01942. Credit the authors. This library is an independent reimplementation. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

Read [`../USING.md`](../USING.md) and [`../NEXT.md`](../NEXT.md) before scoring. How to run the library is there. This page is only the coupling decision.

## Operator

You want a yes-or-no on whether the catalog should keep ATG as a link, probe the repo, onboard it, or embed it. The implementing session runs in **pfy-mentat**, after you ask for that work. Primary orchestration in pfy stays Grok, OpenCode, and skills. This library is a callable control loop for tool DAGs.

What “done” looks like in that later session:

1. `git fetch` in both repositories. Read atg-framework `main`. Do not score from memory of the August 2026 docs-only tree.
2. Run the offline checks in [Verify the library](#verify-the-library) or write down why the machine could not.
3. Fill the gate table in [Score the gates](#score-the-gates) with the commit SHA you fetched.
4. Update the stale catalog text so it describes that SHA. Apply the stage rule in [Which stage to choose](#which-stage-to-choose).
5. Leave eval-harness and the cage unwired. Leave ATG out of the default path.

## Why a new determination is due

pfy already answered the relationship question and then froze a snapshot that is no longer true.

| pfy record | What it still says | What to treat as historical |
|------------|--------------------|-----------------------------|
| `docs/open-questions/OQ-0004-atg-prototype-relationship.md` | Answered 2026-07-30: submodule later, I1 until the gates | The answer still points at the gates. It does not by itself authorize a submodule. |
| Issue #30, reviewed 2026-08-06 | Stay I1 | The written reason was “docs-only, Phase 1 not started, nothing executable to probe.” |
| `docs/ops/atg-coupling.md` | No `src/atg/`, no pyproject, no tests | That paragraph is stale. |
| `TOOLS.md` ATG row | “Still docs-only / Phase-1 skeleton not started.” Next trigger: runnable core. | The trigger named in that row has fired. Firing the trigger refreshes the card. It does not skip the gates. |
| `data/tool_integration_stages.json` | `Atomic Task Graph (ATG)` at I1, `intent: submodule_later`, issues 22 and 30 | Stage file is the structured pin. Update it in the same change as the prose. |
| `data/tools.json` | No ATG object found when this handoff was written (2026-10-05; catalog `last_updated` 2026-10-04) | Confirm with a search before editing. A TOOLS.md row without a `tools.json` object is a triple-write gap. |

atg-framework `main` as of the merge `3983e2e` (and this documentation commit on top of it) contains `src/atg/`, `pyproject.toml`, `examples/toy_parallel.py`, MIT `LICENSE`, Decisions 0001–0020, and a green unit suite. Live Ollama compile is still open. Detail: [`../USING.md`](../USING.md).

## Verify the library

In the atg-framework clone:

```bash
git fetch origin
git status -sb
uv sync --extra dev
uv run pytest -q -m "not integration"
uv run python examples/toy_parallel.py
```

Expect the example to print:

```text
mock total={'value': 25} waves=2 parallel=2
```

Expect pytest to pass the unit tests and deselect the integration test. On 2026-10-05 that was `35 passed, 1 deselected`. If the counts move, trust the command output and cite the new counts in the catalog note.

Live model check, only when `ollama ps` is empty, and only if the determination needs the live gate:

```bash
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
```

Do not load `qwen3.6:35b`, a coder-only tag, a cloud tag, or a 120B tag. If a runner is already loaded, score live evidence as “not re-measured” and point at Decision 0017. Absence of a new run is not a success.

## Score the gates

Use pfy `docs/ops/integration-stages.md`. I3 needs at least 3 of the 4 value gates, and every modularity gate. I4 needs I3 plus `SUBTREES.md`.

Pre-score from 2026-10-05. The pfy session replaces every row after it re-runs the checks. Do not paste this table into pfy as a finished decision.

| Gate | Reading at the time this handoff was written | Counts? |
|------|-----------------------------------------------|---------|
| Gap fill | Explicit compile, parallel tool waves, freeze, and localized repair. pfy’s primary loop does not ship this library. LangGraph overlaps the “run a DAG” part. The distinct piece is the ATG repair and freeze behavior aimed at a small local model. | Partial. Count it only if the session still finds no first-party skill that does this. |
| Operator leverage | Offline `run_task` is one import. No pfy pipeline gets shorter until a harness task exists. | No |
| Evidence | Offline quickstart exits 0. Live toy has not exited 0 (Decision 0017). | Offline yes. Live no. |
| Blast radius | MIT. No model weights. Safe only while it stays off primary orchestration and off the default cage and eval-harness. | Yes, with those constraints written into the coupling doc |

Modularity, if someone copies or imports the repo: one Python package, entry `run_task`, reversible by deleting the pin. The working tree is source and docs, well under the 50 MB I2 size note. That satisfies “small.” It does not satisfy I3.

**Working recommendation for the later session:** refresh I1. Optional I2 probe that only runs pytest and the offline toy in a throwaway directory or `tools/_probe/`. Do not open I3. Do not add a submodule.

Promote toward I3 only after both of these are true:

- Evidence includes either a live toy exit 0 on one 7B–14B tag, or a written pfy decision that the offline control loop alone is the smoke they want.
- A named harness task shows operator leverage, and an ADR keeps ATG off primary orchestration.

I4 (`submodule_later` in the stage file) waits behind that I3 pass and behind `SUBTREES.md`. “Intent: submodule later” is not an instruction to add the submodule in the next edit.

## Which stage to choose

| Choice | Choose it when | Edit |
|--------|----------------|------|
| I1 refresh | Offline library works, live path or pfy leverage is still open. This is the expected outcome. | Replace the docs-only sentences. Keep `integration_stage` at I1. Record the atg commit SHA and the pytest line. |
| I2 probe | Someone must execute the tree inside a pfy checkout to finish the score, and the copy stays under the size gate. | Probe path documented. Probe is not a product surface. Deleting it leaves the catalog pin. |
| I3 onboard | Value gate ≥ 3 of 4, all modularity gates, and a smoke that is not the default cage path. | Skill or smoke, env note, eval task. Still not the primary runtime. |
| I4 submodule | Already I3, and `SUBTREES.md` fits. | Submodule pointer. Rare. |
| Demote or watch | Offline toy stops passing, or the license changes in a way pfy cannot use. | Say so in the coupling doc. MIT is the current license (atg Decision 0019). |

Rejected for this determination, unless a new pfy ADR says otherwise:

- Calling ATG from eval-harness or the cage by default.
- Treating ATG as the orchestrator in place of Grok, OpenCode, and skills.
- Vendoring `src/atg` into pfy by copy.
- Claiming pfy reproduced the paper’s ALFWorld or WebShop numbers because it linked this repo.

## Catalog edits, when the operator asked you to edit pfy

Follow `/catalog-docs` in the pfy repo. In one change:

| File | Edit |
|------|------|
| `TOOLS.md` | ATG row. Remove “docs-only” and “Phase-1 skeleton not started.” Point at the atg commit, the offline command, and the live gap. |
| `data/tools.json` | Add the missing object if it is still missing, or update it. Required fields from that file’s `schema_notes`: `name`, `primary_category`, `github`, `scores`, `tier`. Set `integration_stage`. `json.load` must succeed. |
| `data/tool_integration_stages.json` | Same stage as the prose. Keep issues 22 and 30 as history. |
| `docs/ops/atg-coupling.md` | New dated snapshot: commit SHA, gate table, chosen stage, non-goals repeated. Leave the 2026-08-06 section in place and mark it superseded. |
| `sources/x-posts.md` | Touch only if this determination is also publishing a new post. Entry 001 is the paper post. Do not rewrite it as if atg-framework produced the GPT-4 comparison. A code post is a new entry, and only after the X handoff’s checks. |

Run pfy’s catalog check if the repo has one (`scripts/catalog_check.py` is named from `data/tools.json` schema notes). Do not invent scores. The existing TOOLS.md numbers can stay until a scoring session changes them; if you copy them into `tools.json`, copy them, and say they were copied from the TOOLS.md row on a dated line.

Coupling shape, if a later I3 session wires code:

| Shape | Fit |
|-------|-----|
| `pip` or `uv` dependency on a pinned atg commit, imported by one harness module | Fits Decision 0002 in atg (this repo stays framework-agnostic) and fits a reversible pfy pin. |
| One-way `as_langgraph_node` / `as_dspy_forward` | Already in atg `atg.integrations`. They do not import those frameworks. |
| Git submodule | I4 only. |
| In-process call from the default cage | Out of scope for the current non-goals. |

## Agent

### Definition of done

- Both repos fetched. atg SHA written into the pfy coupling snapshot.
- Offline command output pasted into that snapshot, or an explicit “not run” reason.
- Stage chosen from the table above and recorded in `atg-coupling.md`, `TOOLS.md`, `data/tool_integration_stages.json`, and `data/tools.json` together.
- No import of `atg` added on a default eval or cage path.
- No commit in atg-framework unless the operator asked for an atg change in that session.

### Do not

- Do not treat `docs/ops/atg-coupling.md` from 2026-08-06 as the current maturity statement.
- Do not implement the integration inside an atg-framework session. This handoff is the input to a pfy session.
- Do not re-propose atg decisions 0002 and 0016 (custom core, one-way adapters) from the pfy side.
- Do not start a live Ollama run while `ollama ps` shows a model.
