#!/usr/bin/env python3
"""Generates wade-comment-response-2.html (PR 4596, Wade's four comments of 2026-09-30, W6-W9).

Inputs (all optional, a missing one prints PENDING):
  r5/summary.tsv     unit-test runs on claude-box (buildtest/run.sh)
  r5/round5.diff     the working-tree diff of the change
  r5/wf1.json        verification workflow result (wf_4e5d9ee3-57d)
  r5/wf2.json        diff-review workflow result (wf_48d45328-3c3)
  r5/commit.txt      the local commit id once committed
Pure-ASCII output (artifact mojibake trap): non-ASCII characters are rejected.
"""
import html
import json
import sys
from pathlib import Path

S = Path(__file__).resolve().parent
R5 = Path(sys.argv[1]) if len(sys.argv) > 1 else S / "r5"
OUT = Path("/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/wade-comment-response-2.html")


def esc(s):
    return html.escape(s, quote=False)


def code(s):
    return f"<code>{esc(s)}</code>"


def pre(s):
    return f"<pre><code>{esc(s.strip(chr(10)))}</code></pre>"


def diff(s):
    out = []
    for line in s.strip("\n").split("\n"):
        if line.startswith("=== "):
            out.append(f'<span class="hdr">{esc(line[4:])}</span>')
        elif line.startswith("+"):
            out.append(f'<span class="add">{esc(line)}</span>')
        elif line.startswith("-"):
            out.append(f'<span class="del">{esc(line)}</span>')
        else:
            out.append(f'<span class="ctx">{esc(line)}</span>')
    return '<pre class="diff"><code>' + "\n".join(out) + "</code></pre>"


def read(name, default=""):
    p = R5 / name
    return p.read_text() if p.exists() else default


COMMIT = read("commit.txt").strip() or "PENDING (not committed yet)"
COMMIT_SHORT = COMMIT[:10] if not COMMIT.startswith("PENDING") else COMMIT

# ---------------------------------------------------------------- test table
def test_table():
    txt = read("summary.tsv")
    if not txt.strip():
        return "<p><strong>PENDING:</strong> the claude-box test run has not finished.</p>"
    rows = [l.split("\t") for l in txt.strip().split("\n")[1:]]
    prev = {  # 0f784c44ff on claude-box, 2026-09-30 (exec/review-20260929/buildtest/summary-0f784c44ff.tsv)
        "t_page_share_counters": "61 assertions in 4 test cases",
        "t_amx_dispatch_dtype": "1612 assertions in 1 test case",
        "t_heterogeneous_scheduler": "2783 assertions in 3 test cases",
        "t_llama_unit": "220158 assertions in 61 test cases",
        "t_compute_attention_unit": "(not in the 09-30 table)",
    }
    env_name = {"unset": "unset", "one": "=1", "yes": "=yes"}
    h = ['<div class="tbl"><table><tr><th>Binary</th><th>TRON_ATTN_STATS</th><th>Exit</th><th>Result</th><th>Before this change (head 0f784c44ff)</th><th>Wall</th><th>[attn-stats] lines</th><th>"ignored" warnings</th></tr>']
    for b, e, rc, n, res, wall, as_, ig in rows:
        res = res.replace("All tests passed (", "").replace(")", "").strip()
        h.append(f'<tr><td>{code(b)}</td><td>{env_name.get(e, e)}</td><td class="num">{rc}</td><td>{esc(res)}</td><td>{esc(prev.get(b, ""))}</td><td class="num">{wall} s</td><td class="num">{as_}</td><td class="num">{ig}</td></tr>')
    h.append("</table></div>")
    return "\n".join(h)


# ---------------------------------------------------------------- review summary
def review_section():
    txt = read("wf2.json")
    if not txt.strip():
        return "<p><strong>PENDING:</strong> the diff-review workflow has not finished.</p>"
    d = json.loads(txt)
    kept = d.get("kept", [])
    dropped = d.get("dropped", [])
    h = [f"<p>The review workflow ran six lenses (one review viewpoint each, for example completeness or plain English) with two refuters per finding. It kept {len(kept)} finding(s) and dropped {len(dropped)}. The kept findings and what was done with each:</p>"]
    if kept:
        h.append('<div class="tbl"><table><tr><th>Severity</th><th>Where</th><th>Finding</th><th>Disposition</th></tr>')
        for f in kept:
            h.append(f'<tr><td>{esc(f["severity"])}</td><td>{code(f["file"].removeprefix("/home/jhan/workspace/ai-runs/tron-attn-stats/") + ":" + str(f["line"]))}</td><td>{esc(f["title"])}. {esc(f["claim"])}</td><td>{"confirmed, no change" if f["severity"] == "info" else ("E4a in the apply list below, not applied" if "split" in f["title"] else "applied, see the apply list below")}</td></tr>')
        h.append("</table></div>")
    if dropped:
        h.append("<p>Dropped after refutation (the claim did not hold against the files, or the fix was outside the four comments). The critic still listed two of them as optional edits, and both were applied: the semicolon sentence (E7 in the table below) and &quot;on top of the first call&quot; (E6):</p><ul>")
        for f in dropped:
            h.append(f'<li>{esc(f["title"])} ({code(f["file"].removeprefix("/home/jhan/workspace/ai-runs/tron-attn-stats/") + ":" + str(f["line"]))}, lens {esc(f["lens"])})</li>')
        h.append("</ul>")
    extra = read("review-applied.md")
    if extra.strip():
        h.append(f"<h3>What was applied after the review</h3>{extra}")
    return "\n".join(h)


ROUND5_DIFF = read("round5.diff", "PENDING")

W9_SVG = (S / "w9_fig.svg").read_text() if (S / "w9_fig.svg").exists() else ""

CSS = (S / "gen_wade.py").read_text().split('CSS = """')[1].split('"""')[0]

parts = []
add = parts.append

# ---------------------------------------------------------------- header
add(f"""<title>Wade Review 2 PR 4596</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<h1>PR 4596: Wade's four new comments, the code changes, and the replies</h1>
<div class="meta">2026-09-30 &middot; PR #4596 head <code>0f784c44ff</code> (branch <code>jhan-attn-path-stats</code>, base main <code>66c7bb8db1</code>) &middot; Wade's four inline comments were posted 2026-09-30 16:33 to 16:40 UTC, each as its own review (state COMMENTED) &middot; W6 to W9 = the four comments, numbered after the five of 2026-09-28 (W1 to W5, see <a href="respond-Wade-comments.html">respond-Wade-comments.html</a>) &middot; worktree (a second checkout of the tron repository) <code>~/workspace/ai-runs/tron-attn-stats</code> &middot; the change of this page is local commit <code>{esc(COMMIT_SHORT)}</code>, pushed 2026-09-30 as the PR head</div>

<div class="short">
<p><strong>Short version.</strong> All four comments hold against the code, and all four are answered by one small change: 43 lines added, 60 removed, in four files, no counter, leaf or timer touched. Seven source comments lose their review-history references (W6, W7), one duplicate test case is deleted (W8), and the third stats row key now goes through the same helper as the other two (W9). The change is formatted, built and tested on claude-box (results in section 5) and is pushed as the PR head, with the four reply drafts in section 7.</p>
</div>

<h2 id="toc">Contents</h2>
<p class="toc"><a href="#words">Words used here</a></p>
<ol class="toc">
<li><a href="#glance">The four comments in one table</a></li>
<li><a href="#w67">W6 and W7: review history in source comments</a></li>
<li><a href="#w8">W8: a duplicate test case</a></li>
<li><a href="#w9">W9: the row key computed two ways</a></li>
<li><a href="#verify">Verification: format, build, tests</a></li>
<li><a href="#review">Review of the change</a></li>
<li><a href="#replies">Reply drafts for the four threads</a></li>
<li><a href="#gaps">What is not verified, and what is left for you</a></li>
<li><a href="#sources">Sources and method</a></li>
</ol>
""")

# ---------------------------------------------------------------- words
add("""
<h2 id="words">Words used here</h2>
<div class="tbl"><table>
<tr><th>Term</th><th>Meaning</th></tr>
<tr><td>tron, PR 4596, Wade</td><td>tron is the inference program under test. PR 4596 is the pull request that adds the attention path statistics behind the environment variable <code>TRON_ATTN_STATS</code>. Wade (GitHub Wado-posi) is a tron maintainer who reviews it.</td></tr>
<tr><td>review round, comment label</td><td>Wade's first review (2026-09-28) had five inline comments, which our pages call W1 to W5 and the branch's commit messages call "review round 4". The Claude review of 2026-09-29 is "round 5" with labels R1-M1 and so on. These labels exist only in our pages and in the commit messages. The record folder of this page, <code>exec/counter-20260922/r5/</code>, and its diff <code>round5.diff</code> use a different count: there "r5" and "round5" mean this Wade round (2026-09-30, W6 to W9), not the Claude review. The commit for this round, 441e81178b, carries no round number.</td></tr>
<tr><td>forward, token job, listener</td><td>A forward is one model run over all users' pending token jobs. A token job is one query token of one user in one forward. A listener is the scheduler entry that receives the logits (per-word scores) of a request's last token in that forward.</td></tr>
<tr><td>forward class</td><td>The PR's label per forward: <code>decode_like</code> when every token job has a listener, <code>prompt_or_mixed</code> otherwise. Every counter of a forward is filed under its class.</td></tr>
<tr><td>leaf</td><td>One file under tron's FUSE mount (a user-space file system that shows internal values as files), in the directory <code>/model/&lt;model id&gt;/attention/</code>. A read of a leaf renders one JSON object of the PR's counters and timers, for example <code>decode_like_totals</code> or <code>decode_like_worker_3</code>. One leaf carries many counters, so 'leaf' and 'counter' are not the same thing.</td></tr>
<tr><td>forward_scope</td><td>The C++ object (in <code>attn_stats.hpp</code>) constructed at the top of <code>model::state::forward</code>. It stores the class and starts the wall timer at construction, and files the wall time and the per-forward counts at destruction. It answered W2.</td></tr>
<tr><td>app pool, pool worker, attention worker, main helper</td><td>The app pool is tron's worker thread pool. Each forward splits it: the first <code>n_main_helpers</code> pool workers help the main thread, the last <code>n_attn_workers</code> run attention. Attention worker <code>i</code> runs on pool worker <code>num_workers - n_attn_workers + i</code> (Note [Attention workers are the last pool workers] in <code>model.hpp</code>).</td></tr>
<tr><td>row, row key</td><td>One counter record of the PR per (forward class, pool worker, layer). The row key is the pool worker index. It answered W5. Before that fix, rows were keyed by the attention worker index. That index moves between threads when the split changes.</td></tr>
<tr><td><code>model_stats::pool_worker</code></td><td>The one-line helper in <code>attn_stats.hpp</code> that maps (attention worker index, split) to the pool worker index, with two asserts on its inputs.</td></tr>
<tr><td>speedometer</td><td>A per-pool-worker speed record inside the thread pool. <code>run_attention_job</code> reports each job's work and cycles to it, and the next attention plan weights the split by it.</td></tr>
<tr><td>T2</td><td>The busy time of one attention job on one worker, in TSC cycles (CPU time stamp counter). <code>note_attn_job</code> files it into the worker's row.</td></tr>
<tr><td>hook</td><td>One small function on the stats object that the attention code calls at one point of the forward, for example <code>note_attn_job</code> at the end of each attention job.</td></tr>
<tr><td>TRON_ASSERT</td><td>tron's assert macro. It is active in every build and aborts the process on failure.</td></tr>
<tr><td>Catch2, CHECK, REQUIRE, TEST_CASE</td><td>Catch2 is the unit-test framework. CHECK records a failed assertion and continues, REQUIRE stops the case. A TEST_CASE is one named test.</td></tr>
<tr><td>perfetto</td><td>The trace tool tron emits events for. An event argument is one named value attached to an event.</td></tr>
<tr><td>clang-format</td><td>The code formatter the repository enforces (version 19.1.7, column limit 88 characters per line).</td></tr>
<tr><td>claude-box, delphi-3bda</td><td>claude-box is the AMD development host where this page was made (no AMX hardware). delphi-3bda is the Intel test machine of the earlier rounds. This round was built and tested on claude-box only (sections 5 and 8).</td></tr>
<tr><td>workflow</td><td>A scripted set of independent AI agents, each reading the code, whose claims are checked by other agents that try to refute them. Two ran for this page (section 9).</td></tr>
</table></div>
""")

# ---------------------------------------------------------------- glance
add(f"""
<h2 id="glance">1. The four comments in one table</h2>
<div class="tbl"><table>
<tr><th>Id</th><th>Anchor (at head 0f784c44ff)</th><th>Wade's point in one sentence</th><th>Verdict</th><th>What the change does</th><th>Size</th></tr>
<tr><td>W6</td><td><code>attn_stats.hpp:863</code></td><td>A source comment should not say "PR review round 4, comment W2".</td><td>holds <span class="pill holds">holds</span></td><td>The parenthetical is deleted. The sentence that contained it (the half-record failure mode) stays.</td><td>1 comment, 4 lines to 3</td></tr>
<tr><td>W7</td><td><code>t_attn_stats.cpp:306</code></td><td>Same, and "seems there are more. Scrub please."</td><td>holds: 6 more sites <span class="pill holds">holds</span></td><td>Three sweeps found 7 sites in 3 files, including two that cite history without the words "review round" (a dated live read, "the old keying"). Each keeps its technical reason in present tense.</td><td>7 comments in 3 files</td></tr>
<tr><td>W8</td><td><code>t_attn_stats.cpp:640</code></td><td>The "pool_worker: the last n_attn_workers pool workers run attention" case duplicates the next case, which checks the same mapping and the outcome that matters.</td><td>holds <span class="pill holds">holds</span></td><td>The case is deleted (19 lines). One CHECK line moves into the next case so the <code>+ attn_ix</code> term of the formula keeps a positive check.</td><td>-19 +3 lines</td></tr>
<tr><td>W9</td><td><code>self_attention.hpp:855</code></td><td>The pool-worker row key is computed two ways: inline at :797 and through <code>stats-&gt;pool_worker</code> at :1343 and :1485. One helper for all three.</td><td>holds <span class="pill holds">holds</span></td><td><code>run_attention_job</code> now passes <code>stats_ref.pool_worker(worker_ix, n_attn_workers)</code> to <code>note_attn_job</code>. The inline formula at :797 is main code (code already on the main branch before this PR) that keys the speedometer and stays.</td><td>1 line to 2</td></tr>
</table></div>
<p>Nothing else changes. No leaf name, counter, timer, assert or off-state test case (a test case that checks the stats object built with the switch off, the state a real run has when <code>TRON_ATTN_STATS</code> is unset) is touched. The whole change is one local commit, {code(COMMIT_SHORT)}, on top of the PR head.</p>
""")

# ---------------------------------------------------------------- W6 + W7
add("""
<h2 id="w67">2. W6 and W7: review history in source comments</h2>
<div class="quote"><div class="who">Wade, 2026-09-30 16:33 UTC, on h/tron/models/attn_stats.hpp:863</div>
<p>probably don't want to reference 'PR review round blah comment blah' like this</p></div>
<div class="quote"><div class="who">Wade, 2026-09-30 16:34 UTC, on t/t_attn_stats.cpp:306</div>
<p>same here... seems there are more. Scrub please.</p></div>

<h3>In plain words</h3>
<div class="plain">
<p>A source comment is read by people who never saw the pull request. "PR 4596 review round 4, comment W2" tells them nothing. The comment must instead say what the code guarantees, or what goes wrong without it.</p>
<p>The rule applied here: remove every reference whose meaning depends on the review conversation. Keep the technical reason (the invariant, the ownership rule, the failure mode, why the tempting alternative fails). Where the surrounding comment already gives the reason, delete only the reference. Do not replace the reference with a restatement of the code.</p>
<p>Two kinds of reference had to go. The literal ones name a review round or a comment label. The hidden ones anchor on history in other words: "before the fix", "the old keying", "under the old order", "seen in a live read on 2026-09-29". A future reader cannot anchor those either. They were rewritten as present-tense statements of the failure mode ("keyed by the attention index, both forwards would land in row 0").</p>
</div>

<h3>The sweep</h3>
<p>Three independent sweeps ran over the added lines of the whole PR (11 files), one by grep patterns, one by reading every added comment block, one adversarial over the test files only. They agreed on 7 sites. A final critic re-ran its own grep over the added lines of all 11 files (also README.stats.md, every TEST_CASE and SECTION name, string literals and log messages) and found no eighth site.</p>
<div class="tbl"><table>
<tr><th>#</th><th>File and line at head</th><th>What the comment cited</th><th>What stays after the edit</th></tr>
<tr><td>1</td><td><code>attn_stats.hpp:863</code> (W6, the <code>forward_scope</code> comment)</td><td>"(PR 4596 review round 4, comment W2)"</td><td>The half-record failure mode: a hook caller without the object gets token jobs without forwards, or a wall filed under the previous forward's class.</td></tr>
<tr><td>2</td><td><code>t_attn_stats.cpp:306</code> (W7, case "forward_scope: one object owns the per-forward record")</td><td>"PR 4596 review round 4, comment W2: the record ... had two writers"</td><td><code>forward_scope</code> is the one owner: class at construction, wall and fold at destruction, so every caller of <code>model::state::forward</code> gets a whole record.</td></tr>
<tr><td>3</td><td><code>t_attn_stats.cpp:372</code> (case "the three job counts move together")</td><td>"Seen in a live read of a CPU-attention run on 2026-09-29", "Under the old order"</td><td>The invariant: a reader of the leaves during a forward must never see listener_jobs + kv_only_jobs above token_jobs. Then why: if begin_forward added the listener counts and end_forward the token jobs, listener_jobs would already include the current forward while token_jobs would not.</td></tr>
<tr><td>4</td><td><code>t_attn_stats.cpp:408</code> (case "an out-of-range worker, layer or token job aborts")</td><td>"PR 4596 review round 4, comment W4:"</td><td>In production every index is in range by construction, so a wrong index must fail, not go uncounted.</td></tr>
<tr><td>5</td><td><code>t_attn_stats.cpp:662</code> (case "rows keyed by pool worker")</td><td>"PR 4596 review round 4, comment W5.", "were indexed by", "The old keying", "after the fix", "Under the old keying"</td><td>Rows are keyed by pool worker, with the Note that owns the convention named. Keyed by the attention index, both forwards would land in row 0, a row that no thread of either forward owns.</td></tr>
<tr><td>6</td><td><code>t_llama_unit.cpp:2227</code> (case "pending attention waits for invisible writers on the same page", which calls <code>apply_page_range</code> directly from the test with <code>uses_hw=false</code>; first pool-row check)</td><td>"PR 4596 review round 4, comment W5:", "Before the fix"</td><td>The row is the pool worker's. Keyed by the attention index, the visits would go to row 0, a main helper whenever the pool has more than one worker.</td></tr>
<tr><td>7</td><td><code>t_llama_unit.cpp:2255</code> (the same case, 2-worker split)</td><td>"The old keying put this call in row 0 again"</td><td>If keyed by the attention index, this call would land in row 0 again, and added to the first call.</td></tr>
</table></div>
<p>Site 5 gained one thing on purpose. W8 deletes the only comment in <code>t_attn_stats.cpp</code> that named Note [Attention workers are the last pool workers]. The rows-keyed case now names it instead. Two other test comments name the Note and keep the reference: <code>t_llama_unit.cpp:2229</code> (site 6, reworded by this commit) and <code>heterogeneous_scheduler_compile.cpp:803</code> (not touched by this commit).</p>

<h3>The edits, site by site</h3>
<div class="legend"><span class="del">- removed</span><span class="add">+ added</span><span class="ctx">unchanged context</span></div>
""")

add(diff("""
=== h/tron/models/attn_stats.hpp (site 1, the forward_scope comment)
 // begin_forward) and once at destruction, no write. A caller of the hooks
 // without this object gets a half record: token jobs without forwards, or a
-// wall filed under the previous forward's class (PR 4596 review round 4,
-// comment W2). The destructor also runs when forward() unwinds through an
-// exception, so such a forward is still counted; tron's asserts abort rather
-// than throw.
+// wall filed under the previous forward's class. The destructor also runs
+// when forward() unwinds through an exception, so such a forward is still
+// counted. tron's asserts abort rather than throw.
 struct forward_scope : noncopyable<forward_scope> {
=== t/t_attn_stats.cpp (site 2)
 TEST_CASE("attn-stats forward_scope: one object owns the per-forward record",
     "[attn_stats]") {
-  // PR 4596 review round 4, comment W2: the record behind <class>_forwards
-  // had two writers, the scheduler (forwards and the wall) and the model
-  // (class, token jobs, path sets). forward_scope is the one owner. The class
-  // is stored at construction. The wall and the fold are recorded at
-  // destruction. So every caller of model::state::forward gets a whole record
-  // filed under the class of that forward.
+  // forward_scope is the one owner of the record behind <class>_forwards. The
+  // class is stored at construction. The wall and the fold are recorded at
+  // destruction. With the forwards count and the wall written at one site and
+  // the class and job counts at another, a wall could be filed under the class
+  // of the previous forward. So every caller of model::state::forward gets a
+  // whole record filed under the class of that forward.
=== t/t_attn_stats.cpp (site 3)
-  // Seen in a live read of a CPU-attention run on 2026-09-29: listener_jobs
-  // was one forward ahead of token_jobs. begin_forward added the listener
-  // counts and end_forward added the token jobs. A reader of the leaves
-  // during a forward must never see listener_jobs + kv_only_jobs above
-  // token_jobs. All three are added in end_forward now. Under the old order
-  // the mid-forward CHECKs on listener_jobs, kv_only_jobs and the rendered
-  // leaf fail, for both classes below.
+  // A reader of the leaves during a forward must never see listener_jobs +
+  // kv_only_jobs above token_jobs. end_forward adds all three together. If
+  // begin_forward added the listener counts and end_forward the token jobs,
+  // listener_jobs would already include the current forward while token_jobs
+  // would not. The mid-forward CHECKs below would then fail: listener_jobs,
+  // kv_only_jobs and the rendered leaf for the prompt class, listener_jobs
+  // for the decode class.
=== t/t_attn_stats.cpp (site 4)
-  // PR 4596 review round 4, comment W4: in production every index is in range
-  // by construction (the worker index is below the pool size that sizes the
-  // rows, the layer id below n_layers, the token job below the count that
-  // begin_forward sized). A wrong index must therefore fail, not go uncounted.
-  // Each call runs in a forked child that must die with SIGABRT.
+  // In production every index is in range by construction (the worker index
+  // is below the pool size that sizes the rows, the layer id below n_layers,
+  // the token job below the count that begin_forward sized). A wrong index
+  // must therefore fail, not go uncounted. Each call runs in a forked child
+  // that must die with SIGABRT.
=== t/t_attn_stats.cpp (site 5)
-  // PR 4596 review round 4, comment W5. The rows are sized by the pool (3
-  // here) and were indexed by the attention worker index. The plugin picks
-  // the split per forward (recommend_n_main_helpers), so attention worker 0
-  // of a 1-worker forward is pool worker 2 and attention worker 0 of a
-  // 2-worker forward is pool worker 1: two threads, two cores. The old keying
-  // put both under row 0, a row that no thread of either forward owned.
-  // This case drives the hooks the way self_attention.hpp calls them after
-  // the fix (row = pool_worker(attention index, split)) and checks that the
-  // two forwards land in the two rows those threads own. Under the old
-  // keying every CHECK on rows 1 and 2 below fails and row 0 carries it all.
+  // The rows are sized by the pool (3 here) and keyed by the pool worker, not
+  // by the attention worker index (Note [Attention workers are the last pool
+  // workers] in model.hpp). The plugin picks the split per forward
+  // (recommend_n_main_helpers). So attention worker 0 of a 1-worker forward is
+  // pool worker 2. Attention worker 0 of a 2-worker forward is pool worker 1.
+  // Those are two threads on two cores. Keyed by the attention index, both
+  // forwards would land in row 0, a row that no thread of either forward
+  // owns. This case drives the hooks the way self_attention.hpp calls them
+  // (row = pool_worker(attention index, split)) and checks that the two
+  // forwards land in the two rows those threads own.
=== t/t_llama_unit.cpp (site 6)
-    // PR 4596 review round 4, comment W5: the row is the pool worker's, not
-    // the attention worker's. The call above ran attention worker 0 of a
-    // 1-worker split, which is the last pool worker (Note [Attention workers
-    // are the last pool workers] in model.hpp). Before the fix the visits
-    // went to row 0, which is a main helper whenever the pool has more than
-    // one worker.
+    // The row is the pool worker's, not the attention worker's. The call
+    // above ran attention worker 0 of a 1-worker split, which is the last
+    // pool worker (Note [Attention workers are the last pool workers] in
+    // model.hpp). Keyed by the attention index, the visits would go to row 0.
+    // Row 0 is a main helper whenever the pool has more than one worker.
=== t/t_llama_unit.cpp (site 7)
     // Run after the numeric check above, which the first call feeds. The same
     // attention worker 0 under a 2-worker split lands one row earlier: the
-    // row follows the thread, not the attention index. The old keying put
-    // this call in row 0 again, on top of the first call.
+    // row follows the thread, not the attention index. If keyed by the attention
+    // index, this call would land in row 0 again, and added to the first call.
"""))

add("""
<h3>What is left alone, and why</h3>
<ul>
<li><strong>Commit messages.</strong> Thirteen commit subjects on the branch say "(review round 4, W5)", "(review round 5, R1-M8)" or "(review round 3 picks)", and one more says "review round 3" without the parenthesis. Commit history is the right place for review history, and rewriting it needs a force push. They stay. If you prefer, the merge commit can carry a clean message.</li>
<li><strong><code>t_amx_dispatch_dtype.cpp:20</code></strong> says "Test shape and fakes from codex's review of PR #3879". That line is main code, not part of this PR.</li>
<li><strong>Issue and Note references</strong> (Note [Attention workers are the last pool workers], Note [Attention path stats], README.stats.md) stay. They carry durable technical context.</li>
<li><strong>Test names</strong> such as "attn-stats: an out-of-range worker, layer or token job aborts" and "attn-stats forwards record: the three job counts move together at the end of the forward" describe the required behavior in present tense. The final critic checked every TEST_CASE and SECTION name and found no review narration in them.</li>
</ul>
""")

# ---------------------------------------------------------------- W8
add("""
<h2 id="w8">3. W8: a duplicate test case</h2>
<div class="quote"><div class="who">Wade, 2026-09-30 16:39 UTC, on t/t_attn_stats.cpp:640</div>
<p>Nit: this case duplicates the next one ("rows keyed by pool worker", line 659), which already checks the same mapping (<code>REQUIRE(row == WORKER_2)</code> for split 1, <code>REQUIRE(row == WORKER_1)</code> for split 2) and also checks the outcome that matters: the counts land in the rows of the threads that ran the work, and the main-helper row stays zero. This one adds only the arithmetic of a one-line function, so it could be dropped.</p></div>

<h3>Verdict on each claim</h3>
<div class="tbl"><table>
<tr><th>Claim</th><th>Verdict</th><th>Evidence</th></tr>
<tr><td>The next case checks the same mapping.</td><td>holds</td><td>The rows-keyed case computes <code>row = stats-&gt;pool_worker(WORKER_0, SPLIT_1)</code> and requires 2, then the same for SPLIT_2 and requires 1 [t/t_attn_stats.cpp:682-683, :694-695 at head].</td></tr>
<tr><td>It also checks the outcome that matters.</td><td>holds</td><td>After the two forwards it sums each pool row: row 0 (a main helper in both forwards) has zero visits, jobs, busy and wait cycles, rows 1 and 2 carry one job each with the cycles that were filed [:704-719].</td></tr>
<tr><td>The dropped case adds only the arithmetic.</td><td>holds, with one detail</td><td>Four of its six CHECKs had no other home: the two identity-mapping checks at full split (<code>pool_worker(0, 3) == 0</code>, <code>pool_worker(2, 3) == 2</code>), the second worker of a 2-way split (<code>pool_worker(1, 2) == 2</code>), and one call on a switch-off object. None of the four protects a production path: at head 0f784c44ff both production callers of the helper run only when <code>stats_enabled</code> is true [self_attention.hpp:1341-1344, :1484-1486], so the switch-off sentence described no production caller. The second-worker check is the only positive check of the <code>+ attn_ix</code> term (every other positive check passes attention worker 0), so that one CHECK line moved into the rows-keyed case.</td></tr>
</table></div>

<h3>The edit</h3>
<div class="legend"><span class="del">- removed</span><span class="add">+ added</span><span class="ctx">unchanged context</span></div>
""")
add(diff("""
=== t/t_attn_stats.cpp (the deleted case, 19 lines)
-TEST_CASE("attn-stats pool_worker: the last n_attn_workers pool workers run attention",
-    "[attn_stats]") {
-  // Note [Attention workers are the last pool workers] in model.hpp: attention
-  // worker i of a forward with n attention workers is pool worker
-  // num_workers - n + i. The rows are keyed by that pool worker.
-  constexpr size_t SPLIT_1 = 1;
-  constexpr size_t SPLIT_2 = 2;
-  auto stats = make_stats(STATS_ON_TRUE);
-  CHECK(stats->pool_worker(WORKER_0, N_WORKERS_3) == WORKER_0);
-  CHECK(stats->pool_worker(WORKER_2, N_WORKERS_3) == WORKER_2);
-  CHECK(stats->pool_worker(WORKER_0, SPLIT_2) == WORKER_1);
-  CHECK(stats->pool_worker(WORKER_1, SPLIT_2) == WORKER_2);
-  CHECK(stats->pool_worker(WORKER_0, SPLIT_1) == WORKER_2);
-  // The off state answers the same: the mapping is arithmetic on the pool
-  // size, and a caller may compute it before testing the switch.
-  auto off = make_stats(STATS_OFF_FALSE);
-  CHECK(off->pool_worker(WORKER_0, SPLIT_1) == WORKER_2);
-}
-
=== t/t_attn_stats.cpp (the rows-keyed case, forward B)
   {
     const size_t row = stats->pool_worker(WORKER_0, SPLIT_2);
     REQUIRE(row == WORKER_1);
+    // Checks the "+ attn_ix" term of the row formula: the second attention
+    // worker of this split is the last pool worker.
+    CHECK(stats->pool_worker(WORKER_1, SPLIT_2) == WORKER_2);
     stats->add_visits(row, LAYER_0, tally, PASS_READY_0);
"""))
add("""
<p>Counts:</p>
<ul>
<li>The <code>t_llama_unit</code> binary (which compiles <code>t_attn_stats.cpp</code>) loses one test case and five assertions (six deleted CHECKs, one added).</li>
<li>No file-level constant becomes unused: <code>N_WORKERS_3</code>, <code>WORKER_2</code> and <code>STATS_OFF_FALSE</code> still appear 13, 11 and 7 times (each count includes the definition).</li>
<li>The two <code>SPLIT_</code> constants were locals of the deleted case, and the rows-keyed case has its own copies.</li>
<li>The negative case still checks both asserts of the helper (a split larger than the pool, an attention index at or past the split) [t/t_attn_stats.cpp:431-436 at head].</li>
</ul>
""")

# ---------------------------------------------------------------- W9
add(f"""
<h2 id="w9">4. W9: the row key computed two ways</h2>
<div class="quote"><div class="who">Wade, 2026-09-30 16:40 UTC, on h/tron/models/self_attention.hpp:855</div>
<p>Nit: the pool-worker row key is computed two ways. Here it is the inline <code>pool_worker_ix</code> (<code>tp.num_workers() - n_attn_workers + worker_ix</code>, line 797), while <code>run_joins</code> (line 1343) and <code>apply_page_range</code> (line 1485) call <code>stats-&gt;pool_worker(...)</code>. Suggest one helper for all three, so the rows can't drift if the convention changes.</p></div>

<h3>In plain words</h3>
<div class="plain">
<p>Three hooks file per-worker rows: <code>note_attn_job</code> (T2, once per attention job), <code>note_join_wait</code> (T5, the cycles a worker spends waiting in the join with no join progress, once per job) and <code>add_visits</code> (the visit tally, once per page range). Each needs the row key, the pool worker index. Two of the three asked the stats object for it. The first took a local variable that main code had already computed for another purpose, the speedometer. Both give the same number today. If the convention "attention workers are the last pool workers" ever changed, someone would have to change both, and the rows would be wrong until they did.</p>
<p>The fix is the smallest one: the first hook now asks the stats object too. Every stats row key is then one function call with one definition, one pool size (the size that allocated the rows) and two asserts on its inputs.</p>
</div>

<h3>What the code does</h3>
<p>The formula appears at four places in three headers. Two are main code that the PR did not write.</p>
<div class="tbl"><table>
<tr><th>Site (line at head)</th><th>Code</th><th>Pool size from</th><th>Purpose</th><th>Origin</th></tr>
<tr><td><code>self_attention.hpp:797</code></td><td><code>pool_worker_ix = tp.num_workers() - n_attn_workers + worker_ix</code></td><td>the thread pool</td><td>the speedometer observation at :837, and (before this change) the T2 row at :855</td><td>main (base :761)</td></tr>
<tr><td><code>self_attention.hpp:1498</code></td><td><code>app_pool().num_workers() - n_attn_workers + scratchpad</code></td><td>the thread pool</td><td>the perfetto "app thread id" event argument</td><td>main (base :1396)</td></tr>
<tr><td><code>attn_stats.hpp:431-435</code></td><td><code>model_stats::pool_worker(attn_ix, n_attn_workers)</code>: two asserts, then <code>n_workers - n_attn_workers + attn_ix</code></td><td><code>n_workers</code> = <code>attn.size()</code> at construction</td><td>the row key of <code>run_joins</code> (:1343) and <code>apply_page_range</code> (:1485)</td><td>PR (W5 fix)</td></tr>
<tr><td><code>model.hpp:1741, :2258</code></td><td>the formula in prose, in the plugin contract (a tron plugin is one model family's implementation behind the common model code) and in the Note</td><td>-</td><td>documentation; the Note's last bullet says the stats key rows "through model_stats::pool_worker"</td><td>PR added the bullet</td></tr>
</table></div>
<p>The two pool sizes are equal in production: <code>attn</code> is resized to <code>app_pool().num_workers()</code> at construction [self_attention.hpp:480] and the stats object takes <code>attn.size()</code> [:498]. They differ only in a test fixture that grows <code>attn</code> and rebuilds the stats [t/t_llama_unit.cpp:2614]. In that fixture the rows are sized by <code>attn.size()</code>. So the stats helper is the right key. A thread-pool key could exceed the rows.</p>
<div class="fig">{W9_SVG}
<p class="cap">Figure 1. The three stats row keys before and after the change. Before, the T2 hook took the speedometer's local; after, all three call the one helper. The speedometer (drawn) and the perfetto argument at :1498 (in the table above, not drawn) are main code and keep the thread-pool formula.</p>
</div>

<h3>Options</h3>
<p>Three designs were drafted and scored by three judges (correctness and drift, proportion for a nit, maintainer view a year from now). Scores are out of 10.</p>
<div class="tbl"><table>
<tr><th>Design</th><th>What it changes</th><th>Touches main lines</th><th>Scores</th><th>Why not / why</th></tr>
<tr><td>minimal (chosen)</td><td>:855 calls <code>stats_ref.pool_worker(worker_ix, n_attn_workers)</code>. Nothing else.</td><td>no</td><td class="num">9, 9, 8</td><td>All three stats row keys share one definition and one pool size. Runs only inside the <code>stats_enabled</code> branch, so the off state runs no extra code. Exactly what the nit asks.</td></tr>
<tr><td>one-formula</td><td>A free function in <code>attn_stats.hpp</code> used by :797, :1498 and the member.</td><td>yes, 2 lines</td><td class="num">5, 5, 5</td><td>Closes the drift between main's speedometer and the stats rows too, but rewrites two main-code lines for a nit and puts a thread-pool convention into the stats header.</td></tr>
<tr><td>convention-owner</td><td>A helper in <code>threading.hpp</code> next to <code>app_pool()</code>, used by every site.</td><td>yes, and a header included everywhere</td><td class="num">4, 3, 4</td><td>The right owner in principle, but a full rebuild and a wide diff for a one-line formula.</td></tr>
</table></div>

<h3>The edit</h3>
<div class="legend"><span class="del">- removed</span><span class="add">+ added</span><span class="ctx">unchanged context</span></div>
""")
add(diff("""
=== h/tron/models/self_attention.hpp (run_attention_job, end of the job)
       const uint64_t t_end = hardware::system::rdtsc();
       attn_elapsed += t_end;
       if (stats_enabled) {
-        stats_ref.note_attn_job(pool_worker_ix, layer.i, attn_elapsed);
+        stats_ref.note_attn_job(
+            stats_ref.pool_worker(worker_ix, n_attn_workers), layer.i, attn_elapsed);
         if (worker_ix == attn_stats::WORKER_0) {
           stats_ref.note_attn_job_wall_w0(layer.i, t_end - t_entry);
         }
"""))
add("""
<p>Two things the reply should say.</p>
<ul>
<li>Line 797 is main code that keys the speedometer, a thread-pool structure. The pool size from the thread pool is the right source there. The line stays inline on purpose. If you want line 797 routed through the member as well, that is a one-line follow-up. That call is unconditional. It would then run the two asserts in the off state.</li>
<li>Line 1498 is a pre-existing perfetto trace argument, not a stats row.</li>
</ul>
<p>No new test is needed. The T2 row is already read back through <code>run_attention_job</code> in <code>heterogeneous_scheduler_compile.cpp</code>, which checks that the row is the last pool worker's and that row 0 stays zero. The helper's asserts and the moving-split mapping are covered in <code>t_attn_stats.cpp</code>. A test that could tell the old and new key apart needs a fixture where the thread pool and <code>attn</code> differ in size while an attention worker runs a job. No such fixture exists. Building one is out of scope for a nit.</p>
""")

# ---------------------------------------------------------------- verification
add(f"""
<h2 id="verify">5. Verification: format, build, tests</h2>
<p>All steps ran on claude-box in the worktree, inside the repository's nix shell (nix is the package manager that supplies the pinned compiler and libraries). The run used the same clang 19 toolchain and the same <code>gen/</code> build directory as the 2026-09-30 run at head 0f784c44ff.</p>
<ul>
<li><strong>clang-format</strong> 19.1.7, dry run with <code>--Werror</code> on the four edited files: clean.</li>
<li><strong>Leftover check:</strong> a grep for "review round", "comment W", "before the fix", "old keying", "old order" and "2026-09" over the four edited files finds nothing.</li>
<li><strong>Build:</strong> the five test binaries below, incremental (the header change recompiles every unit that includes <code>self_attention.hpp</code>).</li>
<li><strong>Tests:</strong> two full runs, one after the first edits and one after the review edits of section 6 (same counts, the table shows the second). Each binary three ways, <code>TRON_ATTN_STATS</code> unset, <code>=1</code> and <code>=yes</code>, with <code>--skip-benchmarks</code>. The "before" column is the same run at head 0f784c44ff. The expected delta is in <code>t_llama_unit</code> only: one case and five assertions fewer (W8).</li>
</ul>
{test_table()}
<p>Not run this round: delphi-3bda (busy with another user's runs all afternoon, load average 126 at 17:19 UTC, that is about 126 tasks running or waiting at once). The change has no AMX-specific line. The claude-box build compiles the AMX dispatch code (<code>TRON_AMX_DISPATCH=ON</code> in its CMake cache), so it covers compilation. The claude-box run (an AMD machine, so no AMX hardware) covers every test that the 3bda runs of round 4 executed, except the AMX hardware kernels themselves.</p>
""")

# ---------------------------------------------------------------- review
add(f"""
<h2 id="review">6. Review of the change</h2>
{review_section()}
""")

# ---------------------------------------------------------------- replies
add(f"""
<h2 id="replies">7. Reply drafts for the four threads</h2>
<p>Drafts written as if the change were already pushed, one per thread, for you to post or edit. The commit id is the local commit {code(COMMIT_SHORT)}. It changes if you ask for an amend before the push.</p>
<div class="rec"><div class="lbl">W6 (attn_stats.hpp:863)</div>
<p>Agreed. The parenthetical is gone. The sentence that contained it stays: a hook caller without forward_scope gets a half record. Fixed in {esc(COMMIT_SHORT)}.</p></div>
<div class="rec"><div class="lbl">W7 (t_attn_stats.cpp:306)</div>
<p>Scrubbed. Seven comments in three files cited a review round, a comment label or the state before a fix. Each now states the invariant or the failure mode in present tense, for example "keyed by the attention index, both forwards would land in row 0". The commit messages keep their round labels, as history. Fixed in {esc(COMMIT_SHORT)}.</p></div>
<div class="rec"><div class="lbl">W8 (t_attn_stats.cpp:640)</div>
<p>Agreed, the case is dropped. The rows-keyed case asserts the same two mappings and checks the counts. One CHECK moved there so the second worker of a split (the + attn_ix term) keeps a positive check. Every other positive check passes attention worker 0. Fixed in {esc(COMMIT_SHORT)}.</p></div>
<div class="rec"><div class="lbl">W9 (self_attention.hpp:855)</div>
<p>Agreed. run_attention_job now calls stats_ref.pool_worker(worker_ix, n_attn_workers) like run_joins and apply_page_range. So every stats row key has one definition, one pool size (the size that allocated the rows) and the two input asserts. Line 797 is main code that keys the speedometer, a thread-pool structure. It keeps the pool's own size and stays inline. Line 1498 is the same kind of pre-existing site, the perfetto thread id. If you would rather route 797 through the member too, that is one line. It would then run the asserts in the off state. Fixed in {esc(COMMIT_SHORT)}.</p></div>
""")

# ---------------------------------------------------------------- gaps
add("""
<h2 id="gaps">8. What is not verified, and what is left for you</h2>
<ul>
<li><strong>Not run on delphi-3bda.</strong> The AMX kernels did not execute this round. The change touches no kernel line. The last delphi-3bda runs are at the round-4 head bff317e0d3 (2026-09-29) and at 04da001cb5 (2026-09-30 00:01 UTC, tested as 8670da7f0b, which differs by comments only). The seven round-5 test-only commits up to 0f784c44ff, like this change, ran on claude-box only.</li>
<li><strong>Push.</strong> The commit is local. You decide the push order and the PR replies, as in the earlier rounds.</li>
<li><strong>E4a (section 6).</strong> Three review findings asked for two CHECKs on a split equal to the pool (<code>pool_worker(i, 3) == i</code>). They were left out. Wade's W8 says that arithmetic is droppable. Say before the push if you want them back. The two lines are in the workflow record and in <code>round5.diff</code>.</li>
<li><strong>Live PR body.</strong> It still says <code>t/t_attn_stats.cpp</code> has 12 cases and lists the round-3 verification only. The proposed round-4 body (<a href="pr-body-round4.md">pr-body-round4.md</a>) says 18 cases. That count was right at head 0f784c44ff. After W8 the count is 17 (<code>t_llama_unit --list-tests "[attn_stats]"</code> prints 17 matching test cases), so update it before the body is applied. Apply it only from a fresh fetch and after a diff, as agreed on 2026-09-25.</li>
<li><strong>Commit subjects</strong> with "(review round N, ...)" stay on the branch. Decide at merge time whether the merge message should be clean.</li>
</ul>
""")

# ---------------------------------------------------------------- sources
add("""
<h2 id="sources">9. Sources and method</h2>
<ul>
<li>Wade's comments: GitHub review comments 4146947611 (W6), 4146959502 (W7), 4146998951 (W8), 4147010638 (W9) on positron-ai/tron pull request 4596, all at head 0f784c44ff.</li>
<li>Comment-cleanup rule: the positron-code-review skill (<code>~/.claude/skills/positron-code-review/SKILL.md</code>), derived from Wade's W6 comment.</li>
<li>Verification workflow wf_4e5d9ee3-57d (40 agents): three narration sweeps, one W8 reader, three W9 designers, one refute-and-merge agent plus two verifiers per site, two W8 refuters, two refuters per design, three W9 judges, one completeness critic. Script and result: <code>exec/counter-20260922/r5/</code>.</li>
<li>Diff-review workflow wf_48d45328-3c3 (75 agents): six lenses (completeness, meaning, plain English, W9 correctness, W8 coverage, reviewer's eyes), two refuters for each of the 34 findings (26 kept, 8 dropped), one critic. Result in the same folder.</li>
<li>Edit script <code>r5/apply.py</code> (exact string replacement, aborts on a missing or ambiguous original), build and test script <code>r5/buildtest/run.sh</code>, the diff <code>r5/round5.diff</code>, test outputs <code>r5/buildtest/</code>.</li>
<li>Page generator: <code>exec/counter-20260922/gen_wade2.py</code>; figure <code>w9_fig.svg</code>.</li>
</ul>
</div>
""")

page = "".join(parts)
bad = [c for c in page if ord(c) > 127]
if bad:
    sys.exit(f"non-ASCII characters in the page: {sorted(set(bad))}")
OUT.write_text(page)
print(f"wrote {OUT} ({len(page)} bytes)")
