"""Static checks of a built diagram page (fail loud; run before delivery).

Usage: python3 check_page.py <page.html>
Checks:
  1. pure ASCII
  2. SVG ids unique; every marker url(#x) resolves inside its own SVG
  3. every <article class="unit"> in section 2 has at least one <svg>
  4. every <figure> has a non-empty <figcaption> and a box register
  5. every box-register source "<basename>:<a>[-<b>]" points at head lines
     that contain the box's first identifier (the defining line), within
     +-3 lines of the range; Note [name] sources must exist in the file set
  6. every internal href="#x" resolves to an id
  7. no SVG text element is wider than its viewBox (rough estimate)
"""
import html
import os
import re
import subprocess
import sys

WT = "/home/jhan/workspace/ai-runs/tron-split-pr3"
HEAD = "b39765ec29"
FILES = {
    "kv_cache.hpp": "h/tron/models/kv_cache.hpp",
    "k_vnni.hpp": "h/tron/tensor/k_vnni.hpp",
    "kernels/k_vnni.hpp": "h/tron/kernels/k_vnni.hpp",
    "model.hpp": "h/tron/models/model.hpp",
    "common.hpp": "h/tron/models/common.hpp",
    "self_attention.hpp": "h/tron/models/self_attention.hpp",
    "full.hpp": "h/tron/scheduler/full.hpp",
    "gof.hpp": "h/tron/gof.hpp",
    "gof.cpp": "src/tron/gof.cpp",
    "amx_attn_iface.hpp": "h/tron/kernels/amx_attn_iface.hpp",
    "amx_attn.cpp": "src/tron/kernels/amx_attn.cpp",
    "kv_cache_fwd.hpp": "h/tron/tensor/kv_cache_fwd.hpp",
    "v_vnni.hpp": "h/tron/tensor/v_vnni.hpp",
    "TronCpp.hs": "ingest/src/TronCpp.hs",
    "t_llama_unit.cpp": "t/t_llama_unit.cpp",
    "t_k_vnni_layout.cpp": "t/t_k_vnni_layout.cpp",
    "attn_stats.hpp": "h/tron/models/attn_stats.hpp",
    "view.hpp": "h/tron/tensor/view.hpp",
    "attention_ids.hpp": "h/tron/attention_ids.hpp",
    "t_amx_dispatch_dtype.cpp": "t/t_amx_dispatch_dtype.cpp",
    "t_amx_numerics.cpp": "t/t_amx_numerics.cpp",
    "shard.hpp": "h/tron/shard.hpp",
    "attention_slots.hpp": "h/tron/hardware/attention_slots.hpp",
    "seq.hpp": "h/tron/tensor/seq.hpp",
    "slice.hpp": "h/tron/tensor/slice.hpp",
    "tensor.hpp": "h/tron/tensor/tensor.hpp",
    "LoopyTronSpec.hs": "ingest/test/LoopyTronSpec.hs",
    "README.ci.md": "README.ci.md",
    "dotter.hpp": "h/tron/kernels/dotter.hpp",
    "bf16.hpp": "h/common/numerics/bf16.hpp",
    "fp16.hpp": "h/common/numerics/fp16.hpp",
    "attributes.hpp": "h/common/attributes.hpp",
    "t_phase1_integration.cpp": "t/t_phase1_integration.cpp",
    "t_gof_dma.cpp": "t/t_gof_dma.cpp",
    "t_gof_staging_leaks.cpp": "t/t_gof_staging_leaks.cpp",
    "src/tron/CMakeLists.txt": "src/tron/CMakeLists.txt",
    "page_share_counters.hpp": "h/tron/kernels/page_share_counters.hpp",
}
BASE = "26b86a279a"
STOP = {"the", "and", "for", "with", "from", "into", "case", "state", "before", "after", "worked",
        "example", "step", "stage", "then", "else", "this", "that", "page", "slot", "block", "row",
        "rows", "bits", "bit", "entry", "lane", "lanes", "all", "any", "one", "two", "per", "its",
        "new", "removed", "changed", "head", "base", "main", "thread", "helper", "helpers", "worker",
        "workers", "user", "window", "unit", "units", "list", "call", "calls", "caller", "callers",
        "test", "tests", "only", "same", "whole", "partial", "token", "tokens", "line", "lines",
        "mask", "masks", "true", "false", "when", "where", "what", "who", "not", "yet", "may",
        "data", "model", "layout", "first", "last", "next", "every", "each", "none", "deleted"}
_cache = {}
_bcache = {}


def base_lines(base):
    if base not in _bcache:
        path = FILES.get(base)
        if path is None:
            return None
        r = subprocess.run(["git", "-C", WT, "show", f"{BASE}:{path}"], capture_output=True, text=True)
        _bcache[base] = r.stdout.split("\n") if r.returncode == 0 else []
    return _bcache[base]


def label_tokens(label):
    """Identifier tokens of a box label worth looking up: code names (with an
    underscore or a scope) and words of 4+ letters that are not plain prose."""
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*", label)
    out = []
    for t in toks:
        t = t.split("::")[-1].rstrip(":")
        called = re.search(re.escape(t) + r"\s*\(", label) is not None
        if "_" in t or called or (len(t) >= 4 and t.lower() not in STOP):
            if t not in out:
                out.append(t)
    return out


def source_ranges(source):
    """(is_base, file, a, b) for every range of a source string: 'f.hpp:12-20,
    30-31; g.cpp:7' gives three ranges, the continuation ranges keep the last
    file."""
    out = []
    pat = re.compile(r"(base\s+)?([A-Za-z0-9_./]+\.(?:hpp|cpp|hs|md|txt)):(\d+)(?:-(\d+))?"
                     r"((?:\s*,\s*\d+(?:-\d+)?)*)")
    for m in pat.finditer(source):
        is_base, f = bool(m.group(1)), m.group(2)
        out.append((is_base, f, int(m.group(3)), int(m.group(4) or m.group(3))))
        for c in re.finditer(r"(\d+)(?:-(\d+))?", m.group(5) or ""):
            out.append((is_base, f, int(c.group(1)), int(c.group(2) or c.group(1))))
    return out


def head_lines(base):
    if base not in _cache:
        path = FILES.get(base)
        if path is None:
            return None
        out = subprocess.run(["git", "-C", WT, "show", f"{HEAD}:{path}"], capture_output=True,
                             text=True, check=True).stdout
        _cache[base] = out.split("\n")
    return _cache[base]


def main(page):
    src = open(page, encoding="utf-8").read()
    problems = []
    non_ascii = sorted(set(c for c in src if ord(c) > 127))
    if non_ascii:
        problems.append(f"1. non-ASCII characters: {non_ascii[:10]}")
    svgs = re.findall(r'(<svg id="([A-Za-z0-9_-]+)".*?</svg>)', src, flags=re.S)
    ids = [i for _, i in svgs]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        problems.append(f"2. duplicate svg ids: {dups}")
    for blob, fid in svgs:
        defined = set(re.findall(r'<marker id="([^"]+)"', blob))
        used = set(re.findall(r'url\(#([^)]+)\)', blob))
        miss = used - defined
        if miss:
            problems.append(f"2. {fid}: markers used but not defined in this svg: {sorted(miss)}")
        vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', blob)
        W = int(vb.group(1))
        for m in re.finditer(r'<text x="([\d.]+)" y="[\d.]+" text-anchor="(\w+)" style="font-family:([^;]+);font-size:([\d.]+)px[^"]*"[^>]*>([^<]*)</text>', blob):
            x, anchor, fam, size, s = float(m.group(1)), m.group(2), m.group(3), float(m.group(4)), html.unescape(m.group(5))
            per = 0.60 if "monospace" in fam else 0.55
            w = len(s) * size * per
            x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
            if x0 < -1 or x0 + w > W + 1:
                problems.append(f"7. {fid}: text may exceed the viewBox: '{s[:50]}' at x={x} anchor={anchor} est. width {w:.0f}")
    # 3. units in section 2
    sec2 = src.split('<section id="changes">')[1].split("</section>")[0]
    for art in re.findall(r'<article class="unit" id="([^"]+)">(.*?)</article>', sec2, flags=re.S):
        uid, body = art
        n = body.count("<svg ")
        if n == 0:
            problems.append(f"3. unit {uid} has no diagram")
    # 4/5. figures
    for fig in re.findall(r"<figure.*?</figure>", src, flags=re.S):
        fid = re.search(r'<svg id="([^"]+)"', fig)
        fid = fid.group(1) if fid else "?"
        cap = re.search(r"<figcaption>(.*?)</figcaption>", fig, flags=re.S)
        if not cap or len(html.unescape(cap.group(1)).strip()) < 20:
            problems.append(f"4. {fid}: caption missing or too short")
        reg = re.search(r'<details class="boxes">.*?<ul>(.*?)</ul>', fig, flags=re.S)
        if not reg:
            problems.append(f"4. {fid}: no box register (figure(..., boxes=[...]))")
            continue
        for item in re.findall(r"<li><code>(.*?)</code>: (.*?)</li>", reg.group(1), flags=re.S):
            label, source = html.unescape(item[0]), html.unescape(item[1])
            ok = False
            toks = label_tokens(label)
            if not toks:
                ok = True   # a prose-only label (a legend row, a page-internal name)
            if re.search(r"(^|\s)#[A-Za-z0-9_-]+", source):   # a page anchor as source
                ok = True
            for is_base, base, a, b in source_ranges(source):
                base = base.rsplit("/", 1)[-1] if base not in FILES else base
                lines_ = base_lines(base) if is_base else head_lines(base)
                if lines_ is None:
                    problems.append(f"5. {fid}: unknown file in source '{source}'")
                    ok = True
                    break
                lo, hi = max(1, a - 3), min(len(lines_), b + 3)
                window = "\n".join(lines_[lo - 1:hi]).lower()
                if any(t.lower() in window for t in toks):
                    ok = True
                    break
            if not ok and re.search(r"Note \[", source):
                note = re.search(r"Note \[[^\]]+\]", source).group(0)
                for base in FILES:
                    ls = head_lines(base)
                    if ls and any(note in ln for ln in ls):
                        ok = True
                        break
            if not ok:
                problems.append(f"5. {fid}: box '{label}' not found at its source '{source}'")
    # 6. anchors
    ids_all = set(re.findall(r'id="([^"]+)"', src))
    for href in set(re.findall(r'href="#([^"]+)"', src)):
        if href not in ids_all:
            problems.append(f"6. dangling anchor #{href}")
    print(f"{os.path.basename(page)}: {len(svgs)} svgs, {len(problems)} problems")
    for p in problems:
        print("  ", p)
    return len(problems)


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1]) else 0)
