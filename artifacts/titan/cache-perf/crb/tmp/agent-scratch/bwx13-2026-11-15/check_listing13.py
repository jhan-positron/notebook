#!/usr/bin/env python3
"""check_listing13.py - acceptance test of a bwx13 build (design tackle-8mb.md,
"Fixed setup": reject a build whose acceptance listing differs).

It is check_listing12.py with another reference and other new kernels. The
code of part 1 is unchanged.

Runs on the development machine, on the listing.txt and offsets.tsv that
build13.sh wrote on CRB.
Usage: check_listing13.py [listing.txt [offsets.tsv]]
           [--ref-listing F] [--ref-offsets F] [--binary bwx13] [--ref-binary bwx12] [--skip-new]

The reference is the accepted build of bwx12 (crb-build-1 of the folder
bwx12-2026-11-15), saved in ref-bwx12/listing.txt and ref-bwx12/offsets.tsv
beside this script, binary "bwx12".

Part 1, the 55 kernels of the reference binary. The rules are the rules of
check_listing12.py part 1 (which are the rules of check_listing8.py),
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
   place of the pointer in the table, so they are not compared. The check
   fails if the new binary loads pointers from more
   places of the table than the reference, per function and over all
   kernels. The reference uses one place. A row whose offset differs from the
   reference prints "NOTE: got_offset_differs" in place of "ok": read it.
The loop of a function is the range from the target of its first backward
branch to that branch.

Part 2, the 3 kernels rand_nop0, rand_nop96 and rand_nop256 (the keys of NEW
below). The reference does not have them. All 3 must be in the new listing.
For rand_nopN the function must be, instruction for instruction and with
every operand:
 1. stores of d registers to the stack (any number of instructions);
 2. lsr x10, x1, #5; sub x12, x10, #1; tst x10, x12; mov x9, #0; b.ne to
    loop 2;
 3. loop 1 (the random order): add x11, x9, x9; add x11, x11, #1;
    mul x11, x11, x9; and x11, x11, x12; add x13, x0, x11, lsl #8; the 8 ldp
    of asmread with x13 as the base; N nop; add x9, x9, #1; cmp x9, x10;
    b.cc (the same instruction as b.lo) to the start of loop 1;
 4. b to the first instruction after loop 2;
 5. loop 2 (the order of asmread): add x13, x0, x9, lsl #8; the 8 ldp; N nop;
    add x9, x9, #1; cmp x9, x10; b.cc to the start of loop 2;
 6. loads of d registers from the stack, and ret.
So the function has 8 ldp and N nop in each loop, 5 instructions of index
arithmetic in loop 1 and 1 in loop 2, and no branch beside the four named.
Also:
 7. d8 to d15 are all stored before item 2 and loaded after item 5;
 8. the start of loop 1 modulo 64 equals the planned value (20, the offset of
    asmread in the same listing), and the row in offsets.tsv gives the same
    value. The offset is not important for these kernels: it is checked so
    that the record in offsets.tsv is right.
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
REF_DIR = os.path.join(HERE, "ref-bwx12")
TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")

# The new kernels, as objdump prints them (one space between the fields). x0
# is the pointer and x1 is the number of words. x9 is the step, x10 the number
# of blocks, x11 the block index, x12 the mask, x13 the address of the block.
RAND_LDP8 = ["ldp q0, q1, [x13]", "ldp q2, q3, [x13, #32]", "ldp q4, q5, [x13, #64]", "ldp q6, q7, [x13, #96]",
             "ldp q8, q9, [x13, #128]", "ldp q10, q11, [x13, #160]", "ldp q12, q13, [x13, #192]", "ldp q14, q15, [x13, #224]"]
RAND_INIT = ["lsr x10, x1, #5", "sub x12, x10, #0x1", "tst x10, x12", "mov x9, #0x0"]
RAND_INDEX = ["add x11, x9, x9", "add x11, x11, #0x1", "mul x11, x11, x9", "and x11, x11, x12", "add x13, x0, x11, lsl #8"]
SEQ_INDEX = ["add x13, x0, x9, lsl #8"]
RAND_STEP = ["add x9, x9, #0x1", "cmp x9, x10"]
RAND_MOD = 20  # the planned start of loop 1 modulo 64
NEW = {"rand_nop0": 0, "rand_nop96": 96, "rand_nop256": 256}  # kernel: number of nop per block
NEW_LOOP = NEW  # the name that the code of part 1 uses for "is a new kernel"
SAVE = re.compile(r"(?:stp d(\d+), d(\d+)|str d(\d+)), \[sp(?:, #-?\d+)?\]!?")
RESTORE = re.compile(r"(?:ldp d(\d+), d(\d+)|ldr d(\d+)), \[sp(?:, #\d+)?\](?:, #\d+)?")


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


def expected_body(nops, at):
    """The instructions of rand_nopN between the stores and the loads of d registers. at: the distance of the
    first of them from the function start, in bytes. A branch is written with its target as that distance.
    Returns (list, distance of the start of loop 1)."""
    loop1 = RAND_INDEX + RAND_LDP8 + ["nop"] * nops + RAND_STEP
    loop2 = SEQ_INDEX + RAND_LDP8 + ["nop"] * nops + RAND_STEP
    l1 = at + 4 * (len(RAND_INIT) + 1)
    l2 = l1 + 4 * (len(loop1) + 2)
    l3 = l2 + 4 * (len(loop2) + 1)
    return (RAND_INIT + ["b.ne +0x%x" % l2] + loop1 + ["b.cc +0x%x" % l1, "b +0x%x" % l3] + loop2 + ["b.cc +0x%x" % l2]), l1


def new_problems(kernel, insns, want_mod, off_row):
    """Part 2 for one new kernel. want_mod: the loop start modulo 64 of asmread in the same listing, or None."""
    p = []
    first = insns[0][0]
    text = []
    for _, t in insns:  # a branch target inside the function becomes its distance from the function start
        m = TARGET.search(t)
        if m:
            t = t[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)
        text.append(re.sub(r"^b\.lo ", "b.cc ", t))
    head = 0
    saved, restored = set(), set()
    while head < len(text) and SAVE.fullmatch(text[head]):
        saved |= numbers(SAVE.fullmatch(text[head]))
        head += 1
    if not text or text[-1] != "ret":
        p.append("the function does not end with ret")
    tail = len(text) - 1
    while tail > head and RESTORE.fullmatch(text[tail - 1]):
        restored |= numbers(RESTORE.fullmatch(text[tail - 1]))
        tail -= 1
    body = text[head:tail]
    want, l1 = expected_body(NEW[kernel], 4 * head)
    if body != want:
        for name in ("nop", "ldp"):
            n_got = sum(t.split(" ")[0] == name for t in body)
            n_want = sum(t.split(" ")[0] == name for t in want)
            if n_got != n_want:
                p.append("the function has %d %s between the stores and the loads of d registers, expected %d" % (n_got, name, n_want))
        diff = [i for i in range(max(len(body), len(want))) if (body[i] if i < len(body) else "(none)") != (want[i] if i < len(want) else "(none)")]
        for i in diff[:3]:
            p.append("instruction %d after the stores is '%s', expected '%s'" % (i, body[i] if i < len(body) else "(none)",
                                                                                  want[i] if i < len(want) else "(none)"))
        if len(diff) > 3:
            p.append("%d more instructions differ" % (len(diff) - 3))
    need = set(range(8, 16))
    if need - saved or need - restored:
        p.append("d8-d15: not stored before the code: %s; not loaded after it: %s" % (sorted(need - saved) or "none", sorted(need - restored) or "none"))
    if saved != restored:
        p.append("d registers stored %s, loaded %s" % (sorted(saved), sorted(restored)))
    loop = loop_start(insns)
    if loop is None:
        p.append("no backward branch")
        return p
    if loop - first != l1:
        p.append("the first backward branch goes to +0x%x, loop 1 is expected at +0x%x" % (loop - first, l1))
    if want_mod is None:
        p.append("asmread has no loop in this listing, so the loop offset cannot be compared")
    elif want_mod != RAND_MOD:
        p.append("asmread has its loop at %d modulo 64, the plan says %d" % (want_mod, RAND_MOD))
    if loop % 64 != RAND_MOD:
        p.append("loop offset modulo 64 is %d, planned %d" % (loop % 64, RAND_MOD))
    if off_row != str(loop % 64):
        p.append("offsets.tsv gives %s, the listing gives %d" % (off_row if off_row is not None else "no row", loop % 64))
    return p


def main():
    args = sys.argv[1:]
    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),
           "--binary": "bwx13", "--ref-binary": "bwx12"}
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
        print("the reference listing holds a rand_nop kernel: it is not a listing of %s" % rb)
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

    # Part 2: the rand_nop kernels
    new_bad = 0
    if skip_new:
        print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=NOT CHECKED (--skip-new)" % (b, rb, len(kernels), bad))
        return 1 if bad else 0
    orig = got.get((b, "asmread"), [])
    orig_loop = loop_start(orig) if orig else None
    want_mod = None if orig_loop is None else orig_loop % 64
    print("new_kernel\tstart\tloop_start\tloop_mod64\tasmread_loop_mod64\tcode\tresult")
    for k in NEW_LOOP:
        insns = got.get((b, k), [])
        if not insns:
            print("%s\tNA\tNA\tNA\t%s\t-\tFAIL: no listing" % (k, "NA" if want_mod is None else want_mod))
            new_bad += 1
            continue
        problems = new_problems(k, insns, want_mod, got_off.get((b, k)))
        loop = loop_start(insns)
        print("%s\t%x\t%s\t%s\t%s\t%s\t%s" % (k, insns[0][0], "NA" if loop is None else "%x" % loop,
                                               "NA" if loop is None else loop % 64, "NA" if want_mod is None else want_mod,
                                               "DIFFERS" if any("instruction" in x or "backward" in x or ", expected" in x
                                                                for x in problems) else "expected",
                                               "FAIL: " + "; ".join(problems) if problems else "ok"))
        new_bad += bool(problems)
    print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=%d new_failed_rows=%d" %
          (b, rb, len(kernels), bad, len(NEW_LOOP), new_bad))
    return 1 if bad or new_bad else 0


if __name__ == "__main__":
    sys.exit(main())
