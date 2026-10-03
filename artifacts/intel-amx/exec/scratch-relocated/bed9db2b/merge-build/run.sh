#!/usr/bin/env bash
# Merge-of-main check for PR 4596 on claude-box: ninja inside the nix shell (cmake re-runs itself: t/CMakeLists.txt changed on main),
# then each of the PR's five test binaries three ways (TRON_ATTN_STATS unset / =1 / =yes). Same recipe as exec/counter-20260922/r5/buildtest-run1/run.sh.
set -u
S=/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/bed9db2b-cd22-4507-966d-cc12da65429f/scratchpad/merge-build
WT=/home/jhan/workspace/ai-runs/tron-attn-stats
cd "$WT" || exit 1
T="t_page_share_counters t_amx_dispatch_dtype t_heterogeneous_scheduler t_compute_attention_unit t_llama_unit"
date -u +%FT%TZ > "$S/build.start"
~/.nix-profile/bin/nix develop --accept-flake-config --command bash -c "ninja -C gen -j 20 $T" > "$S/build.log" 2>&1
rc=$?; echo "BUILD_EXIT $rc" | tee "$S/build.exit"; date -u +%FT%TZ > "$S/build.end"
if [ $rc -ne 0 ]; then echo DONE > "$S/.done"; exit 1; fi
echo -e "binary\tenv\texit\tcases_listed\tresult_line\twall_s\tattn_stats_lines\tignored_warn_lines" > "$S/summary.tsv"
for b in $T; do
  n=$(env -u SYSTEM_CONFIG ./gen/$b --list-tests 2>/dev/null | grep -c '^  [^ ]')
  for e in unset one yes; do
    case $e in
      unset) envargs=(-u SYSTEM_CONFIG -u TRON_ATTN_STATS);;
      one)   envargs=(-u SYSTEM_CONFIG TRON_ATTN_STATS=1);;
      yes)   envargs=(-u SYSTEM_CONFIG TRON_ATTN_STATS=yes);;
    esac
    out="$S/$b.$e.out"; t0=$(date +%s.%N)
    env "${envargs[@]}" ./gen/$b --skip-benchmarks > "$out" 2>&1; rc=$?
    t1=$(date +%s.%N); wall=$(awk -v a=$t0 -v b=$t1 'BEGIN{printf "%.1f", b-a}')
    res=$(grep -E 'All tests passed|^test cases:|^assertions:' "$out" | tr '\n' ' ' | sed 's/  */ /g')
    as=$(grep -c '^\[attn-stats\]' "$out"); ig=$(grep -c "TRON_ATTN_STATS='yes' ignored" "$out")
    echo -e "$b\t$e\t$rc\t$n\t$res\t$wall\t$as\t$ig" >> "$S/summary.tsv"
  done
done
cat "$S/summary.tsv"; echo DONE > "$S/.done"
