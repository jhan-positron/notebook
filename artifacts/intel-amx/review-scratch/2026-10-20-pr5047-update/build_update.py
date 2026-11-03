import html
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from notes import note

ROOT = Path(__file__).parent
OUT = Path("/home/jhan/workspace/intel-AMX/random/2026-10-20-pr-5047-line-by-line.html")
ORIGINAL = ROOT / "original.html"
if not ORIGINAL.exists():
    ORIGINAL.write_text(OUT.read_text())
soup = BeautifulSoup(ORIGINAL.read_text(), "html.parser")
BASE = "a5697f86d318e6a87badd4a751a005da52a9c25c"
FIRST = "e17a12ff09ea284ebd2616d1bf0531d7502e118d"
LATEST = "ade89a9d9c83f887270c89d6ae6c02bced3f037e"
MEASURED = "251529f0d865b87aad0673810a5603b4ec339f4d"
GOLDEN = "58e8c54011b03ca3b68c1ee47e803c85765cc873"
GITHUB = "https://github.com/positron-ai/tron"
BENCH = GITHUB + "/pull/5047#issuecomment-6295338954"
records = json.loads((ROOT / "records.json").read_text())
second = json.loads((ROOT / "second.json").read_text())
files = json.loads((ROOT / "files.json").read_text())
assert len(files) == 9
assert sum(f["additions"] for f in files) == 240
assert sum(f["deletions"] for f in files) == 307
assert Counter(r["side"] for r in records) == {"new": 235, "old": 284}
assert all(note(r) for r in records)


def source(sha, name):
    return f"{GITHUB}/blob/{sha}/{name}"


def fragment(text):
    return BeautifulSoup(text, "html.parser")


def replace(tag, text):
    tag.replace_with(fragment(text))


def insert_before(target, text):
    target.insert_before(fragment(text))


def chart():
    x = lambda v: 60 + (v + 2) * 41
    parts = [
        '<svg id="perf-chart" viewBox="0 0 520 300" role="img" '
        'aria-labelledby="perf-chart-title perf-chart-desc" xmlns="http://www.w3.org/2000/svg">',
        '<title id="perf-chart-title">GPT-OSS throughput changes against the historical baseline</title>',
        '<desc id="perf-chart-desc">Generation: plus 7.18 percent, bootstrap interval plus 6.96 to plus 7.41 percent. '
        'Prompt parsing: minus 0.47 percent, bootstrap interval minus 1.02 to plus 0.06 percent. '
        'Both rows use the same horizontal axis from minus 2 to plus 8 percent.</desc>',
        '<rect width="520" height="300" fill="#fff"/>',
    ]
    for tick in [-2, 0, 2, 4, 6, 8]:
        px = x(tick)
        parts.append(f'<line x1="{px}" y1="42" x2="{px}" y2="232" stroke="'
                     + ('#5b6673" stroke-width="1.5"' if tick == 0 else '#e2e8ee" stroke-width="1"')
                     + '/>')
        label = "0%" if tick == 0 else f"{tick:+d}%".replace("-", "−")
        parts.append(f'<text x="{px}" y="255" text-anchor="middle" fill="#4b5866" font-size="15">{label}</text>')
    for label, value, lo, hi, y, color in [
        ("Generation", 7.18, 6.96, 7.41, 100, "#0072b2"),
        ("Prompt parsing", -.47, -1.02, .06, 200, "#b35b00"),
    ]:
        sign = f"{value:+.2f}%".replace("-", "−")
        parts.append(f'<text x="60" y="{y-40}" fill="{color}" font-size="18" font-weight="700">{label}</text>')
        parts.append(f'<text x="{x(value)}" y="{y-13}" text-anchor="middle" fill="{color}" font-size="17" font-weight="700">{sign}</text>')
        parts.append(f'<line x1="{x(lo)}" y1="{y}" x2="{x(hi)}" y2="{y}" stroke="{color}" stroke-width="4"/>')
        for end in (lo, hi):
            parts.append(f'<line x1="{x(end)}" y1="{y-8}" x2="{x(end)}" y2="{y+8}" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<circle cx="{x(value)}" cy="{y}" r="6" fill="{color}" stroke="#fff" stroke-width="1.5"/>')
    parts.append('<text x="265" y="285" text-anchor="middle" fill="#4b5866" font-size="15">Throughput change versus baseline (%)</text></svg>')
    return "".join(parts)


head_lines = (ROOT / "head/h/tron/models/self_attention.hpp").read_text().splitlines()
substitutions = {
    "LATEST_CALL": html.escape("\n".join(line.strip() if i == 0 else "    " + line.strip()
                                       for i, line in enumerate(head_lines[1916:1918]))),
    "LATEST_SELF": source(LATEST, "h/tron/models/self_attention.hpp"),
    "LATEST_CACHE": source(LATEST, "h/tron/models/kv_cache.hpp"),
    "LATEST_SCHED": source(LATEST, "h/tron/scheduler/full.hpp"),
    "LATEST_TEST": source(LATEST, "t/t_llama_unit.cpp"),
    "FIRST_SELF": source(FIRST, "h/tron/models/self_attention.hpp"),
    "BASE_SELF": source(BASE, "h/tron/models/self_attention.hpp"),
    "FIRST_LAYOUT": source(FIRST, "h/tron/tensor/k_vnni.hpp"),
    "AMX": source(FIRST, "h/tron/kernels/amx_attn_iface.hpp"),
    "COMMIT1": GITHUB + "/commit/" + FIRST,
    "COMMIT2": GITHUB + "/commit/" + LATEST,
    "BENCH": BENCH,
    "COMPARE": f"{GITHUB}/compare/{GOLDEN}...{MEASURED}",
    "PERF_CHART": chart(),
}
latest_html = (ROOT / "latest.html").read_text()
for key, value in substitutions.items():
    latest_html = latest_html.replace(f"@@{key}@@", value)
assert "@@" not in latest_html

soup.title.string = "PR 5047 — both commits, every changed line, and the GPT-OSS benchmark"
replace(soup.header, f"""
<header>
<div class="eyebrow">positron-ai/tron · PR 5047 · Updated 20 October 2026</div>
<h1>Select the tokens.<br>Let the cache score them.</h1>
<p class="short"><strong>Short version.</strong> PR 5047 now separates token selection from scoring and puts key-storage decisions inside the cache.
GPT-OSS can be affected through ordinary CPU scoring even though its attention shape excludes the 128×4 AMX path.
The posted +7.18% generation result tests only the first commit against a historical baseline, so it does not isolate this PR’s contribution.</p>
<p class="meta">This update covers both commits through <a href="{GITHUB}/commit/{LATEST}"><code>{LATEST[:12]}</code></a>.
The linked benchmark was last updated at 16:05 UTC on 20 October 2026.
<a href="{GITHUB}/pull/5047">Open PR</a> · <a href="{BENCH}">Open benchmark</a></p>
<div><span class="tag">2 commits covered</span><span class="tag">9 files in final diff</span>
<span class="tag">Final diff +240 / −307</span><span class="tag">Every changed line annotated per commit</span></div>
<p class="meta">PR base: <code>{BASE[:12]}</code> · First commit: <code>{FIRST[:12]}</code> · Current head: <code>{LATEST[:12]}</code>.
Code links are pinned to the relevant revision.</p>
</header>""")
replace(soup.nav, """
<nav aria-label="Table of contents">
<a href="#latest-code">Current code</a><a href="#gptoss">GPT-OSS +7.18% explained</a>
<a href="#words">Words used here</a><a href="#second-overview">New commit overview</a>
<a href="#commit2">New commit: every changed line</a>
<a href="#commit1">First commit: original walkthrough</a><a href="#background">Background</a>
<a href="#intuition">Interactive mask example</a><a href="#verification">Evidence &amp; checks</a>
<a href="#quiz">Five-question quiz</a>
</nav>""")

# Preserve the original explanation, but make its revision scope explicit.
first_anchor = soup.find(id="code-overview")
insert_before(first_anchor, latest_html)
words = soup.find(id="words").extract()
soup.find(id="second-overview").insert_before(words)
new_terms = [
    ("page::score_k", "The cache operation that writes raw query–key dot products for selected token offsets."),
    ("try_score_k_amx", "The cache operation that either runs the supported dense AMX scorer or returns false without changing scores."),
    ("Logical row / row transfer", "One token’s key elements in their normal order. set_k_row stores that row. get_k_row loads it into a caller-provided buffer."),
    ("Scratch buffer", "Temporary memory supplied by the caller for a row being staged for hardware."),
    ("Baseline / candidate", "The reference run used for comparison / the run being evaluated. Here the baseline is historical, rather than the PR’s immediate parent."),
    ("Decode / prefill", "Generating output tokens / processing the input prompt. The benchmark calls these generation and parsing."),
    ("Bootstrap interval", "A statistical range obtained by resampling the recorded iteration samples."),
    ("Register spill", "A compiler-generated save of a temporary value to memory when it cannot remain in a CPU register."),
    ("Test tag", "An identifying value stored in the first key element so allocation and copy tests can recognize a row."),
    ("EAGLE / auxiliary slot", "Draft-model support used in speculative decoding / the extra cache slot exercised by the related tests."),
]
terms = soup.select_one("#words .terms")
for term, definition in new_terms:
    terms.append(fragment(f"<div><dt>{html.escape(term)}</dt><dd>{html.escape(definition)}</dd></div>"))
for dd in terms.select("dd"):
    if "This code calls that count" in dd.get_text():
        dd.string = "Grouped-query attention: query heads per KV head. The first commit calls it operation_kv_mul. The new cache method calls it kv_mul."
    if dd.get_text().startswith("The existing function that scores"):
        dd.string = "The existing function that scores a query group against selected packed keys. The second commit calls it inside the cache."

insert_before(first_anchor, """
<section id="commit1" class="revision-banner">
<div class="eyebrow">Historical walkthrough · first commit</div>
<h2>Commit 1: select tokens, then score</h2>
<p>The sections below preserve the original line-by-line explanation of <code>e17a12ff09ea</code>
against <code>a5697f86d318</code>. They describe the intermediate version measured by the linked benchmark.
The second commit subsequently moves the scoring block into the cache.</p>
<p><a href="#commit2">Return to the second-commit changes</a> · <a href="#latest-code">Return to the final code structure</a></p>
</section>""")
first_anchor.h2.string = "Commit 1 code in one view"
first_anchor.select_one(".caption").clear()
first_anchor.select_one(".caption").append(fragment(
    f'Exact code from first-commit lines 1927–1954. '
    f'<a href="{source(FIRST, "h/tron/models/self_attention.hpp")}#L1927-L1954">Pinned intermediate source</a>. '
    'The second commit moves this scoring block into the cache.'
))
soup.find(id="new-lines").h2.string = "Commit 1: every added line and its context"
soup.find(id="new-lines").find("p").string = (
    "Read in source order. These line numbers refer to e17a12ff09ea, the first commit. "
    "They do not refer to the current head after the scoring block moved into the cache."
)
soup.find(id="removed-lines").h2.string = "Commit 1: every removed line"
soup.find(id="consequences").h2.string = "Commit 1: consequences and evidence"

summaries = {
    "h/tron/models/kv_cache.hpp": (
        "The cache owns key layout, scoring, and conversion.",
        "Adds software scoring and an AMX attempt operation. Removes public row-major and packed storage views. "
        "Adds the expression setter while retaining the existing typed-row setters and getters.",
    ),
    "h/tron/models/self_attention.hpp": (
        "Attention selects offsets and asks the cache for scores.",
        "Replaces the reader block with score_k. Changes the dense AMX helper to return success or refusal. "
        "A refusal reaches the existing software path before attention state is changed.",
    ),
    "h/tron/models/model.hpp": (
        "Key saving uses one cache operation.",
        "Replaces layout and scalar-type branches with the expression setter. "
        "The cache now owns evaluation into the bf16 storage representation.",
    ),
    "h/tron/scheduler/full.hpp": (
        "Hardware staging always loads a logical row.",
        "Both layouts now load into the supplied scratch buffer. The row-major case previously returned a pointer "
        "into the cache, so this adds a row copy on that path.",
    ),
    "h/tron/tensor/k_vnni.hpp": (
        "The layout documentation names the new operation.",
        "Replaces the obsolete public packed-view accessor in the list of page operations. No layout arithmetic changes.",
    ),
    "t/kv_cache_helpers.hpp": (
        "Tests mark rows through the logical interface.",
        "Adds two helpers. The writer zeros a row and stores a marker in element zero. "
        "The reader loads the row and returns element zero as a float.",
    ),
    "t/heterogeneous_scheduler_compile.cpp": (
        "Scheduler allocation tests keep their identifying values.",
        "Replaces direct element access with the helpers. The markers 7, 9, 11, and 13 still distinguish the relevant "
        "sliding and retained slots through allocation failure and retry.",
    ),
    "t/t_llama_unit.cpp": (
        "Cache tests verify rows rather than storage pointers.",
        "Updates API constraints and retention/copy markers. The geometry test now stores and loads complete rows "
        "for both layouts. It covers two pages, all heads, and first/last token positions. "
        "Pointer identity and lazy-view validity checks disappear with the removed API.",
    ),
    "t/t_amx_dispatch_dtype.cpp": (
        "The AMX test comment follows the new ownership.",
        "Only the explanation changes. It now says the cache refuses packed-key AMX execution. "
        "The test’s expectations are unchanged.",
    ),
}
file_stats = {f["filename"]: f for f in second["files"]}
ordered = list(summaries)
assert set(ordered) == set(file_stats)
parts = [
    '<section id="commit2"><div class="eyebrow">New commit · e17a12ff09ea → ade89a9d9c83</div>',
    '<h2>Commit 2: every changed line</h2>',
    '<p>All 235 added lines and 284 removed lines are annotated below. This includes test changes, comments, '
    'and blank lines. Open a file to read its changes in patch order. '
    'Removed-line links point to the first commit. Added-line links point to the current head.</p>',
    '<div class="controls"><button id="expand-second" type="button">Expand all nine files</button>'
    '<button id="collapse-second" type="button">Collapse all nine files</button></div>',
    '<div class="file-index">' + "".join(
        f'<a href="#second-file-{i}">{html.escape(name)}</a>'
        for i, name in enumerate(ordered, 1)
    ) + '</div>',
]
for index, filename in enumerate(ordered, 1):
    stats = file_stats[filename]
    title, overview = summaries[filename]
    data = [r for r in records if r["file"] == filename]
    assert Counter(r["side"] for r in data) == {
        k: v for k, v in {"new": stats["additions"], "old": stats["deletions"]}.items() if v
    }
    head = (ROOT / "head" / filename).read_text().splitlines()
    for r in data:
        if r["side"] == "new":
            assert head[r["line"] - 1] == r["text"], r
    parts.append(f'<article id="second-file-{index}" class="file-block">'
                 f'<h3>{index}. <code>{html.escape(filename)}</code></h3>'
                 f'<p><strong>{title}</strong> {overview}</p>'
                 f'<p class="meta">+{stats["additions"]} / −{stats["deletions"]} lines · '
                 f'<a href="{source(LATEST, filename)}">Current file</a></p>'
                 f'<details class="second-file"><summary>Read all {len(data)} changed lines</summary>'
                 '<div class="line-head"><span>Revision / line</span><span>Code</span><span>Meaning</span></div>')
    current_hunk = None
    for r in data:
        if r["hunk"] != current_hunk:
            current_hunk = r["hunk"]
            parts.append(f'<p class="hunk"><code>{html.escape(str(current_hunk))}</code></p>')
        side, number = r["side"], r["line"]
        change = "added" if side == "new" else "removed"
        sha = LATEST if side == "new" else FIRST
        label = "+ new" if side == "new" else "− old"
        parts.append(
            f'<div class="line {change} second-line" id="c2-f{index}-{side}-{number}" '
            f'data-file="{html.escape(filename, quote=True)}" data-side="{side}" data-line="{number}">'
            f'<div class="num"><a href="{source(sha, filename)}#L{number}">{number}</a>'
            f'<small>{label}</small></div><pre><code>{html.escape(r["text"][2:] if r["text"].startswith("  ") else r["text"])}</code></pre>'
            f'<div class="note">{note(r)}</div></div>'
        )
    parts.append('</details></article>')
parts.append('</section>')
insert_before(soup.find(id="commit1"), "".join(parts))

quiz = [
    ("Why could the first commit affect GPT-OSS despite the AMX shape restriction?", [
        ("It adds a 64×8 AMX kernel.", False, "No such kernel is added. The 128×4 AMX gate remains."),
        ("It also changes ordinary row-major CPU selection and scoring.", True, "GPT-OSS’s 64-element heads use row-major storage. Its software-assigned attention work can reach this changed path."),
        ("It makes the packed-key layout support every head size.", False, "The packed-layout gate still requires 128-element heads."),
    ]),
    ("What can the linked +7.18% generation result establish?", [
        ("The second commit alone improves generation by 7.18%.", False, "The tested merge contains only the first commit."),
        ("The candidate improves against the listed historical baseline, but the PR’s share is unknown.", True, "That comparison spans 83 commits. A paired PR-base versus first-commit measurement is needed for attribution."),
        ("Three independent experiments measured the same improvement.", False, "3/3 means agreement among three statistical methods. The GPT-OSS candidate has one repeat of ten iterations across two instances."),
    ]),
    ("The final cache AMX operation receives packed-key storage. What happens?", [
        ("It returns false before changing scores, and attention can fall back to software.", True, "The cache’s layout branch refuses early. The attention wrapper returns before normalization and value accumulation."),
        ("It returns false after partially updating the attention accumulator.", False, "The refusal is checked before attention-state updates."),
        ("It converts the entire key plane to row-major storage and runs AMX.", False, "This operation adds no conversion or packed AMX kernel."),
    ]),
    ("Which new change can add work for row-major key staging?", [
        ("Replacing a direct cache-row pointer with get_k_row into caller scratch.", True, "The row-major getter copies the row. The old scheduler branch returned the cache pointer directly. This change was not in the linked benchmark."),
        ("Clearing the original selected-token mask after every score.", False, "Scoring clears bits only in the working copy named remaining."),
        ("Running both packed and row-major readers for each token.", False, "The cache selects one reader at compile time."),
    ]),
    ("The selected mask has offsets 1, 3, and 6 set. What does final score_k do?", [
        ("Visits 6, 3, 1 and clears the caller’s mask.", False, "It counts low-order zero bits and clears bits only in a local working copy."),
        ("Visits 1, 3, 6 on the row-major path and leaves unselected scores untouched.", True, "The lowest-set-bit loop preserves increasing token order. An empty mask returns before key storage is accessed."),
        ("Scores all 64 offsets and removes unselected scores afterward.", False, "The row-major loop visits only set bits. The packed reader receives the selection mask."),
    ]),
]
quiz_parts = ['<section id="quiz"><h2>Quiz</h2><p>Five questions covering both commits and the benchmark interpretation.</p>']
for i, (question, choices) in enumerate(quiz, 1):
    quiz_parts.append(f'<div class="quiz-item" id="question-{i}"><h3>{i}. {html.escape(question)}</h3><div class="choices">')
    for label, correct, feedback in choices:
        quiz_parts.append(
            f'<button type="button" class="choice" aria-pressed="false" data-correct="{str(correct).lower()}" '
            f'data-feedback="{html.escape(feedback, quote=True)}">{html.escape(label)}</button>'
        )
    quiz_parts.append('</div><p class="feedback" role="status" hidden></p></div>')
quiz_parts.append('<noscript><p>Enable JavaScript for the quiz and mask example. All annotations and static figures remain readable without it.</p></noscript></section>')
replace(soup.find(id="quiz"), "".join(quiz_parts))
insert_before(soup.find(id="quiz"), f"""
<section id="verification">
<h2>Evidence and checks</h2>
<ul>
<li><strong>Source scope:</strong> both PR commits, pinned to <code>{LATEST[:12]}</code> as the final head.
The first walkthrough covers all 25 additions and 43 deletions, plus 35 context lines.
The second covers all 235 additions and 284 deletions across nine files.</li>
<li><strong>Benchmark scope:</strong> the linked comment as updated at 16:05 UTC on 20 October 2026.
Its measured merge is <code>{MEASURED[:12]}</code>. Its andoria-09 baseline is <code>{GOLDEN[:12]}</code>.
The merge metadata, tree identity, baseline comparison, and exact GPT-OSS row were checked.</li>
<li><strong>Artifact checks:</strong> the generator verifies annotation coverage and added-line text against pinned source.
The mask calculations are deterministic toy examples. They are not inference measurements.</li>
<li><strong>Browser checks:</strong> tested at desktop width 1,360 pixels and mobile width 390 pixels.
The page stays within the viewport, including when all nine files are expanded.
The file controls, mask example, added-line filter, and feedback for all five quiz questions work without JavaScript errors.</li>
<li><strong>Not run:</strong> no Tron build, unit suite, hardware test, or new inference benchmark was run in this session.
The changed tests are explained from source. Their presence is not evidence that they passed.</li>
</ul>
<p>Primary references: <a href="{GITHUB}/commit/{FIRST}">first commit</a>,
<a href="{GITHUB}/commit/{LATEST}">second commit</a>,
<a href="{BENCH}">benchmark comment</a>,
<a href="{GITHUB}/compare/{GOLDEN}...{MEASURED}">baseline-to-candidate comparison</a>,
<a href="https://huggingface.co/openai/gpt-oss-120b/blob/main/config.json">official GPT-OSS configuration</a>.</p>
</section>""")
replace(soup.footer, f"""
<footer>Updated on 2026-10-20. PR 5047 source snapshot: <code>{LATEST}</code>.
The benchmark snapshot measures the first commit only. This is one self-contained HTML document.
It loads no external scripts, fonts, or images.</footer>""")
soup.style.append("""
/* Additions for the two-commit report. */
.perf-figure{margin:24px 0;padding:18px;border:1px solid var(--line);border-radius:10px;background:white}
.perf-figure svg{display:block;width:100%;max-width:720px;margin:0 auto;font-family:inherit}
.perf-figure figcaption{font-size:.93rem;padding-top:12px}
caption{text-align:left;padding:8px 0;font-size:.9rem;color:var(--muted)}
.revision-banner{border-left:5px solid var(--blue);background:var(--blue-bg)}
.file-index{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px;font-size:.88rem}
.file-index a{overflow-wrap:anywhere}
.file-block{border-top:2px solid var(--line);padding-top:8px;margin-top:28px;scroll-margin-top:16px}
.file-block h3{overflow-wrap:anywhere}
.file-block details{padding:10px 8px}
.hunk{padding:8px 10px;background:var(--soft);font-size:.8rem;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
.file-block .line{grid-template-columns:65px minmax(240px,1fr) minmax(260px,1fr)}
@media(max-width:900px){.file-index{grid-template-columns:1fr}.file-block .line{grid-template-columns:48px minmax(0,1fr)}.perf-figure{padding:8px}.file-block details{padding:8px 0}.second-line .note{grid-column:2}}
""")
script = soup.new_tag("script")
script.string = """
document.getElementById("expand-second").addEventListener("click", () => {
  document.querySelectorAll(".second-file").forEach(item => item.open = true);
});
document.getElementById("collapse-second").addEventListener("click", () => {
  document.querySelectorAll(".second-file").forEach(item => item.open = false);
});
document.querySelectorAll(".file-index a").forEach(link => {
  link.addEventListener("click", () => {
    document.querySelector(link.getAttribute("href")).querySelector("details").open = true;
  });
});
"""
soup.main.append(script)

result = str(soup)
assert not re.search(r"@@[A-Z_]+@@", result)
assert len(soup.select(".second-line")) == 519
assert len(soup.select("#new-lines .line.added")) == 25
assert len(soup.select("#removed-lines .line.removed")) == 43
assert len(soup.select(".quiz-item")) == 5
ids = [element["id"] for element in soup.select("[id]")]
assert len(ids) == len(set(ids)), "Duplicate IDs"
for a in soup.select('a[href^="#"]'):
    assert a["href"][1:] in ids, a
assert not soup.select("script[src], link[rel=stylesheet], img[src]")
OUT.write_text(result)
print(f"Wrote {OUT}: {OUT.stat().st_size:,} bytes")
print("Coverage: commit 1 +25/-43 and 35 context; commit 2 +235/-284 across 9 files.")
print("All added rows match pinned sources. All fragment links resolve. No external assets.")
