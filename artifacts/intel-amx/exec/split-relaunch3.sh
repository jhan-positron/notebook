#!/usr/bin/env bash
# Launch the PR 3879 split build chain on delphi-3bda (run from any host with
# ssh access) under the half-split sharing scheme of 2026-09-06
# (~/workspace/notebook/handoffs/delphi-3bda-guard.md): Bill has the first
# four cards and socket 0; we build and test on socket 1 only
# (exec/split-verify3.sh) and ignore Bill's activity in the guard
# (GUARD_EXCLUDE_USERS, the guard doc's fix 2). The two cost-data
# measurements (exec/split-bench3.sh) come last and wait until Bill is idle,
# because `bin/slice bench` uses the whole machine.
# The whole backgrounded group is redirected to /dev/null so the ssh returns
# at once (a redirection on setsid alone left the ssh pipes open in the
# forked subshell until the chain ended).
# Tips as of 2026-09-06 20:20 UTC: PR0 4f4c4d4f4c, PR0b e2f22c7a09, PR1 a92245304d,
# PR2 cca2960f5f, R e449b11452. Edit here if the branches move.
set -u
ssh -o ConnectTimeout=20 delphi-3bda '{ cd ~/workspace/intel-AMX && export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill" && setsid nohup bash -c "
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR0-on 4f4c4d4f4c OFF OFF ON t_page_share_counters t_llama_unit;
exec/split-verify3.sh PR0-off 4f4c4d4f4c OFF OFF OFF t_page_share_counters t_llama_unit;
exec/split-verify3.sh PR0b e2f22c7a09 OFF OFF OFF t_llama_unit;
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR1-on a92245304d ON OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-verify3.sh PR1-off a92245304d OFF OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
FORMAT=1 exec/split-verify3.sh PR2-on cca2960f5f ON ON OFF t_amx_mirror t_amx_arena_leak t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-verify3.sh R-mirror e449b11452 ON ON OFF t_amx_mirror t_amx_numerics t_amx_arena_leak t_amx_dispatch_dtype t_llama_unit;
exec/split-verify3.sh R-canon e449b11452 ON OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-bench3.sh PR0-on t_page_share_counters;
exec/split-bench3.sh PR1-on t_amx_numerics t_amx_dispatch_dtype
"; } >/dev/null 2>&1 </dev/null & disown; sleep 3; pgrep -af "split-verif[y]3|split-benc[h]3" | grep -c bash'
