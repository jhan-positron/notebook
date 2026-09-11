#!/usr/bin/env bash
# Third pass of the PR 3879 split chain on delphi-3bda (2026-09-07): rebuild and
# retest the tips changed by jhan's decision 3 (the t_llama_unit AMX eligibility
# case dropped from PR 1; PR 2 re-stacked with its own mirror-only case), then the
# three cost-data measurements in the kept worktrees. PR 0's built code is still
# f6794a7c15 (its third commit changes only the CI workflow and README.ci.md), so
# the PR 0 worktree from pass 2 serves its bench unchanged. Same rules as
# split-relaunch3.sh (half split with Bill; the bench waits until Bill is idle;
# the pre-CI hold and the CI lease are honoured by the scripts).
# Tips: PR1 9723d56f62, PR2 dfa6a5f71b.
set -u
ssh -o ConnectTimeout=20 delphi-3bda '{ cd ~/workspace/intel-AMX && export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill" && setsid nohup bash -c "
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR1-on 9723d56f62 ON OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-verify3.sh PR1-off 9723d56f62 OFF OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
FORMAT=1 KEEP_WT=1 exec/split-verify3.sh PR2-on dfa6a5f71b ON ON OFF t_amx_mirror t_amx_arena_leak t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-bench3.sh PR0-on t_page_share_counters;
exec/split-bench3.sh PR1-on t_amx_numerics t_amx_dispatch_dtype;
exec/split-bench3.sh PR2-on t_amx_mirror t_amx_arena_leak
"; } >/dev/null 2>&1 </dev/null & disown; sleep 3; pgrep -af "split-verif[y]3|split-benc[h]3" | grep -c bash'
