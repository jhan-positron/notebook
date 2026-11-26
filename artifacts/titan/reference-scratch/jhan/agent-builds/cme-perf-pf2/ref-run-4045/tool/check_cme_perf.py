#!/usr/bin/env python3
"""Check a CME bench boot from its UART log and print E7, E9 and E3.

    check_cme_perf.py UART_LOG [--rows palladium|decode|gdn|gdn-il|isa|pf|fvp|fvp-gdn|fvp-gdn-il|fvp-isa|fvp-pf|
                                       fvp-pf-spm]
    check_cme_perf.py --selftest

Reads the CME,* records of init.sh and cme_perf. PASS needs, for every row of the row set
(rows.sh): CME,rowrc rc=0, a CME,s record per CPU, CME,chk ok=1 where the row asks for a check
rep, end_ok=1 for every chase, and n > 0 for every decode thread beside a chase; then CME,done.
The numbers come from the medians of the CME,s records: E3 from the palladium row set, E7 and E9
from the decode row set, all of them and the mix from the gdn row set (not from the fvp sets):
  E3  = ns per hop of the OCM chase minus ns per hop of the CME L1 chase, idle and loaded
  E7  = (median ticks at 13 blocks - median ticks at 1 block) / 12, per CPU, in ns and CME cycles
  E9  = CME cycles per block and GB/s from OCM, with RPRFM (e9-pf) and without (e9-nopf)
gdn: each number of the mix rows (mix-13, mix-1) is printed beside its solo row.
gdn-il: E7 on CPU 8 and E9 of gdn_rows (za) beside gdn_rows_il (il), and E7 of il on all five; every
decode record of an il-/f-il- row must say kernel=il, and of the other rows of the set kernel=za.
isa: per-class CME timing (cme_perf isa, ../isa): every test of a timed row's set prints one CME,isa
and the row one CME,isaend; on Palladium (isa) each CME,isa needs ok=1. The event pass runs in rows of
its own after the timed rows (isa-ev-*, cme_perf isa --ev) and is recorded, not gated: its group may
not open, and the timing does not depend on it. On Palladium the ev rows and CME,done are notes, so a
run bound that cuts the ev rows keeps the timed verdict; on the FVP (fvp-isa) the ev row and CME,done
are gated. Prints cycles per instruction, per group, the IPC, where the CME cycles went and the time
of each pass (t0_us, us_n1, us_n2, us_ev).
pf: CME prefetch by memory. E9 decode rows with the state in OCM, SMS (mem=dram) or SPM, each with the
kernel its name says (za, nopf, il) and the memory its name says; the stream rows (cme_perf stream) print
one CME,st per CPU and RPRFM distance, each with ok=1 (every call's XOR equals its lap's) and the row's
memory. Prints E9 per CPU and memory with RPRFM on and off, and the stream's GB/s and CME cycles per
64 B line per distance.
Prints one line per check and per number, then "cme-perf: PASS" (exit 0) or "cme-perf: FAIL"
(exit 1).
"""
import argparse
import re
import sys

A5 = [0, 2, 4, 6, 8]
ROWS = {
    "palladium": {
        "e3-l1": ("chase", [0], False), "e3-ocm": ("chase", [0], False),
        "e3-l3": ("chase", [0], False), "e3-ocm-loaded": ("chase", [1], False),
    },
    "decode": {
        "e7-13-cpu0": ("decode", [0], True), "e7-1-cpu0": ("decode", [0], False),
        "e7-13-all": ("decode", [0, 2, 4, 6, 8], True), "e7-1-all": ("decode", [0, 2, 4, 6, 8], False),
        "sve-13-cpu0": ("decode", [0], True), "sve-1-cpu0": ("decode", [0], False),
        "e9-pf": ("decode", [0, 4], True), "e9-nopf": ("decode", [0, 4], True),
    },
    "gdn": {
        "e3-l1": ("chase", [0], False), "e3-ocm": ("chase", [0], False), "e3-l3": ("chase", [0], False),
        "e3-l1-1536": ("chase", [1], False), "e3-ocm-w0": ("chase", [1], False),
        "e7-13-cpu8": ("decode", [8], True), "e7-1-cpu8": ("decode", [8], False),
        "e7-13-all": ("decode", [0, 2, 4, 6, 8], True), "e7-1-all": ("decode", [0, 2, 4, 6, 8], False),
        "e9-pf": ("decode", [0, 2, 4, 6, 8], True), "e9-nopf": ("decode", [0, 2, 4, 6, 8], True),
        "e9-w0": ("decode", [2, 4, 6], True),
        "mix-13": ("chase", [1, 2, 4, 6, 8], False), "mix-1": ("chase", [1, 2, 4, 6, 8], False),
    },
    "gdn-il": {
        "e7-13-cpu8": ("decode", [8], True), "e7-1-cpu8": ("decode", [8], False),
        "il-e7-13-cpu8": ("decode", [8], True), "il-e7-1-cpu8": ("decode", [8], False),
        "e9-pf": ("decode", [0, 2, 4, 6, 8], True), "il-e9-pf": ("decode", [0, 2, 4, 6, 8], True),
        "il-e7-13-all": ("decode", [0, 2, 4, 6, 8], True), "il-e7-1-all": ("decode", [0, 2, 4, 6, 8], False),
    },
    "pf": {
        "e9-sms-pf": ("decode", A5, True), "e9-sms-nopf": ("decode", A5, True),
        "st-sms": ("stream", [8], False), "st-sms-all": ("stream", A5, False),
        "il-e9-sms-pf": ("decode", A5, True),
        "e9-ocm-pf": ("decode", A5, True), "e9-ocm-nopf": ("decode", A5, True), "st-ocm": ("stream", [8], False),
        "e9-spm-pf": ("decode", A5, True), "e9-spm-nopf": ("decode", A5, True),
        "il-e9-spm-pf": ("decode", A5, True), "st-spm": ("stream", [8], False),
    },
    "fvp-pf": {
        "f-e9-sms-pf": ("decode", A5, True), "f-e9-sms-nopf": ("decode", A5, True),
        "f-il-e9-sms-pf": ("decode", A5, True),
        "f-st-sms": ("stream", [8], False), "f-st-sms-all": ("stream", A5, False),
    },
    "fvp-pf-spm": {"f-st-spm": ("stream", [8], False), "f-e9-spm-pf": ("decode", A5, True)},
    "isa": {"isa-tp": ("isa", [8], False), "isa-lat": ("isa", [8], False), "isa-feed": ("isa", [8], False)},
    "fvp-isa": {"f-isa-all": ("isa", [8], False), "f-isa-ev-all": ("isa-ev", [8], False)},
    "fvp-gdn-il": {
        "f-e7-13-cpu8": ("decode", [8], True), "f-il-e7-13-cpu8": ("decode", [8], True),
        "f-il-e9-flush": ("decode", [0, 2, 4, 6, 8], True), "f-il-e7-1-all": ("decode", [0, 2, 4, 6, 8], False),
    },
    "fvp-gdn": {
        "f-e3-l1-1536": ("chase", [1], False), "f-e3-w0shape": ("chase", [1], False),
        "f-e7-13-cpu8": ("decode", [8], True), "f-e7-1-all": ("decode", [0, 2, 4, 6, 8], False),
        "f-e9-flush": ("decode", [0, 2, 4, 6, 8], True), "f-mix": ("chase", [1, 2, 4, 6, 8], False),
    },
    "fvp": {
        "f-za": ("decode", [0], True), "f-nopf": ("decode", [0], True), "f-sve": ("decode", [0], True),
        "f-all": ("decode", [0, 2, 4, 6, 8], False),
        "f-chase-l1": ("chase", [0], False), "f-chase-l3": ("chase", [0], False),
        "f-chase-ocmshape": ("chase", [0], False), "f-chase-loaded": ("chase", [1], False),
    },
}
# The rows of the gdn-il sets that run gdn_rows_il: their decode records must say kernel=il (and the
# other decode rows of those sets kernel=za), so a wrong kernel cannot pass as the other one.
# The pf sets also tell the GDN_NO_RPRFM rows apart (kernel=nopf).
def kernel_of_row(rowset, name):
    if rowset not in ("gdn-il", "fvp-gdn-il", "pf", "fvp-pf", "fvp-pf-spm"):
        return None
    if ROWS[rowset][name][0] != "decode":
        return None
    return "il" if name.startswith(("il-", "f-il-")) else "nopf" if "nopf" in name else "za"


# pf: the memory of each row (CME,s mem= of a decode row, CME,st mem= of a stream row; SMS is mem=dram)
# and the RPRFM distances of each stream row (rows.sh PFL).
PFL = [0, 1024, 2048, 4096, 16384]
STREAM_PF = {"st-ocm": PFL, "st-sms": PFL, "st-spm": PFL, "st-sms-all": [0, 4096], "f-st-sms": PFL,
             "f-st-sms-all": [0, 4096], "f-st-spm": [0, 4096]}


def mem_of_row(name):
    for tag, mem in (("-ocm", "ocm"), ("-sms", "dram"), ("-spm", "spm")):
        if tag in name:
            return mem
    return None


# The tests of each `cme_perf isa` set, in run order (../isa/gen_isa.py TESTS; the selftest compares).
ISA_SETS = {
    "tp": ["ld1h_x2s", "ld1h_x4s", "ld1h_x4", "st1h_x2", "st1h_x2b", "fcvtn", "fdot", "fmlal", "fadd", "fmopa", "mova_zh",
           "mova_zv", "mova_za", "add_x"],
    "lat": ["fadd_chain", "fcvtn_chain", "fdot_chain", "fmlal_chain", "fmopa_chain", "za_roundtrip", "ld_fdot_dep",
            "ld_fdot_ind", "fcvtn_fdot_dep", "fcvtn_fdot_ind", "mova_fcvtn_dep", "mova_fcvtn_ind"],
    "feed": ["feed_dp_ls", "feed_dp_sve", "feed2", "feed3", "feed4"],
}
ISA_ROW_SET = {"isa-tp": "tp", "isa-lat": "lat", "isa-feed": "feed", "f-isa-all": "all",
               "isa-ev-tp": "tp", "isa-ev-lat": "lat", "isa-ev-feed": "feed", "f-isa-ev-all": "all"}
# The event-pass rows of each timed isa row, run after all the timed rows (rows.sh).
ISA_EV_ROW = {"isa-tp": "isa-ev-tp", "isa-lat": "isa-ev-lat", "isa-feed": "isa-ev-feed", "f-isa-all": "f-isa-ev-all"}


def isa_want(name):
    st = ISA_ROW_SET[name]
    return [t for k in ("tp", "lat", "feed") if st in (k, "all") for t in ISA_SETS[k]]


# The loaded chases: each load CPU must print CME,load with at least one gdn_rows call.
LOAD = {"e3-ocm-loaded": [2, 6], "f-chase-loaded": [2, 6]}
REC = re.compile(r"CME,([a-z]+)(?:,(.*))?$")


def kv(s):
    d = {}
    for part in s.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            d[k] = v
    return d


def parse(lines):
    """Records grouped by row: {name: {"rc": int, "s": [..], "chk": [..]}}, and done."""
    rows, cur, done = {}, None, False
    for line in lines:
        m = REC.search(line.rstrip("\r\n"))
        if not m:
            continue
        kind, rest = m.group(1), m.group(2) or ""
        d = kv(rest)
        if kind == "row":
            cur = d.get("name")
            rows[cur] = {"rc": None, "s": [], "chk": [], "load": [], "fatal": [], "isa": [], "isaev": [], "isaend": [],
                         "st": []}
        elif kind == "rowrc" and d.get("name") in rows:
            rows[d["name"]]["rc"] = int(d.get("rc", "-1"))
        elif kind in ("s", "chk", "load", "isa", "isaev", "isaend", "st") and cur in rows:
            rows[cur][kind].append(d)
        elif kind == "fatal" and cur in rows:
            rows[cur]["fatal"].append(rest)
        elif kind == "done":
            done = True
    return rows, done


def check(lines, rowset, out):
    rows, done = parse(lines)
    ok = True
    passed = set()

    def say(good, text):
        nonlocal ok, row_ok
        ok = ok and bool(good)
        row_ok = row_ok and bool(good)
        out(f"{'ok  ' if good else 'FAIL'} {text}")

    for name, (mode, cpus, chk) in ROWS[rowset].items():
        row_ok = True
        r = rows.get(name)
        if r is None:
            say(False, f"{name}: no CME,row record")
            continue
        say(r["rc"] == 0 and not r["fatal"], f"{name}: rc={r['rc']}" + (f" fatal={r['fatal']}" if r["fatal"] else ""))
        if mode == "isa":
            check_isa_row(name, r, cpus, rowset == "isa", say, rows.get(ISA_EV_ROW[name]))
            if row_ok:
                passed.add(name)
            continue
        if mode == "isa-ev":
            check_isa_ev_row(name, r, cpus, say)
            if row_ok:
                passed.add(name)
            continue
        if mode == "stream":
            check_stream_row(name, r, cpus, say)
            if row_ok:
                passed.add(name)
            continue
        got = sorted(int(s.get("cpu", -1)) for s in r["s"])
        say(got == sorted(cpus), f"{name}: CME,s for CPUs {got} (want {sorted(cpus)})")
        wm = mem_of_row(name) if rowset in ("pf", "fvp-pf", "fvp-pf-spm") else None
        if wm:
            ms = sorted({s.get("mem") for s in r["s"]})
            say(ms == [wm], f"{name}: mem {ms} (want ['{wm}'])")
        kw = kernel_of_row(rowset, name)
        if kw:
            ks = sorted({s.get("kernel") for s in r["s"]} | {c.get("kernel") for c in r["chk"]})
            say(ks == [kw], f"{name}: kernel {ks} (want ['{kw}'])")
        if chk:
            c = r["chk"]
            say(len(c) == 1 and c[0].get("ok") == "1",
                f"{name}: check rep " + (f"ok={c[0].get('ok')} state_diff={c[0].get('state_diff')} o_diff={c[0].get('o_diff')}" if c else "missing"))
        if mode == "chase":
            ch = [s for s in r["s"] if s.get("mode") == "chase"]
            say(len(ch) == 1 and ch[0].get("end_ok") == "1", f"{name}: chase end line")
            dec = [s for s in r["s"] if s.get("mode") == "decode"]
            if dec:
                idle = sorted(int(s.get("cpu", -1)) for s in dec if int(s.get("n", "0")) < 1)
                say(not idle, f"{name}: timed calls on every decode CPU beside the chase" + (f" (none on {idle})" if idle else ""))
        if name in LOAD:
            busy = sorted(int(x.get("cpu", -1)) for x in r["load"] if int(x.get("calls", "0")) > 0)
            say(busy == LOAD[name], f"{name}: CME,load with calls > 0 for CPUs {busy} (want {LOAD[name]})")
        if row_ok:
            passed.add(name)
    row_ok = True
    if rowset == "isa":
        for name in ("isa-ev-tp", "isa-ev-lat", "isa-ev-feed"):
            r = rows.get(name)
            n = len(r["isaev"]) if r else 0
            say(True, f"{name}: note: " + ("no CME,row record" if r is None else
                                           f"rc={r['rc']}, CME,isaev for {n} of {len(isa_want(name))} tests"))
        say(True, "CME,done" if done else "note: no CME,done (the run bound came first; the timed rows decide)")
    else:
        say(done, "CME,done")
    if rowset == "palladium":
        numbers_e3(rows, passed, out)
    if rowset == "decode" and ok:
        numbers_decode(rows, out)
    if rowset == "gdn":
        numbers_gdn(rows, passed, out)
    if rowset == "gdn-il":
        numbers_gdn_il(rows, passed, out)
    if rowset == "isa":
        numbers_isa(rows, passed, out)
    if rowset == "pf":
        numbers_pf(rows, passed, out)
    return ok


def check_stream_row(name, r, cpus, say):
    """One CME,st per CPU and distance, each ok=1 (every call's XOR equals its lap's) with n > 0 and the
    row's memory."""
    want = sorted((c, d) for c in cpus for d in STREAM_PF[name])
    got = sorted((int(x.get("cpu", -1)), int(x.get("pf", -1))) for x in r["st"])
    say(got == want, f"{name}: CME,st for (cpu, pf) {got} (want {want})")
    bad = [(x.get("cpu"), x.get("pf")) for x in r["st"] if x.get("ok") != "1" or int(x.get("n", "0")) < 1]
    say(not bad, f"{name}: every lap's XOR, n > 0" + (f" (not for {bad})" if bad else ""))
    wm = mem_of_row(name)
    ms = sorted({x.get("mem") for x in r["st"]})
    say(ms == [wm], f"{name}: mem {ms} (want ['{wm}'])")


def numbers_pf(rows, passed, out):
    """E9 per CPU and memory, RPRFM on (za, il) and off (nopf); the stream per memory and distance.
    "-" where a row did not pass."""
    def get(name, cpu, key, rec="s", pf=None):
        if name not in passed:
            return None
        for x in rows[name][rec]:
            if int(x["cpu"]) == cpu and (pf is None or int(x["pf"]) == pf):
                try:
                    return float(x[key])
                except (KeyError, ValueError):
                    return None
        return None

    f = lambda x, nd=1: "-" if x is None else f"{x:.{nd}f}"
    gain = lambda on, off: "" if on is None or off is None or not off else f" ({100.0 * (on - off) / off:+.1f}%)"
    out("E9 CME cycles per block (GB/s): RPRFM on za | off nopf | on il")
    for mem in ("ocm", "sms", "spm"):
        for c in A5:
            on, off = (get(f"e9-{mem}-pf", c, "cme_cyc_per_block_med"), get(f"e9-{mem}-nopf", c, "cme_cyc_per_block_med"))
            il = get(f"il-e9-{mem}-pf", c, "cme_cyc_per_block_med") if mem != "ocm" else None
            g = lambda n: f(get(n, c, "gbps_med"), 3)
            out(f"E9 {mem} CPU {c}: {f(on)} ({g(f'e9-{mem}-pf')}){gain(on, off)} | {f(off)} ({g(f'e9-{mem}-nopf')})"
                + (f" | {f(il)} ({g(f'il-e9-{mem}-pf')})" if mem != "ocm" else ""))
    for name, c in (("st-ocm", 8), ("st-sms", 8), ("st-spm", 8)) + tuple(("st-sms-all", c) for c in A5):
        cells = []
        for d in STREAM_PF[name]:
            gb = get(name, c, "gbps_med", "st", d)
            cl = get(name, c, "cme_cyc_per_line", "st", d)
            cells.append(f"pf {d}: {f(gb, 3)} GB/s {f(cl, 2)} cyc/line")
        out(f"stream {name} CPU {c}: " + "; ".join(cells))


def check_isa_ev_row(name, r, cpus, say):
    """An event-pass row: CME,isaend, and every CME,isaev on the row's CPU, for the row's tests in order
    (none where the group did not open, as on the FVP)."""
    got = [x.get("test") for x in r["isaev"]]
    want = isa_want(name)
    say(not got or got == want, f"{name}: CME,isaev for {len(got)} tests" + ("" if not got or got == want else
                                                                             f" (want {len(want)} in order)"))
    cpu_ok = all(int(x.get("cpu", -1)) in cpus for x in r["isaev"])
    say(cpu_ok and len(r["isaend"]) == 1 and not r["isa"], f"{name}: CPU {cpus}, CME,isaend and no CME,isa")


def check_isa_row(name, r, cpus, timed, say, evrow=None):
    """One CME,isa per test of the row's set, in order, on the row's CPU, and CME,isaend.
    timed (Palladium): every test ok=1 (its cycles grew with the loop count). The event pass (its own
    row, or this row's CME,isaev in a log from before the split) is a note."""
    want = isa_want(name)
    got = [x.get("test") for x in r["isa"]]
    say(got == want, f"{name}: CME,isa for {len(got)} tests (want {len(want)} in order)"
        + ("" if got == want else f" missing {[t for t in want if t not in got]}"))
    cpu_ok = all(int(x.get("cpu", -1)) in cpus for x in r["isa"] + r["isaev"])
    say(cpu_ok and len(r["isaend"]) == 1, f"{name}: CPU {cpus} and CME,isaend")
    if timed:
        bad = [x.get("test") for x in r["isa"] if x.get("ok") != "1"]
        say(not bad, f"{name}: cycles grew with the loop count" + (f" (not for {bad})" if bad else ""))
        ev = {x.get("test"): x for x in r["isaev"] + (evrow["isaev"] if evrow else [])}
        bad = [t for t in want if ev.get(t, {}).get("full") != "1"]
        if bad:
            say(True, f"{name}: note: event pass missing or multiplexed for {len(bad)} tests "
                f"({'no CME,isaev records' if not ev else bad}); the shares print '-' or are approximate")


def numbers_isa(rows, passed, out):
    """Per test: CME cycles per instruction and per group, the IPC, the unclean reps, and from the event
    pass the share of CME cycles the core sent nothing (fe_cpu) and the issued operations per CME cycle."""
    out("isa test: cyc/op cyc/group IPC | fe_cpu% core_cpubound% issued/cyc (alu mac perm st mmdp mmmv) | unclean"
        " | t0 n1 n2 ev us")
    for name in ("isa-tp", "isa-lat", "isa-feed"):
        if name not in rows:
            continue
        evrow = rows.get(ISA_EV_ROW[name])
        ev = {x.get("test"): x for x in rows[name]["isaev"] + (evrow["isaev"] if evrow else [])}
        for x in rows[name]["isa"]:
            e = ev.get(x.get("test"), {})
            tag = "" if name in passed else " (row FAILED)"
            try:
                cyc = float(e["cme_cyc"])
                keys = ("alu", "mac", "perm", "st", "mmdp", "mmmv")
                issued = sum(float(e[k]) for k in keys)
                shares = (f"{100 * float(e['fe_cpu']) / cyc:.1f} {100 * float(e['core_cpubound']) / cyc:.1f} "
                          f"{issued / cyc:.3f} ({' '.join(f'{float(e[k]) / cyc:.3f}' for k in keys)})")
            except (KeyError, ValueError, ZeroDivisionError):
                shares = "-"
            us = " ".join(str(d.get(k, "-")) for d, k in ((x, "t0_us"), (x, "us_n1"), (x, "us_n2"), (e, "us_ev")))
            out(f"isa {x.get('set')} {x.get('test')}: {x.get('cyc_per_op')} {x.get('cyc_per_group')} {x.get('ipc')} | "
                f"{shares} | {x.get('unclean')} | {us}{tag}")


def med(rows, name, cpu, key="med", mode=None):
    for s in rows[name]["s"]:
        if int(s["cpu"]) == cpu and (mode is None or s.get("mode") == mode):
            return float(s[key])
    raise KeyError((name, cpu))


def numbers_gdn(rows, passed, out):
    """E3, E7 and E9 per row and per CME; each mix number beside its solo row. A number whose rows
    did not all pass prints "-"."""
    def get(name, cpu, key="med", mode=None):
        if name not in passed:
            return None
        try:
            return med(rows, name, cpu, key, mode)
        except (KeyError, ValueError):
            return None

    def sub(a, b, div=1.0):
        return None if a is None or b is None else (a - b) / div

    def f(x, unit="", nd=2):
        return "-" if x is None else f"{x:.{nd}f}{unit}"

    def vs(mix, solo, unit, nd=2):
        if mix is None or solo is None or not solo:
            return f"{f(mix, unit, nd)} (solo {f(solo, unit, nd)})"
        return f"{f(mix, unit, nd)} (solo {f(solo, unit, nd)}, {100.0 * (mix - solo) / solo:+.1f}%)"

    hop = lambda n, c: get(n, c, "ns_per_hop_med", "chase")
    l1, l3, ocm = hop("e3-l1", 0), hop("e3-l3", 0), hop("e3-ocm", 0)
    out(f"E3 hop, 4096 loads per call: L1 {f(l1, ' ns')}, L3 {f(l3, ' ns')}, OCM {f(ocm, ' ns')}; "
        f"E3 (OCM - L1) {f(sub(ocm, l1), ' ns')}")
    l1s, w0 = hop("e3-l1-1536", 1), hop("e3-ocm-w0", 1)
    out(f"E3 hop, 1536 loads per call, CPU 1, window 0 at 160 KiB: L1 {f(l1s, ' ns')}, OCM {f(w0, ' ns')}; "
        f"E3 (OCM - L1) {f(sub(w0, l1s), ' ns')}")
    for m in ("mix-13", "mix-1"):
        h = hop(m, 1)
        out(f"E3 {m} CPU 1: OCM hop {vs(h, w0, ' ns')}; E3 (OCM - L1) {vs(sub(h, l1s), sub(w0, l1s), ' ns')}")

    def e7(n13, n1, c, mode=None):
        return (sub(get(n13, c, mode=mode), get(n1, c, mode=mode), 12.0),
                sub(get(n13, c, "cme_cyc_med", mode), get(n1, c, "cme_cyc_med", mode), 12.0))
    for c in (8,):
        t, k = e7("e7-13-cpu8", "e7-1-cpu8", c)
        out(f"E7 solo CPU {c}: {f(t, ' ticks', 1)} per block, {f(k, ' CME cycles', 1)} per block")
    for c in (0, 2, 4, 6, 8):
        t, k = e7("e7-13-all", "e7-1-all", c)
        out(f"E7 all five, CPU {c}: {f(t, ' ticks', 1)} per block, {f(k, ' CME cycles', 1)} per block")
    t, k = e7("mix-13", "mix-1", 8, "decode")
    ts, ks = e7("e7-13-cpu8", "e7-1-cpu8", 8)
    out(f"E7 mix CPU 8: {vs(t, ts, ' ticks', 1)} per block, {vs(k, ks, ' CME cycles', 1)} per block")

    blk = lambda n, c, mode=None: get(n, c, "cme_cyc_per_block_med", mode)
    gb = lambda n, c, mode=None: get(n, c, "gbps_med", mode)
    for c in (0, 2, 4, 6, 8):
        out(f"E9 home window, CPU {c}: RPRFM on {f(blk('e9-pf', c), ' CME cycles', 1)} per block, "
            f"{f(gb('e9-pf', c), ' GB/s', 3)}; off {f(blk('e9-nopf', c), ' CME cycles', 1)} per block, "
            f"{f(gb('e9-nopf', c), ' GB/s', 3)}")
    for c in (2, 4, 6):
        out(f"E9 window 0, CPU {c}: alone {f(blk('e9-w0', c), ' CME cycles', 1)} per block, "
            f"{f(gb('e9-w0', c), ' GB/s', 3)}")
        for m in ("mix-13", "mix-1"):
            out(f"E9 {m} CPU {c}: {vs(blk(m, c, 'decode'), blk('e9-w0', c), ' CME cycles', 1)} per block, "
                f"{vs(gb(m, c, 'decode'), gb('e9-w0', c), ' GB/s', 3)}")


def numbers_gdn_il(rows, passed, out):
    """E7 and E9 of gdn_rows (za) and gdn_rows_il (il) side by side; "-" where a row did not pass."""
    def get(name, cpu, key="med"):
        if name not in passed:
            return None
        try:
            return med(rows, name, cpu, key)
        except (KeyError, ValueError):
            return None

    def e7(n13, n1, c):
        a, b = get(n13, c, "cme_cyc_med"), get(n1, c, "cme_cyc_med")
        return None if a is None or b is None else (a - b) / 12.0

    f = lambda x, nd=1: "-" if x is None else f"{x:.{nd}f}"

    def ratio(new, old):
        return "" if new is None or old is None or not old else f", {100.0 * (new - old) / old:+.1f}%"

    old, new = e7("e7-13-cpu8", "e7-1-cpu8", 8), e7("il-e7-13-cpu8", "il-e7-1-cpu8", 8)
    out(f"E7 solo CPU 8, CME cycles per block: za {f(old)}, il {f(new)}{ratio(new, old)}")
    for c in (0, 2, 4, 6, 8):
        out(f"E7 il all five, CPU {c}: {f(e7('il-e7-13-all', 'il-e7-1-all', c))} CME cycles per block")
    for c in (0, 2, 4, 6, 8):
        b0, b1 = get("e9-pf", c, "cme_cyc_per_block_med"), get("il-e9-pf", c, "cme_cyc_per_block_med")
        g0, g1 = get("e9-pf", c, "gbps_med"), get("il-e9-pf", c, "gbps_med")
        out(f"E9 home window RPRFM on, CPU {c}: za {f(b0)} CME cycles per block ({f(g0, 3)} GB/s), "
            f"il {f(b1)}{ratio(b1, b0)} ({f(g1, 3)} GB/s)")


def numbers_decode(rows, out):
    for tag, cpus in (("cpu0", [0]), ("all", [0, 2, 4, 6, 8])):
        for c in cpus:
            t13, t1 = med(rows, f"e7-13-{tag}", c), med(rows, f"e7-1-{tag}", c)
            k13, k1 = med(rows, f"e7-13-{tag}", c, "cme_cyc_med"), med(rows, f"e7-1-{tag}", c, "cme_cyc_med")
            out(f"E7 {tag} cpu {c}: {(t13 - t1) / 12:.1f} ticks per block, {(k13 - k1) / 12:.1f} CME cycles per block")
    t13, t1 = med(rows, "sve-13-cpu0", 0), med(rows, "sve-1-cpu0", 0)
    out(f"SSVE2 cpu 0: {(t13 - t1) / 12:.1f} ticks per block")
    for c in (0, 4):
        for name in ("e9-pf", "e9-nopf"):
            out(f"E9 {name} cpu {c}: {med(rows, name, c, 'cme_cyc_per_block_med'):.1f} CME cycles per block, "
                f"{med(rows, name, c, 'gbps_med'):.3f} GB/s")


# E3 from the rows that passed with the E3 shape (4096 loads per call, 64 B lines): any other row, a
# failed one or one of another shape, prints "-" and the others still count.
E3_SHAPE = {"hops": "4096", "stride": "64"}


def numbers_e3(rows, passed, out):
    hop = {}
    for n, c in (("e3-l1", 0), ("e3-l3", 0), ("e3-ocm", 0), ("e3-ocm-loaded", 1)):
        hop[n] = None
        if n not in passed:
            continue
        s = next(x for x in rows[n]["s"] if int(x["cpu"]) == c)
        shape = {k: s.get(k) for k in E3_SHAPE}
        if shape != E3_SHAPE:
            out(f"E3 skips {n}: hops={shape['hops']} stride={shape['stride']} (want hops=4096 stride=64)")
            continue
        hop[n] = float(s["ns_per_hop_med"])
    f = lambda x: "-" if x is None else f"{x:.2f} ns"
    d = lambda x: None if x is None or hop["e3-l1"] is None else x - hop["e3-l1"]
    out(f"E3 hop: L1 {f(hop['e3-l1'])}, L3 {f(hop['e3-l3'])}, OCM idle {f(hop['e3-ocm'])}, "
        f"OCM loaded {f(hop['e3-ocm-loaded'])}")
    out(f"E3 (OCM - L1 hop): idle {f(d(hop['e3-ocm']))}, loaded {f(d(hop['e3-ocm-loaded']))}")


SAMPLE_FVP = """CME,boot,rows=fvp
CME,row,name=f-za,args=decode
CME,s,mode=decode,kernel=za,cpu=0,blocks=13,med=100
CME,chk,mode=decode,kernel=za,cpu=0,state_diff=0,o_diff=0,ok=1
CME,rowrc,name=f-za,rc=0
CME,row,name=f-nopf,args=decode
CME,s,mode=decode,kernel=nopf,cpu=0,blocks=13,med=100
CME,chk,mode=decode,kernel=nopf,cpu=0,state_diff=0,o_diff=0,ok=1
CME,rowrc,name=f-nopf,rc=0
CME,row,name=f-sve,args=decode
CME,s,mode=decode,kernel=sve,cpu=0,blocks=13,med=100
CME,chk,mode=decode,kernel=sve,cpu=0,state_diff=0,o_diff=0,ok=1
CME,rowrc,name=f-sve,rc=0
CME,row,name=f-all,args=decode
CME,s,mode=decode,kernel=za,cpu=0,med=1
CME,s,mode=decode,kernel=za,cpu=2,med=1
CME,s,mode=decode,kernel=za,cpu=4,med=1
CME,s,mode=decode,kernel=za,cpu=6,med=1
CME,s,mode=decode,kernel=za,cpu=8,med=1
CME,rowrc,name=f-all,rc=0
CME,row,name=f-chase-l1,args=chase
CME,s,mode=chase,cpu=0,ns_per_hop_med=1.0,end_ok=1
CME,rowrc,name=f-chase-l1,rc=0
CME,row,name=f-chase-l3,args=chase
CME,s,mode=chase,cpu=0,ns_per_hop_med=1.0,end_ok=1
CME,rowrc,name=f-chase-l3,rc=0
CME,row,name=f-chase-ocmshape,args=chase
CME,s,mode=chase,cpu=0,ns_per_hop_med=1.0,end_ok=1
CME,rowrc,name=f-chase-ocmshape,rc=0
CME,row,name=f-chase-loaded,args=chase
CME,load,cpu=2,kernel=za,blocks=13,mem=dram,slots=8,calls=40
CME,load,cpu=6,kernel=za,blocks=13,mem=dram,slots=8,calls=41
CME,s,mode=chase,cpu=1,ns_per_hop_med=1.0,end_ok=1
CME,rowrc,name=f-chase-loaded,rc=0
CME,done
"""

# The E3 rows in the order of rows.sh (made-up numbers).
SAMPLE_E3 = """CME,boot,rows=palladium
CME,row,name=e3-l1,args=chase
CME,s,mode=chase,cpu=0,stride=64,hops=4096,ns_per_hop_med=2.0,end_ok=1
CME,rowrc,name=e3-l1,rc=0
CME,row,name=e3-ocm,args=chase
CME,s,mode=chase,cpu=0,stride=64,hops=4096,ns_per_hop_med=7.0,end_ok=1
CME,rowrc,name=e3-ocm,rc=0
CME,row,name=e3-l3,args=chase
CME,s,mode=chase,cpu=0,stride=64,hops=4096,ns_per_hop_med=4.0,end_ok=1
CME,rowrc,name=e3-l3,rc=0
CME,row,name=e3-ocm-loaded,args=chase
CME,load,cpu=2,kernel=za,blocks=13,mem=ocm,slots=8,calls=40
CME,load,cpu=6,kernel=za,blocks=13,mem=ocm,slots=8,calls=41
CME,s,mode=chase,cpu=1,stride=64,hops=4096,ns_per_hop_med=9.0,end_ok=1
CME,rowrc,name=e3-ocm-loaded,rc=0
CME,done
"""


def sample_gdn():
    """A gdn log in the order of rows.sh, with made-up numbers."""
    L = ["CME,boot,rows=gdn"]

    def row(name, recs, chk=False):
        L.append(f"CME,row,name={name},up=1.0,args=x")
        L.extend(recs)
        if chk:
            L.append("CME,chk,mode=decode,kernel=za,cpu=0,state_diff=0,o_diff=0,ok=1")
        L.append(f"CME,rowrc,name={name},rc=0,up=1.1")

    ch = lambda c, hops, ns: f"CME,s,mode=chase,cpu={c},stride=64,hops={hops},ns_per_hop_med={ns},end_ok=1"
    dec = lambda c, medv, cyc, blk=0.0, gb=0.0, n=16: (f"CME,s,mode=decode,kernel=za,cpu={c},n={n},med={medv},"
                                                     f"cme_cyc_med={cyc},cme_cyc_per_block_med={blk},gbps_med={gb}")
    row("e3-l1", [ch(0, 4096, 20.0)])
    row("e3-ocm", [ch(0, 4096, 35.0)])
    row("e3-l3", [ch(0, 4096, 26.0)])
    row("e3-l1-1536", [ch(1, 1536, 21.0)])
    row("e3-ocm-w0", [ch(1, 1536, 36.0)])
    row("e7-13-cpu8", [dec(8, 1300, 2600)], True)
    row("e7-1-cpu8", [dec(8, 100, 200)])
    row("e7-13-all", [dec(c, 1300, 2600) for c in (0, 2, 4, 6, 8)], True)
    row("e7-1-all", [dec(c, 100, 200) for c in (0, 2, 4, 6, 8)])
    row("e9-pf", [dec(c, 5000, 10000, 400.0, 10.0) for c in (0, 2, 4, 6, 8)], True)
    row("e9-nopf", [dec(c, 6000, 12000, 500.0, 8.0) for c in (0, 2, 4, 6, 8)], True)
    row("e9-w0", [dec(c, 5000, 10000, 400.0, 10.0) for c in (2, 4, 6)], True)
    for m, blocks in (("mix-13", 13), ("mix-1", 1)):
        e7 = dec(8, 1420, 2840, n=900) if blocks == 13 else dec(8, 100, 200, n=900)
        row(m, [dec(c, 6000, 12000, 500.0, 8.0, n=700) for c in (2, 4, 6)] + [e7, ch(1, 1536, 45.0)])
    L.append("CME,done")
    return L


def sample_gdn_il():
    """A gdn-il log in the order of rows.sh, with made-up numbers."""
    L = ["CME,boot,rows=gdn-il"]

    def row(name, k, cpus, medv, cyc, blk=0.0, gb=0.0, chk=False):
        L.append(f"CME,row,name={name},up=1.0,args=x")
        L.extend(f"CME,s,mode=decode,kernel={k},cpu={c},n=16,med={medv},cme_cyc_med={cyc},"
                 f"cme_cyc_per_block_med={blk},gbps_med={gb}" for c in cpus)
        if chk:
            L.append(f"CME,chk,mode=decode,kernel={k},cpu={cpus[0]},state_diff=5,o_diff=2,ok=1")
        L.append(f"CME,rowrc,name={name},rc=0,up=1.1")

    a5 = [0, 2, 4, 6, 8]
    row("e7-13-cpu8", "za", [8], 2800, 5600, chk=True)
    row("e7-1-cpu8", "za", [8], 400, 800)
    row("il-e7-13-cpu8", "il", [8], 1700, 3400, chk=True)
    row("il-e7-1-cpu8", "il", [8], 300, 520)
    row("e9-pf", "za", a5, 5000, 10000, 500.0, 15.0, chk=True)
    row("il-e9-pf", "il", a5, 4000, 8000, 400.0, 18.0, chk=True)
    row("il-e7-13-all", "il", a5, 1700, 3400, chk=True)
    row("il-e7-1-all", "il", a5, 300, 520)
    L.append("CME,done")
    return L


def sample_isa(rowset="isa", split=True):
    """An isa log in the order of rows.sh, with made-up numbers: 1 cycle per instruction, half of the
    CME cycles waiting on the core. split=False: the shape before the ev rows (each test's CME,isaev in
    its timed row, no timing fields), as GA13 run 4001 printed it."""
    L = [f"CME,boot,rows={rowset}"]
    timed = ["isa-tp", "isa-lat", "isa-feed"] if rowset == "isa" else ["f-isa-all"]
    ev_rows = [ISA_EV_ROW[n] for n in timed] if split else []
    for name in timed + ev_rows:
        L.append(f"CME,row,name={name},up=1.0,args=x")
        for i, t in enumerate(isa_want(name)):
            st = next(k for k, v in ISA_SETS.items() if t in v)
            if not split:
                L.append(f"CME,isa,set={st},test={t},cpu=8,ops=32,group=1,n1=4,n2=132,n=9,cme1_med=300,cme2_med=4396,"
                         f"ok=1,cyc_per_iter=32.00,cyc_per_op=1.000,cyc_per_group=1.000,ipc=1.000,unclean=0,ssve=0")
                L.append(f"CME,isaev,test={t},cpu=8,n2=132,n=9,cme_cyc=4400,fe_cpu=2200,core_cpubound=100,iq_dp0=0,"
                         f"iq_dp1=0,iq_ld=0,alu=4224,mac=0,perm=0,st=0,mmdp=0,mmmv=0,full=1")
            elif name in timed:
                L.append(f"CME,isa,set={st},test={t},cpu=8,group=1,cme1_med=300,cme2_med=4396,cpu2_med=9000,"
                         f"ok=1,cyc_per_op=1.000,cyc_per_group=1.000,ipc=1.000,unclean=0,ssve=0,"
                         f"t0_us={100 * i},us_n1=40,us_n2=60")
            else:
                L.append(f"CME,isaev,test={t},cpu=8,n=9,cme_cyc=4400,fe_cpu=2200,core_cpubound=100,iq_dp0=0,"
                         f"iq_dp1=0,iq_ld=0,alu=4224,mac=0,perm=0,st=0,mmdp=0,mmmv=0,full=1,t0_us={80 * i},us_ev=70")
        L.append(f"CME,isaend,cpu=8,set=x,pass={'timed' if name in timed else 'ev'},disturbed=0,us_row=3000")
        L.append(f"CME,rowrc,name={name},rc=0,up=1.1")
    L.append("CME,done")
    return L


def sample_pf(rowset="pf"):
    """A pf log in the order of rows.sh, with made-up numbers."""
    L = [f"CME,boot,rows={rowset}"]
    for name, (mode, cpus, chk) in ROWS[rowset].items():
        L.append(f"CME,row,name={name},up=1.0,args=x")
        k = kernel_of_row(rowset, name)
        mem = mem_of_row(name)
        if mode == "decode":
            L.extend(f"CME,s,mode=decode,kernel={k},cpu={c},blocks=13,mem={mem},n=16,med=5000,cme_cyc_med=10000,"
                     f"cme_cyc_per_block_med={500.0 if k == 'nopf' else 450.0},gbps_med=10.0" for c in cpus)
            L.append(f"CME,chk,mode=decode,kernel={k},cpu={cpus[0]},state_diff=0,o_diff=0,ok=1")
        else:
            L.extend(f"CME,st,cpu={c},mem={mem},pf={d},lap=262144,n=16,min=9000,med=9000,max=9100,gbps_med=29.127,"
                     f"cme_cyc_med=18000,cpu_cyc_med=18100,cme_cyc_per_line=4.39,ok=1,bad=0,pmu=1,unclean=0,ssve=0"
                     for c in cpus for d in STREAM_PF[name])
            L.extend(f"CME,stend,cpu={c},disturbed=0" for c in cpus)
        L.append(f"CME,rowrc,name={name},rc=0,up=1.1")
    L.append("CME,done")
    return L


def selftest():
    good = SAMPLE_FVP.splitlines()
    cases = [
        ("as recorded", good, True),
        ("no CME,done", [x for x in good if x != "CME,done"], False),
        ("check rep differs", [x.replace("kernel=sve,cpu=0,state_diff=0,o_diff=0,ok=1",
                                         "kernel=sve,cpu=0,state_diff=3,o_diff=0,ok=0") for x in good], False),
        ("chase end line wrong", [x.replace("ns_per_hop_med=1.0,end_ok=1", "ns_per_hop_med=1.0,end_ok=0", 1) for x in good], False),
        ("row rc 124", [x.replace("name=f-all,rc=0", "name=f-all,rc=124") for x in good], False),
        ("one CPU missing", [x for x in good if "cpu=8,med=1" not in x], False),
        ("row missing", [x for x in good if "f-chase-l1" not in x], False),
        ("load CPU idle", [x.replace("cpu=6,kernel=za,blocks=13,mem=dram,slots=8,calls=41",
                                     "cpu=6,kernel=za,blocks=13,mem=dram,slots=8,calls=0") for x in good], False),
        ("console noise", ["[   12.3] random kernel line"] + [f"\r{x}" for x in good], True),
    ]
    bad = 0
    for name, lines, want in cases:
        got = check(lines, "fvp", lambda s: None)
        print(f"{'ok  ' if got == want else 'FAIL'} selftest {name}: verdict {'PASS' if got else 'FAIL'}")
        bad += got != want
    e3 = SAMPLE_E3.splitlines()
    for name, lines, want in (("E3 as recorded", e3, True),
                              ("E3 loaded row missing", [x for x in e3 if "e3-ocm-loaded" not in x], False),
                              ("E3 old shape", [x.replace("stride=64,hops=4096,ns_per_hop_med=7.0",
                                                          "stride=16384,hops=16,ns_per_hop_med=7.0") for x in e3], True)):
        said = []
        got = check(lines, "palladium", said.append)
        idle = "-" if name == "E3 old shape" else "5.00 ns"
        loaded = "7.00 ns" if name != "E3 loaded row missing" else "-"
        good = got == want and f"E3 (OCM - L1 hop): idle {idle}, loaded {loaded}" in said
        print(f"{'ok  ' if good else 'FAIL'} selftest {name}: verdict {'PASS' if got else 'FAIL'}")
        bad += not good
    g = sample_gdn()
    for name, lines, want, need in (
            ("gdn as recorded", g, True, [
                "E3 hop, 4096 loads per call: L1 20.00 ns, L3 26.00 ns, OCM 35.00 ns; E3 (OCM - L1) 15.00 ns",
                "E3 mix-13 CPU 1: OCM hop 45.00 ns (solo 36.00 ns, +25.0%); E3 (OCM - L1) 24.00 ns (solo 15.00 ns, +60.0%)",
                "E7 solo CPU 8: 100.0 ticks per block, 200.0 CME cycles per block",
                "E7 mix CPU 8: 110.0 ticks (solo 100.0 ticks, +10.0%) per block, "
                "220.0 CME cycles (solo 200.0 CME cycles, +10.0%) per block",
                "E9 home window, CPU 4: RPRFM on 400.0 CME cycles per block, 10.000 GB/s; off 500.0 CME cycles per block, 8.000 GB/s",
                "E9 mix-1 CPU 6: 500.0 CME cycles (solo 400.0 CME cycles, +25.0%) per block, "
                "8.000 GB/s (solo 10.000 GB/s, -20.0%)"]),
            ("gdn decode CPU idle in the mix", [x.replace("cpu=4,n=700", "cpu=4,n=0") for x in g], False,
             ["FAIL mix-13: timed calls on every decode CPU beside the chase (none on [4])"]),
            ("gdn mix CPU missing", [x for x in g if not ("cpu=8,n=900" in x and "med=100," in x)], False,
             ["E7 mix CPU 8: - (solo 100.0 ticks) per block, - (solo 200.0 CME cycles) per block"]),
            ("gdn mix chase end wrong", [x.replace("hops=1536,ns_per_hop_med=45.0,end_ok=1", "hops=1536,ns_per_hop_med=45.0,end_ok=0")
                                         for x in g], False, ["FAIL mix-13: chase end line"]),
    ):
        said = []
        got = check(lines, "gdn", said.append)
        miss = [x for x in need if x not in said]
        good = got == want and not miss
        print(f"{'ok  ' if good else 'FAIL'} selftest {name}: verdict {'PASS' if got else 'FAIL'}"
              + (f" missing {miss}" if miss else ""))
        bad += not good
    g = sample_gdn_il()
    for name, lines, want, need in (
            ("gdn-il as recorded", g, True, [
                "E7 solo CPU 8, CME cycles per block: za 400.0, il 240.0, -40.0%",
                "E7 il all five, CPU 4: 240.0 CME cycles per block",
                "E9 home window RPRFM on, CPU 6: za 500.0 CME cycles per block (15.000 GB/s), il 400.0, -20.0% (18.000 GB/s)"]),
            ("gdn-il row ran za", [x.replace("kernel=il,cpu=8,n=16,med=1700", "kernel=za,cpu=8,n=16,med=1700") for x in g], False,
             ["FAIL il-e7-13-cpu8: kernel ['il', 'za'] (want ['il'])",
              "E7 solo CPU 8, CME cycles per block: za 400.0, il -"]),
            ("gdn-il check rep failed", [x.replace("kernel=il,cpu=0,state_diff=5,o_diff=2,ok=1", "kernel=il,cpu=0,state_diff=9,o_diff=2,ok=0", 1)
                                         for x in g], False, ["E9 home window RPRFM on, CPU 0: za 500.0 CME cycles per block (15.000 GB/s), il - (- GB/s)"]),
    ):
        said = []
        got = check(lines, "gdn-il", said.append)
        miss = [x for x in need if x not in said]
        good = got == want and not miss
        print(f"{'ok  ' if good else 'FAIL'} selftest {name}: verdict {'PASS' if got else 'FAIL'}"
              + (f" missing {miss}" if miss else ""))
        bad += not good
    g = sample_isa()
    for name, lines, rowset, want, need in (
            ("isa as recorded", g, "isa", True, ["isa tp fdot: 1.000 1.000 1.000 | 50.0 2.3 0.960 (0.960 0.000 0.000 0.000 0.000 0.000) | 0 | 600 40 60 70",
                                                 "ok   CME,done"]),
            ("isa bound cut the ev rows", g[:next(i for i, x in enumerate(g) if "name=isa-ev-feed" in x)],
             "isa", True, ["ok   isa-ev-feed: note: no CME,row record",
                           "ok   note: no CME,done (the run bound came first; the timed rows decide)",
                           "isa feed feed2: 1.000 1.000 1.000 | - | 0 | 200 40 60 -"]),
            ("isa no CME,done, timed row cut", [x for x in g if x != "CME,done" and "test=feed4" not in x], "isa", False,
             ["FAIL isa-feed: CME,isa for 4 tests (want 5 in order) missing ['feed4']"]),
            ("isa log before the split (run 4001 shape)", sample_isa(split=False), "isa", True,
             ["isa tp fdot: 1.000 1.000 1.000 | 50.0 2.3 0.960 (0.960 0.000 0.000 0.000 0.000 0.000) | 0 | - - - -",
              "ok   isa-ev-tp: note: no CME,row record"]),
            ("isa test missing", [x for x in g if "test=fmopa," not in x], "isa", False,
             ["FAIL isa-tp: CME,isa for 13 tests (want 14 in order) missing ['fmopa']"]),
            ("isa cycles did not grow", [x.replace("test=feed3,cpu=8,group=1,cme1_med=300,cme2_med=4396,cpu2_med=9000,ok=1",
                                                   "test=feed3,cpu=8,group=1,cme1_med=300,cme2_med=300,cpu2_med=9000,ok=0") for x in g],
             "isa", False, ["FAIL isa-feed: cycles grew with the loop count (not for ['feed3'])"]),
            ("isa event pass multiplexed", [x.replace("mmdp=0,mmmv=0,full=1", "mmdp=0,mmmv=0,full=0") if "test=fadd_chain," in x else x
                                            for x in g],
             "isa", True, ["ok   isa-lat: note: event pass missing or multiplexed for 1 tests (['fadd_chain']); the shares print '-' or are approximate"]),
            ("isa without the event group", [x for x in g if not x.startswith("CME,isaev")], "isa", True,
             ["isa tp fdot: 1.000 1.000 1.000 | - | 0 | 600 40 60 -"]),
            ("fvp-isa ok=0 is fine", [x.replace(",ok=1,", ",ok=0,").replace("full=1", "full=0") for x in sample_isa("fvp-isa")],
             "fvp-isa", True, []),
            ("fvp-isa no event group (no CME,isaev)", [x for x in sample_isa("fvp-isa") if not x.startswith("CME,isaev")],
             "fvp-isa", True, ["ok   f-isa-ev-all: CME,isaev for 0 tests"]),
            ("fvp-isa ev row missing", [x for x in sample_isa("fvp-isa") if "f-isa-ev-all" not in x], "fvp-isa", False,
             ["FAIL f-isa-ev-all: no CME,row record"]),
            ("fvp-isa no CME,done", [x for x in sample_isa("fvp-isa") if x != "CME,done"], "fvp-isa", False, ["FAIL CME,done"]),
            ("pf as made", sample_pf(), "pf", True,
             ["E9 sms CPU 4: 450.0 (10.000) (-10.0%) | 500.0 (10.000) | 450.0 (10.000)",
              "stream st-spm CPU 8: pf 0: 29.127 GB/s 4.39 cyc/line; pf 1024: 29.127 GB/s 4.39 cyc/line; "
              "pf 2048: 29.127 GB/s 4.39 cyc/line; pf 4096: 29.127 GB/s 4.39 cyc/line; pf 16384: 29.127 GB/s 4.39 cyc/line"]),
            ("pf stream lap XOR wrong", [x.replace("ok=1,bad=0", "ok=0,bad=3") if x.startswith("CME,st,cpu=8,mem=dram,pf=4096")
                                         else x for x in sample_pf()], "pf", False,
             ["FAIL st-sms: every lap's XOR, n > 0 (not for [('8', '4096')])"]),
            ("pf stream distance missing", [x for x in sample_pf() if not x.startswith("CME,st,cpu=6,mem=dram,pf=4096")],
             "pf", False, []),
            ("pf decode digest differs", [x.replace("kernel=nopf,cpu=0,state_diff=0,o_diff=0,ok=1",
                                                    "kernel=nopf,cpu=0,state_diff=4,o_diff=1,ok=0") for x in sample_pf()],
             "pf", False, []),
            ("pf state in the wrong memory", [x.replace("kernel=za,cpu=2,blocks=13,mem=spm", "kernel=za,cpu=2,blocks=13,mem=dram")
                                              for x in sample_pf()], "pf", False,
             ["FAIL e9-spm-pf: mem ['dram', 'spm'] (want ['spm'])"]),
            ("pf nopf row ran za", [x.replace("kernel=nopf", "kernel=za") if "kernel=nopf,cpu=4,blocks=13,mem=ocm" in x
                                    else x for x in sample_pf()], "pf", False,
             ["FAIL e9-ocm-nopf: kernel ['nopf', 'za'] (want ['nopf'])"]),
            ("pf cut in the SPM rows", sample_pf()[:next(i for i, x in enumerate(sample_pf()) if "name=e9-spm-nopf" in x)],
             "pf", False, ["FAIL e9-spm-nopf: no CME,row record", "FAIL st-spm: no CME,row record", "FAIL CME,done"]),
            ("fvp-pf as made", sample_pf("fvp-pf"), "fvp-pf", True, []),
            ("fvp-pf-spm as made", sample_pf("fvp-pf-spm"), "fvp-pf-spm", True, []),
    ):
        said = []
        got = check(lines, rowset, said.append)
        miss = [x for x in need if x not in said]
        good = got == want and not miss
        print(f"{'ok  ' if good else 'FAIL'} selftest {name}: verdict {'PASS' if got else 'FAIL'}"
              + (f" missing {miss}" if miss else ""))
        bad += not good
    try:    # ISA_SETS matches gen_isa.py's TESTS when the bench sources are next to this file
        import importlib.util
        import pathlib
        gp = pathlib.Path(__file__).resolve().parent.parent / "isa" / "gen_isa.py"
        if gp.exists():
            sys.dont_write_bytecode = True
            spec = importlib.util.spec_from_file_location("gen_isa", gp)
            gen = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gen)
            same = all([t for t, st, _, _ in gen.TESTS if st == k] == v for k, v in ISA_SETS.items()) \
                and sum(map(len, ISA_SETS.values())) == len(gen.TESTS)
            print(f"{'ok  ' if same else 'FAIL'} selftest ISA_SETS == gen_isa.TESTS")
            bad += not same
    except Exception as e:  # noqa: BLE001
        print(f"FAIL selftest ISA_SETS: {e}")
        bad += 1
    print(f"selftest: {'PASS' if not bad else 'FAIL'}")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("log", nargs="?")
    ap.add_argument("--rows", choices=sorted(ROWS), default="palladium")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.log:
        ap.error("UART_LOG is required")
    with open(a.log, errors="replace") as f:
        ok = check(f.readlines(), a.rows, print)
    print(f"cme-perf: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
