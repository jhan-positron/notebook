#!/bin/bash
# p43_rinzler_boost.sh apply|revert|status — Arm B toggle for the P4.3
# rinzler-core frequency A/B on delphi-3bda (new PR-3070 map).
# Rinzler role cores (physical 1,2,73,74 + HT siblings 145,146,217,218):
#   apply  -> CLOS0 (joins the ~4100-class fast set; +4 phys cores keeps
#             the TF grant rung — the 88-core precedent held 4100)
#   revert -> CLOS3 (<=2700 deployed tron112 default)
# Uses only the NOPASSWD isst binary. Does not survive reboot (boot
# service reapplies deployed tron112).
set -u
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
CPUS="1,2,73,74,145,146,217,218"
case "${1:-status}" in
  apply)  $ISST --cpu $CPUS core-power assoc --clos 0 2>&1 | grep -cE "assoc|cpu" ;;
  revert) $ISST --cpu $CPUS core-power assoc --clos 3 2>&1 | grep -cE "assoc|cpu" ;;
  status) ;;
  *) echo "usage: $0 apply|revert|status" >&2; exit 2 ;;
esac
echo "--- rinzler cores (want clos:0 after apply, clos:3 after revert):"
for c in 1 2 73 74 145 217; do
  echo -n "cpu$c "; $ISST --cpu $c core-power get-assoc 2>&1 | grep -m1 -oE "clos:[0-9]"
done
echo "--- controls (worker 27 must stay clos:0, spare 15 must stay clos:3):"
for c in 27 15; do
  echo -n "cpu$c "; $ISST --cpu $c core-power get-assoc 2>&1 | grep -m1 -oE "clos:[0-9]"
done
