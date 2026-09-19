#!/usr/bin/env bash
# Wait for tron publish-deb.yml of 2026-09-18 (cron 01:17 UTC, starts ~01:35) to finish, then build the
# target .deb from the SAME main commit. Fallback at DEADLINE: build from origin/main as it is then.
# usage: wait-and-build.sh   (run detached on delphi-3bda; log exec/logs/ci-mimic-build.log)
set -u
H=~/workspace/intel-AMX/exec/ci-mimic-20260918
DEADLINE="2026-09-18T02:25:00Z"; DAY=2026-09-18
say() { echo "$(date -u +%FT%TZ) $*"; }
sha=""
while :; do
  j=$(gh run list -R positron-ai/tron -w publish-deb.yml -L 3 --json databaseId,createdAt,headSha,status,conclusion,event 2>/dev/null)
  sha=$(printf '%s' "$j" | python3 -c '
import json,sys; day=sys.argv[1]
for r in json.load(sys.stdin):
    if r["createdAt"].startswith(day) and r["status"]=="completed":
        print(r["headSha"] if r["conclusion"]=="success" else "FAILED:"+r["headSha"]); break
' "$DAY" 2>/dev/null)
  [ -n "$sha" ] && break
  if [ "$(date -u +%s)" -ge "$(date -u -d "$DEADLINE" +%s)" ]; then
    git -C /var/tmp/jhan/tron-ci-enable fetch -q origin; sha=$(git -C /var/tmp/jhan/tron-ci-enable rev-parse origin/main)
    say "DEADLINE reached; publish-deb of $DAY not completed -> fallback origin/main $sha (drift vs the nightly deb to be listed later)"; break
  fi
  say "publish-deb $DAY not completed yet: $(printf '%s' "$j" | head -c 300)"; sleep 120
done
case $sha in FAILED:*) say "publish-deb $DAY FAILED; the nightly will keep the installed deb -> build from its commit 31b80a18fa12f70382e36611b41891ac76c0bb74"; sha=31b80a18fa12f70382e36611b41891ac76c0bb74;; esac
say "building target from main $sha"
bash "$H/build-target.sh" "$sha"
