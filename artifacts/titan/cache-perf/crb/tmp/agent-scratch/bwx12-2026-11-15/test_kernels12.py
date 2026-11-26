#!/usr/bin/env python3
"""test_kernels12.py - local tests of the kernels of round 5 (bwx12).

Runs on the development machine (x86-64). There is no AArch64 compiler here,
so the asm text of the new kernels is NOT assembled by this test. What it does:

 1. source: bwx12.c and bwx12_selftest.c without their blocks "bwx12+" to
    "bwx12-" are bwx11.c and bwx11_selftest.c byte for byte (sha256 of the
    accepted build, ref-bwx11/build.txt).
 2. stand-in build: build12.sh builds bwx12.c here (plain C stand-in kernels),
    runs the self-test and writes listing.txt and offsets.tsv. --list must
    print 55 names. The same script text builds the bwx11 source (bwx12.c
    without its blocks) as the reference. check_listing12.py --skip-new must
    find the 29 old kernels with the same machine code and the same loop
    offset in both builds: the new kernels do not move the old ones.
 3. AArch64 text: gcc -E -D__aarch64__ expands the macros of the AArch64
    branch. The test takes the asm template of every new kernel from that
    output, expands .rept, puts the registers in (x0, x1, x2 as in the
    accepted listings), and writes the function as objdump would print it,
    with the frame that gcc 14.2 made for the same clobber list in the
    accepted build (an ASSUMPTION: 4 stores of d8-d15 when v8-v15 are
    clobbered, else none). The function start is the next 64 B boundary plus
    the pad of PLACE(name), computed from the expanded text. This listing,
    after the accepted listing of bwx11, must pass check_listing12.py.
 4. changed copies of that listing must fail: one nop less, an add with
    another source register, a loop moved by 4 B, a missing store of d8.

Usage: test_kernels12.py            (KEEP=1 keeps the temporary folder)
Output: one line per check, "PASS name" or "FAIL name: detail". Exit status 0
only if every check passed.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref-bwx11")
sys.path.insert(0, HERE)
import check_listing12 as cl  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or detail == "" else ": %s" % (detail,)))
    fails += not ok


def strip12(text):
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        if line == "/* bwx12+ */\n":
            skip = True
        elif line == "/* bwx12- */\n":
            skip = False
        elif not skip:
            out.append(line)
    return "".join(out)


def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, **kw)


def checker(args):
    return run([sys.executable, os.path.join(HERE, "check_listing12.py")] + args)


def test_source(tmp):
    digests = dict(reversed(l.split()) for l in open(os.path.join(REF, "build.txt")) if re.match(r"[0-9a-f]{64}  ", l))
    for new, old in (("bwx12.c", "bwx11.c"), ("bwx12_selftest.c", "bwx11_selftest.c")):
        text = strip12(open(os.path.join(HERE, new)).read())
        check("source: %s without its bwx12 blocks has the sha256 of the accepted %s" % (new, old),
              hashlib.sha256(text.encode()).hexdigest() == digests.get(old), digests.get(old))
        open(os.path.join(tmp, old), "w").write(text)


def test_standin(tmp):
    new, old = os.path.join(tmp, "new"), os.path.join(tmp, "old")
    os.mkdir(new)
    os.mkdir(old)
    for name in ("bwx12.c", "bwx12_selftest.c", "build12.sh"):
        shutil.copy(os.path.join(HERE, name), new)
    # the reference: the bwx11 source under the names of bwx12, so the same build script builds it
    src = open(os.path.join(tmp, "bwx11.c")).read()
    open(os.path.join(old, "bwx12.c"), "w").write(src.replace('#include "bwx11_selftest.c"', '#include "bwx12_selftest.c"'))
    shutil.copy(os.path.join(tmp, "bwx11_selftest.c"), os.path.join(old, "bwx12_selftest.c"))
    shutil.copy(os.path.join(HERE, "build12.sh"), old)
    cpus = ",".join(str(c) for c in sorted(os.sched_getaffinity(0)) if c <= 119)
    env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=os.path.join(tmp, "no-marker"))
    for d in (new, old):
        r = run(["bash", os.path.join(d, "build12.sh")], env=env)
        check("stand-in build: build12.sh exit 0 in %s" % os.path.basename(d), r.returncode == 0, r.stderr[-400:])
        if r.returncode:
            return
    names = run([os.path.join(new, "bwx12"), "--list"]).stdout.split()
    check("stand-in build: --list prints 55 names, the 26 new ones last and in the order of check_listing12.py",
          len(names) == 55 and names[29:] == list(cl.NEW), names[29:])
    st = open(os.path.join(new, "selftest-bwx12.txt")).read()
    rows = [l.split(",") for l in st.splitlines() if not l.startswith(("#", "call,"))]
    per = {k: sum(1 for r in rows if r[0] == k and r[-1] == "pass") for k in cl.NEW}
    want = {k: 8 if k.startswith("read") else 5 if k.startswith("write") else 8 for k in cl.NEW}
    check("stand-in build: the self-test has 8 passed checks per new read kernel, 5 per write kernel, 8 per copy kernel",
          per == want and "FAIL" not in st and st.rstrip().endswith("# failures=0"), per)
    r = checker([os.path.join(new, "listing.txt"), "--ref-listing", os.path.join(old, "listing.txt"),
                 "--ref-offsets", os.path.join(old, "offsets.tsv"), "--ref-binary", "bwx12", "--skip-new"])
    check("stand-in build: the 29 old kernels have the same machine code and loop offset with and without the new kernels",
          r.returncode == 0 and "kernels=29 failed_rows=0" in r.stdout, r.stdout[-600:])
    place = [l for l in open(os.path.join(new, "build.txt")) if l.startswith("## placement bwx12")]
    place_old = [l for l in open(os.path.join(old, "build.txt")) if l.startswith("## placement bwx12")]
    check("stand-in build: call() to timed_sequence_hot() start at the same offsets modulo 64 with and without the new kernels",
          place and place == place_old, (place, place_old))


FRAME = ["stp d8, d9, [sp, #-64]!", "END", "stp d10, d11, [sp, #16]", "stp d12, d13, [sp, #32]", "stp d14, d15, [sp, #48]"]
UNFRAME = ["ldp d10, d11, [sp, #16]", "ldp d12, d13, [sp, #32]", "ldp d14, d15, [sp, #48]", "ldp d8, d9, [sp], #64"]


def aarch64_functions(tmp):
    """{kernel: (pad, [instruction text before the loop], [loop], [after the loop])} from gcc -E -D__aarch64__"""
    stub = os.path.join(tmp, "stub")
    os.mkdir(stub)
    open(os.path.join(stub, "arm_neon.h"), "w").write("")
    r = run(["gcc", "-E", "-P", "-D__aarch64__", "-I", stub, os.path.join(HERE, "bwx12.c")])
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])
    text = r.stdout
    out = {}
    for k in cl.NEW:
        m = re.search(r'__asm__\(((?:\s*"[^"]*")+)\s*\);\s*__attribute__\(\(noinline\)\) static void k_%s\(([^)]*)\)\s*\{(.*?)\n\}' % k,
                      text, re.S)
        if not m:
            raise RuntimeError("no function k_%s in the expanded text" % k)
        place = "".join(re.findall(r'"([^"]*)"', m.group(1))).replace("\\n", "\n")
        pad = eval(re.search(r"\.fill (.*), 1, 0", place).group(1))  # an expression of numbers, from our own source
        body = m.group(3)
        a = body.index("__asm__ volatile(")
        # the template: the string literals up to the first ':' that stands outside a string
        i, lit = a + len("__asm__ volatile("), []
        while True:
            c = body[i]
            if c == '"':
                j = i + 1
                while body[j] != '"':
                    j += 2 if body[j] == "\\" else 1
                lit.append(body[i + 1:j])
                i = j + 1
            elif c == ":":
                break
            else:
                i += 1
        operands = body[i:body.index(");", i)]  # the operand and clobber lists of this asm statement only
        asm = "".join(lit).replace("\\n", "\n").replace("\\t", "\t")
        copy = "restrict d" in m.group(2)
        reg = {"s": "x1", "d": "x0", "end": "x2"} if copy else {"p": "x0", "end": "x1", "v": "x2"}
        lines, rep = [], None
        for line in asm.split("\n"):
            line = re.sub(r"%\[(\w+)\]", lambda g: reg[g.group(1)], line.strip())
            if not line:
                continue
            g = re.fullmatch(r"\.rept (\d+)", line)
            if g:
                rep = (int(g.group(1)), [])
            elif line == ".endr":
                lines += rep[1] * rep[0]
                rep = None
            elif rep is not None:
                rep[1].append(line)
            else:
                lines.append(line)
        at = lines.index("1:")
        init, loop = lines[:at], lines[at + 1:]
        if loop[-1] != "b.lo 1b":
            raise RuntimeError("%s: the template does not end with b.lo 1b" % k)
        loop = loop[:-1]
        # the spelling of objdump: immediates of add and movi in hex
        def spell(t):
            t = re.sub(r"^(add x\d, x\d, )#(\d+)$", lambda g: "%s#0x%x" % (g.group(1), int(g.group(2))), t)
            return re.sub(r"^(movi v\d+\.4s, )#(\d+)$", lambda g: "%s#0x%x" % (g.group(1), int(g.group(2))), t)
        init, loop = [spell(t) for t in init], [spell(t) for t in loop]
        end = cl.COPY_END_POINTER if copy else cl.END_POINTER
        framed = '"v8"' in operands
        head = [end if t == "END" else t for t in FRAME] if framed else [end]
        out[k] = (pad, head + init, loop, (UNFRAME if framed else []) + ["ret"], operands)
    return out


def synth(funcs, binary="bwx12", start=0x6000, change=None):
    """(listing text, offsets rows) of the new kernels; change(kernel, pad, head, loop, tail) may alter one"""
    text, rows, addr = [], [], start
    for k, (pad, head, loop, tail, _) in funcs.items():
        head, loop, tail = list(head), list(loop), list(tail)
        if change:
            pad, head, loop, tail = change(k, pad, head, loop, tail)
        addr = (addr + 63) // 64 * 64 + pad
        first, loop_at = addr, addr + 4 * len(head)
        text.append("=== %s %s ===\n%016x <k_%s>:" % (binary, k, first, k))
        for t in head + loop + ["b.cc %x <k_%s+0x%x>  // b.lo, b.ul, b.last" % (loop_at, k, loop_at - first)] + tail:
            op, _, arg = t.partition(" ")
            text.append("    %x:\t%s\t%s" % (addr, op, arg))
            addr += 4
        text.append("")
        rows.append("%s\t%s\tk_%s\t%x\t%x\t%d" % (binary, k, k, first, loop_at, loop_at % 64))
    return "\n".join(text) + "\n", "\n".join(rows) + "\n"


def test_aarch64_text(tmp):
    try:
        funcs = aarch64_functions(tmp)
    except RuntimeError as e:
        check("AArch64 text: the expanded source has the asm template of every new kernel", False, e)
        return
    check("AArch64 text: the expanded source has the asm template of every new kernel", len(funcs) == 26)
    ref_l = open(os.path.join(REF, "listing.txt")).read().replace("=== bwx11 ", "=== bwx12 ")
    ref_o = open(os.path.join(REF, "offsets.tsv")).read().replace("bwx11\t", "bwx12\t")

    def result(change=None):
        l, o = synth(funcs, change=change)
        lp, op = os.path.join(tmp, "syn-listing.txt"), os.path.join(tmp, "syn-offsets.tsv")
        open(lp, "w").write(ref_l + l)
        open(op, "w").write(ref_o + o)
        return checker([lp, op])

    r = result()
    check("AArch64 text: the listing made from the source text passes check_listing12.py (26 new kernels, loop offsets 20, 40, 52)",
          r.returncode == 0 and "new_kernels=26 new_failed_rows=0" in r.stdout and "kernels=29 failed_rows=0" in r.stdout,
          "\n".join(l for l in r.stdout.splitlines() if "FAIL" in l)[:1500])
    # clobber lists: every v register of the text is named as a clobber
    bad = []
    for k, (_, head, loop, _, operands) in funcs.items():
        used = {int(n) for t in head + loop for n in re.findall(r"\b[qv](\d+)\b", t)}
        named = {int(n) for n in re.findall(r'"v(\d+)"', operands)}
        if not used <= named:
            bad.append((k, sorted(used - named)))
    check("AArch64 text: every vector register that a new kernel uses is in its clobber list", not bad, bad)

    def one_nop_less(victim):
        def f(k, pad, head, loop, tail):
            if k == victim:
                loop.remove("nop")
            return pad, head, loop, tail
        return f

    def other_source(k, pad, head, loop, tail):
        if k == "read_dadd8":
            loop[loop.index("add v17.2d, v17.2d, v2.2d")] = "add v17.2d, v17.2d, v24.2d"
        return pad, head, loop, tail

    def moved(k, pad, head, loop, tail):
        return (pad + 4 if k == "write_nop96" else pad), head, loop, tail

    def no_d8(k, pad, head, loop, tail):
        if k == "read_iadd16":
            head[0] = "sub sp, sp, #0x40"
        return pad, head, loop, tail

    def no_init(k, pad, head, loop, tail):
        if k == "read_dadd2":
            head.remove("movi v16.4s, #0x0")
            pad += 4
        return pad, head, loop, tail

    for name, change, kernel in (("one nop less in read_nop256", one_nop_less("read_nop256"), "read_nop256"),
                                 ("one nop less in copy_nop192", one_nop_less("copy_nop192"), "copy_nop192"),
                                 ("one nop less in read_sp56", one_nop_less("read_sp56"), "read_sp56"),
                                 ("an add of read_dadd8 that takes v24 in place of a loaded register", other_source, "read_dadd8"),
                                 ("the loop of write_nop96 moved by 4 B", moved, "write_nop96"),
                                 ("read_iadd16 without the store of d8 and d9", no_d8, "read_iadd16"),
                                 ("read_dadd2 without the movi of v16", no_init, "read_dadd2")):
        r = result(change)
        failed = [l.split("\t")[0] for l in r.stdout.splitlines() if "\tFAIL" in l]
        check("check_listing12.py fails, on this kernel only: %s" % name, r.returncode == 1 and failed == [kernel], failed)


def main():
    tmp = tempfile.mkdtemp(prefix="bwx12-test-")
    try:
        test_source(tmp)
        test_standin(tmp)
        test_aarch64_text(tmp)
    finally:
        if os.environ.get("KEEP"):
            print("# kept: %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print("# failed checks: %d" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
