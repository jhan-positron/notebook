#!/bin/bash
# rz_wrapper.sh — "dedicated coordinator" arm: replace the LOWEST app-core
# of each instance (24 for instance-0, 96 for instance-1) with a boosted
# spare (15 / 87). The map rule pins Main/coordinator to the lowest core,
# so main moves to the spare; the worker set is otherwise identical.
# Exec'd by systemd with the rinzler instance env already loaded.
set -u
AA8=/var/tmp/jhan/ef-inv/tron-29924aa8
ARGS="$RZ_CLI_ARGS"
case "${RZ_INSTANCE:-x}" in
  0) NEW=$(echo "$ARGS" | sed "s/,24-29,/,15,25-29,/") ;;
  1) NEW=$(echo "$ARGS" | sed "s/,96-101,/,87,97-101,/") ;;
  *) NEW="$ARGS" ;;
esac
if [ "$NEW" = "$ARGS" ] && [ "${RZ_INSTANCE:-x}" != "x" ]; then
  echo "rz_wrapper: SUBSTITUTION FAILED for instance $RZ_INSTANCE — running stock args" >&2
fi
echo "rz_wrapper: instance=${RZ_INSTANCE:-?} app-cores rewritten: $(echo "$NEW" | grep -oE -- "--app-cores [^ ]*" | head -c 120)" >&2
exec /usr/bin/taskset -c "${CPUAFFINITY}" "$AA8/gen/rinzler" $NEW
