# Attribution Policy — atg-framework

How this repository credits **ideas**, **algorithms**, and **code** that come from research or third parties. Binding for human contributors and coding agents.

## Why this exists

This project is an **independent prototype** inspired by academic research. Correct attribution:

1. Respects the original authors’ intellectual contribution.
2. Avoids implying endorsement or “official” status when none exists.
3. Keeps academic and open-source norms (cite what you use; don’t claim originality for borrowed design).
4. Survives agent-driven development, where code can grow faster than memory of sources.

## Canonical sources

| Artifact | Path | Role |
|----------|------|------|
| Machine-readable software + preferred paper cite | [`CITATION.cff`](../CITATION.cff) | GitHub “Cite this repository”; Zotero/Citation File Format |
| BibTeX | [`docs/citations.bib`](citations.bib) | Papers, reports, READMEs, design docs |
| Human + agent policy (this file) | `docs/ATTRIBUTION.md` | Rules for what to attribute and where |
| Agent skill | [`.grok/skills/attribution/SKILL.md`](../.grok/skills/attribution/SKILL.md) | Operational checklist for Grok/agents |

When any of these drift, **fix this file and `CITATION.cff` first**, then sync the rest.

## Foundational paper (must cite)

**Title:** Atomic Task Graph: A Unified Framework for Agentic Planning and Execution  
**Authors:** Yue Zhang, Sihan Chen\*, Ziwen Huang\*, Hanyun Cui, Kangye Ji, Zhi Wang  
\* Equal contribution.  
**Affiliations:** South China University of Technology; Tsinghua Shenzhen International Graduate School, Tsinghua University  
**Year:** 2026  
**arXiv:** [2607.01942](https://arxiv.org/abs/2607.01942)  
**DOI:** [10.48550/arXiv.2607.01942](https://doi.org/10.48550/arXiv.2607.01942)  
**HTML:** https://arxiv.org/html/2607.01942  
**BibTeX key:** `zhang2026atg` (see `docs/citations.bib`)  
**Paper license (text):** arXiv.org perpetual non-exclusive license — covers the paper, **not** this software.

### Ideas that originate in the paper (attribute as ATG / Zhang et al. 2026)

Do **not** present these as original inventions of this repo:

- Explicit **Atomic Task Graph** as a unified planning + execution substrate
- **Interface-preserving recursive graph compilation** (coarse → atomic DAG, interface stability)
- **Graph evolution / refinement history** for later localization
- **Dependency-aware (parallel) execution** over explicit I/O edges
- **Pre-execution thought experiment** (lightweight plan validation before environment cost)
- **Minimal necessary subgraph repair** (freeze validated regions; repair smallest affected subgraph)
- Empirical framing around long-horizon agents, intermediate-result reuse, and localized failure recovery

### What *this* repo may claim

- Engineering choices, APIs, tests, integrations (DSPy, LangGraph, Ollama, …)
- Local LLM adaptations, packaging, benchmarks re-implemented *for this stack*
- Novel extensions **only if** clearly labeled as extensions and distinguished from the paper

**Default phrasing:** “inspired by / based on / implementing concepts from Zhang et al. (2026)” — never “we propose ATG” unless quoting the paper authors.

## Where attribution must appear

| Surface | Requirement |
|---------|-------------|
| `README.md` | Full paper citation (authors, year, title, arXiv, DOI); link to this policy |
| `CITATION.cff` | Up to date; `preferred-citation` = paper |
| `docs/citations.bib` | Paper + software entries |
| Package / library root (`atg/__init__.py` when present) | Short credit + link to paper and this policy |
| Module docs for core algorithms (`planner`, `executor`, `repair`, graph history) | Explicit “Paper: Zhang et al. 2026, §X” or idea name |
| Non-trivial algorithm source files | Module docstring or top comment with paper cite + section if known |
| Design docs / ADRs that adopt paper mechanisms | Reference `zhang2026atg` and idea name |
| Public demos, papers, blog posts about this code | Cite the paper; optionally cite the software |
| Benchmarks ported from or aligned with paper evals | Credit paper + original benchmark papers (ALFWorld, WebShop, ScienceWorld, etc.) |

### Code comment pattern (when implementing paper algorithms)

```python
"""Dependency-aware ready-queue execution.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4.2
(Dependency-Aware Execution). See docs/ATTRIBUTION.md and docs/citations.bib
(zhang2026atg). This is an independent reimplementation, not official code.
"""
```

### What *not* to do

- Drop author names and cite only “Tsinghua / SCUT researchers”
- Paste paper text, figures, or tables without checking paper license and fair use
- Claim this repo is the authors’ official implementation unless they say so
- Attribute unrelated third-party code only to the ATG paper
- Strip attribution when refactoring (“cleanup” must preserve credit)

## Adding a new source

When adopting a **new** paper, library algorithm, or substantial external design:

1. Add a BibTeX entry to `docs/citations.bib` (stable key: `lastnameYEARkeyword`).
2. If it is a primary influence on the project, add a row under **Additional sources** below and, if citable as preferred, update `CITATION.cff` `references` / notes.
3. Attribute at the **narrowest correct scope** (module/file for a local algorithm; README for project-wide foundations).
4. If the source is code (not just a paper), record license compatibility before copy or heavy paraphrase.

### Additional sources

| Key / ID | Work | Used for | Status |
|----------|------|----------|--------|
| `zhang2026atg` | Zhang et al., ATG, arXiv:2607.01942 | Core architecture | **Primary** |

*(Add rows as dependencies accumulate.)*

## Relationship to third-party software licenses

- **Paper attribution ≠ code license.** Citing Zhang et al. does not grant rights to copy proprietary or non-open code.
- This repository’s software license is declared in `LICENSE` / README (TBD as of policy creation).
- Dependencies keep their own licenses; list them via normal packaging (`pyproject.toml`, NOTICE if needed).
- Prefer clean-room reimplementation of *ideas* over translating paper pseudocode line-for-line when ambiguity exists; still cite the idea source.

## Agent / automation checklist

Before merging non-trivial work, agents must verify:

- [ ] New core ATG mechanism still maps to paper idea names and is not rebranded as original without note
- [ ] New modules implementing paper §§ have docstring attribution
- [ ] README / CITATION.cff / citations.bib still accurate if metadata changed
- [ ] No false “we introduce ATG” marketing copy in user-facing text
- [ ] New external algorithms got a citations.bib entry + local credit

Full operational skill: `.grok/skills/attribution/SKILL.md` (`/attribution`).

## Standard citation forms

### Inline (prose)

> …using interface-preserving recursive compilation as described by Zhang et al. (2026) [arXiv:2607.01942].

### Full reference

Zhang, Y., Chen, S., Huang, Z., Cui, H., Ji, K., & Wang, Z. (2026). *Atomic Task Graph: A Unified Framework for Agentic Planning and Execution*. arXiv:2607.01942. https://doi.org/10.48550/arXiv.2607.01942

### BibTeX

See `docs/citations.bib` entry `zhang2026atg`.

### APA-ish software cite (this repo)

atg-framework contributors. (2026). *atg-framework* [Computer software]. https://github.com/themark-net/atg-framework  
(Also cite Zhang et al., 2026, for the method.)

## Maintenance

- Update this file when the foundational paper version, DOI, or author list changes.
- After a journal/conference version appears, keep arXiv cite and add the archival venue entry; prefer the version of record when available.
- Policy changes that affect default credit language should be noted in `docs/TODO.md` or an ADR if architectural marketing claims change.
