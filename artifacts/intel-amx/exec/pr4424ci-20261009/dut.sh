#!/usr/bin/env bash
# DUT-side helper for the pr4424ci campaign (runs ON delphi-3bda, called over ssh by campaign.sh).
# Forked 2026-10-08 from exec/q4b-fpga-20260921/dut.sh (platformd 0.11 explicit named engines, restore-target rule,
# hwattn-off/clear, verify-env). Changes: OUT is this campaign's scratch directory; ensure-canon/ensure-vnnik are
# replaced by ensure-target (the PR 4424 deb that build-target.sh wrote to $OUT); new command memsnap (one JSON line
# with the memory fields of every running rinzler engine and of /proc/meminfo; the DRIVER st_ci_perf.py calls it over
# ssh after every provisioning and after every benchmark, so campaign.sh never has to).
#
#   dut.sh installed                 -> "<tron version> <sha256 of /opt/positron/bin/rinzler>"
#   dut.sh preflight                 -> read-only report of everything the campaign relies on
#   dut.sh ensure-target             -> install $OUT/target.deb (PR 4424 + deb preset AMX + VNNI K) if not installed;
#                                       verified by version (manifest.json deb name) and rinzler sha ($OUT/rinzler.target)
#   dut.sh save-base-deb VERSION [FILE] -> keep a local copy of a nightly deb (apt-get download or the apt cache) as
#                                       $OUT/FILE (nightly.deb = the base arm, already saved; restore.deb = the restore target)
#   dut.sh ensure-base VERSION SHA [FILE] -> reinstall the nightly package VERSION if not installed (saved copy FILE
#                                       first, then the repository); verify SHA
#   dut.sh hwattn-off                -> write USE_HW_ATTN=0 to /opt/positron/user/config.env (14 bytes). The rinzler unit
#                                       reads this file LAST (EnvironmentFile=-), so the key wins over instance-N.env;
#                                       engines read it at START only, so the caller restarts them
#   dut.sh hwattn-clear              -> truncate config.env to 0 bytes; the caller restarts the engines afterwards
#   dut.sh verify-env                -> VERIFY_HWATTN=set: every running rinzler pid must carry USE_HW_ATTN=0 exactly once;
#                                       VERIFY_HWATTN=unset: no pid may carry it. rc 1 if a pid is wrong; the pid count must
#                                       equal platformd's configured engine count (VERIFY_ENV_PIDS overrides; rc 2 on a mismatch)
#   dut.sh memsnap                   -> one JSON line: per rinzler pid VmRSS, VmHWM (peak RSS), HugetlbPages from
#                                       /proc/PID/status (sudo -n cat: the units run as positron) and /proc/meminfo
#                                       MemAvailable, MemFree, HugePages_Free, Committed_AS; plus sums over the pids
#   dut.sh lease-free                -> exit 0 when the CI lease is not held (600 s grace), 1 when busy
#   dut.sh serving-down              -> after an idle check (IDLE_MIN minutes), stop the production engines through platformd
#                                       (POST /api/inference/down), remove positron's hugepage slice files, report free hugepages
#   dut.sh serving-up                -> POST /api/inference/up, then wait for platformd idle + all configured engines running
#
# The package steps repeat the nightly's own sequence (system_ci workflow yaml: apt-get remove -y tron,
# apt-get update, apt-get install -y tron) with the .deb given as a local file to apt-get install.
# apt never restarts engines: the caller restarts them (serving-down, serving-up) after every package switch.
# platformd 0.11 restarts units stopped with systemctl, so serving down/up always go through platformd's API.
set -u
OUT=/var/tmp/jhan/pr4424ci-20261009
PLATFORMD=http://localhost:8080
# platformd 0.11: engines are named entries; a legacy template may still carry "count" (default 1)
engine_count() { curl -s -m 5 $PLATFORMD/api/config | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]["inference"]["engines"]; print(sum(int(v.get("count",1)) for v in r.values()))' 2>/dev/null; }
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
    echo "== saved nightly deb (base arm): $(ls -la $OUT/nightly.deb 2>/dev/null || echo none) version $(dpkg-deb -f $OUT/nightly.deb Version 2>/dev/null)"
    echo "== saved restore deb: $(ls -la $OUT/restore.deb 2>/dev/null || echo none) version $(dpkg-deb -f $OUT/restore.deb Version 2>/dev/null)"
    echo "== target build: status=$(cat $OUT/build.status 2>/dev/null || echo missing) deb=$(ls $OUT/target.deb 2>/dev/null) version=$(target_version 2>/dev/null) rinzler_sha=$(target_sha 2>/dev/null)"
    cat "$OUT/manifest.json" 2>/dev/null
    read -r _iv _isha < <(installed)
    if [ -n "${_isha:-}" ] && [ "$_isha" = "$(target_sha 2>/dev/null)" ]; then echo "== installed rinzler IS the target build's (must be no at preflight): yes"; else echo "== installed rinzler IS the target build's (must be no at preflight): no"; fi
    echo "== unit ExecStart: $(grep '^ExecStart=' /etc/systemd/system/rinzler@.service)"
    echo "== unit num-expert-replicas count: $(grep -c 'num-expert-replicas' /etc/systemd/system/rinzler@.service) (0 = pristine deb file)"
    echo "== drop-ins: $(ls /etc/systemd/system/rinzler@.service.d/ 2>/dev/null || echo none)"
    echo "== platformd: $(systemctl is-active platformd) version $(curl -s -m 5 $PLATFORMD/api/internal/maintenance/versions | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]; print(r.get("platformd"),"tron",r.get("tron"))' 2>/dev/null)"
    echo "== platformd engine config: $(curl -s -m 5 $PLATFORMD/api/config | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]["inference"]["engines"]; print(len(r),"entries",[(k,"tp",v.get("tensor_parallelism"),[m["shape"] for m in v.get("models",[])],"ingress",(v.get("ingress") or {}).get("port"),"count",v.get("count",1)) for k,v in sorted(r.items())])' 2>/dev/null)"
    echo "== engines: $(curl -s -m 5 $PLATFORMD/api/inference/status | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]; print([(e.get("name"),e.get("instance"),e.get("status")) for e in r["engines"]])' 2>/dev/null)"
    echo "== test proxy default: $(curl -s -m 5 $PLATFORMD/api/internal/proxy/default | head -c 200)"
    echo "== rinzler units: $(systemctl list-units 'rinzler@*' --no-legend --no-pager | awk '{print $1,$3,$4}' | tr '\n' ';')"
    echo "== lease: $(cat /run/lock/systems-test-ci.lease 2>/dev/null || echo 'no lease file')"
    echo "== bill marker: $(ls /bill-has-instance-0,2 2>/dev/null || echo absent)"
    echo "== hugepages: $(grep -E 'HugePages_(Total|Free)' /proc/meminfo | tr '\n' ' ') node0 $(cat /sys/devices/system/node/node0/hugepages/hugepages-1048576kB/free_hugepages)/256 free node1 $(cat /sys/devices/system/node/node1/hugepages/hugepages-1048576kB/free_hugepages)/256 free; files: $(ls /dev/hugepages/ | tr '\n' ' ')"
    echo "== config.env bytes (must be 0): $(stat -c %s /opt/positron/user/config.env 2>/dev/null)"
    echo "== engine env AMX/HW_ATTN vars (must be 0): $(sudo -n grep -c -E 'USE_HW_ATTN|TRON_AMX|TRON_K_VNNI' /etc/rinzler/instance-*.env 2>/dev/null | tr '\n' ' ')"
    echo "== memsnap: $(bash "$0" memsnap 2>/dev/null | tail -1 | head -c 600)"
    echo "== speed select: $(sudo -n /usr/local/sbin/intel-speed-select-state verify 2>&1 | tail -1)"
    echo "== load: $(uptime)"
    echo "== campaign flock: $(flock -n /var/tmp/jhan/3bda-campaign.lock true 2>/dev/null && echo free || echo HELD)"
    echo "== other campaigns of ours: $(pgrep -u jhan -a -f 'campaign[.]sh|runtron|make deb|ninja|build-target' | grep -v -E 'dut.sh|pgrep' | head -5 | tr '\n' ';')"
    ;;
  ensure-target)
    [ "$(cat $OUT/build.status 2>/dev/null)" = ok ] || { say "target build not ok"; exit 1; }
    [ -s "$OUT/target.deb" ] && [ -s "$OUT/rinzler.target" ] || { say "target.deb or rinzler.target missing in $OUT"; exit 1; }
    want=$(target_version); wsha=$(target_sha)
    read -r have hsha < <(installed)
    if [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ]; then say "target package already installed ($have)"; exit 0; fi
    say "installing target package $want (was $have)"
    sudo -n apt-get remove -y tron >"$OUT/apt-remove-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get remove rc=$?"
    sudo -n apt-get install -y --allow-downgrades "$OUT/target.deb" >"$OUT/apt-install-target-$(date -u +%H%M%S).log" 2>&1 || { say "FAILED apt-get install target rc=$?"; tail -20 "$OUT"/apt-install-target-*.log; exit 1; }
    read -r have hsha < <(installed)
    [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ] || { say "FAILED verify: have $have $hsha want $want $wsha"; exit 1; }
    say "target package installed and verified: $have rinzler sha $hsha"
    ;;
  save-base-deb)
    # keep a local copy of a nightly deb while its version is still in the repo index (tomorrow's publish-deb
    # at ~01:34 UTC may drop it); ensure-base installs this file first and falls back to the repository.
    # FILE defaults to nightly.deb (the base arm); the campaign saves the restore target as restore.deb.
    want=${2:?VERSION}; file=${3:-nightly.deb}
    case $file in nightly.deb|restore.deb) ;; *) say "save-base-deb: FILE must be nightly.deb or restore.deb"; exit 2;; esac
    if [ -s "$OUT/$file" ] && [ "$(dpkg-deb -f "$OUT/$file" Version 2>/dev/null)" = "$want" ]; then say "deb $want already saved as $file"; exit 0; fi
    tmp="$OUT/.$file.tmp"; rm -f "$tmp"   # the kept copy (if any, of another version) is replaced only after the download succeeded
    ( cd "$OUT" && apt-get download "tron=$want" >"$OUT/apt-download-$(date -u +%H%M%S).log" 2>&1 && mv -f "tron_${want}_amd64.deb" "$tmp" ) \
      || { c=$(ls /var/cache/apt/archives/tron_${want}_amd64.deb 2>/dev/null | head -1); [ -n "$c" ] && cp -f "$c" "$tmp"; }
    [ -s "$tmp" ] || { say "could not save the deb $want as $file (download and apt cache both failed; the existing $file, if any, is kept)"; exit 1; }
    v=$(dpkg-deb -f "$tmp" Version 2>/dev/null)
    [ "$v" = "$want" ] || { say "downloaded deb has version '$v', wanted $want (the existing $file, if any, is kept)"; rm -f "$tmp"; exit 1; }
    mv -f "$tmp" "$OUT/$file"
    say "saved deb $want as $file: $(stat -c %s "$OUT/$file") bytes, sha256 $(sha256sum "$OUT/$file" | cut -c1-16)"
    ;;
  ensure-base)
    want=${2:?VERSION}; wsha=${3:?SHA}; file=${4:-nightly.deb}
    read -r have hsha < <(installed)
    if [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ]; then say "nightly package $want already installed"; exit 0; fi
    say "reinstalling nightly package $want (was $have) from $file"
    sudo -n apt-get remove -y tron >"$OUT/apt-remove-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get remove rc=$?"
    if [ -s "$OUT/$file" ] && [ "$(dpkg-deb -f "$OUT/$file" Version 2>/dev/null)" = "$want" ]; then
      say "installing the saved local copy $OUT/$file"
      sudo -n apt-get install -y --allow-downgrades "$OUT/$file" >"$OUT/apt-install-base-$(date -u +%H%M%S).log" 2>&1 || say "WARNING local install rc=$?; trying the repository"
    fi
    read -r have hsha < <(installed)
    if [ "$have" != "$want" ]; then
      sudo -n apt-get update >"$OUT/apt-update-$(date -u +%H%M%S).log" 2>&1 || say "WARNING apt-get update rc=$?"
      sudo -n apt-get install -y --allow-downgrades "tron=$want" >"$OUT/apt-install-base-$(date -u +%H%M%S).log" 2>&1 || { say "FAILED apt-get install tron=$want rc=$?"; tail -20 "$OUT"/apt-install-base-*.log; exit 1; }
    fi
    read -r have hsha < <(installed)
    [ "$have" = "$want" ] && [ "$hsha" = "$wsha" ] || { say "FAILED verify: have $have $hsha want $want $wsha"; exit 1; }
    say "nightly package installed and verified: $have rinzler sha $hsha"
    ;;
  hwattn-off)
    # Software attention for every engine platformd starts from now on. The unit reads config.env at engine START only:
    # the caller restarts the engines afterwards.
    printf 'USE_HW_ATTN=0\n' | sudo -n tee /opt/positron/user/config.env >/dev/null || { say "hwattn-off FAILED: sudo tee rc=$?"; exit 1; }
    b=$(stat -c %s /opt/positron/user/config.env 2>/dev/null)
    say "hwattn-off: config.env is now ${b:-?} bytes (must be 14), content: $(tr '\n' ' ' </opt/positron/user/config.env 2>/dev/null)"
    [ "${b:-0}" = 14 ] || exit 1
    ;;
  hwattn-clear)
    sudo -n truncate -s 0 /opt/positron/user/config.env || { say "hwattn-clear FAILED: sudo truncate rc=$?"; exit 1; }
    b=$(stat -c %s /opt/positron/user/config.env 2>/dev/null)
    say "hwattn-clear: config.env is now ${b:-?} bytes (must be 0)"
    [ "${b:-1}" = 0 ] || exit 1
    ;;
  verify-env)
    # Every running rinzler is read from /proc/PID/environ as root (the units run as positron). Expected pid count =
    # platformd's configured engine count (VERIFY_ENV_PIDS overrides, at least 1 when platformd does not answer).
    # rc 1 = a pid has the wrong USE_HW_ATTN=0 line count (one restart, then stop); rc 2 = pid count differs from the
    # expected count (an engine-count problem, not a config.env problem).
    cfg=$(engine_count)
    mode=${VERIFY_HWATTN:-set}   # set: every pid must carry USE_HW_ATTN=0 exactly once (CPU attention forced); unset: no pid may carry it (FPGA attention)
    case $mode in set) wantc=1;; unset) wantc=0;; *) say "verify-env: VERIFY_HWATTN must be set or unset, got '$mode'"; exit 3;; esac
    want=${VERIFY_ENV_PIDS:-$cfg}; n=0; bad=0
    for p in $(pgrep -x rinzler); do
      n=$((n+1))
      envl=$(sudo -n cat "/proc/$p/environ" 2>/dev/null | tr '\0' '\n')
      c=$(printf '%s\n' "$envl" | grep -c '^USE_HW_ATTN=0$'); nl=$(printf '%s\n' "$envl" | grep -c .)
      cmd=$(sudo -n cat "/proc/$p/cmdline" 2>/dev/null | tr '\0' ' ' | cut -c1-160)
      say "verify-env: pid $p USE_HW_ATTN=0 lines=${c:-?} of ${nl:-?} environment lines (want $wantc, mode $mode); cmd: ${cmd:-?}"
      [ "${c:-x}" = "$wantc" ] || bad=$((bad+1))
    done
    say "verify-env: mode $mode; $n rinzler pid(s) (expected ${want:-'>= 1: platformd config unreadable'}; platformd configured engines ${cfg:-?}, units active $(units_active)), $bad with the wrong USE_HW_ATTN=0 line count (must be 0); config.env bytes: $(stat -c %s /opt/positron/user/config.env 2>/dev/null)"
    [ "$bad" -eq 0 ] || exit 1
    if [ -n "$want" ]; then [ "$n" -eq "$want" ] || exit 2; else [ "$n" -ge 1 ] || exit 2; fi
    ;;
  memsnap)
    # One JSON line. Per running rinzler pid: VmRSS (resident set now), VmHWM (peak resident set since the process
    # started; platformd starts a new process per provisioning, so the peak belongs to the current model), HugetlbPages
    # (1 GiB hugepage mappings = the weights and the K/V arena), VmSize, RssAnon, RssFile, RssShmem; all from
    # /proc/PID/status read as root. Host: MemTotal, MemFree, MemAvailable, Committed_AS, HugePages_Total/Free, Cached,
    # Shmem from /proc/meminfo. Sums over the pids are precomputed for the summary. Never fails: an unreadable pid is
    # reported with "status": "unreadable" and rc stays 0.
    python3 - <<'PY'
import json, os, re, subprocess, time
FIELDS = ("VmRSS", "VmHWM", "HugetlbPages", "VmSize", "VmPeak", "RssAnon", "RssFile", "RssShmem")
def read_status(pid):
    try:
        out = subprocess.run(["sudo", "-n", "cat", f"/proc/{pid}/status"], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return None
    d = {}
    for line in out.splitlines():
        m = re.match(r"^(\w+):\s+(\d+) kB", line)
        if m and m.group(1) in FIELDS:
            d[m.group(1) + "_kB"] = int(m.group(2))
    return d or None
try:
    pids = subprocess.run(["pgrep", "-x", "rinzler"], capture_output=True, text=True, timeout=15).stdout.split()
except Exception:
    pids = []
engines = []
for p in pids:
    unit = None
    try:
        cg = open(f"/proc/{p}/cgroup").read().strip().splitlines()[-1]
        m = re.search(r"(rinzler@\d+)\.service", cg)
        unit = m.group(1) if m else cg[-60:]
    except Exception:
        pass
    st = read_status(p)
    engines.append({"pid": int(p), "unit": unit, **(st or {"status": "unreadable"})})
mi = {}
try:
    for line in open("/proc/meminfo"):
        k, v = line.split(":", 1)
        parts = v.split()
        if k in ("MemTotal", "MemFree", "MemAvailable", "Committed_AS", "HugePages_Total", "HugePages_Free", "Hugepagesize", "Cached", "Shmem"):
            mi[k + ("_kB" if len(parts) > 1 else "")] = int(parts[0])
except Exception as exc:
    mi["error"] = repr(exc)
def ssum(key):
    return sum(e.get(key, 0) for e in engines)
print(json.dumps({"t": time.time(), "host": os.uname().nodename, "n_pids": len(engines), "engines": engines, "meminfo": mi,
                  "sum_VmRSS_kB": ssum("VmRSS_kB"), "sum_VmHWM_kB": ssum("VmHWM_kB"), "sum_HugetlbPages_kB": ssum("HugetlbPages_kB"),
                  "unreadable_pids": [e["pid"] for e in engines if e.get("status") == "unreadable"]}))
PY
    ;;
  serving-down)
    # Idle test before stopping engines that could serve somebody: no request line in the rinzler journal for
    # IDLE_MIN minutes and no established TCP connection from another host to an engine or proxy port.
    IDLE_MIN=${IDLE_MIN:-5}
    if [ "$(units_active)" = 0 ]; then say "no rinzler@N unit active"; else
      ok=0
      for try in $(seq 1 12); do   # up to 12 min of 60-s polls
        j=$(sudo -n journalctl -u 'rinzler@*' --since "-${IDLE_MIN} min" --no-pager 2>&1) || { say "journalctl failed (${j:0:100}); not touching serving"; sleep 60; continue; }
        traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'Parsing the prompt|response tokens|chat/completions|Request [0-9]+\]') || true
        busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
        # platformd 0.11 probes every engine's ingress port from the host's own address (health_check_external), so peers that are
        # this host's own addresses are not remote users. The peer address (column 4, port stripped, IPv6 brackets stripped) must
        # not be one of this host's own addresses: matched with index() on a space-padded string, not with a regex.
        own=" 127.0.0.1 ::1 $(hostname -I 2>/dev/null | tr '\n' ' ') "
        conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 or sport = :3000 or sport = :3001 or sport = :3002 or sport = :3003 or sport = :80 )' 2>/dev/null | awk -v own="$own" '{ peer=$4; sub(/:[0-9]+$/, "", peer); gsub(/[][]/, "", peer); if (index(own, " " peer " ") == 0) n++ } END { print n + 0 }') || true
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
    # Wait until platformd is idle and every configured engine runs (up to 300 s, then 10 s settle): a config PATCH
    # from the harness while platformd is still 'updating' races the engine lifecycle.
    want=$(engine_count)
    st=
    for _ in $(seq 1 60); do
      # platformd 0.11 has no shared "activity" field: read idle as "every engine settled" (running, degraded or stopped), as the
      # harness's PlatformdHealthChecker.check_activity_idle does
      st=$(curl -s -m 5 $PLATFORMD/api/inference/status | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]; e=r["engines"]; act=r.get("activity") or ("idle" if all(x.get("status") in ("running","degraded","stopped") for x in e) else "settling"); print(act, sum(1 for x in e if x.get("status")=="running"))' 2>/dev/null)
      [ "$st" = "idle ${want:-4}" ] && break
      sleep 5
    done
    sleep 10
    say "units_active=$(units_active) platformd: activity+running='${st:-?}' configured engines=${want:-?} (waited for 'idle $want')"
    ;;
  *) echo "usage: dut.sh installed|preflight|ensure-target|ensure-base VERSION SHA [FILE]|save-base-deb VERSION [FILE]|hwattn-off|hwattn-clear|[VERIFY_HWATTN=set|unset] verify-env|memsnap|lease-free|[IDLE_MIN=n] serving-down|serving-up"; exit 2 ;;
esac
