#!/usr/bin/env python3
"""Step F instruction comparison: parse `objdump -d -r --no-show-raw-insn -C`
output of harness_base.o and harness_branch.o, histogram mnemonics per h_*
function and per its in-object callee closure, and diff what differs.
Usage: analyze.py <base.objdump.txt> <branch.objdump.txt> <outdir>"""
import collections, difflib, os, re, sys

SYM_RE = re.compile(r"^[0-9a-f]+ <(.+)>:$")
INS_RE = re.compile(r"^\s*([0-9a-f]+):\t(.*)$")
REL_RE = re.compile(r"^\s+[0-9a-f]+: (R_X86_64_\w+)\t(.+?)(?:[-+]0x[0-9a-f]+)?$")
PREFIXES = {"lock", "rep", "repz", "repnz", "data16", "cs", "ds", "notrack", "bnd"}

def short(name):
    """Readable alias for the long template names."""
    name = re.sub(r"tron::detail::kv_layout<std::array<tron::kv_slot_spec, 1ul>\{tron::kv_slot_spec \[1\]\{tron::kv_slot_spec\{tron::kv_geometry\{1ul, 128ul\}, tron::kv_slot_retention\{\(tron::kv_slot_retention_kind\)1, 64ul\}\}\}\}, true, tron::kv_geometry\{1ul, 128ul\}>", "RECL_LAYOUT", name)
    name = re.sub(r"tron::detail::kv_layout<std::array<tron::kv_slot_spec, 1ul>\{tron::kv_slot_spec \[1\]\{tron::kv_slot_spec\{tron::kv_geometry\{1ul, 128ul\}\}\}\}, true, tron::kv_geometry\{1ul, 128ul\}>", "LAYOUT", name)
    name = name.replace("tron::book<1ul, 1ul, 128ul, 0ul, RECL_LAYOUT >", "recl_book_t")
    name = name.replace("tron::book<1ul, 1ul, 128ul, 0ul, LAYOUT >", "book_t")
    name = name.replace("tron::page<1ul, 1ul, 128ul, 0ul, RECL_LAYOUT >", "recl_page_t")
    name = name.replace("tron::page<1ul, 1ul, 128ul, 0ul, LAYOUT >", "page_t")
    name = name.replace("std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >", "std::string")
    if name.startswith("_ZN4tron4book") and "for_each_slot_impl" in name:
        name = "book_t::for_each_slot_impl<0>(copy_from lambda)  [mangled]"
    return name

def parse(path):
    funcs = collections.OrderedDict()
    cur = None
    for line in open(path):
        line = line.rstrip("\n")
        m = SYM_RE.match(line)
        if m:
            cur = m.group(1); funcs[cur] = []; continue
        if cur is None: continue
        m = REL_RE.match(line)
        if m and funcs[cur]:
            funcs[cur][-1]["reloc"] = (m.group(1), m.group(2)); continue
        m = INS_RE.match(line)
        if not m: continue
        text = m.group(2).split("#")[0].strip()
        if not text or text == "...": continue
        toks = text.split()
        mnem = toks[0]; rest = toks[1:]
        while mnem in PREFIXES and rest:      # 'rep stos', 'lock cmpxchg', 'cs nopw'
            mnem = mnem + " " + rest[0]; rest = rest[1:]
        ops = " ".join(rest)
        funcs[cur].append({"addr": m.group(1), "mnem": mnem, "ops": ops, "reloc": None})
    return funcs

def norm(ins):
    """Instruction text without addresses: for sequence comparison."""
    ops = re.sub(r"\b[0-9a-f]+ <.*>\s*$", "<JT>", ins["ops"])   # jump/call targets in-function (symbol+offset, may contain >)
    r = ins["reloc"]
    if r:
        sym = re.sub(r"^\.L\.str(\.\d+)?$", ".L.str", r[1])   # string-literal labels are numbered per TU
        return ins["mnem"] + " " + ops + "  ; " + r[0] + " " + short(sym)
    return ins["mnem"] + " " + ops

def callees(funcs, name):
    out = []
    for ins in funcs[name]:
        if ins["mnem"] in ("call", "jmp") and ins["reloc"]:
            out.append(ins["reloc"][1])
    return out

def closure(funcs, root):
    seen = collections.OrderedDict([(root, None)]); stack = [root]; ext = collections.OrderedDict()
    while stack:
        f = stack.pop()
        for c in callees(funcs, f):
            if c in funcs:
                if c not in seen: seen[c] = None; stack.append(c)
            else:
                ext[c] = None
    return list(seen), list(ext)

def hist(funcs, names):
    h = collections.Counter()
    for n in names:
        for ins in funcs[n]: h[ins["mnem"]] += 1
    return h

def fmt_hist(h):
    return ", ".join("%s %d" % (k, v) for k, v in sorted(h.items(), key=lambda kv: (-kv[1], kv[0])))

def hist_diff(hb, hr):
    keys = sorted(set(hb) | set(hr))
    return [(k, hb.get(k, 0), hr.get(k, 0)) for k in keys if hb.get(k, 0) != hr.get(k, 0)]

def main():
    base_p, br_p, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    B = parse(base_p); R = parse(br_p)
    roots = [n for n in B if n.startswith("h_")]
    assert roots == [n for n in R if n.startswith("h_")], "wrapper sets differ"
    rep = []
    P = rep.append
    P("Step F instruction comparison, base = %s, branch = %s" % (base_p, br_p))
    P("")
    P("Symbols only in base:   " + "; ".join(short(n) for n in B if n not in R))
    P("Symbols only in branch: " + "; ".join(short(n) for n in R if n not in B))
    P("")
    P("=" * 100)
    P("PER WRAPPER FUNCTION (the h_* body alone, callees NOT included)")
    P("=" * 100)
    P("%-22s %6s %6s  %s" % ("function", "base", "branch", "verdict / mnemonic differences (base -> branch)"))
    for r in roots:
        hb, hr = hist(B, [r]), hist(R, [r])
        nb = [norm(i) for i in B[r]]; nr = [norm(i) for i in R[r]]
        if nb == nr: v = "identical (instruction sequence)"
        elif hb == hr: v = "same mnemonic histogram, different operands/order (see diff)"
        else: v = "DIFFERS: " + "; ".join("%s %d->%d" % d for d in hist_diff(hb, hr))
        P("%-22s %6d %6d  %s" % (r, sum(hb.values()), sum(hr.values()), v))
        if nb != nr:
            with open(os.path.join(outdir, "diff_%s.txt" % r), "w") as f:
                f.write("\n".join(difflib.unified_diff(nb, nr, "base/" + r, "branch/" + r, lineterm="", n=3)) + "\n")
    P("")
    P("=" * 100)
    P("PER CALL CLOSURE (wrapper + every callee defined in the same object, transitively)")
    P("=" * 100)
    for r in roots:
        cb, eb = closure(B, r); cr, er = closure(R, r)
        hb, hr = hist(B, cb), hist(R, cr)
        P("")
        P("-- %s: closure base %d insns in %d funcs, branch %d insns in %d funcs" % (r, sum(hb.values()), len(cb), sum(hr.values()), len(cr)))
        sb = set(map(short, cb)); sr = set(map(short, cr))
        for n in cb: P("   base   callee: %-70s %5d insns" % (short(n), len(B[n])))
        for n in cr:
            if short(n) not in sb: P("   branch ONLY:   %-70s %5d insns" % (short(n), len(R[n])))
        for n in cb:
            if short(n) not in sr: P("   base ONLY:     %-70s" % short(n))
        P("   external callees base:   " + ", ".join(short(e) for e in eb))
        P("   external callees branch: " + ", ".join(short(e) for e in er))
        d = hist_diff(hb, hr)
        P("   closure histogram: " + ("IDENTICAL" if not d else "DIFFERS: " + "; ".join("%s %d->%d" % x for x in d)))
        # per-callee sequence comparison for shared callees
        for n in cb:
            m = [x for x in cr if short(x) == short(n)]
            if not m: continue
            nb = [norm(i) for i in B[n]]; nr = [norm(i) for i in R[m[0]]]
            if nb == nr: P("   callee %-60s identical" % short(n)[:60])
            else:
                hdb, hdr = hist(B, [n]), hist(R, [m[0]])
                dd = hist_diff(hdb, hdr)
                P("   callee %-60s %d -> %d insns; %s" % (short(n)[:60], len(nb), len(nr), ("same histogram, operands/order differ" if not dd else "; ".join("%s %d->%d" % x for x in dd))))
                fn = re.sub(r"[^A-Za-z0-9_]+", "_", short(n))[:80]
                with open(os.path.join(outdir, "diff_callee_%s.txt" % fn), "w") as f:
                    f.write("\n".join(difflib.unified_diff(nb, nr, "base/" + short(n), "branch/" + short(m[0]), lineterm="", n=3)) + "\n")
    P("")
    P("=" * 100)
    P("CLEARING / BULK-STORE SCAN in h_make_book and h_restore closures (both trees)")
    P("=" * 100)
    for r in ("h_make_book", "h_restore"):
        for tag, F in (("base", B), ("branch", R)):
            cl, ext = closure(F, r)
            hits = []
            for n in cl:
                for ins in F[n]:
                    t = ins["mnem"] + " " + ins["ops"]
                    rel = ins["reloc"][1] if ins["reloc"] else ""
                    if ins["mnem"].startswith("rep ") or "stos" in ins["mnem"] or re.search(r"memset|bzero|memcpy|memmove|fill", rel):
                        hits.append("%s @%s: %s  ; %s" % (short(n)[:50], ins["addr"], t, short(rel)))
            P("%-7s %-12s rep-stos/memset/bzero/memcpy hits in closure: %s" % (tag, r, ("NONE" if not hits else "")))
            for h in hits: P("      " + h)
            P("%-7s %-12s all call/jmp targets in closure:" % (tag, r))
            for n in cl:
                for c in callees(F, n):
                    P("      %-60s -> %s" % (short(n)[:60], short(c)))
    open(os.path.join(outdir, "report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))
    # full listings of the allocation-path functions for manual reading
    for tag, F in (("base", B), ("branch", R)):
        for r in ("h_make_book", "h_restore"):
            cl, _ = closure(F, r)
            with open(os.path.join(outdir, "listing_%s_%s.txt" % (tag, r)), "w") as f:
                for n in cl:
                    if "spdlog" in n or "tron_abort" in n or "basic_string" in n or "fmt::" in n: continue
                    f.write("==== %s\n" % short(n))
                    for ins in F[n]:
                        f.write("  %6s: %s\n" % (ins["addr"], norm(ins)))
                    f.write("\n")

main()
