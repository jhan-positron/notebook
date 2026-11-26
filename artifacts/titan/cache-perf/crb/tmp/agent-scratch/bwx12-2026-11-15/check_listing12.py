#!/usr/bin/env python3
"""check_listing12.py - acceptance test of a bwx12 build (design tackle-8mb.md,
"Fixed setup": reject a build whose acceptance listing differs).

It is check_listing11.py with another reference and other new kernels. The
code of part 1 is unchanged.

Runs on the development machine, on the listing.txt and offsets.tsv that
build12.sh wrote on CRB.
Usage: check_listing12.py [listing.txt [offsets.tsv]]
           [--ref-listing F] [--ref-offsets F] [--binary bwx12] [--ref-binary bwx11] [--skip-new]

The reference is the accepted build of bwx11 (crb-build-1 of the folder
bwx11-2026-11-15), saved in ref-bwx11/listing.txt and ref-bwx11/offsets.tsv
beside this script, binary "bwx11".

Part 1, the 29 kernels of the reference binary. The rules are the rules of
check_listing11.py part 1 (which are the rules of check_listing8.py),
unchanged. For every kernel of the reference:
 1. the new listing has the kernel, and the function has a loop;
 2. the whole function text equals the reference text, apart from addresses;
 3. the loop start modulo 64 equals the reference value. Both are computed
    from the listings;
 4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as
    the new listing and as the row of the reference offsets.tsv.

What "apart from addresses" means here:
 - an instruction address is not compared;
 - a branch target inside the function is compared as its distance from the
   function start;
 - a target outside the function (the stub of bl, the page of a single adrp)
   is compared by its symbol name, not by its address;
 - the pair "adrp xN, page" + "ldr xN, [xN, #offset]" loads a pointer from
   the table of global addresses of the binary. In the reference only the
   load of the stack-guard pointer has this form. Page and offset are the
   place of the pointer in that table. The linker sets them, so they are not
   compared with the reference. The pair is accepted only where the reference
   has it, because the rest of the text must be equal. The listing does not
   name the pointer. So this is checked: the new listing must not use more
   places of the table than the reference, per function and over all
   kernels. The reference uses one place. A row whose offset differs from the
   reference prints "NOTE: got_offset_differs" in place of "ok": read it.
The loop of a function is the range from the target of its first backward
branch to that branch.

Part 2, the 26 kernels of round 5 (the keys of NEW below). The reference does
not have them. All 26 must be in the new listing. For each one:
 1. the function has exactly one backward branch, and no other branch or call;
 2. the instructions of the loop equal the expected list (the field "loop" of
    NEW), with every operand. The loop ends with b.cc (the same instruction
    as b.lo) to the loop start. The expected lists:
      read_nopN       the 8 ldp of asmread, N nop, add #256, cmp
      read_daddK      the 8 ldp, K "add vA.2d, vA.2d, vL.2d" with vL a
                      register that the 8 ldp loaded, add #256, cmp
      read_iadd16     the 8 ldp, 16 "add vA.2d, vA.2d, vB.2d" with vB one of
                      v24-v31, add #256, cmp
      read_spN        the 4 ldp of read_sparse, N nop, add #128, cmp
      read_1pl_nop96  the 4 ldr of read_1pl, 96 nop, add #256, cmp
      write_nopN      the 8 stp of asmwrite, N nop, add #256, cmp
      copy_nopN       the 8 ldp and 8 stp of asmcopy, N nop, the two add, cmp
 3. the instructions before the loop are: the computation of the end pointer
    (once), stores of d registers to the stack, and the instructions of the
    field "init" in their order (the movi of the add kernels, the dup of the
    write kernels), and nothing else. Every instruction after the loop is a
    load of d registers from the stack, and the last one is ret;
 4. every register from v8 to v15 that the loop uses is stored before the
    loop and loaded after it (d8-d15 are callee-saved);
 5. the loop start modulo 64 equals the planned value (20 for a read kernel,
    40 for a write kernel, 52 for a copy kernel), it equals the loop start
    modulo 64 of the original in the same listing (asmread, asmwrite or
    asmcopy), and the row in offsets.tsv gives the same value.
Any other kernel that the reference lacks is a failure.

--skip-new leaves out part 2. It is only for a build on a machine that is not
AArch64, where the new kernels are plain C stand-in loops. The last line then
says that the new kernels were NOT CHECKED.
Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(HERE, "ref-bwx11")
TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")

# The loop of each new kernel, as objdump prints it (one space between the
# fields). x0 is the pointer and x1 is the end, as in every asm read and write
# kernel of the reference. A copy kernel has the destination in x0, the source
# in x1 and the end in x2. The loop branch stands after these instructions.
LDP8 = ["ldp q0, q1, [x0]", "ldp q2, q3, [x0, #32]", "ldp q4, q5, [x0, #64]", "ldp q6, q7, [x0, #96]",
        "ldp q8, q9, [x0, #128]", "ldp q10, q11, [x0, #160]", "ldp q12, q13, [x0, #192]", "ldp q14, q15, [x0, #224]"]
STEP = ["add x0, x0, #0x100", "cmp x0, x1"]
STEP128 = ["add x0, x0, #0x80", "cmp x0, x1"]
LDR4 = ["ldr q0, [x0]", "ldr q1, [x0, #64]", "ldr q2, [x0, #128]", "ldr q3, [x0, #192]"]
STP8 = ["stp q0, q0, [x0%s]" % ("" if o == 0 else ", #%d" % o) for o in range(0, 256, 32)]
COPY_LDP8 = [t.replace("[x0", "[x1") for t in LDP8]
COPY_STP8 = [t.replace("ldp", "stp") for t in LDP8]
COPY_STEP = ["add x1, x1, #0x100", "add x0, x0, #0x100", "cmp x1, x2"]
END_POINTER = "add x1, x0, x1, lsl #3"
COPY_END_POINTER = "add x2, x1, x2, lsl #3"
ACC_ZERO = ["movi v%d.4s, #0x0" % r for r in range(16, 24)]
CONST_ONE = ["movi v%d.4s, #0x1" % r for r in range(24, 32)]


def vadd(pairs):
    return ["add v%d.2d, v%d.2d, v%d.2d" % (a, a, b) for a, b in pairs]


def spec(loop, mod, like, init=(), end=END_POINTER):
    """loop: the instructions of the loop before its branch; mod: the planned loop start modulo 64; like: the
    kernel of the reference whose loop offset this kernel must have; init: the instructions before the loop
    beside the end pointer and the stores of d registers; end: the computation of the end pointer"""
    return {"loop": loop, "mod": mod, "like": like, "init": list(init), "end": end}


NEW = {}
for _n in (48, 56, 72, 80, 88, 112, 160, 192, 256):
    NEW["read_nop%d" % _n] = spec(LDP8 + ["nop"] * _n + STEP, 20, "asmread")
NEW["read_dadd2"] = spec(LDP8 + vadd([(16, 0), (17, 8)]) + STEP, 20, "asmread", ACC_ZERO)
NEW["read_dadd4"] = spec(LDP8 + vadd([(16, 0), (17, 4), (18, 8), (19, 12)]) + STEP, 20, "asmread", ACC_ZERO)
NEW["read_dadd8"] = spec(LDP8 + vadd([(16 + i, 2 * i) for i in range(8)]) + STEP, 20, "asmread", ACC_ZERO)
NEW["read_dadd16"] = spec(LDP8 + vadd([(16 + i % 8, i) for i in range(16)]) + STEP, 20, "asmread", ACC_ZERO)
NEW["read_iadd16"] = spec(LDP8 + vadd([(16 + i % 8, 24 + i % 8) for i in range(16)]) + STEP, 20, "asmread", ACC_ZERO + CONST_ONE)
for _n in (24, 32, 40, 48, 56):
    NEW["read_sp%d" % _n] = spec(LDP8[:4] + ["nop"] * _n + STEP128, 20, "asmread")
NEW["read_1pl_nop96"] = spec(LDR4 + ["nop"] * 96 + STEP, 20, "asmread")
for _n in (32, 96, 128, 256):
    NEW["write_nop%d" % _n] = spec(STP8 + ["nop"] * _n + STEP, 40, "asmwrite", ["dup v0.2d, x2"])
for _n in (96, 192):
    NEW["copy_nop%d" % _n] = spec(COPY_LDP8 + COPY_STP8 + ["nop"] * _n + COPY_STEP, 52, "asmcopy", end=COPY_END_POINTER)
NEW_LOOP = NEW  # the name that the code of part 1 uses for "is a new kernel"
SAVE = re.compile(r"(?:stp d(\d+), d(\d+)|str d(\d+)), \[sp(?:, #-?\d+)?\]!?")
RESTORE = re.compile(r"(?:ldp d(\d+), d(\d+)|ldr d(\d+)), \[sp(?:, #\d+)?\](?:, #\d+)?")
BRANCH = re.compile(r"(b|bl|br|blr|b\.[a-z]+|cbn?z|tbn?z)\b")


def sections(path):
    """{(binary, kernel): [(address, text), ...]} from the '=== binary kernel ===' blocks of objdump text"""
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


def offsets(path):
    """{(binary, kernel): loop_mod64 as text} from offsets.tsv"""
    out = {}
    with open(path) as f:
        head = f.readline().rstrip("\n").split("\t")
        if head != ["binary", "kernel", "function", "start", "loop_start", "loop_mod64"]:
            raise ValueError("%s: unexpected header line" % path)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) != 6:
                raise ValueError("%s: a row with %d fields" % (path, len(p)))
            out[(p[0], p[1])] = p[5]
    return out


def loop_start(insns):
    """address of the loop start: the target of the first backward branch into the function, or None"""
    first = insns[0][0]
    for addr, text in insns:
        m = TARGET.search(text)
        if m and first <= int(m.group(1), 16) < addr:
            return int(m.group(1), 16)
    return None


def whole(insns):
    """(function text without addresses, the places (page, offset) of the pointer loads from the table)"""
    first, last, out, got = insns[0][0], insns[-1][0], [], []
    adrp_reg = adrp_page = None
    for _, text in insns:
        m = TARGET.search(text)
        page = None
        if m and first <= int(m.group(1), 16) <= last:
            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)
        elif m:
            page = m.group(1)
            text = text[:m.start()] + "(outside %s)" % text[m.start():].split(" ", 1)[1]
        load = re.fullmatch(r"ldr (x\d+), \[(x\d+), #(\d+)\]", text)
        if load and adrp_reg and load.group(1) == adrp_reg and load.group(2) == adrp_reg:
            got.append((adrp_page, load.group(3)))
            out[-1] = "adrp %s, (table page)" % adrp_reg
            text = "ldr %s, [%s, #(table)]" % (adrp_reg, adrp_reg)
        m = re.match(r"adrp (x\d+), ", text)
        adrp_reg, adrp_page = (m.group(1), page) if m and page else (None, None)
        out.append(text)
    return out, got


def numbers(match):
    return {int(g) for g in match.groups() if g is not None}


def new_problems(kernel, insns, want_mod, off_row):
    """Part 2 for one new kernel. want_mod: the loop start modulo 64 of the original (the field "like") in the
    same listing, or None."""
    p = []
    sp = NEW[kernel]
    first = insns[0][0]
    back = [i for i, (addr, text) in enumerate(insns)
            if TARGET.search(text) and first <= int(TARGET.search(text).group(1), 16) <= addr]
    if len(back) != 1:
        return ["%d backward branches, 1 expected" % len(back)]
    end = back[0]
    loop = int(TARGET.search(insns[end][1]).group(1), 16)
    begin = next((i for i, (addr, _) in enumerate(insns) if addr == loop), None)
    if begin is None:
        return ["the loop branch goes to %x, which is not the address of an instruction" % loop]
    others = [text for i, (_, text) in enumerate(insns) if i != end and BRANCH.match(text)]
    if others:
        p.append("a branch or call beside the loop branch: %s" % "; ".join(others))
    body, want = [text for _, text in insns[begin:end]], sp["loop"]
    if body != want:
        # the count of nop first: one line says what is wrong with a loop of the wrong length
        if body.count("nop") != want.count("nop"):
            p.append("the loop has %d nop, expected %d" % (body.count("nop"), want.count("nop")))
        diff = [i for i in range(max(len(body), len(want))) if (body[i] if i < len(body) else "(none)") != (want[i] if i < len(want) else "(none)")]
        for i in diff[:3]:
            p.append("loop instruction %d is '%s', expected '%s'" % (i, body[i] if i < len(body) else "(none)",
                                                                   want[i] if i < len(want) else "(none)"))
        if len(diff) > 3:
            p.append("%d more loop instructions differ" % (len(diff) - 3))
    if not re.fullmatch(r"b\.(cc|lo) %x <k_%s\+0x%x>" % (loop, re.escape(kernel), loop - first), insns[end][1]):
        p.append("the loop branch is '%s', expected b.cc (b.lo) to the loop start" % insns[end][1])
    head, tail = [text for _, text in insns[:begin]], [text for _, text in insns[end + 1:]]
    saved, restored, init = set(), set(), []
    for text in head:
        m = SAVE.fullmatch(text)
        if m:
            saved |= numbers(m)
        elif text != sp["end"]:
            init.append(text)
    if head.count(sp["end"]) != 1:
        p.append("before the loop: '%s' stands %d times, 1 expected" % (sp["end"], head.count(sp["end"])))
    if init != sp["init"]:
        p.append("before the loop, beside the end pointer and the stores of d registers: '%s', expected '%s'" %
                 ("; ".join(init) or "nothing", "; ".join(sp["init"]) or "nothing"))
    if not tail or tail[-1] != "ret":
        p.append("the function does not end with ret")
    for text in tail[:-1]:
        m = RESTORE.fullmatch(text)
        if m:
            restored |= numbers(m)
        else:
            p.append("after the loop: '%s' is not a load of d registers from the stack" % text)
    used = {int(n) for text in body for n in re.findall(r"\b[qvd](\d+)\b", text) if 8 <= int(n) <= 15}
    if used - saved or used - restored:
        p.append("the loop uses v%s; not stored before the loop: %s; not loaded after it: %s" %
                 (",".join(str(n) for n in sorted(used)), sorted(used - saved) or "none", sorted(used - restored) or "none"))
    if saved != restored:
        p.append("d registers stored %s, loaded %s" % (sorted(saved), sorted(restored)))
    if want_mod is None:
        p.append("%s has no loop in this listing, so the loop offset cannot be compared" % sp["like"])
    elif loop % 64 != want_mod:
        p.append("loop offset modulo 64 is %d, %s has %d" % (loop % 64, sp["like"], want_mod))
    if loop % 64 != sp["mod"]:
        p.append("loop offset modulo 64 is %d, planned %d" % (loop % 64, sp["mod"]))
    if off_row != str(loop % 64):
        p.append("offsets.tsv gives %s, the listing gives %d" % (off_row if off_row is not None else "no row", loop % 64))
    return p


def main():
    args = sys.argv[1:]
    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),
           "--binary": "bwx12", "--ref-binary": "bwx11"}
    skip_new = "--skip-new" in args
    if skip_new:
        args.remove("--skip-new")
    for name in opt:
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                print("%s needs a value" % name)
                return 2
            opt[name] = args[i + 1]
            del args[i:i + 2]
    if len(args) > 2 or any(a.startswith("--") for a in args):
        print(__doc__)
        return 2
    listing = args[0] if args else os.path.join(HERE, "listing.txt")
    offs = args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.abspath(listing)), "offsets.tsv")
    try:
        ref, got = sections(opt["--ref-listing"]), sections(listing)
        ref_off, got_off = offsets(opt["--ref-offsets"]), offsets(offs)
    except (OSError, ValueError) as e:
        print("cannot use: %s" % e)
        return 2
    b, rb = opt["--binary"], opt["--ref-binary"]
    kernels = [k for (bb, k) in ref if bb == rb]
    if not kernels or any(not ref[(rb, k)] or loop_start(ref[(rb, k)]) is None for k in kernels):
        print("the reference listing has no usable block of binary %s" % rb)
        return 2
    if any(k in NEW_LOOP for k in kernels):
        print("the reference listing holds a kernel of round 5: it is not a listing of %s" % rb)
        return 2
    if not any(bb == b for bb, _ in got):
        print("no '=== %s kernel ===' block in %s" % (b, listing))
        return 2

    # Part 1: the kernels of the reference (the code of check_listing8.py)
    bad, r_places, g_places = 0, set(), set()
    print("kernel\tstart\tloop_start\tloop_mod64\tref_loop_mod64\ttext\tresult")
    for k in kernels:
        r_insns, insns = ref[(rb, k)], got.get((b, k), [])
        r_mod = loop_start(r_insns) % 64
        loop = loop_start(insns) if insns else None
        if loop is None:
            print("%s\tNA\tNA\tNA\t%d\t-\tFAIL: no listing or no loop" % (k, r_mod))
            bad += 1
            continue
        problems, notes = [], []
        (r_text, r_got), (text, g_got) = whole(r_insns), whole(insns)
        same = text == r_text
        if not same:
            problems.append("function text differs from the reference")
        else:
            r_places.update(r_got)
            g_places.update(g_got)
            if len(set(g_got)) > len(set(r_got)):
                problems.append("the pointer loads after adrp use %d places of the table (%s), the reference uses %d" %
                                (len(set(g_got)), ", ".join("page %s offset %s" % g for g in g_got), len(set(r_got))))
            elif [o for _, o in g_got] != [o for _, o in r_got]:
                notes.append("got_offset_differs (%s, reference %s)" % (",".join(o for _, o in g_got), ",".join(o for _, o in r_got)))
        if loop % 64 != r_mod:
            problems.append("loop offset modulo 64 is %d, reference %d" % (loop % 64, r_mod))
        if ref_off.get((rb, k)) != str(r_mod):
            problems.append("reference offsets.tsv gives %s" % ref_off.get((rb, k), "no row"))
        if got_off.get((b, k)) != str(loop % 64):
            problems.append("offsets.tsv gives %s, the listing gives %d" % (got_off.get((b, k), "no row"), loop % 64))
        print("%s\t%x\t%x\t%d\t%d\t%s\t%s" % (k, insns[0][0], loop, loop % 64, r_mod, "same" if same else "DIFFERS",
                                             "FAIL: " + "; ".join(problems) if problems else "NOTE: " + "; ".join(notes) if notes else "ok"))
        if not same:
            for i in range(max(len(text), len(r_text))):
                g = text[i] if i < len(text) else "(none)"
                w = r_text[i] if i < len(r_text) else "(none)"
                print("    %s %-40s | reference %s" % ("  " if g == w else "!=", g, w))
        bad += bool(problems)
    if len(g_places) > len(r_places):
        print("FAIL: the pointer loads after adrp use %d places of the table over all kernels (%s), the reference uses %d" %
              (len(g_places), ", ".join("page %s offset %s" % g for g in sorted(g_places)), len(r_places)))
        bad += 1
    extra = sorted(k for bb, k in got if bb == b and k not in kernels and k not in NEW_LOOP)
    if extra:
        print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))
        bad += 1

    # Part 2: the kernels of round 5
    new_bad = 0
    if skip_new:
        print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=NOT CHECKED (--skip-new)" % (b, rb, len(kernels), bad))
        return 1 if bad else 0
    like_mod = {}
    for name in sorted({sp["like"] for sp in NEW.values()}):
        orig = got.get((b, name), [])
        orig_loop = loop_start(orig) if orig else None
        like_mod[name] = None if orig_loop is None else orig_loop % 64
    print("new_kernel\tstart\tloop_start\tloop_mod64\toriginal_loop_mod64\tloop\tresult")
    for k in NEW_LOOP:
        insns = got.get((b, k), [])
        want_mod = like_mod[NEW[k]["like"]]
        if not insns:
            print("%s\tNA\tNA\tNA\t%s\t-\tFAIL: no listing" % (k, "NA" if want_mod is None else want_mod))
            new_bad += 1
            continue
        problems = new_problems(k, insns, want_mod, got_off.get((b, k)))
        loop = loop_start(insns)
        print("%s\t%x\t%s\t%s\t%s\t%s\t%s" % (k, insns[0][0], "NA" if loop is None else "%x" % loop,
                                               "NA" if loop is None else loop % 64, "NA" if want_mod is None else want_mod,
                                               "DIFFERS" if any("loop instruction" in x or "loop branch" in x or "backward" in x or "nop, expected" in x
                                                                for x in problems) else "expected",
                                               "FAIL: " + "; ".join(problems) if problems else "ok"))
        new_bad += bool(problems)
    print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=%d new_failed_rows=%d" %
          (b, rb, len(kernels), bad, len(NEW_LOOP), new_bad))
    return 1 if bad or new_bad else 0


if __name__ == "__main__":
    sys.exit(main())
