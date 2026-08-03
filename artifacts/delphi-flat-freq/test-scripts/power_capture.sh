#!/bin/bash
# power_capture.sh start <outdir> | stop <outdir> — standard power capture
# for ALL tests (user directive 2026-07-16). Writes power.tsv + a summary
# line to power_summary.txt on stop.
# 2026-07-30 A0 fix (runbook 04): turbostat REWRITES its argv (commas ->
# spaces), so the old stop pkill pattern only matched the sudo wrapper and
# leaked the turbostat child (12 pairs ran Jul 23->30). start now setsids
# the capture into its own process group; stop kills the WHOLE GROUP.
set -u
CMD="${1:?start|stop}"; OUT="${2:?outdir}"
case "$CMD" in
  start)
    mkdir -p "$OUT"
    setsid nohup sudo -n turbostat --quiet \
      --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,PkgWatt,RAMWatt \
      -i 30 > "$OUT/power.tsv" 2> "$OUT/power.err" < /dev/null &
    echo $! > "$OUT/.power_pid"
    echo "power capture started (pgid $(cat "$OUT/.power_pid"))"
    ;;
  stop)
    if [ -f "$OUT/.power_pid" ]; then
      PGID="$(cat "$OUT/.power_pid")"
      sudo -n kill -- "-$PGID" 2>/dev/null        # whole group: sudo + child
      sleep 1
      sudo -n kill -9 -- "-$PGID" 2>/dev/null     # belt-and-braces if alive
    fi
    # fallback: match BOTH argv forms (sudo wrapper commas; child spaces)
    sudo -n pkill -f "turbostat --quiet --show Package,Core,CPU,Avg_MHz" 2>/dev/null
    sudo -n pkill -f "turbostat --quiet --show Package Core CPU Avg_MHz" 2>/dev/null
    sleep 1
    awk "\$1==\"-\" && \$5>20 {n++; pw+=\$7; rw+=\$8; bz+=\$6} END {if(n>0) printf \"loaded_samples=%d mean_PkgWatt=%.0f mean_RAMWatt=%.0f mean_Bzy_MHz=%.0f\n\", n, pw/n, rw/n, bz/n; else print \"no loaded samples\"}" "$OUT/power.tsv" | tee "$OUT/power_summary.txt"
    ;;
esac
