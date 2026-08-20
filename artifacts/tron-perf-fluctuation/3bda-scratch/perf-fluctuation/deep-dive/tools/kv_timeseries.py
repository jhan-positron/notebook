#!/usr/bin/env python3
"""Stream a perf.script file; emit 50ms bins of cycles: total(worker threads), kv-wait, pool-idle."""
import re, sys

hdr = re.compile(r'^(\S+)\s+\d+\s+\[\d+\]\s+([\d.]+):\s+(\d+)\s+cycles')
def main(path, out):
    bins = {}
    t0 = None
    comm = ts = period = None
    is_worker = False
    leaf = None
    has_raj = False
    def flush():
        nonlocal t0
        if ts is None or not is_worker: return
        t = float(ts)
        nonlocal_t0 = t0
        b = int((t - t0) / 0.05)
        e = bins.setdefault(b, [0, 0, 0])
        e[0] += period
        if leaf and ("mwaitx::" in leaf or "readiness_source::wait" in leaf):
            if has_raj:
                e[1] += period
            else:
                e[2] += period
    with open(path, errors="replace") as fh:
        for line in fh:
            m = hdr.match(line)
            if m:
                flush()
                comm, ts_s, per_s = m.group(1), m.group(2), m.group(3)
                if t0 is None: t0 = float(ts_s)
                ts, period = ts_s, int(per_s)
                is_worker = "worker" in comm
                leaf = None; has_raj = False
            elif line.startswith("\t"):
                if leaf is None:
                    leaf = line
                if "run_attention_job" in line:
                    has_raj = True
            elif not line.strip():
                pass
        flush()
    with open(out, "w") as o:
        o.write("bin_s,total_cyc,kv_wait_cyc,other_wait_cyc\n")
        for b in sorted(bins):
            e = bins[b]
            o.write(f"{b*0.05:.2f},{e[0]},{e[1]},{e[2]}\n")
    print("wrote", out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
