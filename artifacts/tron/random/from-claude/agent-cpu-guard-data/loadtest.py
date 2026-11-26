#!/usr/bin/env python3
"""A/B load test for the agent CPU guard.

Each phase starts N busy-loop processes through `/bin/bash -c`, the same way
Claude Code and Codex start a command, with or without BASH_ENV pointing at
the guard. During the phase it reads:

- the container cgroup's cpu.stat (CPU time used) and cpu.pressure (time in
  which every runnable process of the container waited for a CPU), and
- a probe thread that does a fixed small piece of work every 5 ms and records
  how late each round finishes. The probe stands for an interactive tool.

usage: loadtest.py GUARD_PATH OUT_JSON PHASE [PHASE...]
       PHASE = name:guard|noguard|idle:nprocs:seconds
"""
import json
import os
import subprocess
import sys
import threading
import time

CG = "/sys/fs/cgroup"


def counters():
    usage = None
    for line in open(f"{CG}/cpu.stat"):
        k, v = line.split()
        if k == "usage_usec":
            usage = int(v)
    some = full = None
    for line in open(f"{CG}/cpu.pressure"):
        parts = line.split()
        total = int(parts[-1].split("=")[1])
        if parts[0] == "some":
            some = total
        else:
            full = total
    return {"t": time.time(), "usage": usage, "some": some, "full": full}


class Probe(threading.Thread):
    """Fixed work + 5 ms sleep per round; records the wall time per round."""

    def __init__(self):
        super().__init__(daemon=True)
        self.rounds = []
        self.stop = False

    def run(self):
        while not self.stop:
            t0 = time.perf_counter()
            sum(range(20000))          # about 0.3 ms of CPU
            time.sleep(0.005)
            self.rounds.append(time.perf_counter() - t0)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def run_phase(guard, name, mode, nprocs, seconds):
    env = dict(os.environ)
    env.pop("BASH_ENV", None)
    env.pop("AGENT_CPU_GUARD", None)
    if mode == "guard":
        env["BASH_ENV"] = guard
    # One parent bash, as an agent would start it; it starts the busy loops.
    script = (
        f'for i in $(seq {nprocs}); do '
        f'timeout {seconds} bash -c "while :; do :; done" & done; '
        'echo "nproc=$(nproc)"; wait'
    )
    probe = Probe()
    c0 = counters()
    probe.start()
    proc = None
    cpus_seen = []
    if mode != "idle":
        proc = subprocess.Popen(["/bin/bash", "-c", script], env=env,
                                stdout=subprocess.PIPE, text=True,
                                start_new_session=True)
        time.sleep(min(1.5, seconds / 2))
        # Which CPUs do the busy loops (state R, same session) run on now?
        out = subprocess.run(
            ["ps", "-s", str(proc.pid), "-o", "psr=,stat="],
            capture_output=True, text=True).stdout.splitlines()
        cpus_seen = sorted({int(l.split()[0]) for l in out
                            if l.split()[1].startswith("R")})
        nproc_line = proc.stdout.readline().strip()
        proc.wait()
    else:
        nproc_line = ""
        time.sleep(seconds)
    probe.stop = True
    probe.join()
    c1 = counters()
    wall = c1["t"] - c0["t"]
    r = probe.rounds
    return {
        "phase": name, "mode": mode, "nprocs": nprocs, "seconds": seconds,
        "wall_s": round(wall, 2),
        "nproc_seen_by_batch": nproc_line,
        "cpus_running_batch": cpus_seen,
        "cpus_used": round((c1["usage"] - c0["usage"]) / 1e6 / wall, 2),
        "full_stall_pct": round(100 * (c1["full"] - c0["full"]) / 1e6 / wall, 2),
        "some_stall_pct": round(100 * (c1["some"] - c0["some"]) / 1e6 / wall, 2),
        "probe_rounds": len(r),
        "probe_p50_ms": round(1000 * pct(r, 50), 2),
        "probe_p99_ms": round(1000 * pct(r, 99), 2),
        "probe_max_ms": round(1000 * max(r), 2),
        "probe_rounds_over_20ms": sum(1 for x in r if x > 0.020),
        "started": time.strftime("%H:%M:%S", time.localtime(c0["t"])),
    }


def main():
    guard, out = sys.argv[1], sys.argv[2]
    results = []
    for spec in sys.argv[3:]:
        name, mode, nprocs, seconds = spec.split(":")
        res = run_phase(guard, name, mode, int(nprocs), float(seconds))
        results.append(res)
        print(json.dumps(res), flush=True)
        time.sleep(3)   # let the scheduler settle between phases
    json.dump(results, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
