#!/usr/bin/env python3
"""check_listing8.py - acceptance test of a bwx8 build (design tackle-8mb.md,
"Fixed setup": reject a build whose acceptance listing differs).

Runs on the development machine, on the listing.txt and offsets.tsv that
build8.sh wrote on CRB.
Usage: check_listing8.py [listing.txt [offsets.tsv]]
           [--ref-listing F] [--ref-offsets F] [--binary bwx8] [--ref-binary bwx]

The reference is the saved accepted build of bwx: crb-build-2/listing.txt and
offsets.tsv in the folder bwx-2026-11-13, binary "bwx".

Checks, for every kernel of the reference binary:
 1. the new listing has the kernel, and the function has a loop;
 2. the whole function text equals the reference text, apart from addresses;
 3. the loop start modulo 64 equals the reference value. Both are computed
    from the listings;
 4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as
    the new listing and as the row of the reference offsets.tsv.
A kernel of the new listing that the reference lacks is a failure.

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
Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(HERE, "..", "bwx-2026-11-13", "crb-build-2")
TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")


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


def main():
    args = sys.argv[1:]
    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),
           "--binary": "bwx8", "--ref-binary": "bwx"}
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
    if not any(bb == b for bb, _ in got):
        print("no '=== %s kernel ===' block in %s" % (b, listing))
        return 2

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
    extra = sorted(k for bb, k in got if bb == b and k not in kernels)
    if extra:
        print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))
        bad += 1
    print("# binary=%s reference=%s kernels=%d failed_rows=%d" % (b, rb, len(kernels), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
