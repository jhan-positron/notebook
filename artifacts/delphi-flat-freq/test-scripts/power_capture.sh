#!/bin/bash
# power_capture.sh start <outdir> | stop <outdir> — standard power capture
# for ALL tests (user directive 2026-07-16). Writes power.tsv + a summary
# line to power_summary.txt on stop.
set -u
CMD="${1:?start|stop}"; OUT="${2:?outdir}"
case "$CMD" in
  start)
    mkdir -p "$OUT"
    nohup sudo -n turbostat --quiet \
      --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,PkgWatt,RAMWatt \
      -i 30 > "$OUT/power.tsv" 2> "$OUT/power.err" < /dev/null &
    echo $! > "$OUT/.power_pid"
    echo "power capture started (pid $(cat "$OUT/.power_pid"))"
    ;;
  stop)
    [ -f "$OUT/.power_pid" ] && sudo -n kill "$(cat "$OUT/.power_pid")" 2>/dev/null
    sudo -n pkill -f "turbostat --quiet --show Package,Core,CPU,Avg_MHz" 2>/dev/null
    sleep 1
    awk "\$1==\"-\" && \$5>20 {n++; pw+=\$7; rw+=\$8; bz+=\$6} END {if(n>0) printf \"loaded_samples=%d mean_PkgWatt=%.0f mean_RAMWatt=%.0f mean_Bzy_MHz=%.0f\n\", n, pw/n, rw/n, bz/n; else print \"no loaded samples\"}" "$OUT/power.tsv" | tee "$OUT/power_summary.txt"
    ;;
esac
