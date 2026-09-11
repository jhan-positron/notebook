#!/usr/bin/env bash
# Bench-only chain (2026-09-07 19:xx UTC): the two cost-data measurements with a
# 24-hour wait each (the pass-3 chain's bench step had a 12-hour deadline from
# 11:57 UTC and would have given up at 23:57 UTC while Bill's engines run). Uses the
# reviewed split-bench3.sh (monitor-gated start, retry after a stop, worktree kept).
# Kept worktrees: /var/tmp/jhan/tron-split-PR0-on (f6794a7c15), tron-split-PR1-on (9723d56f62).
set -u
ssh -o ConnectTimeout=20 delphi-3bda '{ cd ~/workspace/intel-AMX && export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill" && setsid nohup bash -c "
BENCH_WAIT_SEC=86400 exec/split-bench3.sh PR0-on t_page_share_counters;
BENCH_WAIT_SEC=86400 exec/split-bench3.sh PR1-on t_amx_numerics t_amx_dispatch_dtype
"; } >/dev/null 2>&1 </dev/null & disown; sleep 3; pgrep -af "split-benc[h]3" | grep -c bash'
