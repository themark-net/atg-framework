---
name: attribution
description: >
  Enforce correct academic and third-party attribution for atg-framework:
  paper cites, CITATION.cff, BibTeX, code docstrings, and no false originality
  claims for ATG ideas. Use when the user runs /attribution, asks to credit a
  paper or source, implements planner/executor/repair/graph-history features,
  ports benchmarks from papers, adds external algorithms, writes README or
  design docs that describe ATG methods, or before releasing/publishing work
  that reuses research ideas.
argument-hint: "[audit|add-source|sync|module] [path or bib key]"
---

# Attribution — Credit Sources During Development

You keep **ideas, algorithms, and external designs** correctly attributed in this repo. Source of truth for policy: `docs/ATTRIBUTION.md`. Do not invent a parallel credit system.

## When to run

- User invokes `/attribution` or asks about citation / credit / paper attribution.
- Implementing or refactoring **core ATG** mechanisms (graph compilation, dependency execution, thought experiment, subgraph repair, refinement history).
- Adding a **new paper, algorithm, or substantial third-party design**.
- Writing or editing **README**, design docs, ADRs, module docs, or public-facing claims about originality.
- Pre-release / publish checklist: “are we citing correctly?”
- Audit mode: user asks whether credit is complete or drifted.

## Step 0 — Load policy and canonical cites

1. Git root: `git rev-parse --show-toplevel`.
2. Read (in order):
   - `docs/ATTRIBUTION.md` — rules and idea inventory
   - `CITATION.cff` — machine-readable preferred citation
   - `docs/citations.bib` — BibTeX keys
3. Foundational paper key: **`zhang2026atg`** (Zhang et al., 2026, arXiv:2607.01942).  
   Never credit only institutions; always **named authors** when citing the paper.

## Step 1 — Modes

| Mode | Behavior |
|------|----------|
| `audit` (default if no args) | Check surfaces in Step 2; report gaps; fix safe missing links/comments when in write mode |
| `add-source` | Register a new paper/algorithm: BibTeX + ATTRIBUTION row + local credit at use site |
| `sync` | Align README citation block, CITATION.cff, citations.bib, ATTRIBUTION metadata (authors, DOI, year, title) |
| `module <path>` | Ensure a source file/module has correct docstring attribution for paper-derived logic |

## Step 2 — Required surfaces (audit checklist)

Verify each exists and is consistent:

| Surface | Must have |
|---------|-----------|
| `README.md` | Named authors, year, title, arXiv, DOI; link to `docs/ATTRIBUTION.md` |
| `CITATION.cff` | `preferred-citation` = ATG paper; software type for this repo |
| `docs/citations.bib` | `zhang2026atg` (+ software entry if present) |
| `docs/ATTRIBUTION.md` | Idea inventory + “what this repo may claim” |
| Package root / core modules | Short credit when code exists (`atg/__init__.py`, planner, executor, repair) |

**Fail** an audit if README cites only affiliations without author names, or if user-facing text says “we propose ATG” for this repo’s authors.

## Step 3 — When writing code from paper ideas

1. Map the feature to a paper concept name (from ATTRIBUTION idea list or paper §).
2. Add module docstring (or file header) using the pattern in `docs/ATTRIBUTION.md`:
   - Paper: Zhang et al. (2026)
   - Idea / section if known
   - Bib key `zhang2026atg`
   - “Independent reimplementation, not official”
3. Prefer **idea-level** reimplementation over copying paper prose.
4. Do **not** strip attribution during refactors; move comments with the logic.
5. If you invent an extension, label it explicitly as an extension of Zhang et al., not as the original ATG definition.

## Step 4 — Adding a new external source

1. Add BibTeX to `docs/citations.bib` (`lastnameYEARkeyword`).
2. Append a row to **Additional sources** in `docs/ATTRIBUTION.md`.
3. If project-wide influence: mention in README “Related work / additional sources” only if material.
4. Credit at the narrowest correct scope (file > module > README).
5. For **code** sources: check license before copy; record license notes in ATTRIBUTION if non-trivial.

## Step 5 — Sync metadata

If paper details change (new arXiv version, journal version, author list):

1. Update `CITATION.cff` `preferred-citation` and `references`.
2. Update `docs/citations.bib`.
3. Update README citation block and `docs/ATTRIBUTION.md` “Foundational paper”.
4. Keep arXiv ID stable; add venue citation when version of record exists.

## Step 6 — Report

Always report:

- Mode run
- Files checked / written
- Gaps found (and fixed vs still open)
- Any new BibTeX keys added

## Anti-patterns

- Institution-only credit (“researchers from Tsinghua…”) without names
- Claiming originality for recursive compilation, dependency-aware execution, thought experiment, or minimal subgraph repair
- Duplicate citation systems (random NOTICE files that contradict CITATION.cff)
- Copying figures/tables from the PDF without license/fair-use care
- “Official implementation” language without author confirmation
- Deleting credit comments as noise

## Related skills

- `/docs` — module docs should include attribution links for paper-derived modules
- `/adr` — design decisions that adopt paper mechanisms should cite `zhang2026atg`
- `/open-questions` — park unresolved credit questions (e.g. dual license, journal version)
