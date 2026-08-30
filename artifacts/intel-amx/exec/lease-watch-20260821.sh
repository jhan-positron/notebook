#!/usr/bin/env bash
# Lease-format probe, 2026-08-21 CI window (QUEUE.md "LEASE FORMAT VERIFICATION").
# Samples /run/lock/systems-test-ci.lease on delphi-3bda every 20 min from
# 03:30Z to 09:30Z. Read-only; no machine state touched.
OUT=/home/jhan/workspace/intel-AMX/exec/logs/lease-watch-20260821.log
START=$(date -u -d '2026-08-21 03:30' +%s)
END=$(date -u -d '2026-08-21 09:30' +%s)

now=$(date -u +%s)
if (( now < START )); then
    echo "=== $(date -u +%FT%TZ) armed, sleeping until 03:30Z" >> "$OUT"
    sleep $(( START - now ))
fi

while (( $(date -u +%s) < END )); do
    ts=$(date -u +%FT%TZ)
    out=$(ssh -o ConnectTimeout=15 -o BatchMode=yes jhan@delphi-3bda \
        'if [ -f /run/lock/systems-test-ci.lease ]; then
             echo PRESENT
             ls -l /run/lock/systems-test-ci.lease
             cat /run/lock/systems-test-ci.lease
         else
             echo ABSENT
         fi' 2>&1)
    rc=$?
    {
        echo "=== $ts rc=$rc"
        echo "$out"
    } >> "$OUT"
    sleep 1200
done
echo "=== $(date -u +%FT%TZ) window end" >> "$OUT"
