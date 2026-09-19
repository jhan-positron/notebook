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

Env: OPENAI_HOST, OPENAI_TOKEN, PLATFORMD_PORT, SSH_USER=jhan, SSH_PASS=,
TALOS_STUB_OUT, CI_MIMIC_OUT (result json), CI_MIMIC_MODELS (comma list to
subset/reorder the 12 configs; default = all, harness order), CI_MIMIC_ARM (label).
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
    """Run a helper command on the DUT as SSH_USER; returns (rc, stdout)."""
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", SSH_HOST_ALIAS, cmd], capture_output=True, text=True, timeout=timeout)
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
                  "echo '=== config.env bytes (engine EnvironmentFile, must be 0)'; stat -c %s /opt/positron/user/config.env; "
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
    sel = [m.strip() for m in os.environ.get("CI_MIMIC_MODELS", "").split(",") if m.strip()]
    if sel:
        cfgs = [c for c in perf_mod.configs if c["model"] in sel]
        missing = [m for m in sel if m not in {c["model"] for c in cfgs}]
        if missing:
            raise SystemExit(f"unknown models in CI_MIMIC_MODELS: {missing}")
        perf_mod.configs = cfgs  # test_performance iterates over the module global
    log.info("arm=%s configs=%s", arm, [(c["model"], c["nominal_users"]) for c in perf_mod.configs])
    amx_probe_on = os.environ.get("CI_MIMIC_AMX_PROBE", "0") == "1"
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
              "ssh_user": SSH_USER, "client_host": os.uname().nodename, "configs": [(c["model"], c["nominal_users"]) for c in perf_mod.configs],
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
        record["check"] = {"supported_models": supported, "missing": missing}
        dump()
        return 0

    orig_provision = dut.provision_model

    async def provision_and_snapshot(name, session=None, pay_for_determinism=False, use_speculation='0'):
        t0 = time.time()
        await orig_provision(name, session=session, pay_for_determinism=pay_for_determinism, use_speculation=use_speculation)
        snap = snapshot_layout(f"after-provision:{name}")
        snap["provision_seconds"] = round(time.time() - t0, 1)
        record["snapshots"].append(snap)
        dump()
        # The harness's own post-provision health check only WARNS (inventory.py: "Health check failed,
        # continuing anyway"). Make a wrong engine count a hard error here so perf.py's 3-attempt
        # provisioning loop retries instead of benchmarking on 3 of 4 engines.
        tp = int(name.rsplit("-tp", 1)[1]) if "-tp" in name else 1
        eng = engines_running(snap["text"])
        running = [e for e in (eng or []) if e[1] == "running"]
        if eng is None or len(running) != 8 // tp:
            dut._provisioned_model = None  # force a full re-provision on retry
            raise RuntimeError(f"engine count after provisioning {name}: {eng} (expected {8 // tp} running)")
        # only the pid lines count: the section header itself contains the word "(deleted)" (false alarms in the 13:42 UTC base arm)
        stale = [l for l in snap["text"].splitlines() if re.match(r"^\d+ /\S+ \(deleted\)", l)]
        if stale:
            log.error("an engine still runs a deleted binary after provisioning %s: %s", name, stale)
        if amx_probe_on and name in amx_models:
            record["amx_probes"].append(amx_probe(name, arm))
            dump()

    dut.provision_model = provision_and_snapshot

    orig_benchmark = perf_mod.benchmark_tps

    def benchmark_and_keep(config, raise_for_goal=True):
        r = orig_benchmark(config, raise_for_goal=raise_for_goal)
        record["raw"].append({"model": config.model, "n_users": config.n_users, "n_rounds": config.n_rounds,
                              "ttfts_ms": [float(x) for x in (r.ttfts or [])], "tpss": [float(x) for x in (r.tpss or [])],
                              "prompt_tokens": list(getattr(r, "prompt_tokens", []) or []), "cached_tokens": list(getattr(r, "cached_tokens", []) or []),
                              "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        dump()
        return r

    perf_mod.benchmark_tps = benchmark_and_keep  # perf.py calls the module-level name at benchmark time

    t0 = time.time()
    results = perf_mod.test_performance(dut=dut, sample_type=None, sample_attrs=None, raise_for_goal=False,
                                        continuous_usage=1, use_speculation=os.environ.get("SYSTEM_CI_SPECULATION", "0"))
    record["perf_minutes"] = round((time.time() - t0) / 60, 2)
    for r in results:
        d = {k: getattr(r, k, None) for k in ("use_case", "tps_mean", "tps_std_dev", "p05_tps", "min_tps", "ttft_mean", "prefill_mean",
                                              "prompt_tokens", "cache_hit_pct", "context")}
        d["tps_results"] = [float(x) for x in (getattr(r, "tps_results", None) or [])]
        record["results"].append(d)
    record["talos_stub"] = {"samples": talos.session.samples, "descriptions": talos.session.descriptions}
    record["snapshots"].append(snapshot_layout("after"))
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    dump()
    for d in record["results"]:
        log.info("RESULT %s: TPS %.2f (sd %.2f, min %.2f) TTFT %s ms", d["use_case"], d["tps_mean"] or 0, d["tps_std_dev"] or 0, d["min_tps"] or 0, d["ttft_mean"])
    failed = [d["use_case"] for d in record["results"] if not d["tps_results"]]
    if failed:
        log.error("configs without results: %s", failed)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
