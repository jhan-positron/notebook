#!/usr/bin/env python3
"""pr5606-check-20261123: symbol check for the one-definition rule of gen/t_amx_dispatch_dtype.

The one-definition rule of C++ says that every copy of an inline function or a template instance in a program
must come from the same source text. Here the test's own object file is compiled with -DTRON_AMX_DISPATCH and
everything else on its link line is compiled without. A function that both sides define would then exist in
two different versions, and the linker keeps only one.

Such functions are "weak" symbols (nm types W and V) or "unique" symbols (nm type u). This script
  1. reads the link line of the test (from `ninja -t commands`),
  2. lists the weak and unique symbols that the test's object defines, with sizes (nm -S --defined-only),
  3. lists the symbols that every other object file and every member of every static library on the link
     line defines,
  4. reads the linker map of a second link of the same command (lld -Map), which names the object that each
     symbol of the final binary comes from, and the objects that the linker really used,
  5. prints the counts and the lists described in the README.
Usage: symbols.py <gen dir> <link line file> <linker map file> <final binary> <output dir>
"""
import collections
import os
import re
import shlex
import subprocess
import sys

gen, link_file, map_file, binary, outdir = sys.argv[1:6]
TEST_OBJ = "t/CMakeFiles/t_amx_dispatch_dtype.dir/t_amx_dispatch_dtype.cpp.o"
WEAK = set("WVu")
WORDS = ("self_attention", "apply_page", "apply_dense", "amx_attn")
NS = "tron::amx_attn_h128g4::"


def sh(args):
    return subprocess.run(args, cwd=gen, capture_output=True, text=True, errors="replace").stdout


def demangle(names):
    names = list(names)
    if not names:
        return {}
    out = subprocess.run(["llvm-cxxfilt-19"], input="\n".join(names) + "\n", capture_output=True, text=True).stdout.split("\n")
    return dict(zip(names, out))


# ---- 1. the link line -------------------------------------------------------------------------------------
link = open(link_file).read().strip()
seg = [s for s in link.split(" && ") if " -o t_amx_dispatch_dtype " in s][0]
toks = shlex.split(seg)
objs = [t for t in toks if t.endswith(".o")]
archives = list(dict.fromkeys(t for t in toks if t.endswith(".a")))
shared = list(dict.fromkeys(t for t in toks if ".so" in os.path.basename(t) or t.startswith("-l")))
assert TEST_OBJ in objs, "the test object is not on the link line"
print(f"link line: {len(objs)} object files, {len(archives)} static libraries, {len(shared)} shared libraries")
print("  object files, in link order: " + ", ".join(objs))
print("  static libraries: " + ", ".join(archives))
print("  shared libraries (not inspected, their code is not copied into the binary): " + ", ".join(shared))

# ---- 2 and 3. nm ------------------------------------------------------------------------------------------
NM = re.compile(r"^(?:(?P<file>[^:]+):(?:(?P<member>[^:]+):)?)?(?P<addr>[0-9a-f]+) (?:(?P<size>[0-9a-f]+) )?(?P<type>\S) (?P<name>.+)$")


def nm_defined(path):
    """Yields (object label, type, size or None, name) for every defined symbol of an object or archive."""
    for line in sh(["nm", "-S", "--defined-only", "-A", path]).split("\n"):
        m = NM.match(line)
        if not m:
            continue
        label = m.group("file") + (f"({m.group('member')})" if m.group("member") else "")
        size = int(m.group("size"), 16) if m.group("size") else None
        yield label, m.group("type"), size, m.group("name")


test_weak = {}
test_all = {}
for label, typ, size, name in nm_defined(TEST_OBJ):
    test_all[name] = (typ, size)
    if typ in WEAK:
        test_weak[name] = (typ, size)
print(f"\ntest object {TEST_OBJ}:")
print(f"  defined symbols: {len(test_all)}; weak or unique (nm types W, V, u): {len(test_weak)} "
      f"({dict(collections.Counter(t for t, _ in test_weak.values()))})")

others = collections.defaultdict(list)  # name -> [(object label, type, size)]
n_obj = collections.Counter()
for path in [o for o in objs if o != TEST_OBJ] + archives:
    seen = set()
    for label, typ, size, name in nm_defined(path):
        others[name].append((label, typ, size))
        seen.add(label)
    n_obj[path] = len(seen)
print(f"other objects on the link line with at least one defined symbol: {sum(n_obj.values())} "
      f"(per file: " + ", ".join(f"{os.path.basename(k)} {v}" for k, v in n_obj.items()) + ")")

# ---- 4. the linker map ------------------------------------------------------------------------------------
# lld map: VMA LMA Size Align, then the output section, or 8 spaces + "file:(section)", or 16 spaces + symbol.
MAPLINE = re.compile(r"^\s*([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+(\d+) (.*)$")
origin = {}  # symbol name as the map prints it -> object label
used = collections.Counter()
cur = None
for line in open(map_file, errors="replace"):
    m = MAPLINE.match(line.rstrip("\n"))
    if not m:
        continue
    rest = m.group(5)
    if rest.startswith(" " * 16):
        if cur:
            origin.setdefault(rest.strip(), cur)
    elif rest.startswith(" " * 8):
        r = rest.strip()
        k = r.rfind(":(")
        cur = r[:k] if k > 0 else None
        if cur and not cur.startswith("<"):
            used[cur] += 1
    else:
        cur = None
print(f"\nlinker map: {len(used)} objects gave at least one section to the binary; {len(origin)} symbols have an origin")
used_objs = set(used)


def is_used(label):
    return label in used_objs


# ---- 5. the counts ----------------------------------------------------------------------------------------
def report(title, pick):
    common = {n: [d for d in others.get(n, []) if pick(d[0])] for n in test_weak}
    common = {n: ds for n, ds in common.items() if ds}
    differ = {n: ds for n, ds in common.items() if any(d[2] != test_weak[n][1] for d in ds)}
    print(f"\n{title}")
    print(f"  weak or unique symbols of the test object that another object also defines: {len(common)}")
    print(f"  of those, with a size that differs from the test object's size: {len(differ)}")
    kinds = collections.Counter(d[1] for ds in common.values() for d in ds)
    print(f"  nm types of the other definitions: {dict(kinds)}")
    return common, differ


common_all, differ_all = report("A. against every object and library member on the link line:", lambda label: True)
common_used, differ_used = report("B. against the objects that the linker really used (linker map):", is_used)

dm = demangle(set(test_all) | set(others) | set(origin))
with open(f"{outdir}/common-symbols.tsv", "w") as f:
    f.write("# symbol defined in the test object (weak or unique) and in another object on the link line\n")
    f.write("# size in test object\tsizes elsewhere\tsize differs\tused by linker elsewhere\tobject the binary takes it from\tdemangled name\n")
    for n in sorted(common_all, key=lambda x: dm.get(x, x)):
        ds = common_all[n]
        sizes = sorted({d[2] for d in ds if d[2] is not None})
        f.write(f"{test_weak[n][1]}\t{','.join(map(str, sizes))}\t{'yes' if n in differ_all else 'no'}\t"
                f"{'yes' if n in common_used else 'no'}\t{origin.get(n) or origin.get(dm.get(n, n)) or '-'}\t{dm.get(n, n)}\n")

with open(f"{outdir}/defs.tsv", "w") as f:
    f.write("# every definition of a symbol that the test object defines as weak or unique\n# mangled name\tobject (TEST = the test object)\tnm type\tsize\n")
    for n in sorted(test_weak):
        f.write(f"{n}\tTEST\t{test_weak[n][0]}\t{test_weak[n][1]}\n")
        for label, typ, size in others.get(n, []):
            f.write(f"{n}\t{label}\t{typ}\t{size}\n")


def family(name):
    """The library a symbol belongs to, judged by the namespaces its demangled name mentions."""
    d = dm.get(name, name)
    for key, fam in (("tron::", "mentions tron::"), ("fmt::", "fmt (formatting library)"), ("nlohmann::", "nlohmann (JSON library)"),
                     ("spdlog::", "spdlog (logging library)"), ("Catch::", "Catch2 (test framework)"), ("std::", "C++ standard library"),
                     ("__gnu_cxx::", "C++ standard library")):
        if key in d:
            return fam
    return "other"


print("\nC. the common symbols of count A by library (all / with a size difference):")
fam_all = collections.Counter(family(n) for n in common_all)
fam_diff = collections.Counter(family(n) for n in differ_all)
for fam, c in sorted(fam_all.items(), key=lambda kv: -kv[1]):
    print(f"  {fam}: {c} / {fam_diff.get(fam, 0)}")
tron_diff = sorted((n for n in differ_all if family(n) == "mentions tron::"), key=lambda x: dm.get(x, x))
print(f"  common symbols that mention tron:: and differ in size: {len(tron_diff)} (first 30 follow)")
for n in tron_diff[:30]:
    ds = differ_all[n]
    print(f"    test {test_weak[n][1]} B; elsewhere " + ", ".join(sorted({f'{d[2]} B in {d[0]}' for d in ds})[:3])
          + f" | binary takes it from {origin.get(n) or origin.get(dm.get(n, n)) or '-'} | {dm.get(n, n)[:220]}")
takes = collections.Counter((origin.get(n) or origin.get(dm.get(n, n)) or "-") == TEST_OBJ for n in common_used)
print(f"  of the {len(common_used)} common symbols of count B, the binary takes {takes.get(True, 0)} from the test object and {takes.get(False, 0)} from another object")
if differ_all:
    print("\n   symbols with a size difference (first 12, by name); full list in common-symbols.tsv:")
    for n in sorted(differ_all, key=lambda x: dm.get(x, x))[:12]:
        ds = differ_all[n]
        print(f"  test {test_weak[n][1]} B; elsewhere " + ", ".join(sorted({f'{d[2]} B in {d[0]}' for d in ds})[:3])
              + f" | binary takes it from {origin.get(n) or origin.get(dm.get(n, n)) or '-'} | {dm.get(n, n)[:200]}")

print("\nD. common symbols whose demangled name contains " + ", ".join(WORDS) + ":")
hits = [n for n in common_all if any(w in dm.get(n, n) for w in WORDS)]
print(f"  count: {len(hits)}")
for n in sorted(hits, key=lambda x: dm.get(x, x)):
    ds = common_all[n]
    print(f"  test {test_weak[n][1]} B; elsewhere " + ", ".join(sorted({f'{d[2]} B in {d[0]}' for d in ds}))
          + f" | {dm.get(n, n)[:300]}")
n_test_words = collections.Counter()
for n in test_weak:
    for w in WORDS:
        if w in dm.get(n, n):
            n_test_words[w] += 1
print(f"  for scale, weak or unique symbols of the test object alone that contain each word: {dict(n_test_words)}")
n_other_words = collections.Counter()
for n in others:
    for w in WORDS:
        if w in dm.get(n, n):
            n_other_words[w] += 1
print(f"  symbols of the other objects that contain each word: {dict(n_other_words)}")

# ---- namespace tron::amx_attn_h128g4 in the final binary --------------------------------------------------
print(f"\nE. symbols of namespace {NS[:-2]} in the final binary, and the object each one comes from:")
final = []
for line in sh(["nm", "-S", "--defined-only", binary]).split("\n"):
    m = NM.match(line)
    if m:
        final.append((m.group("type"), int(m.group("size"), 16) if m.group("size") else None, m.group("name")))
fdm = demangle({n for _, _, n in final})
rows = [(t, s, n) for t, s, n in final if NS in fdm.get(n, n)]
by_origin = collections.Counter()
for t, s, n in sorted(rows, key=lambda r: fdm.get(r[2], r[2])):
    src = origin.get(n) or origin.get(fdm.get(n, n)) or "?"
    definers = sorted({d[0] for d in others.get(n, [])} | ({TEST_OBJ} if n in test_all else set()))
    by_origin[src] += 1
    starts = fdm.get(n, n).startswith(NS)
    print(f"  [{t}] {s} B from {src} | defined on the link line by: {', '.join(definers) or '-'} | "
          f"{'entry point' if starts else 'mentions the namespace'}: {fdm.get(n, n)[:230]}")
print(f"  count: {len(rows)}; by origin: {dict(by_origin)}")

# ---- undefined symbols of the test object that touch the dispatch template --------------------------------
print("\nF. undefined symbols of the test object whose name contains self_attention, attn_accum or amx_attn")
print("   (a call from the test object into code that another object compiled without the define):")
und = [l.split()[-1] for l in sh(["nm", "-u", TEST_OBJ]).split("\n") if l.strip()]
udm = demangle(set(und))
uh = [n for n in und if any(w in udm.get(n, n) for w in ("self_attention", "attn_accum", "amx_attn"))]
print(f"  undefined symbols of the test object: {len(und)}; with one of the three words: {len(uh)}")
for n in uh[:20]:
    print(f"  defined by {', '.join(sorted({d[0] for d in others.get(n, [])})) or 'nothing on the link line'} | {udm.get(n, n)[:230]}")

# ---- which other objects define any instance of the template ----------------------------------------------
defs = collections.Counter()
for n, ds in others.items():
    if "tron::self_attention<" in dm.get(n, n):
        for label, typ, size in ds:
            defs[label] += 1
n_test = sum(1 for n in test_all if "tron::self_attention<" in dm.get(n, n))
print(f"\nG. symbols of the template tron::self_attention<...>: {n_test} defined in the test object; "
      f"{sum(defs.values())} defined in {len(defs)} other objects on the link line")
for label, c in sorted(defs.items(), key=lambda kv: -kv[1])[:25]:
    print(f"  {c} symbols in {label} (used by the linker: {'yes' if is_used(label) else 'no'})")
