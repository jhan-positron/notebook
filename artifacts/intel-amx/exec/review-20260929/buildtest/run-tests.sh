#!/usr/bin/env bash
# Runs each built test binary three ways (TRON_ATTN_STATS unset / =1 / =yes) from the worktree root.
# Output per run: $S/<binary>.<env>.out (full output), $S/summary.tsv (one line per run).
set -u
S=/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/c1e2475d-c671-4e92-9fc3-579c9ced20ea/scratchpad/buildtest
WT=/home/jhan/workspace/ai-runs/tron-attn-stats
cd "$WT" || exit 1
echo -e "binary\tenv\texit\tcases_listed\tresult_line\twall_s\tattn_stats_lines\tignored_warn_lines" > "$S/summary.tsv"
for b in t_page_share_counters t_amx_dispatch_dtype t_heterogeneous_scheduler t_llama_unit; do
  n=$(env -u SYSTEM_CONFIG ./gen/$b --list-tests 2>/dev/null | grep -c '^  [^ ]')
  env -u SYSTEM_CONFIG ./gen/$b --list-tests > "$S/$b.list-tests.out" 2>&1
  for e in unset one yes; do
    case $e in
      unset) envargs=(-u SYSTEM_CONFIG -u TRON_ATTN_STATS);;
      one)   envargs=(-u SYSTEM_CONFIG TRON_ATTN_STATS=1);;
      yes)   envargs=(-u SYSTEM_CONFIG TRON_ATTN_STATS=yes);;
    esac
    out="$S/$b.$e.out"
    t0=$(date +%s.%N)
    env "${envargs[@]}" ./gen/$b --skip-benchmarks > "$out" 2>&1
    rc=$?
    t1=$(date +%s.%N)
    wall=$(awk -v a=$t0 -v b=$t1 'BEGIN{printf "%.1f", b-a}')
    res=$(grep -E 'All tests passed|^test cases:|^assertions:' "$out" | tr '\n' ' ' | sed 's/  */ /g')
    as=$(grep -c '^\[attn-stats\]' "$out")
    ig=$(grep -c "TRON_ATTN_STATS='yes' ignored" "$out")
    echo -e "$b\t$e\t$rc\t$n\t$res\t$wall\t$as\t$ig" >> "$S/summary.tsv"
  done
done
cat "$S/summary.tsv"
