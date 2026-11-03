import html, re, sys
G = "/home/jhan/workspace/intel-AMX/exec/pr5015-diagrams-20261018"
sys.path[:0] = [G, G + "/figs"]
import check_page as cp
import d_amx_attn_a4 as m
problems = []
for fig in re.findall(r"<figure.*?</figure>", "".join(m.figs()), flags=re.S):
    fid = re.search(r'<svg id="([^"]+)"', fig).group(1)
    blob = re.search(r'(<svg id="[^"]+".*?</svg>)', fig, flags=re.S).group(1)
    W = int(re.search(r'viewBox="0 0 (\d+) (\d+)"', blob).group(1))
    for mm in re.finditer(r'<text x="([\d.]+)" y="[\d.]+" text-anchor="(\w+)" style="font-family:([^;]+);font-size:([\d.]+)px[^"]*"[^>]*>([^<]*)</text>', blob):
        x, anchor, fam, size, s = float(mm.group(1)), mm.group(2), mm.group(3), float(mm.group(4)), html.unescape(mm.group(5))
        per = 0.60 if "monospace" in fam else 0.55
        w = len(s) * size * per
        x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        if x0 < -1 or x0 + w > W + 1:
            problems.append(f"7. {fid}: text may exceed the viewBox: '{s[:50]}' at x={x} est. width {w:.0f}")
    reg = re.search(r'<details class="boxes">.*?<ul>(.*?)</ul>', fig, flags=re.S)
    n = 0
    for item in re.findall(r"<li><code>(.*?)</code>: (.*?)</li>", reg.group(1), flags=re.S):
        n += 1
        label, source = html.unescape(item[0]), html.unescape(item[1])
        toks = cp.label_tokens(label)
        ok = not toks
        for is_base, base, a, b in cp.source_ranges(source):
            lines_ = cp.base_lines(base) if is_base else cp.head_lines(base)
            if lines_ is None:
                problems.append(f"5. {fid}: unknown file in source '{source}'"); ok = True; break
            lo, hi = max(1, a - 3), min(len(lines_), b + 3)
            window = "\n".join(lines_[lo - 1:hi]).lower()
            if any(t.lower() in window for t in toks):
                ok = True; break
        if not ok:
            problems.append(f"5. {fid}: box '{label}' not found at its source '{source}' (tokens {toks})")
    print(f"{fid}: {n} boxes checked")
print(f"{len(problems)} problems")
for p in problems: print("  ", p)
