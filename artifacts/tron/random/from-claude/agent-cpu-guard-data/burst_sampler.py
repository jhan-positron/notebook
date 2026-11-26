#!/usr/bin/env python3
"""Sample CPU use of the container every 100 ms and name who makes bursts.

Per interval it records the CPU time the whole container used (cpu.stat).
For intervals above BURST_MS it also records, per process, the CPU time of
the process itself and of children that exited in the interval (cutime and
cstime in /proc/PID/stat), so short-lived children are attributed to the
process that started them.

usage: burst_sampler.py SECONDS OUT_JSON
"""
import json
import os
import sys
import time

TICK = os.sysconf("SC_CLK_TCK")
BURST_MS = 150
CG = "/sys/fs/cgroup"


def cg_usage():
    for line in open(f"{CG}/cpu.stat"):
        k, v = line.split()
        if k == "usage_usec":
            return int(v)


def cg_full():
    for line in open(f"{CG}/cpu.pressure"):
        p = line.split()
        if p[0] == "full":
            return int(p[-1].split("=")[1])


def scan():
    d = {}
    for e in os.scandir("/proc"):
        if not e.name.isdigit():
            continue
        try:
            s = open(f"/proc/{e.name}/stat").read()
        except OSError:
            continue
        r = s.rindex(")")
        comm = s[s.index("(") + 1:r]
        f = s[r + 2:].split()
        # f[0]=state f[1]=ppid ... utime=f[11] stime=f[12] cutime=f[13] cstime=f[14]
        d[int(e.name)] = (comm, int(f[1]), int(f[11]) + int(f[12]),
                          int(f[13]) + int(f[14]))
    return d


def aff(pid):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("Cpus_allowed_list"):
                return line.split()[1]
    except OSError:
        pass
    return "?"


def cmdline(pid):
    try:
        return open(f"/proc/{pid}/cmdline").read().replace("\0", " ")[:160]
    except OSError:
        return ""


def main():
    seconds, out = float(sys.argv[1]), sys.argv[2]
    me = os.getpid()
    intervals = []
    bursts = []
    prev = scan()
    u0, t0, f0 = cg_usage(), time.perf_counter(), cg_full()
    end = t0 + seconds
    nxt = t0 + 0.1
    while time.perf_counter() < end:
        time.sleep(max(0, nxt - time.perf_counter()))
        nxt += 0.1
        cur = scan()
        u1, t1, f1 = cg_usage(), time.perf_counter(), cg_full()
        wall_ms = (t1 - t0) * 1000
        used_ms = (u1 - u0) / 1000
        intervals.append((round(wall_ms, 1), round(used_ms, 1),
                          round((f1 - f0) / 1000, 1)))
        if used_ms > BURST_MS:
            rows = []
            for pid, (comm, ppid, own, kids) in cur.items():
                if pid == me:
                    continue
                p = prev.get(pid)
                d_own = (own - p[2]) if p else own
                d_kids = (kids - p[3]) if p else kids
                if d_own + d_kids > 0:
                    rows.append((1000 * (d_own + d_kids) / TICK, pid, comm,
                                 ppid, 1000 * d_own / TICK,
                                 1000 * d_kids / TICK))
            rows.sort(reverse=True)
            top = [{"ms": round(r[0]), "pid": r[1], "comm": r[2],
                    "ppid": r[3], "own_ms": round(r[4]),
                    "kids_ms": round(r[5]),
                    "pcomm": cur.get(r[3], ("?",))[0],
                    "aff": aff(r[1]),
                    "cmd": cmdline(r[1])} for r in rows[:8]]
            bursts.append({"t": time.strftime("%H:%M:%S"),
                           "wall_ms": round(wall_ms, 1),
                           "used_ms": round(used_ms, 1),
                           "stall_ms": round((f1 - f0) / 1000, 1),
                           "top": top})
        prev, u0, t0, f0 = cur, u1, t1, f1
    json.dump({"intervals": intervals, "bursts": bursts}, open(out, "w"))
    used = sorted(i[1] for i in intervals)
    n = len(used)
    print(f"intervals={n} mean_used_ms={sum(used)/n:.1f} "
          f"p50={used[n//2]:.0f} p90={used[int(.9*n)]:.0f} "
          f"p99={used[int(.99*n)]:.0f} max={used[-1]:.0f}")
    for thr in (100, 200, 300, 400, 500, 600, 800):
        k = sum(1 for x in used if x > thr)
        print(f"  intervals using more than {thr} ms: {k} ({100*k/n:.1f}%)")
    stall = sum(i[2] for i in intervals)
    wall = sum(i[0] for i in intervals)
    print(f"full stall: {stall:.0f} ms of {wall:.0f} ms ({100*stall/wall:.2f}%)")


if __name__ == "__main__":
    main()
