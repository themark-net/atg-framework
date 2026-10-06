# Toy PoC offline report

Toy-scale synthetic metrics for localized repair (Zhang et al. 2026, arXiv:2607.01942, §4.3). Not ALFWorld, WebShop, or ScienceWorld scores.

Localized repair is the product path (Decision 0014). Global replan and sequential replay are measurement arms only.

`repairs` on localized counts `repair_graph` calls. On global replan it counts one whole-graph recompile after a tool failure. Sequential replay discards outputs and runs the chain again, so its `repairs` stays 0.

`max_parallel` is the widest wave in that arm, not a sum across tasks.

| arm | success | llm_calls | tool_calls | nodes_frozen_reused | repairs | wall_time_s | max_parallel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| localized | 12 | 16 | 37 | 6 | 4 | 0.008400 | 3 |
| global_replan | 12 | 20 | 43 | 0 | 4 | 0.007615 | 3 |
| sequential | 12 | 12 | 43 | 0 | 0 | 0.002686 | 1 |

Check: localized llm_calls (16) < global_replan llm_calls (20) is true.
Check: sequential max_parallel is 1.

## Tasks

| task | failed_once | expected | loc_llm | glob_llm | seq_llm | loc_tools | seq_tools | loc_frozen | loc_ok | glob_ok | seq_ok |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| add_pair | no | 5 | 1 | 1 | 1 | 1 | 1 | 0 | yes | yes | yes |
| mul_pair | no | 42 | 1 | 1 | 1 | 1 | 1 | 0 | yes | yes | yes |
| scale_sum | no | 20 | 1 | 1 | 1 | 2 | 2 | 0 | yes | yes | yes |
| parallel_sums | no | 10 | 1 | 1 | 1 | 3 | 3 | 0 | yes | yes | yes |
| parallel_prod | no | 29 | 1 | 1 | 1 | 3 | 3 | 0 | yes | yes | yes |
| diamond | no | 18 | 1 | 1 | 1 | 4 | 4 | 0 | yes | yes | yes |
| three_wide | no | 12 | 1 | 1 | 1 | 5 | 5 | 0 | yes | yes | yes |
| nested_chain | no | 36 | 1 | 1 | 1 | 3 | 3 | 0 | yes | yes | yes |
| fail_parallel | yes | 25 | 2 | 3 | 1 | 3 | 4 | 1 | yes | yes | yes |
| fail_chain | yes | 21 | 2 | 3 | 1 | 3 | 4 | 1 | yes | yes | yes |
| fail_diamond | yes | 14 | 2 | 3 | 1 | 4 | 6 | 2 | yes | yes | yes |
| fail_wide | yes | 12 | 2 | 3 | 1 | 5 | 7 | 2 | yes | yes | yes |
