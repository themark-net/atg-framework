# Autonomous decisions — 2026-10-06

1. Finish work lives on `build/atg-finish` in `/tmp/atg-finish`, branched from `origin/main` `29bca8a`. The main checkout keeps its uncommitted founder edits. Alternative was committing those edits first. Why: the resume contract forbids touching that checkout.
2. Phase A is Decision 0021 and phase B is Decision 0022, written in separate worktrees and merged here. Alternative was one shared decision number. Why: the two edits run at the same time.
3. Lemonade and vLLM are not installed and are not loaded in phase D. LOCAL-BENCH-5 already records Lemonade as skipped and vLLM as an import failure. Alternative was installing a backend. Why: the contract forbids system packages, and the bench says those runtimes are not working here.
