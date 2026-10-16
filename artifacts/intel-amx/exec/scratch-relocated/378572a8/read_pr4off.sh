#!/usr/bin/env bash
# Print the pr4off-E-cpu results: per-arm rows and the comparison rows, with the band per cell (2 x max sd, floors 0.40 TPS / 0.15 s).
R=/home/jhan/workspace/intel-AMX/exec/results/pr4off-E-cpu
echo "== $(date -u +%FT%TZ) done marker: $(cat /home/jhan/workspace/intel-AMX/exec/logs/pr4off-E-cpu.done 2>/dev/null)"
echo "== per-arm rows (cell | arm | n | TPS | sd | TTFT s | sd | early-stop):"
grep '^| q3-4b' "$R/summary.md" | awk -F'|' 'NF>=14 {printf "%s |%s |%s |%s |%s |%s |%s |%s\n",$2,$7,$8,$9,$10,$11,$12,$13}'
echo "== comparisons (cell | pair | TPS % | TTFT % | TTFT ms | paired TPS (sd,n,t) | paired TTFT ms (sd,n,t)):"
grep '^| q3-4b' "$R/summary.md" | awk -F'|' 'NF<14 && NF>=9 {printf "%s |%s |%s |%s |%s |%s |%s\n",$2,$4,$5,$6,$7,$8,$9}'
echo "== runs recorded: $(grep -c '^### runtron' "$R/rt-results.txt" 2>/dev/null); failed: $(grep -c 'RUN-FAILED\|RUN-STOPPED' "$R/rt-results.txt" 2>/dev/null)"
