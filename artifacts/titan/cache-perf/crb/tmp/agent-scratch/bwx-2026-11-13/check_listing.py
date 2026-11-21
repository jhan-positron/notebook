#!/usr/bin/env python3
"""check_listing.py - acceptance test of a bwx build (handoff.md, B.7).

Runs on the development machine, on the listing.txt that build.sh wrote on CRB.
Usage: check_listing.py [listing.txt] [probe.txt]

Checks, for each of the four binaries bwx, bwx_o0, bwx_o36, bwx_o52 (a binary
that listing.txt lacks is a failure; "--binaries a,b" names another list):
 1. every kernel is present and has a loop;
 2. the loop body equals the reference in probe.txt:
    - read, write, copy, asmread, asmwrite, asmcopy and the A/A copies: the
      loop of the same kernel in "bw_new";
    - oldread, oldread2, oldwrite, oldcopy: the loop of k_read, k_write,
      k_copy in "bw_old";
    - asmcopy_c: the loop of "bw_new k_copy";
    - asmcopy_c_reg: that loop with q31..q16 renamed to q0..q15;
    - asmcopy_c_add: the 8 ldp of that loop, its 8 stp with the offsets 0 to
      224, then its two add, cmp and branch;
    - read_nopN: the loop of "bw_new k_asmread" with N nop before its add;
    - read_sparse: the first 4 ldp of that loop, 9 nop, add of 128, cmp, branch;
 3. the planned loop offsets modulo 64: bwx has copy at 36 and asmcopy,
    asmcopy2, asmcopy_c, asmcopy_c_add, asmcopy_c_reg at 52; bwx_oN has copy,
    asmcopy and asmcopy2 at N;
 4. every A/A copy has its own start address and the loop offset modulo 64 of
    its original.
 5. code outside the loop:
    - read, write, copy, asmread, asmwrite, asmcopy, the A/A copies and the
      old kernels: the whole function equals the function in probe.txt
      (prologue, end computation, epilogue, any second loop);
    - asmcopy_c, asmcopy_c_add, asmcopy_c_reg, read_nopN, read_sparse (no
      listing of them exists in probe.txt): the function has exactly one
      backward branch;
    - every kernel that uses q8 to q15 (asmread, asmread2, read_nopN, asmcopy,
      asmcopy2, asmcopy_c_reg): "stp d8, d9", "stp d10, d11", "stp d12, d13",
      "stp d14, d15" stand before the loop and the four matching ldp after it.
    Check 5 is stricter than handoff B.7, which names the loop bodies only.
    What it does not see: the code outside the loop of the five kernels
    without a listing in probe.txt, apart from the two points above.
The loop of a function is the range from the target of its first backward
branch to that branch. Addresses are not compared: a branch target inside the
function is compared as a distance from the loop start (check 2) or from the
function start (check 5).
Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "..", "..", "..", "results", "kernels-20261113T181222Z", "probe.txt")

KERNELS = ["read", "write", "copy", "asmread", "asmwrite", "asmcopy", "oldread", "oldwrite", "oldcopy",
           "asmread2", "asmwrite2", "asmcopy2", "oldread2", "asmcopy_c", "asmcopy_c_add", "asmcopy_c_reg",
           "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse"]
AA = {"asmread2": "asmread", "asmwrite2": "asmwrite", "asmcopy2": "asmcopy", "oldread2": "oldread"}
# kernel -> (reference binary, reference function) for an unchanged loop
SAME = {"read": ("bw_new", "k_read"), "write": ("bw_new", "k_write"), "copy": ("bw_new", "k_copy"),
        "asmread": ("bw_new", "k_asmread"), "asmwrite": ("bw_new", "k_asmwrite"), "asmcopy": ("bw_new", "k_asmcopy"),
        "asmread2": ("bw_new", "k_asmread"), "asmwrite2": ("bw_new", "k_asmwrite"), "asmcopy2": ("bw_new", "k_asmcopy"),
        "oldread": ("bw_old", "k_read"), "oldread2": ("bw_old", "k_read"),
        "oldwrite": ("bw_old", "k_write"), "oldcopy": ("bw_old", "k_copy"),
        "asmcopy_c": ("bw_new", "k_copy")}


def planned(binary):
    """kernel -> planned loop offset modulo 64, for the kernels that have one"""
    if binary == "bwx":
        return {"copy": 36, "asmcopy": 52, "asmcopy2": 52, "asmcopy_c": 52, "asmcopy_c_add": 52, "asmcopy_c_reg": 52}
    m = re.fullmatch(r"bwx_o(\d+)", binary)
    if m:
        n = int(m.group(1))
        return {"copy": n, "asmcopy": n, "asmcopy2": n}
    return {}


def sections(path):
    """{(binary, name): [(address, text), ...]} from '=== binary name ===' blocks of objdump text"""
    out, cur = {}, None
    with open(path) as f:
        for line in f:
            m = re.match(r"=== (\S+) (\S+) ===", line)
            if m:
                cur = out.setdefault((m.group(1), m.group(2)), [])
                continue
            m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)
            if m and cur is not None:
                text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()
                cur.append((int(m.group(1), 16), text))
            elif line.startswith("##"):
                cur = None
    return out


def loop_of(insns):
    """(loop start address, normalized loop text) or None. The loop ends at the
    first instruction that branches backward to an address inside the function."""
    if not insns:
        return None
    first = insns[0][0]
    for i, (addr, text) in enumerate(insns):
        m = re.search(r"\b([0-9a-f]+) <[^>]+>$", text)
        if not m:
            continue
        tgt = int(m.group(1), 16)
        if first <= tgt < addr:
            body = [t for a, t in insns[:i + 1] if a >= tgt]
            body[-1] = text[:m.start()] + "LOOP"
            return tgt, body
    return None


def backward_branches(insns):
    """number of instructions that branch backward to an address inside the function"""
    first, n = insns[0][0], 0
    for addr, text in insns:
        m = re.search(r"\b([0-9a-f]+) <[^>]+>$", text)
        if m and first <= int(m.group(1), 16) < addr:
            n += 1
    return n


def whole(insns):
    """the function text; a branch target inside the function becomes its distance from the function start"""
    first, last, out = insns[0][0], insns[-1][0], []
    for _, text in insns:
        m = re.search(r"\b([0-9a-f]+) <[^>]+>$", text)
        if m and first <= int(m.group(1), 16) <= last:
            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)
        elif m:
            # an address outside the function (adrp of a data page, bl of a library stub) depends on
            # where the linker put that target in this binary, not on the code of the kernel
            text = text[:m.start()] + "(outside)"
        out.append(text)
    return out


# kernels that use q8 to q15, so d8 to d15 must be saved before the loop and restored after it
SAVE_D8_D15 = {"asmread", "asmread2", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "asmcopy", "asmcopy2", "asmcopy_c_reg"}
# kernels whose whole function is in probe.txt (asmcopy_c has only its loop from there)
WHOLE = {k: v for k, v in SAME.items() if k != "asmcopy_c"}
D_PAIRS = ["d8, d9", "d10, d11", "d12, d13", "d14, d15"]
BINARIES = ["bwx", "bwx_o0", "bwx_o36", "bwx_o52"]


def save_problems(insns, loop_start, loop_len):
    """the pairs of d8 to d15 that are not saved before the loop or not restored after it"""
    before = [t for a, t in insns if a < loop_start]
    after = [t for a, t in insns if a >= loop_start + 4 * loop_len]
    out = []
    for pair in D_PAIRS:
        if not any(re.match(r"stp %s, \[sp" % pair, t) for t in before):
            out.append("no 'stp %s' before the loop" % pair)
        if not any(re.match(r"ldp %s, \[sp" % pair, t) for t in after):
            out.append("no 'ldp %s' after the loop" % pair)
    return out


def expected(kernel, ref):
    """the loop text that the kernel must have, built from the reference loops"""
    if kernel in SAME:
        return ref[SAME[kernel]]
    c, r = ref[("bw_new", "k_copy")], ref[("bw_new", "k_asmread")]
    if kernel == "asmcopy_c_reg":
        return [re.sub(r"\bq(\d+)\b", lambda m: "q%d" % (31 - int(m.group(1))), t) for t in c]
    if kernel == "asmcopy_c_add":
        ldp = [t for t in c if t.startswith("ldp")]
        stp = [t for t in c if t.startswith("stp")]
        add = [t for t in c if t.startswith("add")]
        dst = re.search(r"\[(\w+)", stp[0]).group(1)
        stp = [re.sub(r"\[.*\]", "[%s]" % dst if i == 0 else "[%s, #%d]" % (dst, 32 * i), t) for i, t in enumerate(stp)]
        return ldp + stp + add + c[-2:]
    m = re.fullmatch(r"read_nop(\d+)", kernel)
    if m:
        return r[:8] + ["nop"] * int(m.group(1)) + r[8:]
    if kernel == "read_sparse":
        return r[:4] + ["nop"] * 9 + [r[8].replace("#0x100", "#0x80")] + r[9:]
    raise KeyError(kernel)


def main():
    args, want_bins = sys.argv[1:], BINARIES
    if "--binaries" in args:
        i = args.index("--binaries")
        if i + 1 >= len(args):
            print("--binaries needs a comma-separated list")
            return 2
        want_bins = args[i + 1].split(",")
        del args[i:i + 2]
    listing = args[0] if len(args) > 0 else os.path.join(HERE, "listing.txt")
    probe = args[1] if len(args) > 1 else PROBE
    try:
        ref_raw, got_raw = sections(probe), sections(listing)
    except OSError as e:
        print("cannot read: %s" % e)
        return 2
    ref, ref_whole = {}, {}
    for key in set(SAME.values()):
        lp = loop_of(ref_raw.get(key, []))
        if lp is None:
            print("probe.txt has no loop for %s %s" % key)
            return 2
        ref[key] = lp[1]
        ref_whole[key] = whole(ref_raw[key])
    found = sorted({b for b, _ in got_raw})
    if not found:
        print("no '=== binary kernel ===' block in %s" % listing)
        return 2
    # the expected binaries, then any other binary of the listing
    binaries = want_bins + [b for b in found if b not in want_bins]

    bad = 0
    for b in want_bins:
        if b not in found:
            print("%s\t-\tNA\tNA\tNA\t-\t-\tFAIL: the listing has no block of this binary" % b)
            bad += 1
    print("binary\tkernel\tstart\tloop_start\tloop_mod64\tplanned\tloop_body\tresult")
    for b in binaries:
        if b not in found:
            continue
        info = {}
        for k in KERNELS:
            insns = got_raw.get((b, k), [])
            lp = loop_of(insns)
            problems = []
            if lp is None:
                print("%s\t%s\tNA\tNA\tNA\t-\t-\tFAIL: no listing or no loop" % (b, k))
                bad += 1
                continue
            start, (loop, body) = insns[0][0], lp
            info[k] = (start, loop % 64)
            want = expected(k, ref)
            same = body == want
            if not same:
                problems.append("loop body differs from the reference")
            plan = planned(b).get(k)
            if plan is not None and loop % 64 != plan:
                problems.append("loop offset is not the planned %d" % plan)
            if k in AA and AA[k] in info:
                if info[AA[k]][0] == start:
                    problems.append("same start address as %s" % AA[k])
                if info[AA[k]][1] != loop % 64:
                    problems.append("loop offset differs from %s (%d)" % (AA[k], info[AA[k]][1]))
            elif k in AA:
                problems.append("original %s is missing" % AA[k])
            # code outside the loop
            outside = k in WHOLE and whole(insns) != ref_whole[WHOLE[k]]
            if outside and same:
                problems.append("code outside the loop differs from %s %s of probe.txt" % WHOLE[k])
            nback = backward_branches(insns)
            if k not in WHOLE and nback != 1:
                problems.append("%d backward branches, 1 expected" % nback)
            if k in SAVE_D8_D15:
                problems += save_problems(insns, loop, len(body))
            print("%s\t%s\t%x\t%x\t%d\t%s\t%s\t%s" % (b, k, start, loop, loop % 64, "-" if plan is None else plan,
                                                      "same" if same else "DIFFERS",
                                                      "FAIL: " + "; ".join(problems) if problems else "ok"))
            if not same:
                for i in range(max(len(body), len(want))):
                    g = body[i] if i < len(body) else "(none)"
                    w = want[i] if i < len(want) else "(none)"
                    print("    %s %-34s | expected %s" % ("  " if g == w else "!=", g, w))
            elif outside:
                g_all, w_all = whole(insns), ref_whole[WHOLE[k]]
                for i in range(max(len(g_all), len(w_all))):
                    g = g_all[i] if i < len(g_all) else "(none)"
                    w = w_all[i] if i < len(w_all) else "(none)"
                    print("    %s %-34s | probe.txt %s" % ("  " if g == w else "!=", g, w))
            bad += bool(problems)
        extra = sorted(k for bb, k in got_raw if bb == b and k not in KERNELS)
        if extra:
            print("%s\t(kernels in the listing that this script does not know: %s)" % (b, ", ".join(extra)))
            bad += 1
    print("# binaries=%d (expected: %s) kernels_per_binary=%d failed_rows=%d" % (len(found), ",".join(want_bins), len(KERNELS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
