#!/usr/bin/env bash
# Second pass of the PR 3879 split chain on delphi-3bda (2026-09-06 23:4x UTC):
# rebuild and retest the tips that changed after the first pass (clang-format
# reflows folded in; PR 2's two mirror-only test descriptors given an explicit
# attention_operation_config), so the tested SHA is the pushed SHA, then the
# cost-data measurements (split-bench3.sh) for PR 0, PR 1 and PR 2 in the kept
# worktrees. Same rules as split-relaunch3.sh (half split with Bill: socket 1
# only; guard ignores Bill for builds; the bench waits until Bill is idle).
# PR 0b (e2f22c7a09) and the reference R (e449b11452) are unchanged and not repeated.
# Tips: PR0 f6794a7c15, PR1 32a4d1664f, PR2 8a878984e7.
set -u
ssh -o ConnectTimeout=20 delphi-3bda '{ cd ~/workspace/intel-AMX && export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill" && setsid nohup bash -c "
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR0-on f6794a7c15 OFF OFF ON t_page_share_counters t_llama_unit;
exec/split-verify3.sh PR0-off f6794a7c15 OFF OFF OFF t_page_share_counters t_llama_unit;
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR1-on 32a4d1664f ON OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-verify3.sh PR1-off 32a4d1664f OFF OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR2-on 8a878984e7 ON ON OFF t_amx_mirror t_amx_arena_leak t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-bench3.sh PR0-on t_page_share_counters;
exec/split-bench3.sh PR1-on t_amx_numerics t_amx_dispatch_dtype;
exec/split-bench3.sh PR2-on t_amx_mirror t_amx_arena_leak
"; } >/dev/null 2>&1 </dev/null & disown; sleep 3; pgrep -af "split-verif[y]3|split-benc[h]3" | grep -c bash'
