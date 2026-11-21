#!/usr/bin/env python3
"""est_chip_time.py - size a run from the script's own command list.

Reads the output of `sh run_asimov.sh --dry-run` (one "+ ..." line per
measurement command) and counts, per command, exactly what latency.c and
bandwidth.c will do: chase hops (warm-up and timed), DUP+LASTB control hops,
chain builds, buffer fills, flush lines, bandwidth bytes (warm-up and timed)
and the launches of the command and of the cmncount helper. Then it turns the
counts into chip seconds with the assumptions listed in ASSUME, every one of
them labelled (est.) or by its measured source. Counts are exact; seconds are
estimates.

A meshmap command (run_map.sh) is counted by the order of work of meshmap.c.
Its counts print on a line of their own. Its classification is counted at the
projected count (5/4 x nodes x lines probes, the count meshmap itself uses to
choose the lines per node). meshmap does not enforce that count: its limit is
time (it stops the walk at twice --max-classify-s).

usage: sh run_asimov.sh --dry-run | python3 est_chip_time.py [--phase F]
"""
import re
import sys

# ---- assumptions (ns per hop, GB/s, ns per launch); the source of each is its comment ----
ASSUME = {
    # core chase, by footprint: run 3 (membench-jibin-004) best rows
    "core_ns": [(32 << 10, 2.0), (128 << 10, 6.1), (192 << 10, 14.0), (2 << 20, 24.1), (8 << 20, 45.1), (1 << 40, 52.2)],
    # CME chase, by footprint: run 3 best rows (cme-latency-dram-*.csv)
    "cme_ns": [(4 << 10, 21.4), (8 << 10, 24.2), (16 << 10, 31.6), (64 << 10, 47.6), (256 << 10, 53.1), (2 << 20, 57.6), (8 << 20, 66.2), (1 << 40, 70.3)],
    "ocm_core_ns": 25.3,  # run 3 dense all-five from CPU 2 (per-region rows 18.5 to 28.5)
    "ocm_cme_ns": 44.7,   # run 3 dense all-five through the CME (per-region rows 35.5 to 38.5)
    "roundtrip_ns": 21.0, # run 3 cme-roundtrip rows (21.004 to 21.006 ns per hop over 30 rows)
    "civac_ns": 7.0,      # run 1 (est. from the OCM write rows)
    "chain_build_ns_per_line": 10.0,  # est.: one random 8 B store per line, three passes
    "fill_ns_per_8B": 0.3,            # est.: 32 GB/s store rate (run 1)
    "core_read_gbps": 10.0, "core_write_gbps": 32.0, "core_copy_gbps": 14.0,  # run 1 beyond L2 (copy est.)
    "cme_read_gbps": 34.5, "cme_write_gbps": 30.0, "cme_copy_gbps": 25.0,     # read: asimov-bench run 4045; write and copy est.
    "launch_ns": 14e6,  # run 1 (est.): process start per command
    "probe_pair_ns": 60.0,   # est.: one DC CIVAC, DSB SY and load of a DRAM-backed line (a probe of meshmap's classification)
    "mesh_read_ns": 7000.0,  # est.: one group read of the mesh counters from a CPU that is not the PMU's CPU (derived from the counter disable times in cmn-counts.csv, 6.5 to 11 us)
    "evictor_ns": 24.0,      # est.: one independent load of meshmap's evictor, costed as a dependent load served by the mesh cache (the upper side: independent loads overlap)
    "call_ns": 21.7,    # derived from run 3's two controls: cme-call (42.7 ns per one-hop call) minus cme-roundtrip (21.0 ns per hop); est. when reused for the bandwidth kernels' entry and exit
}

KIB = 1024


def parse_bytes(s):
    m = re.fullmatch(r"([0-9.]+)([KMG]?)", s)
    v = float(m.group(1))
    return int(v * {"": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30}[m.group(2)])


def ns_by_size(table, size):
    for lim, ns in table:
        if size <= lim:
            return ns
    return table[-1][1]


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def latency_cmd(args):
    cme = "--cme" in args
    sizes = [parse_bytes(x) for x in opt(args, "--sizes").split(",")]
    loads = parse_bytes(opt(args, "--loads", "64K"))
    reps = int(opt(args, "--reps", "3"))
    fresh = int(opt(args, "--fresh", "0"))
    flush = "--flush" in args
    ocm = opt(args, "--mem") == "ocm"
    sparse = "--sparse" in args or "--sparse-vary" in args
    # --seq (a sequential chain) is costed at the random chain's ns per hop: a budgeting assumption (est.), not a proved bound
    r = dict(hops=0, hop_ns=0.0, ctl_hops=0, ctl_calls=0, lines_built=0, fill_8b=0, civac=0)
    if cme:
        r["ctl_hops"] = (1 + reps) * loads + reps * 64  # the cme-roundtrip chain, then 64 one-hop cme-call calls per rep
        r["ctl_calls"] = reps * 64                       # each a complete kernel call (entry and exit), costed at call_ns
    for size in sizes:
        n = size // 4096 if sparse else size // 64  # members per chain
        chains = fresh if fresh else 1
        r["lines_built"] += chains * n
        r["fill_8b"] += size // 8
        hops = 2 * n  # warm-up: chain 0 walked twice
        if fresh:
            hops += (chains - 1) * n
            walks = chains - 1
        else:
            per = n if flush else n * ((loads + n - 1) // n)
            hops += reps * per
            walks = reps
        if flush:
            r["civac"] += walks * (size // 64)  # the flush covers every line of the buffer
        # a --no-thp --no-hugetlb row (4 KiB pages) is costed at the same rate as the hugepage-backed run 3 rows;
        # its translation-miss cost is not modelled, so its time is an estimate with a known omission
        ns = ASSUME["ocm_cme_ns" if cme else "ocm_core_ns"] if ocm else ns_by_size(ASSUME["cme_ns" if cme else "core_ns"], size)
        r["hops"] += hops
        r["hop_ns"] += hops * ns
    return r


def bandwidth_cmd(args):
    cme = "--cme" in args
    threads = int(opt(args, "--threads", "1"))
    size = parse_bytes(opt(args, "--bytes", "1M"))
    passes = int(opt(args, "--passes", "4"))
    reps = int(opt(args, "--reps", "3"))
    kernel = opt(args, "--kernel", "all")
    kernels = ["read", "write", "copy"] if kernel == "all" else [kernel]
    flush_before = "--flush-before" in args
    # an OCM buffer has one segment per 256 KiB region and pass() calls the kernel once per segment
    nseg = -(-size // (256 * KIB)) if opt(args, "--mem") == "ocm" else 1
    r = dict(timed_bytes=0, warm_bytes=0, fill_8b=0, civac=0, calls=0, bw_s=0.0)
    for k in kernels:
        mult = 2 if k == "copy" else 1
        per_pass = size * mult * threads
        r["warm_bytes"] += reps * per_pass
        r["timed_bytes"] += reps * passes * per_pass
        # --asm-passes: the timed passes are one kernel call per rep (the warm-up pass still calls per segment)
        r["calls"] += reps * (1 + (1 if "--asm-passes" in args else passes)) * threads * nseg
        if flush_before:
            r["civac"] += reps * size * threads // 64
        # read-pf4/8/16 and read-2s are costed at the plain read rate (est.): a faster read only shortens them
        key = ("cme_" if cme else "core_") + ("read" if k.startswith("read") or k == "ldr16" else "write" if k in ("write", "str16") else "copy") + "_gbps"
        r["bw_s"] += reps * (passes + 1) * per_pass / (ASSUME[key] * 1e9) / threads * threads
    r["fill_8b"] = size * threads * (2 if "copy" in kernels else 1) // 8
    return r


def meshmap_cmd(args):
    # A cell is one (kind, cpu, node). A cycle is one chase of `lines` loads with what the kind does
    # before it. slc and ocm-evict: a store to every chain line, then the evictor (one load of every
    # other line of the buffer); they warm up, twice as long on the first CPU of each node.
    # ocm-flush and dram-flush: DC CIVAC on every chain line; no warm-up.
    r = dict(map_loads=0, evictor=0, stores=0, probes=0, pairs=0, mesh_reads=0, lines_built=0, fill_8b=0, civac=0, map_ns=0.0)
    if "--selftest" in args:
        return r  # the unit checks: no measurement work
    ncpu = len(opt(args, "--cpus", "2,4,6,8,3,5,7,9").split(","))
    nlast = len(opt(args, "--last-cpus").split(",")) if "--last-cpus" in args else 0
    ids = [int(i) for i in opt(args, "--nodes", "88,160,216,288,344").split(",")]
    nodes = len(ids)
    lines = int(opt(args, "--lines", "2048"))
    reps = int(opt(args, "--reps", "7"))
    warm = int(opt(args, "--warm", "2"))
    perf = "--no-perf" not in args               # --no-perf: no mesh counter, no real probe
    # The two OCM kinds exist only for a node id that has an OCM region (meshmap.c ocm_node).
    ocm_nodes = 0 if "--no-ocm" in args else sum(i in (88, 160, 216, 288, 344) for i in ids)
    buf = (2 << 20) // 64                        # the DRAM buffer is 2 MiB: 32,768 lines

    def kind_cells(n):                           # the cells of one kind that has n nodes
        return (ncpu + nlast) * n

    def kind_cycles(n, evicting):
        if not evicting:
            return kind_cells(n) * reps
        return kind_cells(n) * (warm + reps) + (n * warm if kind_cells(n) else 0)

    cells = kind_cells(nodes)                    # per DRAM kind
    slc_ns = ns_by_size(ASSUME["core_ns"], 2 << 20)  # a load served by the mesh cache: the table's 2 MiB row
    dram_ns = ASSUME["core_ns"][-1][1]               # a load fetched from DRAM: the table's last row
    ocm_ns = ASSUME["ocm_core_ns"]
    kinds = [(True, slc_ns, nodes), (False, dram_ns, nodes), (False, ocm_ns, ocm_nodes), (True, ocm_ns, ocm_nodes)]
    for evicting, ns, n in kinds:
        cycles = kind_cycles(n, evicting)
        r["lines_built"] += kind_cells(n) * reps * lines  # one chain per rep, built before the cell's first cycle
        r["map_loads"] += cycles * lines
        r["map_ns"] += cycles * lines * ns
        if evicting:
            r["stores"] += cycles * lines
            r["evictor"] += cycles * (buf - lines)
            r["map_ns"] += cycles * lines * ns    # a store is costed as a load of its line (est., the upper side)
        else:
            r["civac"] += cycles * lines
    r["stores"] += cells * lines                  # dram-flush stores its lines once more after a cell's last pass
    r["map_ns"] += cells * lines * slc_ns + r["evictor"] * ASSUME["evictor_ns"]
    r["fill_8b"] = buf * 8
    if perf:
        r["probes"] = 5 * nodes * lines // 4      # the projected count; each probe ends with one counter read
        r["pairs"] = r["probes"] * int(opt(args, "--probe-loads", "64"))
        # A bracket reads the counters twice. The ocm-flush cells of --cpus run before the counters
        # are open. One idle row per CPU. 100 more reads: 2 after the open, 65 for the read floor,
        # 1 before the first probe, 1 after each of the first 32 probes (their lines are printed).
        brackets = sum(kind_cycles(n, e) for e, _, n in kinds) - ncpu * ocm_nodes * reps + ncpu + nlast
        r["mesh_reads"] = r["probes"] + 2 * brackets + 100
        r["map_ns"] += r["pairs"] * ASSUME["probe_pair_ns"] + r["mesh_reads"] * ASSUME["mesh_read_ns"]
    # not counted: the two neighbour loads of a probe, retried probes, the first store to the OCM lines,
    # the shuffles of the evictor lists and of the store order, the 32 empty brackets (all small, est.).
    # With the counters read one by one (meshmap's level 3) a read costs about five times more (est.).
    return r


def main():
    phase = opt(sys.argv, "--phase")
    rows = []
    cur_phase = None
    for line in sys.stdin:
        line = line.rstrip("\n")
        m = re.match(r"## ([A-Z0-9])\.", line)
        if m:
            cur_phase = m.group(1)
            continue
        if not line.startswith("+ "):
            continue
        if phase and cur_phase != phase:
            continue
        args = line[2:].split()
        helper = 0
        if args[0] in ("cmn", "cmn0", "cmnq"):
            helper = 1
            args = args[2:]
        elif args[0] == "xp":   # run_followup.sh G6: xp <label> <node ids> <cmd...>
            helper = 1
            args = args[3:]
        prog = args[0].rsplit("/", 1)[-1]
        a = args[1:]
        if prog == "latency":
            r = latency_cmd(a)
            t = (r["hop_ns"] + r["ctl_hops"] * ASSUME["roundtrip_ns"] + r["ctl_calls"] * ASSUME["call_ns"]
                 + r["lines_built"] * ASSUME["chain_build_ns_per_line"]
                 + r["fill_8b"] * ASSUME["fill_ns_per_8B"] + r["civac"] * ASSUME["civac_ns"])
            # not counted: the 32 empty timed brackets per command and the timer reads around each pass (unmeasured)
        elif prog in ("bandwidth", "bandwidth_r2", "bandwidth_r3"):
            r = bandwidth_cmd(a)
            t = (r["bw_s"] * 1e9 + r["fill_8b"] * ASSUME["fill_ns_per_8B"] + r["civac"] * ASSUME["civac_ns"]
                 + (r["calls"] * ASSUME["call_ns"] if "--cme" in a else 0))
        elif prog == "meshmap":
            r = meshmap_cmd(a)
            t = (r["map_ns"] + r["lines_built"] * ASSUME["chain_build_ns_per_line"]
                 + r["fill_8b"] * ASSUME["fill_ns_per_8B"] + r["civac"] * ASSUME["civac_ns"])
        else:
            continue
        r.update(prog=prog, helper=helper, cme="--cme" in a, phase=cur_phase, work_ns=t, line=line)
        rows.append(r)

    def total(key):
        return sum(r.get(key, 0) for r in rows)

    launches = len(rows) + total("helper")
    work = total("work_ns")
    launch = launches * ASSUME["launch_ns"]
    print(f"commands: {len(rows)}  helper launches: {total('helper')}  launches: {launches}")
    print(f"chase hops: {total('hops'):,}  control hops: {total('ctl_hops'):,} (of which one-hop control calls: {total('ctl_calls'):,})  lines built: {total('lines_built'):,}")
    print(f"bandwidth timed bytes: {total('timed_bytes'):,}  warm-up bytes: {total('warm_bytes'):,}  kernel calls: {total('calls'):,}")
    print(f"DC CIVAC lines: {total('civac'):,}  fill 8 B stores: {total('fill_8b'):,}")
    if any(r["prog"] == "meshmap" for r in rows):
        print(f"meshmap: chase loads: {total('map_loads'):,}  evictor loads: {total('evictor'):,}  stores: {total('stores'):,}  "
              f"probes: {total('probes'):,}  flush-and-load pairs: {total('pairs'):,}  mesh counter reads: {total('mesh_reads'):,}")
    print(f"work (est.): {work / 1e9:.3f} s   launches at {ASSUME['launch_ns'] / 1e6:.0f} ms (est.): {launch / 1e9:.3f} s   total (est.): {(work + launch) / 1e9:.3f} s")
    print()
    print("per command (est. ms of work, launches):")
    for r in rows:
        print(f"  {r['work_ns'] / 1e6:8.1f} ms  {1 + r['helper']}  {r['line'][2:][:150]}")


if __name__ == "__main__":
    main()
