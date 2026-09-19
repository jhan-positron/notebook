#!/usr/bin/env bash
# DUT-side helper for the ci-mimic campaign (runs ON delphi-3bda, called over ssh by campaign.sh).
#
#   dut.sh installed                 -> "<tron version> <sha256 of /opt/positron/bin/rinzler>"
#   dut.sh preflight                 -> read-only report of everything the campaign relies on
#   dut.sh ensure-target             -> install the target .deb (PR #4424 + AMX + VNNI K preset) if not installed
#   dut.sh ensure-base VERSION SHA   -> reinstall the nightly's apt package VERSION if not installed; verify SHA
#   dut.sh lease-free                -> exit 0 when the CI lease is not held (600 s grace), 1 when busy
#
# The package steps repeat the nightly's own sequence (system_ci workflow yaml: apt-get remove -y tron,
# apt-get update, apt-get install -y tron) with the target .deb given as a local file to apt-get install.
# No engine is started or stopped by hand: platformd re-creates the rinzler@N units when the harness
# provisions the next model, exactly as it does for the nightly after its reinstall.
# Approved by jhan 2026-09-18 02:1x UTC (package swap + restore + marker release).
set -u
OUT=/var/tmp/jhan/ci-mimic-20260918
export DEBIAN_FRONTEND=noninteractive
say() { echo "$(date -u +%FT%TZ) dut: $*"; }
installed() { printf '%s %s\n' "$(dpkg-query -W -f='${Version}' tron 2>/dev/null || echo none)" "$(sha256sum /opt/positron/bin/rinzler 2>/dev/null | cut -d' ' -f1)"; }
target_version() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); n=d["deb"]; print(n.split("_")[1])' "$OUT/manifest.json"; }
target_sha() { sha256sum "$OUT/rinzler.target" | cut -d' ' -f1; }

case ${1:-} in
  installed) installed ;;
  lease-free)
    source ~/workspace/intel-AMX/exec/lib-guard.sh
    if ci_lease_busy 600; then echo busy; exit 1; else echo free; exit 0; fi ;;
  preflight)
    echo "== time $(date -u +%FT%TZ)"
    echo "== installed tron: $(installed)"
    echo "== apt candidate: $(apt-cache policy tron 2>/dev/null | grep -E 'Candidate|Installed' | tr '\n' ' ')"
    echo "== target build: status=$(cat $OUT/build.status 2>/dev/null || echo missing) deb=$(ls $OUT/target.deb 2>/dev/null) version=$(target_version 2>/dev/null) rinzler_sha=$(target_sha 2>/dev/null)"
    cat "$OUT/manifest.json" 2>/dev/null
    echo "== unit ExecStart: $(grep '^ExecStart=' /etc/systemd/system/rinzler@.service)"
    echo "== unit num-expert-replicas count: $(grep -c 'num-expert-replicas' /etc/systemd/system/rinzler@.service) (0 = pristine deb file)"
    echo "== drop-ins: $(ls /etc/systemd/system/rinzler@.service.d/ 2>/dev/null || echo none)"
    echo "== platformd: $(systemctl is-active platformd) $(curl -s -m 5 localhost:8080/api/config | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]["inference"]["engines"]["default"]; print("count",r["count"],"tp",r["tensor_parallelism"],"models",[m["shape"] for m in r["models"]],"spec",r["use_speculation"])' 2>/dev/null)"
    echo "== engines: $(curl -s -m 5 localhost:8080/api/inference/status | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]; print([(e.get("instance"),e.get("status")) for e in r["engines"]])' 2>/dev/null)"
    echo "== rinzler units: $(systemctl list-units 'rinzler@*' --no-legend --no-pager | awk '{print $1,$3,$4}' | tr '\n' ';')"
    echo "== lease: $(cat /run/lock/systems-test-ci.lease 2>/dev/null || echo 'no lease file')"
    echo "== bill marker: $(ls /bill-has-instance-0,2 2>/dev/null || echo absent)"
    echo "== hugepages: $(grep -E 'HugePages_(Total|Free)' /proc/meminfo | tr '\n' ' ') node0 $(cat /sys/devices/system/node/node0/hugepages/hugepages-1048576kB/free_hugepages)/256 free node1 $(cat /sys/devices/system/node/node1/hugepages/hugepages-1048576kB/free_hugepages)/256 free; files: $(ls /dev/hugepages/ | tr '\n' ' ')"
    echo "== config.env bytes (must be 0): $(stat -c %s /opt/positron/user/config.env 2>/dev/null)"
    echo "== engine env AMX/HW_ATTN vars (must be 0): $(sudo -n grep -c -E 'USE_HW_ATTN|TRON_AMX|TRON_K_VNNI' /etc/rinzler/instance-*.env 2>/dev/null | tr '\n' ' ')"
    echo "== speed select: $(sudo -n /usr/local/sbin/intel-speed-select-state verify 2>&1 | tail -1)"
    echo "== load: $(uptime)"
    echo "== campaign flock: $(flock -n /var/tmp/jhan/3bda-campaign.lock true 2>/dev/null && echo free || echo HELD)"
    echo "== jhan test processes: $(pgrep -u jhan -a -f 'runtron|rinzler\.|campaign|make deb|ninja' | grep -v -E 'dut.sh|pgrep' | head -5 | tr '\n' ';')"
    ;;
  ensure-target)
    [ "$(cat $OUT/build.status 2>/dev/null)" = ok ] || { say "target build not ok"; exit 1; }
    want=$(target_version); wsha=$(target_sha)
    read -r have hsha < <(installed)
    if [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ]; then say "target already installed ($have)"; exit 0; fi
    say "installing target $want (was $have)"
    sudo -n apt-get remove -y tron >"$OUT/apt-remove-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get remove rc=$?"
    sudo -n apt-get install -y --allow-downgrades "$OUT/target.deb" >"$OUT/apt-install-target-$(date -u +%H%M%S).log" 2>&1 || { say "FAILED apt-get install target rc=$?"; tail -20 "$OUT"/apt-install-target-*.log; exit 1; }
    read -r have hsha < <(installed)
    [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ] || { say "FAILED verify: have $have $hsha want $want $wsha"; exit 1; }
    say "target installed and verified: $have rinzler sha $hsha"
    ;;
  ensure-base)
    want=${2:?VERSION}; wsha=${3:?SHA}
    read -r have hsha < <(installed)
    if [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ]; then say "base already installed ($have)"; exit 0; fi
    say "reinstalling nightly package $want (was $have)"
    sudo -n apt-get remove -y tron >"$OUT/apt-remove-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get remove rc=$?"
    sudo -n apt-get update >"$OUT/apt-update-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get update rc=$?"
    sudo -n apt-get install -y --allow-downgrades "tron=$want" >"$OUT/apt-install-base-$(date -u +%H%M%S).log" 2>&1 || { say "FAILED apt-get install tron=$want rc=$?"; tail -20 "$OUT"/apt-install-base-*.log; exit 1; }
    read -r have hsha < <(installed)
    [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ] || { say "FAILED verify: have $have $hsha want $want $wsha"; exit 1; }
    say "base restored and verified: $have rinzler sha $hsha"
    ;;
  *) echo "usage: dut.sh installed|preflight|ensure-target|ensure-base VERSION SHA|lease-free"; exit 2 ;;
esac
