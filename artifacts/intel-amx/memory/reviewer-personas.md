---
name: reviewer-personas
description: "~/workspace/reviewers/<name>.md are persona specs so agents can review jhan's PRs acting as a specific human reviewer; alexey.md (Alexey Radul, GitHub axch) was the first, built 2026-08-24"
metadata: 
  node_type: memory
  type: project
  originSessionId: e9870795-1bb4-4098-a36f-3cbfba04df2c
  modified: 2026-08-27T17:33:14.446Z
---

jhan keeps reviewer persona files in `~/workspace/reviewers/<name>.md`. Purpose: prompt an agent to review jhan's PR *as that reviewer would* before the human sees it.

- First persona: Alexey Radul (GitHub `axch`), primary reviewer of positron-ai/tron. Built 2026-08-24 from 1003 review summaries + 1269 top-level inline comments + 47 conversation comments on 794 non-own PRs (2024-01 → 2026-08). Raw data + scripts lived in the session scratchpad (`axch/fetch.sh`, `prepare.py`, `stats.py`).
- Data recipe that worked: `gh search prs --reviewed-by <login> --owner positron-ai --limit 1000` for the PR set; repo-wide `gh api repos/<r>/pulls/comments --paginate` filtered by `.user.login` for inline comments (validated 12/12 against per-PR endpoint); per-PR `pulls/N/reviews` for summaries. `gh api` has no `-c` flag — use `| tojson` in `--jq`. Drop the reviewer's own PRs (replies to reviewers are not reviews).

**Why:** the persona doc must emphasize what the reviewer *normally focuses on* (ranked by frequency), decision rules (approve vs. request changes), phrasing, and negative space (what they ignore) — not a biography.

**How to apply:** when asked to build or update a persona in `~/workspace/reviewers/`, follow the recipe above, rank findings by measured counts, tag themes by code area, and verify quotes verbatim against raw data. Lessons from alexey.md (2026-08-24): synthesis agents invent plausible phrases ("LGTM for my part" had 0 occurrences) and owner attributions (fritzo/speculation, Mark/structured-output were unsupported) — grep every attributed phrase and every name→area mapping; per-theme CR% is uninformative (baseline for any commented PR ≈ 47%), use stated reasons in CHANGES_REQUESTED bodies instead; the persona must state that an empty approval is the most common review (48% of PRs), or the agent manufactures comments; calibrate the verdict by finding count (1 → 20% CR, 2 → 34%, 3–4 → 55%, 5+ → 84%). See [[amx-tron-softattn-project]] for the tron context jhan's PRs land in.

**First use (2026-08-24, PR #3879, deliverable `~/workspace/intel-AMX/PR3879/alexey-review.html`,
generator `gen_review.py` in session scratchpad c79e32fa):** recipe that worked = (1) orchestrator reads
the whole `gh pr diff` and drafts candidate findings; (2) one workflow: verifier agents check every
candidate against clean `git worktree`s of PR head and merge base (file:line + quoted code, verdict
CONFIRMED/REFUTED/PARTIAL) in parallel with independent finder agents per persona lens (correctness,
comment accuracy, tests, design/scope, threading) given the candidate list as "do not repeat";
(3) second workflow: 1-2 adversarial refuters per verdict-carrying finding; fold their precision into the
comment text. Output layout: verdict + body in his voice, inline comments in his voice with a separate
verification column (persona item + agent id) that is NOT part of the review, a "checked and clean"
table (incl. my own refuted candidates), glossary, method. Lessons: 5 of 55 orchestrator candidates were
wrong (scope-of-variable, macro defined-ness, includes) - never publish an unverified candidate; finders
found the real bug (EAGLE storage-view aliasing) that the orchestrator missed; agents' line numbers
are head-tree lines, not diff lines.

**Round-2 recipe (2026-08-25, PR #3879):** (1) `gh pr view --json headRefOid,commits` + `git diff old..new`
(the delta) and fresh worktrees; (2) dump round-1 comments to JSON with ids; 4 status agents re-anchor each
comment to the new head (FIXED/PARTIAL/NOT_ADDRESSED/OBSOLETE + new_line + 2-8 line snippet range); 3 finders
on the delta only; (3) read the author's triage file (jhan writes DONE/IGNORE next to each comment in
PR3879/alexey-review.md) and check DONE items against the code - two "DONE" doc fixes had introduced new
errors; (4) output: carried-over comments keep round-1 text (a GitHub thread stays as written) plus one
follow-up sentence where partially addressed; resolved table; new comments marked; every comment prints
the source snippet from the new head with the anchored line marked (user request 2026-08-25); Markdown twin
alexey-review-<round>.md. Round-1 HTML archived as alexey-review-1.html; alexey-review.html = latest.

**Suggested-fix blocks (jhan request 2026-08-25, PR #3879 round 3):** for doc comments jhan wants the
replacement text, not only the ask. Generator now supports FIX = {comment_id: dict(lines=(a,b), text, note)}
rendered as "Suggested fix (added at your request) - replace lines a-b with:" + green <pre class="fix"> in
HTML and a ```suggestion fence in MD (four-backtick fence when the replacement itself contains a fence).
Label them as added at the user's request: the 2026 Alexey describes fixes, he does not paste suggestion
blocks (0.5% of his 2026 comments). Fix notes carry the evidence and anything jhan must confirm (e.g. the
64% figure = P0 fit 3.43 ms + 0.734 us x ctx -> 6.01/9.44 ms at ctx 8192).

**Round 4 (2026-08-25, working tree d176c88b3 + uncommitted doc/intel-amx.md):** deliverables
PR3879/alexey-review-4.md + alexey-review.html (round 3 archived as alexey-review-3.html). Pipeline copied to
~/workspace/intel-AMX/exec/review-pipeline/ (gen_review4.py + r4/ data; the earlier rounds' generator lived only in a
session scratchpad). Recipe that worked for an incremental round: only items anchored in files changed since the
previous head can change status -> 3 status verifiers over those items (status, new anchor, evidence, deviation from
the suggested fix, his-voice follow-up, suggested fix) + 1 finder over the delta + 1 refuter each; carry everything
else with previous text/lines. Refuters caught two factual slips (a "not reproducible" number that was in a prefill
cell; an off-by-3 line ref) and rejected all 4 finder candidates as duplicates/CI-enforced - fold such into the
existing item's follow-up. Result: 82 -> 77 open (6 fixed, 1 new), blockers 5 -> 3 (R2-03 default-true ctor, R1-51
amx_fused_bench kernel copies, R1-58 compile-only config).

**Round 5 (2026-08-25, head a5ef6576; delta = bench deleted + doc/Note numbers rewritten):** deliverables
PR3879/alexey-review-5.md + alexey-review.html (round 4 archived as alexey-review-4.html); pipeline
exec/review-pipeline/gen_review5.py + r5/ (round4_comments.json = open set dumped from gen_review4's all_comments(),
build_status5.py pairs workflow results with prompts via agent-<id>.jsonl line 0, round5_data.py). New this round:
(1) a bot review (Codex via jeremyconner1975) had landed - persona C2 means Alexey answers it; rendered as `reply_to`
items ("reply" mark, quoted bot text) that fold into his own round-1 threads (R1-12 alignment, R1-31 lazy pack);
(2) a deleted file's comments -> OBSOLETE rows (new_line 0) and the blocker whose remaining half moved elsewhere -> a
DROP/"merged" row with FIXED_VOICE pointing at the new threads; (3) items in unchanged files that *cite* the deleted
file (R1-37, R1-65) also need re-judging. Verification that paid: three independent finders caught a wrong
provenance date (doc/Note say 2026-08-19, the sweep record is 2026-08-18T18:34Z); a finder found the bench's per-page
pack_q asymmetry inside the quoted ~560 ns gap (I re-read the d176c88b3 source to confirm); refuters removed
non-reproducible histogram counts and a stale line ref from the Codex-reply voice. CI fact for the body: a draft PR
without the `Run CI` label runs lint only - check `gh run view <id> --json jobs` and per-commit check-runs (0 for the
last seven commits) before repeating "Run CI outstanding". Render check: the carried EAGLE SVG had an overlapping
label since round 3 - render every SVG (there are two; the first is not the chart). Result: 77 -> 75 open (1 fixed,
5 obsolete, 1 merged, 5 new incl. 2 Codex replies), blockers 3 -> 2 (R2-03, R1-58).

**Round 5b (2026-08-25, head 234c02bde):** jhan removed doc/intel-amx.md from the PR (archived at
github.com/jhan-positron/notebook artifacts/intel-amx, commit f3d1ee4; PR body edited to point there) and asked that
the review carry nothing about it -> generator `HIDDEN_FILES` drops those comments everywhere (no "removed" row
either), carried texts that named the file get a `TEXT_EDIT` substitution noted in the verification line, and the
R1-14 follow-up/fix moved the provenance ask into the Note itself. jhan also asked for suggested-fix sub-sections
under each blocker: generator FIX now takes `plan` / `hunks` (multi-file) / `sites` (call-site table) besides the
single-hunk form. Recipe that made those fixes trustworthy without touching the user's tree or build: copy h/ + the
test files to scratch, apply the patch text-keyed (line-keyed edits shifted when a replacement added a line), take
each TU's command from gen/compile_commands.json, swap `-o`, prepend `-I<scratch>/h`, add `-fsyntax-only
-fno-color-diagnostics`; the nix env is not on PATH, so a small driver resolves "fatal error: 'X' file not found"
by `find /nix/store -maxdepth 6 -path '*/include/X'` and retries with -isystem (oneTBB, ck were the two needed);
t_llama_unit needs `-I t/` for testutil.hpp; add a negative check (unpatched caller vs patched header must fail).
R1-58's compile-only target = OBJECT library like heterogeneous_scheduler_compile with PRIVATE
TRON_AMX_DISPATCH/TRON_AMX_K_MIRROR + the kernel TU with -mamx flags + a TU doing
`template struct full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>` (syntax-checks in 26 s); the CMake hunk
itself was not configured. Files: exec/review-pipeline/r5/fix/.
Outcome (2026-08-25 evening): jhan chose the default-false variant for R2-03 (keep the 3-arg forms, delegate with
false; 8 mirror-test sites pass true; node_base default false) - pushed as b2010bee9 - and applied R5-02's header fix
(b85fd2789). Both were syntax-checked with the build's compile commands and clang-format --dry-run before commit;
not built or run. The round-5 review files predate these two commits (R2-03 should drop to partial/non-blocking,
R5-02 fixed) - regenerate before the next round.
**jhan's decision on R1-58 (2026-08-25, late):** the compile-only CI configuration is an accepted limitation until
the CI team adds a config (tracked in tron issue #3997; TODO at the two options in src/tron/CMakeLists.txt,
commit 298dbad0f; "Validation and CI coverage" section in the PR body). **At the next Alexey round, SKIP R1-58** - do
not re-raise it or count it as a blocker; do not put verify-run logs in the PR description (jhan removed the
placeholder). Verify runs on delphi-3bda (exec/p2-verify-after-ci.sh) still happen; their results go into the
project memory [[amx-tron-softattn-project]], not the PR.

**Round 6 (2026-08-26, head 3fa11d911; delta = my 3 commits + jhan's 275fa89a0 comment trims, 35b3f3cae pack padding
zeroed once, 3fa11d911 exact-"1" kill switch):** deliverables PR3879/alexey-review-6.md + alexey-review.html (round 5
archived as alexey-review-5.html, WITH its hand-inserted R1-47 block; the block is now carried by gen_review6.py's
RESPONSES dict under the declined row). Pipeline exec/review-pipeline/gen_review6.py + r6/. Recipe additions that
worked: (1) triage.json drives statuses - verifiers get each item's triage; done/partial are checked (R1-14 'done' did
NOT hold: the Note still says 2026-08-19 and names no record), ignore/defer become DECLINED/DEFERRED with a
predicted_reply in his voice and a "Declined or deferred by the author" table (section 2a) instead of re-raising;
question items stay open with the tree's answer in triage_check; (2) detect hand edits before regenerating by diffing
the deliverable against a fresh regeneration into scratch (40 diff lines = the R1-47 box); (3) a self-correction round:
two delta sentences were wrong and one was Alexey's own round-1 suggestion (R1-15 'anywhere else the arena RAM is
wasted' - nothing is allocated on a non-AMX host) - the persona concedes in his own thread ("my round-1 phrasing was
wrong"); (4) finders confirmed the padding-zero invariant of 35b3f3cae to the index formula, and found that the reuse
sentence 'so callers can reuse the same buffer' became false (each pack's live data lands in the other's padding; only
discarded S rows are affected) - the one new comment R6-01. Result: 73 -> 61 open (11 fixed, 2 declined/deferred,
1 new), blockers 2 -> 0 (verdict still CHANGES_REQUESTED on the A3 false-sentence stack). R2-03 remainder fix = one
constructor / one try_create with defaulted trailing params, syntax-checked on HEAD (r6/fix/kv_cache.diff).
Round-6b (jhan request): every item named in the verdict's "what still blocks" list carries a Suggested fix block
(R1-10, R3-02, R2-06, R1-12 added; R1-14, R1-15, R6-01 already had one). Each comment rewrite went through one
adversarial fact-checker before publishing - worth it: my R3-02 draft claimed the kernel-body literals were "tile
geometry, not model shape" (false: step*4, k<4, half<2 are model-derived), and my R1-12 draft (fixed
`alignas(64) thread_local` pack array sized by max_minibatch_size) was REJECTED on a measured cost I had not
considered: a function-local thread_local in a template is one static-TLS block per model instantiation, zero-filled
by glibc on every thread at creation; ingest plugins hard-code max_minibatch_size = 1024 (ingest/src/TronCpp.hs:264)
-> 4 MB per eligible model, est. ~52 MB per thread for a production build. Lesson: never propose thread_local
arrays sized by a plugin constant inside model templates; check ingest-generated plugin constants, not only
llama.hpp. The R1-12 fix published is the zero-cost arm (drop "64B-aligned" from the two contracts) with the
attn_accum direction named for the perf question.
Round-6c (2026-08-27): jhan asked for a plain-language "unpacking" of a dense comment (R1-10's Note) as a sub-section
under the item, after the Suggested fix. Generator hook: EXPLAIN = {id: dict(title, md)} with the text kept in
r6/explain_<id>.md (markdown: headings, fenced diagrams, a "the comment says | in plain words" table, glossary);
gen_review6.py's md_to_html_simple() renders it; label "Explanation (added at your request)". Reuse for any item
jhan finds too dense.

**Decision record (2026-08-25):** jhan wants author decisions to persist across mock-review rounds. File:
`~/workspace/intel-AMX/PR3879/triage.json` = {id: {decision: done|partial|ignore|defer|question, reason, commit,
date, by}}. `exec/review-pipeline/gen_review4.py` loads it into TRIAGE ("your triage:" note per item);
`exec/review-pipeline/README.md` documents the round recipe: verifiers get the triage; ignore/defer items are NOT
re-raised - the persona's predicted reply to the author's reason goes into a "Declined or deferred by the author" table.
Seeded with 29 decisions (e.g. R1-47 ignore = refactor not bug; R1-58 defer = tracked in #3997; R2-03 done b2010bee9).
Keep the json updated whenever a decision is made; fill `commit` after pushing.
**Round-6d (2026-08-27, pushed 3fa11d911 -> 7aae13df5):** jhan liked the R1-10 "Sentence by sentence" table (comment
says | in plain words) and asked for the source Note itself to be rewritten in that register, then pushed. Result:
7aae13df5 rewrites Note [Tile stores write 16 rows] (7 -> 20 lines) + scopes the TILE_ROWS_16 comment; 5081d0bed
(input-2-ai/add-comments.md) labels every tile-register argument in amx_attn.cpp (`N /* dest tile */`, `/* src tile 0 */`,
`/* src tile 1 */`, `N /* src tile */`; 39 sites; clang-format reflowed 8 lines). triage.json R1-10 = done 7aae13df5.
Recipe that worked: draft -> workflow of 3 lens checkers (source / plain-English / persona) each with refuters on
non-nit issues -> fold -> 2-lens final gate on the exact text -> apply text-keyed (apply.py) -> clang-format-19
--dry-run -Werror (binary: /nix/store/1qrbfcklnlwn982a0n430054g9lavsn5-clang-format-19/bin/clang-format-19; the
wrapper path in compile_commands also exists) -> -fsyntax-only via r5/fix/fixcheck.py -> commit. Catches that paid:
my draft re-introduced the all-kernels generalization one sentence before the fix ("a width-4 result has real data in
only 4 rows" is false for qk_canonical_128x4's stored tiles - its padding is in columns); "which is what t_amx_numerics
passes it" was a test reference in a header (production s_pages is 4 rows too); "transposed there" misdescribed the data
path; "packed Q rows" collides with q_packed. The review files (alexey-review.html / -6.md) predate both commits -
regenerate before the next round (R1-10 -> fixed; amx_attn.cpp line numbers shifted: stores now :143-146/:225-228/:264-267).
