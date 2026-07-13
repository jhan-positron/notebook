#!/bin/bash
# p43_worker_toggle.sh clamp|fast|status — toggle the tron112 WORKER set
# (7-14,24-71,79-86,96-143 + HT siblings) between CLOS3 (<=2700) and
# CLOS0 (~4000-4100) while serving runs. Rinzler/dev/platform cores are
# NOT touched (must stay clos:3). The Q1 decisive experiment.
set -u
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
W="7-14,24-71,79-86,96-143,151-158,168-215,223-230,240-287"
case "${1:-status}" in
  clamp) $ISST --cpu $W core-power assoc --clos 3 >/dev/null 2>&1 ;;
  fast)  $ISST --cpu $W core-power assoc --clos 0 >/dev/null 2>&1 ;;
  status) ;;
  *) echo "usage: $0 clamp|fast|status" >&2; exit 2 ;;
esac
echo "--- workers (27, 100, 151):"
for c in 27 100 151; do echo -n "cpu$c "; $ISST --cpu $c core-power get-assoc 2>&1 | grep -m1 -oE "clos:[0-9]"; done
echo "--- controls (rinzler 1 + spare 15 stay clos:3):"
for c in 1 15; do echo -n "cpu$c "; $ISST --cpu $c core-power get-assoc 2>&1 | grep -m1 -oE "clos:[0-9]"; done
