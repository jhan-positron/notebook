#!/usr/bin/env python3
"""Run the nightly System CI perf phase (scripts/perf.py test_performance) against
delphi-3bda exactly as system_ci does: the harness itself provisions every config
through platformd (legacy posadm path: TRON_USE_SPECULATION patch, models.load with
tp -> 8//tp engines), waits for the engines and the Caddy upstreams, then runs
testlib.tps.benchmark_tps through the proxy at $OPENAI_HOST.

Deviations from `uv run system_ci` (each recorded in the result JSON):
  * only the perf phase (no functional / MMLU Pro / soak);
  * ssh to the DUT as $SSH_USER (jhan, key auth) instead of positron/password:
    posadm.RemoteContext is patched to that user and its login() (ssh-copy-id to
    the positron account) is a no-op. Every command the harness runs on the DUT
    (curl to platformd on localhost:8080, systemctl is-enabled, posadm info,
    curl to Caddy metrics) works for a plain user;
  * talos is the recording stub (nothing is written to the CI database or Slack);
  * after each provisioning the platformd instance env files are snapshotted
    (sudo cat /etc/rinzler/instance-*.env) as evidence of the engine layout;
  * optional AMX-busy probe (CI_MIMIC_AMX_PROBE=1) before the benchmark of the
    models listed in CI_MIMIC_AMX_MODELS: 20 s of `perf stat` on the engine pids
    while 4 short streaming requests run. Runs BEFORE benchmark_tps, so it does
    not touch the measured rounds.

  * l8b-levers campaign (2026-09-19): CI_MIMIC_CONFIGS_JSON replaces the harness's
    config list with the dict list of that file (users x prompt-length grid of one
    model); every raw record carries the config name, prompt_length, wall time,
    the per-engine request counts read from the rinzler FUSE stats before and
    after the benchmark (prompts_total per instance = the Caddy spread) and the
    number of anomalous-sample lines; after every provisioning the engine pids
    must map the installed rinzler binary (sha256 from CI_MIMIC_INSTALLED_SHA or
    the snapshot's own line) and none may run a deleted one, otherwise the pass
    STOPS with rc 7 (a same-model pass after a package switch would otherwise
    benchmark the previous arm's binary).

  * q4b-swattn campaign (2026-09-19, copied from exec/l8b-levers-20260919): with
    CI_MIMIC_REQUIRE_HWATTN0=1 every engine pid must show USE_HW_ATTN=0 in its
    /proc/PID/environ after provisioning (software attention forced through
    /opt/positron/user/config.env), otherwise the pass STOPS with rc 8; every
    snapshot also records rinzler's FUSE config limits max_prompt_tokens and
    max_total_tokens per instance (/var/run/rinzler/N/rinzler/config/), and
    every raw record carries the last limits and the environment verdict.

  * q4b-fpga campaign (2026-09-21, copied from exec/q4b-swattn-20260919): platformd 0.11.0 (explicit named engines
    default-0..3 with per-engine ingress; the harness's auto mode picks the explicit provisioner and creates the test
    proxy "default" on port 80). New knob CI_MIMIC_REQUIRE_HWATTN_UNSET=1: for FPGA-attention arms NO engine pid may
    carry USE_HW_ATTN=0 (rc 8 otherwise); CI_MIMIC_REQUIRE_HWATTN0=1 keeps the CPU-attention meaning (every pid exactly 1).

Env: OPENAI_HOST, OPENAI_TOKEN, PLATFORMD_PORT, SSH_USER=jhan, SSH_PASS=,
TALOS_STUB_OUT, CI_MIMIC_OUT (result json), CI_MIMIC_MODELS (comma list to
subset/reorder the 12 configs; default = all, harness order), CI_MIMIC_ARM (label),
CI_MIMIC_CONFIGS_JSON (config dict list; CI_MIMIC_MODELS is then ignored),
CI_MIMIC_INSTALLED_SHA (sha256 of /opt/positron/bin/rinzler the pass must run).
Exit codes: 0 all configs have results; 2 some config has none; 7 stopped (stale binary); 8 stopped (an engine without
USE_HW_ATTN=0); 9 stopped (the CI lease became busy: checked before every provisioning and every cell when CI_MIMIC_LEASE_CHECK=1).
PYTHONPATH: this dir's talos_stub first, the systems_test checkout second.
"""
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
                    datefmt="%d/%b/%Y %H:%M:%S UTC")
logging.Formatter.converter = time.gmtime
logging.getLogger('asyncssh').setLevel(logging.WARNING)
log = logging.getLogger("ci_mimic")

import asyncssh  # noqa: E402
import posadm.context as posadm_context  # noqa: E402

SSH_USER = os.environ.get("SSH_USER", "jhan")
SSH_HOST_ALIAS = os.environ.get("CI_MIMIC_SSH_ALIAS", "delphi-3bda")  # ~/.ssh/config alias for helper commands


# --- posadm: ssh as SSH_USER with key auth, never touch the positron account ---
async def _connect_as_user(self):
    if self._conn is None:
        options = asyncssh.SSHClientConnectionOptions(username=SSH_USER, known_hosts=None)
        self._conn = await asyncssh.connect(self.host, options=options)
    return self._conn


async def _login_noop(self, password=''):
    return None


posadm_context.RemoteContext._connect = _connect_as_user
posadm_context.RemoteContext.login = _login_noop

from testlib.inventory import Andoria  # noqa: E402
from scripts import perf as perf_mod  # noqa: E402
import talos  # noqa: E402  (the recording stub)


def ssh(cmd, timeout=120):
    """Run a helper command on the DUT as SSH_USER; returns (rc, stdout+stderr). Never raises: a hung or failed ssh
    returns rc -1 and the error text, so a bookkeeping read cannot fail a benchmark (review 2026-09-19 C15/C27)."""
    try:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", SSH_HOST_ALIAS, cmd], capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        log.warning("ssh helper failed: %r (cmd %.80s)", exc, cmd)
        return -1, f"ssh failed: {exc!r}"
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def versions_via_ssh():
    """Same parsing as Andoria.get_versions(), over a subprocess ssh so no asyncio loop is involved."""
    rc, out = ssh("/opt/positron/bin/posadm info", timeout=120)
    versions, started = {}, False
    for line in out.splitlines():
        if started:
            fields = line.split(":")
            if fields[0].strip():
                versions[fields[0].strip()] = ":".join(fields[1:]).strip()
        elif "=Positron Software Versions=" in line:
            started = True
    return versions


def snapshot_layout(tag):
    rc, out = ssh("for f in /etc/rinzler/instance-*.env; do echo \"=== $f\"; sudo -n cat $f | grep -v '^#'; done; "
                  "echo '=== engines'; curl -s -m 5 localhost:8080/api/inference/status | python3 -c 'import json,sys; "
                  "r=json.load(sys.stdin)[\"results\"]; print(json.dumps([(e.get(\"instance\"),e.get(\"status\"),e.get(\"api\",{}).get(\"port\")) for e in r[\"engines\"]]))'; "
                  "echo '=== caddy'; curl -s -m 5 localhost:2019/metrics | grep caddy_reverse_proxy_upstreams_healthy; "
                  "echo '=== rinzler'; sha256sum /opt/positron/bin/rinzler; dpkg -l tron | tail -1; "
                  "echo '=== unit'; grep -c 'num-expert-replicas' /etc/systemd/system/rinzler@.service; "
                  "echo '=== engine env AMX/HW_ATTN vars (must be 0)'; sudo -n grep -c -E 'USE_HW_ATTN|TRON_AMX|TRON_K_VNNI' /etc/rinzler/instance-*.env | tr '\\n' ' '; echo; "
                  "echo '=== pids and binaries they run (a \"(deleted)\" exe = old binary still serving)'; "
                  "for p in $(pgrep -x rinzler); do echo \"$p $(sudo -n readlink /proc/$p/exe) $(sudo -n sha256sum /proc/$p/exe 2>/dev/null | cut -c1-16)\"; done; "
                  "echo '=== hugepages (1 GiB) total/free per NUMA node; files'; "
                  "for n in 0 1; do echo \"node$n $(cat /sys/devices/system/node/node$n/hugepages/hugepages-1048576kB/nr_hugepages)/$(cat /sys/devices/system/node/node$n/hugepages/hugepages-1048576kB/free_hugepages)\"; done; ls /dev/hugepages | tr '\\n' ' '; echo; "
                  "echo '=== config.env bytes (engine EnvironmentFile; 0 in production, 14 while this campaign forces USE_HW_ATTN=0)'; stat -c %s /opt/positron/user/config.env; "
                  "echo '=== USE_HW_ATTN=0 lines in each engine environment (hwattn <pid> <count|NA> <environment lines>; count must be 1 each when software attention is forced; NA = environment unreadable)'; "
                  "for p in $(pgrep -x rinzler); do sudo -n cat /proc/$p/environ 2>/dev/null | tr '\\0' '\\n' | awk -v p=$p 'BEGIN{c=0;n=0} {n++; if ($0==\"USE_HW_ATTN=0\") c++} END{print \"hwattn\", p, (n==0 ? \"NA\" : c), n}'; done; "
                  "echo '=== rinzler FUSE config limits per instance (fuse <i> <max_prompt_tokens> <max_total_tokens>; NA = unreadable within 5 s)'; "
                  "for i in 0 1 2 3; do echo \"fuse $i $(timeout -k 2 5 cat /var/run/rinzler/$i/rinzler/config/max_prompt_tokens 2>/dev/null || echo NA) $(timeout -k 2 5 cat /var/run/rinzler/$i/rinzler/config/max_total_tokens 2>/dev/null || echo NA)\"; done; "
                  "echo '=== intel speed select (CLOS policy the 13-night reference ran under)'; sudo -n /usr/local/sbin/intel-speed-select-state verify 2>&1 | tail -6; "
                  "echo '=== load'; uptime")
    try:  # host-wide CPU pressure seen from this container (the CI runner is an idle VM; this host was saturated 13:40-15:00 UTC 2026-09-18)
        psi = open("/proc/pressure/cpu").read().split("\n")[0]
    except Exception:
        psi = None
    return {"tag": tag, "t": time.time(), "rc": rc, "text": out, "client_load": os.getloadavg(), "client_cpu_psi": psi}


def engines_running(snapshot_text):
    """Parse the '=== engines' line of a snapshot: list of (instance, status, port)."""
    import ast
    for i, line in enumerate(snapshot_text.splitlines()):
        if line.strip() == "=== engines":
            try:
                return ast.literal_eval(snapshot_text.splitlines()[i + 1].strip())
            except Exception:
                return None
    return None


def client_path_timing(n=20):
    """Client -> Caddy timings the nightly's TTFT also contains: DNS lookup, TCP connect, full GET of /v1/models."""
    url = os.environ["OPENAI_HOST"].rstrip("/") + "/models"
    rows = []
    for _ in range(n):
        p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{time_namelookup} %{time_connect} %{time_total}", url], capture_output=True, text=True, timeout=20)
        try:
            rows.append([float(x) * 1000 for x in p.stdout.split()])
        except ValueError:
            pass
    if not rows:
        return None
    med = lambda k: sorted(r[k] for r in rows)[len(rows) // 2]
    return {"n": len(rows), "namelookup_ms_median": round(med(0), 3), "connect_ms_median": round(med(1), 3), "total_ms_median": round(med(2), 3),
            "total_ms_max": round(max(r[2] for r in rows), 3)}


class StopPass(BaseException):
    """Raised (not an Exception, so perf.py's retry loops do not swallow it) when the engines do not run the
    installed binary after provisioning (exit code 7) or lack USE_HW_ATTN=0 (exit code 8); main() returns .code."""

    def __init__(self, msg, code=7):
        super().__init__(msg)
        self.code = code


def hwattn_check(snapshot_text):
    """Parse the 'hwattn <pid> <count|NA> [<environment lines>]' lines of a snapshot: (ok, {pid: count or "NA"}); ok = at
    least one pid and every count == 1 (exactly one USE_HW_ATTN=0 line in that engine's environment). "NA" = the
    environment could not be read (pid gone between pgrep and cat, sudo failure, zombie): not a missing key."""
    counts = {}
    for l in snapshot_text.splitlines():
        m = re.match(r"^hwattn (\d+) (\d+|NA)(?: (\d+))?\s*$", l)
        if m:
            counts[int(m.group(1))] = "NA" if m.group(2) == "NA" else int(m.group(2))
    return (bool(counts) and all(v == 1 for v in counts.values())), counts


def lease_busy():
    """True when the CI lease is busy (dut.sh lease-free says 'busy', rc 1). An ssh failure is NOT busy (no new stop path for
    hiccups). Enabled by CI_MIMIC_LEASE_CHECK=1 with the helper path in CI_MIMIC_DUT_HELPER (plan 2a: lease busy mid-run = stop)."""
    helper = os.environ.get("CI_MIMIC_DUT_HELPER")
    if not helper or os.environ.get("CI_MIMIC_LEASE_CHECK", "0") != "1":
        return False
    rc, out = ssh(f"bash {helper} lease-free", timeout=120)
    return rc == 1 and "busy" in out


def fuse_limits(snapshot_text):
    """Parse the 'fuse <i> <max_prompt_tokens> <max_total_tokens>' lines: {instance: {limit: int|None}}."""
    out = {}
    for l in snapshot_text.splitlines():
        m = re.match(r"^fuse (\d) (\S+) (\S+)\s*$", l)
        if m:
            vals = []
            for v in (m.group(2), m.group(3)):
                try:
                    vals.append(int(v))
                except ValueError:
                    vals.append(None)
            out[int(m.group(1))] = {"max_prompt_tokens": vals[0], "max_total_tokens": vals[1]}
    return out


FUSE_STATS = ("prompts_total", "concurrent_requests", "monitor/active/sessions",
              "monitor/cumulative/completed_sessions", "monitor/cumulative/anomalous_sessions", "monitor/cumulative/abandoned_sessions",
              "monitor/cumulative/processing_errors", "monitor/cumulative/tokens_prompted", "monitor/cumulative/tokens_prompted_cached",
              "monitor/cumulative/tokens_generated",
              # 2026-09-22: the card-side K/V allocator (bytes over the whole card) and the count of 1024-token shards that fell back to
              # CPU attention because the card had no room (tron: "HBM bypass space exhausted"); per device of a tp2 engine (0 and 1).
              # The 2026-09-21 passes hit this in the warm cells from prompt 4096 up (2,804 journal warnings) without recording it.
              "devices/0/allocator/free_total", "devices/0/allocator/free_max", "devices/1/allocator/free_total", "devices/1/allocator/free_max",
              "memory_pressure/hbm/0/sw_fallback_total", "memory_pressure/hbm/1/sw_fallback_total")


def engine_counters(tag):
    """Per-instance rinzler FUSE stats (/var/run/rinzler/N/rinzler/stats/...). prompts_total = requests admitted since
    the process started (resets on restart); read before and after a benchmark its delta is the per-engine request
    count, i.e. how Caddy spread the users. Returns {"tag", "t", "rc", "counters": {instance: {stat: int|None}}, "raw"}."""
    cmd = "for i in 0 1 2 3; do for s in " + " ".join(FUSE_STATS) + "; do printf '%s %s %s\\n' $i $s \"$(cat /var/run/rinzler/$i/rinzler/stats/$s 2>/dev/null | head -c 40 | tr -d '\\n' || echo NA)\"; done; done"
    rc, out = ssh(cmd, timeout=60)
    counters = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit():
            val = parts[2] if len(parts) > 2 else None
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = None
            counters.setdefault(int(parts[0]), {})[parts[1]] = val
    return {"tag": tag, "t": time.time(), "rc": rc, "counters": counters, "raw": out[-2000:]}


def counter_delta(before, after, stat="prompts_total"):
    """after - before per instance; None where either side is missing or the counter went backwards (a restart)."""
    d = {}
    for i in sorted(set(before.get("counters", {})) | set(after.get("counters", {}))):
        b = before.get("counters", {}).get(i, {}).get(stat)
        a = after.get("counters", {}).get(i, {}).get(stat)
        d[i] = (a - b) if (a is not None and b is not None and a >= b) else None
    return d


def binary_check(snapshot_text, installed_sha):
    """Parse the snapshot's pid lines ('<pid> <exe path> [(deleted)] [<sha256 prefix 16>]') and the '=== rinzler'
    sha256sum line. Returns (ok, detail dict)."""
    lines = snapshot_text.splitlines()
    snap_sha = None
    for i, l in enumerate(lines):
        if l.strip() == "=== rinzler" and i + 1 < len(lines):
            m = re.match(r"^([0-9a-f]{64})\s", lines[i + 1])
            snap_sha = m.group(1) if m else None
    want = (installed_sha or snap_sha or "")[:16]
    pids, bad = [], []
    for l in lines:
        m = re.match(r"^(\d+) (\S+)( \(deleted\))?(?: ([0-9a-f]{16}))?\s*$", l)
        if not m:
            continue
        pid, exe, deleted, sha16 = m.group(1), m.group(2), bool(m.group(3)), m.group(4)
        pids.append((pid, exe, deleted, sha16))
        if deleted or not want or sha16 != want:
            bad.append(l)
    detail = {"installed_sha_env": installed_sha, "snapshot_sha": snap_sha, "want16": want, "pids": pids, "bad": bad,
              "env_matches_snapshot": (installed_sha is None or snap_sha is None or installed_sha == snap_sha)}
    ok = bool(pids) and not bad and detail["env_matches_snapshot"]
    return ok, detail


def caddy_health_events(t0, t1):
    """Number of Caddy health-checker journal lines between two epoch times (an engine dropped from the proxy
    pool during a config moves users to the other engines; review K4). None when the read failed."""
    rc, out = ssh(f"sudo -n journalctl -u caddy --since @{int(t0)} --until @{int(t1) + 1} --no-pager -o cat 2>/dev/null | grep -c health_checker", timeout=60)
    try:
        return int(out.strip().splitlines()[-1]) if rc in (0, 1) else None   # grep -c exits 1 when the count is 0
    except (ValueError, IndexError):
        return None


def amx_probe(model, tag):
    """20 s of EXE.AMX_BUSY (raw event 0xb7 umask 0x02) on every rinzler pid while 4 short
    streaming requests run through the proxy. Returns the parsed count (cycles) or None."""
    import openai
    client = openai.OpenAI(base_url=os.environ["OPENAI_HOST"], api_key=os.environ.get("OPENAI_TOKEN", "token-secret"))
    stop = threading.Event()

    def worker(i):
        prompt = ("Write a long, detailed essay about the history of the Roman Empire. " * 60)[:6000]
        while not stop.is_set():
            try:
                s = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                                   max_tokens=256, stream=True, extra_body={"ignore_eos": True})
                for _ in s:
                    if stop.is_set():
                        break
            except Exception as exc:
                log.warning("amx probe request failed: %s", exc)
                time.sleep(1)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(4)]
    for t in threads:
        t.start()
    time.sleep(3)
    rc, out = ssh("pids=$(pgrep -x rinzler | paste -sd,); echo pids=$pids; "
                  "sudo -n perf stat -x, -e cpu/event=0xb7,umask=0x02,name=amx_busy/ -p $pids -- sleep 20 2>&1", timeout=90)
    stop.set()
    for t in threads:
        t.join(timeout=30)
    count = None
    for line in out.splitlines():
        if "amx_busy" in line:
            try:
                count = int(line.split(",")[0])
            except ValueError:
                pass
    log.info("AMX probe %s (%s): amx_busy=%s raw=%r", model, tag, count, out.strip()[:300])
    return {"tag": tag, "model": model, "amx_busy_cycles": count, "raw": out, "t": time.time()}


def main():
    arm = os.environ.get("CI_MIMIC_ARM", "arm")
    out_path = os.environ["CI_MIMIC_OUT"]
    cfg_path = os.environ.get("CI_MIMIC_CONFIGS_JSON")
    sel = [m.strip() for m in os.environ.get("CI_MIMIC_MODELS", "").split(",") if m.strip()]
    if cfg_path:
        with open(cfg_path) as f:
            cfgs = json.load(f)
        need = ("name", "model", "nominal_users", "shared_prompt_length", "prompt_length", "generate_length", "start_capture", "end_capture")
        for c in cfgs:
            missing = [k for k in need if k not in c]
            if missing:
                raise SystemExit(f"config {c.get('name')} lacks keys {missing}")
        names = [c["name"] for c in cfgs]
        if len(set(names)) != len(names):
            raise SystemExit(f"config names must be unique (perf.py keys its summary by name): {names}")
        perf_mod.configs = cfgs
        sel = []  # CI_MIMIC_MODELS is ignored with a configs file
        log.info("configs from %s: %d entries", cfg_path, len(cfgs))
    if sel:
        cfgs = [c for c in perf_mod.configs if c["model"] in sel]
        missing = [m for m in sel if m not in {c["model"] for c in cfgs}]
        if missing:
            raise SystemExit(f"unknown models in CI_MIMIC_MODELS: {missing}")
        perf_mod.configs = cfgs  # test_performance iterates over the module global
    log.info("arm=%s configs=%s", arm, [(c["name"], c["nominal_users"], c["prompt_length"]) for c in perf_mod.configs])
    installed_sha = os.environ.get("CI_MIMIC_INSTALLED_SHA") or None
    amx_probe_on = os.environ.get("CI_MIMIC_AMX_PROBE", "0") == "1"
    require_hwattn0 = os.environ.get("CI_MIMIC_REQUIRE_HWATTN0", "0") == "1"
    require_hwattn_unset = os.environ.get("CI_MIMIC_REQUIRE_HWATTN_UNSET", "0") == "1"
    if require_hwattn0 and require_hwattn_unset:
        raise SystemExit("CI_MIMIC_REQUIRE_HWATTN0 and CI_MIMIC_REQUIRE_HWATTN_UNSET cannot both be 1")
    amx_models = [m.strip() for m in os.environ.get("CI_MIMIC_AMX_MODELS", "llama-3.1-8b-instruct-good-tp2,ingested-qwen-3-4b-instruct-2507-tp2").split(",")]

    dut = Andoria.from_env()
    dut.user = SSH_USER
    dut.password = os.environ.get("SSH_PASS", "")
    if not dut.password:
        # asyncssh: no password -> public-key auth only (our ~/.ssh key)
        async def connect_keys(self=dut):
            if self.conn is None:
                self.conn = await asyncssh.connect(self.hostname, options=asyncssh.SSHClientConnectionOptions(username=SSH_USER, known_hosts=None))
            self.posadm_client = await __import__("posadm").Client.make_remote(self.hostname)
            return self.conn
        dut.connect = connect_keys

    record = {"arm": arm, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "openai_host": os.environ["OPENAI_HOST"],
              "ssh_user": SSH_USER, "client_host": os.uname().nodename,
              "configs": [{"name": c["name"], "model": c["model"], "nominal_users": c["nominal_users"], "prompt_length": c["prompt_length"]} for c in perf_mod.configs],
              "configs_json": cfg_path, "installed_sha_env": installed_sha, "stop": None, "binary_checks": [],
              "require_hwattn0": require_hwattn0, "require_hwattn_unset": require_hwattn_unset, "hwattn_checks": [], "fuse_limits": [],
              "deviations": ["perf phase only", f"ssh as {SSH_USER} (key) instead of positron", "talos recording stub",
                             "client host = " + os.uname().nodename, "layout snapshots after provisioning" + (", AMX probe before selected benchmarks" if amx_probe_on else "")],
              "snapshots": [], "amx_probes": [], "results": [], "versions": None, "env": {k: os.environ.get(k) for k in
              ("OPENAI_HOST", "PLATFORMD_PORT", "SYSTEM_CI_SPECULATION", "STAGGER_DELAY", "CONTINUOUS_USAGE", "MAX_TOKENS", "TPS_GOALS", "PLATFORMD_IDLE_TIMEOUT")}}

    def dump():
        with open(out_path, "w") as f:
            json.dump(record, f, indent=1, default=str)

    # Versions via a plain ssh subprocess, NOT dut.get_versions(): that would open the asyncssh connection in an
    # event loop of ours, and test_performance() then runs dut.provision_model in ITS OWN new loop -> asyncssh
    # raises "Task ... attached to a different loop" (this killed the 13:35 UTC base arm). The harness must be
    # the first to touch dut.conn.
    record["versions"] = versions_via_ssh()
    log.info("DUT versions: %s", record["versions"])
    record["snapshots"].append(snapshot_layout("before"))
    record["client_path_timing"] = client_path_timing()
    log.info("client path timing: %s", record["client_path_timing"])
    record["raw"] = []  # per config: every per-request TTFT/TPS/prompt/cached token count (PerfResult keeps only ttft_mean)
    dump()
    if os.environ.get("CI_MIMIC_CHECK") == "1":
        # read-only connectivity check: ssh + posadm context + platformd GETs, no provisioning (own loop is fine here)
        loop = asyncio.new_event_loop()
        supported = loop.run_until_complete(dut.get_supported_models())
        log.info("CHECK ok: %d supported models, capabilities=%s, layout snapshot %d bytes",
                 len(supported), sorted(dut.posadm_client.ctx.platformd_capabilities), len(record["snapshots"][0]["text"]))
        missing = [c["model"] for c in perf_mod.configs if "-".join(c["model"].split("-")[:-1]) not in supported]
        log.info("CHECK configs not in supported list: %s", missing)
        ctr = engine_counters("check")
        ok, detail = binary_check(record["snapshots"][0]["text"], installed_sha)
        log.info("CHECK engine counters rc=%s prompts_total=%s; binary check ok=%s bad=%s want16=%s",
                 ctr["rc"], {i: v.get("prompts_total") for i, v in ctr["counters"].items()}, ok, detail["bad"], detail["want16"])
        che = caddy_health_events(time.time() - 3600, time.time())
        log.info("CHECK caddy health events in the last hour: %s", che)
        hw_ok, hw_counts = hwattn_check(record["snapshots"][0]["text"])
        log.info("CHECK USE_HW_ATTN=0 per engine pid: ok=%s counts=%s; FUSE limits: %s", hw_ok, hw_counts, fuse_limits(record["snapshots"][0]["text"]))
        record["check"] = {"supported_models": supported, "missing": missing, "engine_counters": ctr, "binary_check": detail, "caddy_health_events_last_hour": che,
                           "hwattn": {"ok": hw_ok, "counts": hw_counts}, "fuse_limits": fuse_limits(record["snapshots"][0]["text"])}
        dump()
        return 0

    orig_provision = dut.provision_model
    count_failures = {"n": 0}   # consecutive wrong-engine-count results; a same-model provision cannot repair them

    async def provision_and_snapshot(name, session=None, pay_for_determinism=False, use_speculation='0'):
        t0 = time.time()
        if lease_busy():
            msg = f"STOP: CI lease busy before provisioning {name} (plan 2a)"
            log.error(msg)
            record["stop"] = msg
            dump()
            raise StopPass(msg, 9)
        try:
            await orig_provision(name, session=session, pay_for_determinism=pay_for_determinism, use_speculation=use_speculation)
        except (asyncssh.Error, OSError, ConnectionError) as exc:
            # a dropped asyncssh connection is never repaired by the harness itself (review K3): reset so the retry reconnects
            log.warning("provisioning hit a connection error %r; resetting the DUT ssh connection for the retry", exc)
            dut.conn = None
            dut.posadm_client = None
            raise
        snap = snapshot_layout(f"after-provision:{name}")
        if snap.get("rc") != 0:   # an ssh failure is not an engine problem: retry the read once, then let perf.py retry (D7)
            log.warning("layout snapshot ssh failed (rc %s); retrying the read in 15 s", snap.get("rc"))
            time.sleep(15)
            snap = snapshot_layout(f"after-provision:{name}")
        snap["provision_seconds"] = round(time.time() - t0, 1)
        record["snapshots"].append(snap)
        dump()
        if snap.get("rc") != 0:
            raise RuntimeError(f"layout snapshot ssh failed twice (rc {snap.get('rc')}): {snap.get('text', '')[:200]}; provisioning retried")
        # The harness's own post-provision health check only WARNS (inventory.py: "Health check failed,
        # continuing anyway"). Make a wrong engine count a hard error here so perf.py's 3-attempt
        # provisioning loop retries instead of benchmarking on 3 of 4 engines.
        tp = int(name.rsplit("-tp", 1)[1]) if "-tp" in name else 1
        eng = engines_running(snap["text"])
        running = [e for e in (eng or []) if e[1] == "running"]
        if eng is None or len(running) != 8 // tp:
            dut._provisioned_model = None  # force a full re-provision on retry
            count_failures["n"] += 1
            if count_failures["n"] >= 2:
                # verified 2026-09-19: the legacy posadm path never restarts a same-model engine, so retrying cannot bring
                # a missing engine back; stop the pass so campaign.sh restarts the engines and repeats (review K3)
                msg = f"STOP: engine count wrong {count_failures['n']} times in a row after provisioning {name}: {eng} (expected {8 // tp} running); not repairable by re-provision"
                log.error(msg)
                record["stop"] = msg
                dump()
                raise StopPass(msg)
            raise RuntimeError(f"engine count after provisioning {name}: {eng} (expected {8 // tp} running)")
        count_failures["n"] = 0
        # every engine pid must map the installed binary (no "(deleted)" exe, sha256 prefix == the installed one);
        # only the pid lines count: the section header itself contains the word "(deleted)"
        ok, detail = binary_check(snap["text"], installed_sha)
        detail.update({"model": name, "t": time.time()})
        record["binary_checks"].append(detail)
        dump()
        if not ok:
            msg = f"STOP: engines do not run the installed rinzler after provisioning {name}: bad={detail['bad']} pids={detail['pids']} want16={detail['want16']} env_matches_snapshot={detail['env_matches_snapshot']}"
            log.error(msg)
            record["stop"] = msg
            dump()
            raise StopPass(msg, 7)
        # software attention forced on both arms (q4b-swattn plan 2a): every engine pid must carry USE_HW_ATTN=0
        hw_ok, hw_counts = hwattn_check(snap["text"])
        if (require_hwattn0 or require_hwattn_unset) and any(v == "NA" for v in hw_counts.values()):
            # an unreadable environment is not a missing key: read again once (pid gone between pgrep and cat, sudo hiccup)
            log.warning("USE_HW_ATTN=0 check: environment unreadable for %s; re-reading the snapshot in 10 s", [p for p, v in hw_counts.items() if v == "NA"])
            time.sleep(10)
            snap2 = snapshot_layout(f"after-provision-reread:{name}")
            record["snapshots"].append(snap2)
            if snap2.get("rc") == 0:
                hw_ok, hw_counts = hwattn_check(snap2["text"])
        hw_unset_ok = bool(hw_counts) and all(v == 0 for v in hw_counts.values())   # FPGA-attention arms: no engine carries the key
        record["hwattn_checks"].append({"model": name, "t": time.time(), "ok": hw_ok, "unset_ok": hw_unset_ok, "counts": hw_counts,
                                        "required": require_hwattn0, "required_unset": require_hwattn_unset})
        record["fuse_limits"].append({"model": name, "t": time.time(), "limits": fuse_limits(snap["text"])})
        dump()
        log.info("USE_HW_ATTN=0 per engine pid after provisioning %s: ok=%s unset_ok=%s counts=%s (required0=%s required_unset=%s); FUSE limits %s",
                 name, hw_ok, hw_unset_ok, hw_counts, require_hwattn0, require_hwattn_unset, record["fuse_limits"][-1]["limits"])
        if require_hwattn0 and not hw_ok:
            msg = f"STOP: engines without USE_HW_ATTN=0 after provisioning {name}: counts={hw_counts} (every running rinzler must show exactly 1)"
            log.error(msg)
            record["stop"] = msg
            dump()
            raise StopPass(msg, 8)
        if require_hwattn_unset and not hw_unset_ok:
            msg = f"STOP: an engine carries USE_HW_ATTN=0 after provisioning {name} in an FPGA-attention arm: counts={hw_counts} (every running rinzler must show 0)"
            log.error(msg)
            record["stop"] = msg
            dump()
            raise StopPass(msg, 8)
        if amx_probe_on and name in amx_models:
            record["amx_probes"].append(amx_probe(name, arm))
            dump()

    dut.provision_model = provision_and_snapshot

    orig_benchmark = perf_mod.benchmark_tps

    def config_name(config):
        hits = [c["name"] for c in perf_mod.configs
                if c["model"] == config.model and c["nominal_users"] == config.n_users and c["prompt_length"] == config.prompt_length]
        return hits[0] if len(hits) == 1 else None

    def benchmark_and_keep(config, raise_for_goal=True):
        name = config_name(config)
        if lease_busy():
            msg = f"STOP: CI lease busy before the cell {name} (plan 2a)"
            log.error(msg)
            record["stop"] = msg
            dump()
            raise StopPass(msg, 9)
        before = engine_counters(f"before:{name}")
        n_samples0 = len(talos.session.samples)   # the harness's per-request samples reach this process through the queue
        t_start = time.time()
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            r = orig_benchmark(config, raise_for_goal=raise_for_goal)
        finally:
            t_end = time.time()
            wall = t_end - t_start
            after = engine_counters(f"after:{name}")
            new_samples = talos.session.samples[n_samples0:]
            # the same condition tps.py uses for its 'anomalous tps=' log line (that line is printed in the worker
            # process; the sample itself is recorded here in the parent; review C1/C14/C16)
            anomalous = sum(1 for s_ in new_samples if s_.get("type") == "tps" and (s_.get("tps") or 0) > 1000)
            record["raw"].append({"name": name, "model": config.model, "n_users": config.n_users, "n_rounds": config.n_rounds,
                                  "prompt_length": config.prompt_length, "generate_length": config.generate_length,
                                  "started": started, "t_start": t_start, "t_end": t_end, "wall_seconds": round(wall, 1),
                                  "engine_counters_before": before, "engine_counters_after": after,
                                  "engine_requests": counter_delta(before, after, "prompts_total"),
                                  "engine_completed_sessions": counter_delta(before, after, "monitor/cumulative/completed_sessions"),
                                  "engine_tokens_generated": counter_delta(before, after, "monitor/cumulative/tokens_generated"),
                                  "hbm_sw_fallback_dev0": counter_delta(before, after, "memory_pressure/hbm/0/sw_fallback_total"),
                                  "hbm_sw_fallback_dev1": counter_delta(before, after, "memory_pressure/hbm/1/sw_fallback_total"),
                                  "hbm_free_total_after": {i: v.get("devices/0/allocator/free_total") for i, v in after.get("counters", {}).items()},
                                  "anomalous_samples": anomalous, "tps_samples_seen": sum(1 for s_ in new_samples if s_.get("type") == "tps"),
                                  "caddy_health_events": caddy_health_events(t_start, t_end),
                                  "amx_busy_cycles": (record["amx_probes"][-1].get("amx_busy_cycles") if record["amx_probes"] else None),
                                  "binary_check_ok": ((not record["binary_checks"][-1].get("bad")) if record["binary_checks"] else None),
                                  "hwattn_ok": (record["hwattn_checks"][-1].get("ok") if record["hwattn_checks"] else None),
                                  "hwattn_unset_ok": (record["hwattn_checks"][-1].get("unset_ok") if record["hwattn_checks"] else None),
                                  "fuse_limits": (record["fuse_limits"][-1].get("limits") if record["fuse_limits"] else None)})
        rec = record["raw"][-1]
        rec.update({"ttfts_ms": [float(x) for x in (r.ttfts or [])], "tpss": [float(x) for x in (r.tpss or [])],
                    "prompt_tokens": list(getattr(r, "prompt_tokens", []) or []), "cached_tokens": list(getattr(r, "cached_tokens", []) or []),
                    "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        dump()
        log.info("CONFIG DONE %s users=%d prompt=%d wall=%.1fs engine_requests=%s anomalous_samples=%d caddy_health_events=%s amx_busy=%s",
                 name, config.n_users, config.prompt_length, wall, rec["engine_requests"], rec["anomalous_samples"], rec["caddy_health_events"], rec["amx_busy_cycles"])
        return r

    perf_mod.benchmark_tps = benchmark_and_keep  # perf.py calls the module-level name at benchmark time

    t0 = time.time()
    try:
        results = perf_mod.test_performance(dut=dut, sample_type=None, sample_attrs=None, raise_for_goal=False,
                                            continuous_usage=1, use_speculation=os.environ.get("SYSTEM_CI_SPECULATION", "0"))
    except StopPass as stop:
        record["perf_minutes"] = round((time.time() - t0) / 60, 2)
        record["snapshots"].append(snapshot_layout("after-stop"))
        record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        dump()
        log.error("pass stopped (rc %d): %s", getattr(stop, "code", 7), stop)
        return getattr(stop, "code", 7)
    record["perf_minutes"] = round((time.time() - t0) / 60, 2)
    def name_of(ctx):
        ctx = ctx or {}
        hits = [c["name"] for c in perf_mod.configs if c["model"] == ctx.get("model") and c["nominal_users"] == ctx.get("nominal_users")
                and c["prompt_length"] == ctx.get("prompt_length")]
        return hits[0] if len(hits) == 1 else "unknown:" + str(ctx).replace(" ", "")

    for r in results:
        d = {k: getattr(r, k, None) for k in ("use_case", "tps_mean", "tps_std_dev", "p05_tps", "min_tps", "ttft_mean", "prefill_mean",
                                              "prompt_tokens", "cache_hit_pct", "context")}
        d["tps_results"] = [float(x) for x in (getattr(r, "tps_results", None) or [])]
        d["name"] = name_of(d["context"])
        record["results"].append(d)
    record["talos_stub"] = {"samples": talos.session.samples, "descriptions": talos.session.descriptions}
    record["snapshots"].append(snapshot_layout("after"))
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    dump()
    for d in record["results"]:
        log.info("RESULT %s (%s): TPS %.2f (sd %.2f, min %.2f) TTFT %s ms", d["name"], d["use_case"], d["tps_mean"] or 0, d["tps_std_dev"] or 0, d["min_tps"] or 0, d["ttft_mean"])
    failed = [d["name"] for d in record["results"] if not d["tps_results"]]
    if failed:
        log.error("configs without results: %s", failed)
        log.error("FAILED_CONFIGS %s", ",".join(failed))   # parsed by campaign.sh (names, no spaces)
        return 2
    return 0


if __name__ == "__main__":
    try:
        rc_ = main()
    except SystemExit as exc:
        rc_ = exc.code if isinstance(exc.code, int) else 1
    except BaseException:  # noqa: BLE001  a crash must still give a clean rc 1 and a Traceback in driver.log
        log.exception("driver crashed")
        rc_ = 1
    # After a failed cell the harness leaves worker processes blocked on their queues; the interpreter's exit hook would
    # then wait for them until GNU timeout kills the group (review C2/C17). Kill them and leave without the hook.
    import multiprocessing
    for p_ in multiprocessing.active_children():
        try:
            p_.kill()
        except Exception:
            pass
    logging.shutdown()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc_)
