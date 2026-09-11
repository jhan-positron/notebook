#!/usr/bin/env bash
# Relaunch the PR 3879 split build chain on delphi-3bda (run from any host with
# ssh access). Usage: split-relaunch.sh   (after jhan lifts the hold: also
# delete or shorten /var/tmp/jhan/3bda-blackout on 3bda, or the guard waits).
# Tips as of 2026-09-06 20:20 UTC: PR0 4f4c4d4f4c, PR0b e2f22c7a09, PR1 a92245304d,
# PR2 cca2960f5f, R e449b11452. Edit here if the branches move.
set -u
ssh -o ConnectTimeout=20 delphi-3bda 'cd ~/workspace/intel-AMX && setsid nohup bash -c "
FORMAT=1 BENCH=t_page_share_counters exec/split-verify2.sh PR0-on 4f4c4d4f4c OFF OFF ON t_page_share_counters t_llama_unit;
exec/split-verify2.sh PR0-off 4f4c4d4f4c OFF OFF OFF t_page_share_counters t_llama_unit;
exec/split-verify2.sh PR0b e2f22c7a09 OFF OFF OFF t_llama_unit;
FORMAT=1 BENCH=\"t_amx_numerics t_amx_dispatch_dtype\" exec/split-verify2.sh PR1-on a92245304d ON OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-verify2.sh PR1-off a92245304d OFF OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
FORMAT=1 exec/split-verify2.sh PR2-on cca2960f5f ON ON OFF t_amx_mirror t_amx_arena_leak t_amx_numerics t_amx_dispatch_dtype t_llama_unit;
exec/split-verify2.sh R-mirror e449b11452 ON ON OFF t_amx_mirror t_amx_numerics t_amx_arena_leak t_amx_dispatch_dtype t_llama_unit;
exec/split-verify2.sh R-canon e449b11452 ON OFF OFF t_amx_numerics t_amx_dispatch_dtype t_llama_unit
" >/dev/null 2>&1 < /dev/null & disown; sleep 3; pgrep -af "split-verif[y]2" | grep -c bash'
