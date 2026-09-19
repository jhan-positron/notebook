#!/usr/bin/env bash
# DUT-side helper for the canon-ci campaign (runs ON delphi-3bda, called over ssh by campaign.sh).
# Forked from exec/ci-mimic-20260918/dut.sh (2026-09-18); the package it installs is the canonical-AMX
# .deb (main 3faba6d0fd + deb preset TRON_AMX_DISPATCH=ON, no PR #4424), built by build-canon.sh.
#
#   dut.sh installed                 -> "<tron version> <sha256 of /opt/positron/bin/rinzler>"
#   dut.sh preflight                 -> read-only report of everything the campaign relies on
#   dut.sh ensure-canon              -> install the canonical-AMX .deb if not installed
#   dut.sh save-base-deb VERSION     -> keep a local copy of the nightly's deb (apt-get download or the apt cache)
#   dut.sh ensure-base VERSION SHA   -> reinstall the nightly's package VERSION if not installed (saved copy first,
#                                       then the repository); verify SHA
#   dut.sh lease-free                -> exit 0 when the CI lease is not held (600 s grace), 1 when busy
#   dut.sh serving-down              -> after an idle check, stop the production engines through platformd
#                                       (POST /api/inference/down), remove positron's hugepage slice files,
#                                       report free hugepages. This is the START condition of the
#                                       issue4500-20260918 campaign (session vnnied-k-in-place-c3), which
#                                       takes the machine over after us (handoff agreed 2026-09-18 22:1x UTC).
#   dut.sh serving-up                -> POST /api/inference/up (only when no handoff is wanted)
#
# The package steps repeat the nightly's own sequence (system_ci workflow yaml: apt-get remove -y tron,
# apt-get update, apt-get install -y tron) with the .deb given as a local file to apt-get install.
# No engine is started or stopped by hand during the run: platformd re-creates the rinzler@N units when
# the harness provisions the next model, exactly as it does for the nightly after its reinstall.
# Approved by jhan 2026-09-18 (package swap + restore + Bill marker + platformd down at the end).
set -u
OUT=/var/tmp/jhan/canon-ci-20260918
PLATFORMD=http://localhost:8080
export DEBIAN_FRONTEND=noninteractive
say() { echo "$(date -u +%FT%TZ) dut: $*"; }
installed() { printf '%s %s\n' "$(dpkg-query -W -f='${Version}' tron 2>/dev/null || echo none)" "$(sha256sum /opt/positron/bin/rinzler 2>/dev/null | cut -d' ' -f1)"; }
target_version() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); n=d["deb"]; print(n.split("_")[1])' "$OUT/manifest.json"; }
target_sha() { sha256sum "$OUT/rinzler.target" | cut -d' ' -f1; }
units_active() { systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active$'; }
hp_free() { awk '/^HugePages_Free/{print $2}' /proc/meminfo; }

case ${1:-} in
  installed) installed ;;
  lease-free)
    source ~/workspace/intel-AMX/exec/lib-guard.sh
    if ci_lease_busy 600; then echo busy; exit 1; else echo free; exit 0; fi ;;
  preflight)
    echo "== time $(date -u +%FT%TZ)"
    echo "== installed tron: $(installed)"
    echo "== apt candidate: $(apt-cache policy tron 2>/dev/null | grep -E 'Candidate|Installed' | tr '\n' ' ')"
    echo "== apt versions in the repo index: $(apt-cache madison tron 2>/dev/null | awk '{print $3}' | head -5 | tr '\n' ' ')"
    echo "== saved nightly deb: $(ls -la $OUT/nightly.deb 2>/dev/null || echo none)"
    echo "== canon build: status=$(cat $OUT/build.status 2>/dev/null || echo missing) deb=$(ls $OUT/target.deb 2>/dev/null) version=$(target_version 2>/dev/null) rinzler_sha=$(target_sha 2>/dev/null)"
    cat "$OUT/manifest.json" 2>/dev/null
    echo "== unit ExecStart: $(grep '^ExecStart=' /etc/systemd/system/rinzler@.service)"
    echo "== unit num-expert-replicas count: $(grep -c 'num-expert-replicas' /etc/systemd/system/rinzler@.service) (0 = pristine deb file)"
    echo "== drop-ins: $(ls /etc/systemd/system/rinzler@.service.d/ 2>/dev/null || echo none)"
    echo "== platformd: $(systemctl is-active platformd) $(curl -s -m 5 $PLATFORMD/api/config | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]["inference"]["engines"]["default"]; print("count",r["count"],"tp",r["tensor_parallelism"],"models",[m["shape"] for m in r["models"]],"spec",r["use_speculation"])' 2>/dev/null)"
    echo "== engines: $(curl -s -m 5 $PLATFORMD/api/inference/status | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]; print([(e.get("instance"),e.get("status")) for e in r["engines"]])' 2>/dev/null)"
    echo "== rinzler units: $(systemctl list-units 'rinzler@*' --no-legend --no-pager | awk '{print $1,$3,$4}' | tr '\n' ';')"
    echo "== lease: $(cat /run/lock/systems-test-ci.lease 2>/dev/null || echo 'no lease file')"
    echo "== bill marker: $(ls /bill-has-instance-0,2 2>/dev/null || echo absent)"
    echo "== hugepages: $(grep -E 'HugePages_(Total|Free)' /proc/meminfo | tr '\n' ' ') node0 $(cat /sys/devices/system/node/node0/hugepages/hugepages-1048576kB/free_hugepages)/256 free node1 $(cat /sys/devices/system/node/node1/hugepages/hugepages-1048576kB/free_hugepages)/256 free; files: $(ls /dev/hugepages/ | tr '\n' ' ')"
    echo "== config.env bytes (must be 0): $(stat -c %s /opt/positron/user/config.env 2>/dev/null)"
    echo "== engine env AMX/HW_ATTN vars (must be 0): $(sudo -n grep -c -E 'USE_HW_ATTN|TRON_AMX|TRON_K_VNNI' /etc/rinzler/instance-*.env 2>/dev/null | tr '\n' ' ')"
    echo "== speed select: $(sudo -n /usr/local/sbin/intel-speed-select-state verify 2>&1 | tail -1)"
    echo "== load: $(uptime)"
    echo "== campaign flock: $(flock -n /var/tmp/jhan/3bda-campaign.lock true 2>/dev/null && echo free || echo HELD)"
    echo "== other campaigns of ours: $(pgrep -u jhan -a -f 'campaign[.]sh|runtron|make deb|ninja|build-canon' | grep -v -E 'dut.sh|pgrep' | head -5 | tr '\n' ';')"
    ;;
  ensure-canon)
    [ "$(cat $OUT/build.status 2>/dev/null)" = ok ] || { say "canon build not ok"; exit 1; }
    want=$(target_version); wsha=$(target_sha)
    read -r have hsha < <(installed)
    if [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ]; then say "canon package already installed ($have)"; exit 0; fi
    say "installing canon package $want (was $have)"
    sudo -n apt-get remove -y tron >"$OUT/apt-remove-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get remove rc=$?"
    sudo -n apt-get install -y --allow-downgrades "$OUT/target.deb" >"$OUT/apt-install-canon-$(date -u +%H%M%S).log" 2>&1 || { say "FAILED apt-get install canon rc=$?"; tail -20 "$OUT"/apt-install-canon-*.log; exit 1; }
    read -r have hsha < <(installed)
    [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ] || { say "FAILED verify: have $have $hsha want $want $wsha"; exit 1; }
    say "canon package installed and verified: $have rinzler sha $hsha"
    ;;
  save-base-deb)
    # keep a local copy of the nightly's deb while its version is still in the repo index (tomorrow's publish-deb
    # at ~01:34 UTC may drop it); ensure-base installs this file first and falls back to the repository
    want=${2:?VERSION}
    if [ -s "$OUT/nightly.deb" ] && [ "$(dpkg-deb -f "$OUT/nightly.deb" Version 2>/dev/null)" = "$want" ]; then say "nightly deb $want already saved"; exit 0; fi
    rm -f "$OUT/nightly.deb"
    ( cd "$OUT" && apt-get download "tron=$want" >"$OUT/apt-download-$(date -u +%H%M%S).log" 2>&1 && mv -f "tron_${want}_amd64.deb" nightly.deb ) \
      || { c=$(ls /var/cache/apt/archives/tron_${want}_amd64.deb 2>/dev/null | head -1); [ -n "$c" ] && cp -f "$c" "$OUT/nightly.deb"; }
    [ -s "$OUT/nightly.deb" ] || { say "could not save the nightly deb $want (download and apt cache both failed)"; exit 1; }
    v=$(dpkg-deb -f "$OUT/nightly.deb" Version 2>/dev/null)
    [ "$v" = "$want" ] || { say "saved deb has version '$v', wanted $want"; rm -f "$OUT/nightly.deb"; exit 1; }
    say "saved nightly deb $want: $(stat -c %s "$OUT/nightly.deb") bytes, sha256 $(sha256sum "$OUT/nightly.deb" | cut -c1-16)"
    ;;
  ensure-base)
    want=${2:?VERSION}; wsha=${3:?SHA}
    read -r have hsha < <(installed)
    if [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ]; then say "base already installed ($have)"; exit 0; fi
    say "reinstalling nightly package $want (was $have)"
    sudo -n apt-get remove -y tron >"$OUT/apt-remove-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get remove rc=$?"
    if [ -s "$OUT/nightly.deb" ] && [ "$(dpkg-deb -f "$OUT/nightly.deb" Version 2>/dev/null)" = "$want" ]; then
      say "installing the saved local copy $OUT/nightly.deb"
      sudo -n apt-get install -y --allow-downgrades "$OUT/nightly.deb" >"$OUT/apt-install-base-$(date -u +%H%M%S).log" 2>&1 || say "WARNING local install rc=$?; trying the repository"
    fi
    read -r have hsha < <(installed)
    if [ "$have" != "$want" ]; then
      sudo -n apt-get update >"$OUT/apt-update-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get update rc=$?"
      sudo -n apt-get install -y --allow-downgrades "tron=$want" >"$OUT/apt-install-base-$(date -u +%H%M%S).log" 2>&1 || { say "FAILED apt-get install tron=$want rc=$?"; tail -20 "$OUT"/apt-install-base-*.log; exit 1; }
    fi
    read -r have hsha < <(installed)
    [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ] || { say "FAILED verify: have $have $hsha want $want $wsha"; exit 1; }
    say "base restored and verified: $have rinzler sha $hsha"
    ;;
  serving-down)
    # Idle test before stopping engines that could serve somebody: no request line in the rinzler journal for
    # IDLE_MIN minutes and no established TCP connection from another host to an engine or proxy port.
    # (The only traffic tonight was our own harness; a 5-minute window keeps the handoff short.)
    IDLE_MIN=${IDLE_MIN:-5}
    if [ "$(units_active)" = 0 ]; then say "no rinzler@N unit active"; else
      ok=0
      for try in $(seq 1 12); do   # up to 12 min of 60-s polls
        j=$(sudo -n journalctl -u 'rinzler@*' --since "-${IDLE_MIN} min" --no-pager 2>&1) || { say "journalctl failed (${j:0:100}); not touching serving"; sleep 60; continue; }
        traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'Parsing the prompt|response tokens|chat/completions|Request [0-9]+\]') || true
        busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
        conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 or sport = :80 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
        say "engines active; last $IDLE_MIN min: request-lines=${traffic:-?} non-idle-stats=${busy:-?} remote-conns=${conns:-?}"
        if [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ] && [ "${conns:-1}" -eq 0 ]; then ok=1; break; fi
        sleep 60
      done
      [ $ok = 1 ] || { say "engines still see traffic; NOT taking serving down"; exit 1; }
      say "taking production serving down through platformd: $(curl -s -m 60 -X POST $PLATFORMD/api/inference/down | head -c 200)"
      for _ in $(seq 1 36); do [ "$(units_active)" = 0 ] && break; sleep 5; done
      [ "$(units_active)" = 0 ] || { say "rinzler@N units still active 180 s after the down request"; systemctl list-units 'rinzler@*' --no-legend --no-pager; exit 1; }
    fi
    sleep 5
    # positron's slice files stay allocated until unlinked (the units are inactive: synchronous stop). Ours only when unmapped; anyone else's stay.
    for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/rinzler-*; do
      [ -e "$f" ] || continue
      if [ "$(stat -c %U "$f" 2>/dev/null)" = positron ]; then { rm -f "$f" 2>/dev/null || sudo -n rm -f "$f"; } && say "removed $f (production engines down)"
      elif [ -O "$f" ]; then ! fuser -s "$f" 2>/dev/null && rm -f "$f" && say "removed $f (unmapped, ours)"
      else say "$f belongs to $(stat -c %U "$f" 2>/dev/null || echo '?'), left alone"
      fi
    done
    say "serving down: units_active=$(units_active) HugePages_Free=$(hp_free) (512 = all free; the next campaign needs >= 256) engines: $(curl -s -m 5 $PLATFORMD/api/inference/status | head -c 200)"
    [ "$(hp_free)" -ge 256 ] || { say "WARNING fewer than 256 free hugepages"; exit 1; }
    ;;
  serving-up)
    say "bringing production serving up through platformd: $(curl -s -m 60 -X POST $PLATFORMD/api/inference/up | head -c 200)"
    for _ in $(seq 1 36); do [ "$(units_active)" -ge 1 ] && break; sleep 5; done
    say "units_active=$(units_active)"
    ;;
  *) echo "usage: dut.sh installed|preflight|ensure-canon|ensure-base VERSION SHA|save-base-deb VERSION|lease-free|serving-down|serving-up"; exit 2 ;;
esac
