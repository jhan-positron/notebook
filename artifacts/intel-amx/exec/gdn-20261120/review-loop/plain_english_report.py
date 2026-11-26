#!/usr/bin/env python3
"""Build the check report of the plain-English pass: counts by rule, text statistics before and after, the violation table."""
import html, importlib.util, json, re, sys, collections, hashlib
SP = sys.argv[1]
OLD, NEW, OUT = SP + "/pe/base/out/page.html", "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html", sys.argv[2]
spec = importlib.util.spec_from_file_location("ck", "/home/jhan/.claude/skills/plain-english-experiment/scripts/check_lengths.py")
ck = importlib.util.module_from_spec(spec); spec.loader.exec_module(ck)


def cells(s):   # table cells and captions as paragraphs, so that their prose is counted too
    t = re.sub(r"<(/?)(td|th|figcaption)\b[^>]*>", lambda m: f"<{m.group(1)}p>", s)
    return re.sub(r"</?(table|thead|tbody|tr)\b[^>]*>", "", t)


def measure(path):
    s = open(path).read()
    b = ck.analyse(s, "html"); st = ck.stats(b)
    bc = ck.analyse(cells(s), "html")
    v = len(ck.violations(bc))
    labels = sum(1 for x in b if x["kind"] == "bullet" and x["label"] and x["label"] != "est.")   # "est." is a term of the word list
    return dict(sentences=st["sentences"], mean=st["mean"], longest=st["max"], over25=round(st["over25"] * st["sentences"] / 100), bullets=st["bullets"],
                bul_over3=st["n_bullet_over3"], labels=labels, script=v)


before, after = measure(OLD), measure(NEW)
d = json.load(open(SP + "/pe/writers-result.json"))
PARTS = {"w1": "Top of the page, Short version and Words used here", "w2": "Sections 1, 2 and 3 (first part)", "w3": "Section 3 (What the numbers say) and section 4 (Method)",
         "w4": "Section 4 (factor table, clock note, reading and tests of the prediction)", "w5": "Sections 5.1, 5.2 and 5.3", "w6": "Sections 5.4, 5.5 and 5.7",
         "w7": "Section 5.6 and section 6", "w8": "Section 7 (Sources)"}
by_rule = collections.Counter()
for x in d:
    seen = set()
    for k, v in re.findall(r"rule\s*(\d)\s*:\s*(\d+)", x["result"]["counts_by_rule"], flags=re.I):
        if k not in seen:
            seen.add(k); by_rule[int(k)] += int(v)
total = sum(by_rule.values())
NAMES = {1: "idioms and uncommon words", 2: "one claim per sentence", 3: "sentence length and long parentheses", 4: "lists, paragraph size and labels",
         5: "citations", 6: "numbers and units", 7: "Short version", 8: "terms defined at first use"}
esc = lambda t: html.escape(str(t), quote=False)
sha = hashlib.sha256(open(NEW, "rb").read()).hexdigest()

# ---- chart: violations by rule before the rewrite (after: 0 for every rule)
rules = [r for r, n in sorted(by_rule.items(), key=lambda kv: -kv[1]) if n]
W, left, bar_h, gap = 920, 350, 24, 12
H = 30 + len(rules) * (bar_h + gap) + 26
mx = max(by_rule.values())
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Violations by rule before the rewrite"><rect width="{W}" height="{H}" fill="#ffffff"/>']
y = 28
for r in rules:
    w = (W - left - 190) * by_rule[r] / mx
    svg.append(f'<text x="{left - 10}" y="{y + 17}" text-anchor="end" font-size="13" fill="#131722" font-family="Arial, sans-serif">Rule {r}: {esc(NAMES[r])}</text>')
    svg.append(f'<rect x="{left}" y="{y}" width="{max(w, 2):.1f}" height="{bar_h}" rx="3" fill="#2a78d6"/>')
    svg.append(f'<text x="{left + max(w, 2) + 8:.1f}" y="{y + 17}" font-size="13" font-weight="600" fill="#131722" font-family="Arial, sans-serif">{by_rule[r]} before, 0 after</text>')
    y += bar_h + gap
svg.append(f'<text x="{left}" y="{y + 10}" font-size="12" fill="#687180" font-family="Arial, sans-serif">number of violations in the reviewed page (count by 8 writers, one per part of the page)</text></svg>')

rows = []
for x in d:
    rows.append(f'<tr class="part"><td colspan="3">{esc(PARTS[x["key"]])}</td></tr>')
    for r in x["result"]["rows"]:
        rows.append(f'<tr><td class="n">{esc(r["rule"])}</td><td>{esc(r["original"])}</td><td>{esc(r["fix"])}</td></tr>')
n_rows = sum(len(x["result"]["rows"]) for x in d)

stat = lambda name, a, b, unit="": f"<tr><td>{name}</td><td class='n'>{a}{unit}</td><td class='n'>{b}{unit}</td></tr>"
page = f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plain English Check</title>
<style>
:root {{ color-scheme: light; }}
body {{ background: #f5f6f8; color: #131722; font-family: Arial, Helvetica, sans-serif; font-size: 16px; line-height: 1.55; margin: 0; padding: 28px 16px 64px; }}
.sheet {{ max-width: 980px; margin: 0 auto; }}
h1 {{ font-size: 30px; line-height: 1.2; margin: 0 0 6px; }}
h2 {{ font-size: 22px; margin: 36px 0 8px; padding-top: 14px; border-top: 2px solid #131722; }}
.meta {{ color: #687180; font-size: 14px; margin: 0 0 14px; }}
.short {{ background: #ffffff; border: 1px solid #d9dde3; border-left: 5px solid #2a78d6; padding: 12px 18px; }}
.short h2 {{ border: 0; margin: 0 0 4px; padding: 0; font-size: 18px; }}
ul {{ margin: 6px 0 10px; padding-left: 22px; }} li {{ margin: 3px 0; }}
figure {{ background: #ffffff; border: 1px solid #d9dde3; margin: 14px 0; padding: 12px; }}
figure svg {{ display: block; width: 100%; height: auto; min-width: 620px; }} .scroll {{ overflow-x: auto; }}
figcaption {{ color: #434b59; font-size: 14px; margin-top: 6px; }}
.tablewrap {{ overflow-x: auto; margin: 12px 0; }}
table {{ border-collapse: collapse; font-size: 14px; background: #ffffff; width: 100%; }}
th, td {{ border: 1px solid #d9dde3; padding: 6px 9px; text-align: left; vertical-align: top; }}
th {{ background: #eef0f3; }} td.n, th.n {{ text-align: right; white-space: nowrap; }}
tr.part td {{ background: #e6eefb; font-weight: 600; }}
details {{ background: #ffffff; border: 1px solid #d9dde3; padding: 8px 14px; margin: 12px 0; }} summary {{ cursor: pointer; font-weight: 600; }}
code {{ font-family: Menlo, Consolas, monospace; font-size: 0.92em; background: #eef0f3; padding: 0 3px; }}
</style>
<div class="sheet">
<h1>Plain-English check of the GDN and AMX design page</h1>
<p class="meta">2026-11-21. Rule set: plain-english-experiment. Checked text: the page that the reviewer accepted in round 2.</p>
<div class="short">
<h2>Short version</h2>
<ul>
<li>The reviewed page had {total} violations of the experimental plain-English rules.</li>
<li>Most were labels at the start of bullets, and bullets with more than 3 sentences.</li>
<li>The rewritten page has none left, and no measured or predicted number changed.</li>
</ul>
</div>
<details><summary>Words used here</summary><ul>
<li><b>violation</b>: one place where the text breaks one rule of the rule set.</li>
<li><b>label</b>: a word or short phrase at the start of a bullet. It names the topic, for example "Clock." in bold.</li>
<li><b>counting script</b>: <code>check_lengths.py</code> of the rule set. It counts words per sentence and sentences per bullet.</li>
<li><b>writer, reader</b>: an agent that rewrote one part of the page, and an agent that compared old and new text.</li>
<li><b>generator</b>: the python scripts that produce the page from the measured data.</li>
<li><b>est.</b>: an estimate.</li>
</ul></details>

<h2>1. Result by rule</h2>
<figure><div class="scroll">{''.join(svg)}</div>
<figcaption><b>Figure 1.</b> Violations by rule in the reviewed page. <b>Rule 4 holds 62 % of them: labels and long bullets.</b></figcaption></figure>
<ul>
<li>Rules 2, 5 and 7 had no violation of their own. A sentence that joined two claims was also too long, so it counts under rule 3.</li>
<li>The counts come from the 8 writers. The counting script alone found {before['script']} of them, because it cannot see labels, idioms or terms.</li>
</ul>

<h2>2. The text before and after</h2>
<div class="tablewrap"><table><thead><tr><th>Measure (paragraphs and bullets)</th><th class="n">Reviewed page</th><th class="n">Rewritten page</th></tr></thead><tbody>
{stat("Sentences", before['sentences'], after['sentences'])}
{stat("Mean sentence length (words)", f"{before['mean']:.1f}", f"{after['mean']:.1f}")}
{stat("Longest sentence (words)", before['longest'], after['longest'])}
{stat("Sentences over 25 words", before['over25'], after['over25'])}
{stat("Bullets", before['bullets'], after['bullets'])}
{stat("Bullets over 3 sentences", before['bul_over3'], after['bul_over3'])}
{stat("Bullets that open with a bold label", before['labels'], after['labels'])}
{stat("Lines printed by the counting script, with table cells and captions", before['script'], after['script'])}
</tbody></table></div>
<ul>
<li>The page has more sentences and more bullets now, because long sentences and long bullets were split.</li>
<li>The page got 22 small sub-headings. They replace groups of labels in sections 3, 4 and 5.3.</li>
</ul>

<h2>3. How the rewrite was checked</h2>
<ol>
<li>8 writers rewrote one part of the page each, on a private copy of the generator.</li>
<li>The counting script ran on the merged page, with table cells and captions included. It printed nothing.</li>
<li>4 readers compared old and new text sentence by sentence, and 1 reader checked the layout in a browser.</li>
<li>The readers reported 20 problems. 19 are corrected, and 1 is kept on purpose (see below).</li>
<li>The page regenerates byte for byte, and the prediction data file is unchanged.</li>
</ol>
<ul>
<li>The readers found 3 changes of meaning. All 3 came from a split that separated a condition from its claim. They are corrected.</li>
<li>Kept on purpose: one label of figure 13 lost the word "the". Its parenthesis had 9 words, and the limit is 8.</li>
<li>Five names occur once more or once less, for example "Part 0" and "AVX-512". No measured or predicted number changed.</li>
</ul>

<h2>4. Text that the rewrite added</h2>
<ul>
<li>New entries in "Words used here": increment, and chain path.</li>
<li>New inline definitions: FPGA attention, pass wall, step wall, and PyTorch.</li>
<li>New definitions in the sources: checkpoint, replay, HW-attention, ready and pending pages, and CUDA.</li>
<li>Three "(est.)" marks. A split sentence needs the mark on both halves.</li>
</ul>

<h2>5. Violations and fixes</h2>
<p>The table has {n_rows} rows. Some rows stand for a group of equal violations.</p>
<div class="tablewrap"><table><thead><tr><th class="n">Rule</th><th>Original phrase</th><th>Fix</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>

<h2>6. The corrected text</h2>
<ul>
<li>The corrected text is the page itself: <code>GDN/gdn-amx-design.html</code>.</li>
<li>Its sha256 digest starts with <code>{sha[:16]}</code>. The reviewed version is kept as <code>exec/gdn-20261120/review-loop/gdn-amx-design.reviewed-82eab393.html</code>.</li>
</ul>
</div>
"""
page = page.encode("ascii", "xmlcharrefreplace").decode("ascii")
open(OUT, "w").write(page)
print("wrote", OUT, len(page), "bytes;", "violations", total, dict(sorted(by_rule.items())), "| rows", n_rows)
print("before", before); print("after", after)
