# Toy PoC offline report

Toy-scale synthetic metrics for localized repair (Zhang et al. 2026, arXiv:2607.01942, §4.3). Not ALFWorld, WebShop, or ScienceWorld scores.

Localized repair is the product path (Decision 0014). Global replan and sequential replay are measurement arms only.

`repairs` on localized counts `repair_graph` calls. On global replan it counts one whole-graph recompile after a tool failure. Sequential replay discards outputs and runs the chain again, so its `repairs` stays 0.

`max_parallel` is the widest wave in that arm, not a sum across tasks.

| arm | success | llm_calls | tool_calls | nodes_frozen_reused | repairs | wall_time_s | max_parallel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| localized | 1 | 12 | 5 | 0 | 0 | 855.987579 | 3 |
| global_replan | 1 | 12 | 5 | 0 | 0 | 850.577303 | 3 |
| sequential | 1 | 12 | 5 | 0 | 0 | 851.272995 | 1 |

Check: localized llm_calls (12) < global_replan llm_calls (12) is false.
Check: sequential max_parallel is 1.

## Tasks

| task | failed_once | expected | loc_llm | glob_llm | seq_llm | loc_tools | seq_tools | loc_frozen | loc_ok | glob_ok | seq_ok |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| add_pair | no | 5 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| mul_pair | no | 42 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| scale_sum | no | 20 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| parallel_sums | no | 10 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| parallel_prod | no | 29 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| diamond | no | 18 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| three_wide | no | 12 | 1 | 1 | 1 | 5 | 5 | 0 | yes | yes | yes |
| nested_chain | no | 36 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| fail_parallel | yes | 25 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| fail_chain | yes | 21 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| fail_diamond | yes | 14 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
| fail_wide | yes | 12 | 1 | 1 | 1 | 0 | 0 | 0 | no | no | no |
