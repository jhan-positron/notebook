# Mirror vs VNNI-K page: where its test data live, and what to capture

Written 2026-09-19 by Claude (cross-check requested by jhan). Checked against notebook commit 39c71bf
(origin/main, fetched 2026-09-19 11:42 PDT) and the canonical folder on the same day.

## Short version

The page `status/mirror-vs-VNNI-K.html` (52 runtron tests, 16 CI-harness tests) is preserved in the
notebook, but the raw data behind it mostly is not: raw per-request lines exist in the notebook for
28 of the 52 tests, derived numbers in other preserved pages cover 20 more, and 4 tests have no copy
outside `~/workspace/intel-AMX`. That folder is a single NFS export with no visible snapshots and no
git history, so an accidental deletion would destroy the only copy of the page's input file and of the
raw logs for 24 tests. Capturing about 2.0 MiB of files into the notebook (listed in section 6) would
make every test re-derivable from GitHub alone.

## Words used here

- notebook: the git repository github.com/jhan-positron/notebook, cloned at `~/workspace/notebook`;
  it holds mirror copies of selected files from this project.
- canonical folder: `~/workspace/intel-AMX` on the shared NFS home (filer.positron.internal), the
  authoritative copy of every file of this project; it is not a git repository.
- the page: `VNNIed-K-in-place/status/mirror-vs-VNNI-K.html` (151079 bytes, generated 2026-09-14).
- row: one line of the page's Table 1 (keys R1 to R52, our runtron tests) or Table 2 (keys C1 to C16,
  CI-harness tests). "The 52 tests" are the 52 Table 1 rows.
- runtron: tron's command-line tool (tron is the inference program under test). rinzler: the
  production server. CI harness: the nightly systems_test throughput test driving a rinzler server.
- TPS: decode tokens per second per user. TTFT: time to first token (runtron: batched prefill time in
  seconds; CI harness: milliseconds to the first streamed chunk).
- arms: AMX off (kill switch TRON_AMX_DISABLE=1), AMX compiled off (binary built without AMX),
  canonical (AMX on, row-major K, PR 3879), mirror (AMX on with a second VNNI-layout copy of K),
  VNNI-K (K stored once in the VNNI layout, PR 4424). AMX and VNNI are CPU instruction sets.
- raw data: the runtron output lines per request ("average tok/s" and "Parsing the prompt took"), or
  the CI harness per-request samples (perf.json). Every TPS and TTFT on the page is computed from
  these. derived data: means, standard deviations and counts written into a report or summary.
- rows.json: `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json`, the generator's input (see 2).

## 1. What was checked

- The page's "Raw data by row key" lists were parsed with a script. They cite 301 distinct files
  (298 plain paths plus 3 sibling log files named inside "X.done and Y.log" entries). All 301 exist in
  the canonical folder.
- Each cited path was looked up in the notebook working tree at the mirrored path and at the
  relocated path `artifacts/intel-amx/amx-decode-boost-202608/`, and confirmed tracked on origin/main
  with `git ls-tree`.
- The generator's input was located through the 2026-09-14 session transcript and the page was
  regenerated from it (section 2).
- Three independent verifier agents and one completeness critic re-derived the counts and searched
  the whole notebook (working tree and 445 commits of history) for any other copy of the numbers.

## 2. How the page is built

The page is written by `exec/vnnik-20260914/gen_compare.py` from one input file, rows.json
(545679 bytes, 239 rows: 179 runtron and 60 CI-harness, from 8 result sets). rows.json was produced on
2026-09-14 by a Claude Workflow named `pull-mirror-vs-vnni-data` (16 agents extracted and verified the
numbers from the result files), then hand-edited (two g1mirror rows relabeled as mirror, two
"baseline" wordings replaced, caveats prefixed with their source id).

Running the generator on rows.json reproduces the current page with zero differing lines once the
"Pulled from the existing result files on <timestamp>" sentence is masked. Every row of rows.json
carries its source file paths with line numbers, and 147 of the 201 rows the page uses carry the
per-repetition values in their notes field.

Trap: `gen_compare.py ROWS_JSON` with one argument writes to the hardcoded canonical page path and
overwrites the page. Always pass the output path as the second argument:
`python3 gen_compare.py ROWS_JSON OUT_HTML`.

## 3. What the notebook holds today

- The page, at `artifacts/intel-amx/vnnied-k-in-place/status/mirror-vs-VNNI-K.html`. It differs from
  the canonical copy only by a 6-line "Rendered page" comment prepended (336 bytes); the rest is
  byte-identical. Registered in `artifacts/intel-amx/README.md` lines 799-800.
- The generator `gen_compare.py`, byte-identical, standard library only.
- Raw result files for 28 of the 52 rows, all byte-identical to the canonical copies:
  `exec/results/perf-round-20260825/perf-round.txt`, `exec/results/perf-round-20260830/perf-round.txt`
  and `perf-round-ext.txt`, and the ctxfill, ctxfill2 and fence3 captures relocated under
  `artifacts/intel-amx/amx-decode-boost-202608/`. Together they hold 1112 per-request lines. Two
  verifiers recomputed R1 and R30 from these copies and matched the page.
- `exec/results/p0perf-20260913/summary.md`, which holds per-run means for R34, R49, C8 and C13 but no
  per-request lines.
- Report pages, handoffs and one audit file that carry derived numbers for 20 more rows (section 4).

The notebook does NOT hold rows.json, the workflow script that built it, or the result trees
`exec/results/{t4, vnnik-20260914, p0perf-20260911, g1-20260908, more-testing-r1}` and the four loose
result texts `qwen8u8k-pr1-*.txt` and `gptoss120b-pr1-half-*.txt`. Of the 301 cited files, 271 are
absent. This follows the notebook's stated rule: "bulk result trees stay on the canonical storage"
[artifacts/intel-amx/README.md:113-114, 442-444].

## 4. Per-row status if only the notebook survived

Table 1 rows (the 52 runtron tests):

| What the notebook has | Rows | Count | Where |
|---|---|---|---|
| Raw per-request lines | R1-R3, R5, R10, R11, R13-R21, R23-R26, R28-R32, R37, R38, R41, R42 | 28 | perf-round texts; ctxfill, ctxfill2, fence3 captures |
| Per-repetition values, no per-request lines | R35, R39, R47, R50, R51, R52; R33, R48; R4, R6; R43 | 11 | `VNNIed-K-in-place/status/codex-perf-audit.json`; `pr3879/PR1/Friday-morning-CI-results.html`; `handoffs/claude_20260908-20260909_pr-3879-description-wording.md`; `pr3879/PR1/pr-body.md` |
| Means only, at the page's precision | R34, R49; R45; R44; R46; R7, R8 | 7 | `exec/results/p0perf-20260913/summary.md`; `pr3879/new-PRs/Tuesday-morning-status.html`; pr-body.md and the 09-08/09 handoff; handoff and `pr3879/PR-open-comments.html`; `exec/review-pipeline/r4/workflow_out.json` |
| Means at one decimal, no TTFT, no sd | R9, R12 | 2 | `rampup/2026-08-19-amx-status.html`, `tron-amx-distilled.html` |
| Nothing that reproduces the page's values | R22, R27, R36, R40 | 4 | none (the 2026-08-19 four-arm qwen3-4b tests; sources `t4/t4-suite.txt`, `t4/p2-inc3-arena.txt`, `t4/t4-reps.txt`, `t4/t4-power.txt`) |

So 28 tests keep their raw data, 20 keep derived numbers only, and 4 lose everything.

Table 2 rows (16 CI-harness tests): C8, C13 have per-run means in summary.md; C9, C16 have
per-repetition values in the Friday page; C1, C5, C7, C14 have means at page precision in
`pr3879/breakup-PR3879.html`; C2, C4, C6, C10, C11, C12, C15 have one-decimal means in the Tuesday
page; C3 has nothing. No CI row has its per-request samples (perf.json) in the notebook.

## 5. The risk

- The canonical folder is one NFS export (`filer.positron.internal:/mnt/flash_pool/homes/jhan`).
  delphi-3bda mounts the same home, so a deletion there is a deletion everywhere.
- No `.snapshot` directory is visible from the client at `~`, `~/workspace` or `~/workspace/intel-AMX`.
  Whether the filer keeps snapshots is Insufficient data; the storage administrator would know.
- The folder is not a git repository. A deleted file has no history to recover from.
- The only other copies of rows.json are inside Claude session records under `~/.claude/projects/`,
  which sit on the same NFS home and are not a repository.
- rows.json exists in exactly one place. So does every raw file of the 24 unprotected tests.
- After a deletion, the 4 tests of the last table row could not be re-scoped at all, and the 20 tests
  with derived numbers only could not be re-analysed (no per-request or per-repetition data to
  recompute a mean, a spread or a different statistic from).

## 6. What to capture into the notebook

Three tiers. Sizes are file sizes on disk today. Mirror each file at
`artifacts/intel-amx/<same path relative to ~/workspace/intel-AMX>`, the convention the existing
`exec/results/perf-round-*` entries follow, and register the batch in `artifacts/intel-amx/README.md`.

Tier 1: makes the page regenerable (0.53 MiB, 2 files).

| File | Bytes | Why |
|---|---|---|
| `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` | 545679 | the generator's only input; regenerates the page exactly; holds source paths with line numbers and per-repetition notes |
| `pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` (today only at `~/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/scripts/`) | 8981 | the extraction recipe; copy it first into the canonical folder (`exec/vnnik-20260914/`), then mirror it beside the two scripts already in `artifacts/intel-amx/exec/workflows/` |

Tier 2: raw per-request lines for the 24 unprotected runtron rows (0.82 MiB, 24 files). The
`rt-results.txt` files contain the same per-request lines as the per-repetition `rt/*.log` files
(480 of 480 for vnnik, 192 of 192 for each p0perf), so the logs are not needed.

| Files | Rows served | Bytes |
|---|---|---|
| `exec/results/t4/t4-suite.txt`, `t4-shapes.txt`, `t4-reps.txt`, `t4-power.txt`, `p2-inc3-arena.txt` | R7, R8, R9, R12, R22, R27, R36, R40 | 136723 |
| `exec/results/vnnik-20260914/rt-results.txt`, `summary.json`, `summary.md`, `build.txt` | R35, R39, R47, R50, R51, R52 | 273059 |
| `exec/results/p0perf-20260911/rt-results.txt`, `summary.json`, `summary.md`, `build.txt` | R33, R48 (and C9, C16 means) | 108296 |
| `exec/results/p0perf-20260913/rt-results.txt`, `summary.json`, `build.txt` | R34, R49 (and C8, C13) | 113568 |
| `exec/results/g1-20260908/runtron-8u8k.txt`, `summary.json`, `summary.md`, `summary.txt` | R45 (and the g1 CI rows' means) | 140030 |
| `exec/results/qwen8u8k-pr1-20260907T1904.txt`, `qwen8u8k-pr1-half-20260907T1904.txt`, `qwen8u8k-pr1-half-20260909T1704.txt` | R43, R44, R46 | 54232 |
| `exec/results/gptoss120b-pr1-half-20260909T1706.txt` | R4, R6 | 35505 |

Optional in this tier: the 7 cited `exec/results/g1-20260908/runtron-g1{canon,kill,mirror}-rep*.log`
files (664904 bytes). Their 80 per-request lines are already in `runtron-8u8k.txt`.

Tier 3: raw per-request samples for the 16 CI-harness rows (0.62 MiB, 189 files). For each of the 54
cited cell directories under `exec/results/<campaign>/cells/`, capture `perf*.json` (the per-request
samples), `meta.json` (settings) and `proof.txt` where present, plus two notes files.

| Campaign | Cell directories | Files | KiB |
|---|---|---|---|
| `g1-20260908` | 21 | 69 | 226 |
| `more-testing-r1` | 13 | 26 | 47 |
| `p0perf-20260911` | 8 | 26 | 122 |
| `p0perf-20260913` | 12 | 66 | 186 |
| `exec/results/more-testing-r1/notes.md`, `PR3879/more-testing/round-1/status.md` | - | 2 | 56 |

Total for all three tiers: about 2.0 MiB, 215 files. The exact path list is in the check script's
output `capture_list.json` (session scratchpad, 2026-09-19); regenerate it by parsing the page's
"Raw data by row key" lists.

Deliberately not proposed (12.1 MiB, 140 files): the 13 `rinzler.log` server logs (9.5 MiB), the
per-repetition `rt/*.log` files (duplicates of `rt-results.txt`), `functional.xml`, and the
`exec/logs/*.done` markers and campaign logs. They add provenance, not numbers. If they are wanted,
they fit the notebook's size (the repository is 64 MiB today).

Process, per the notebook convention: edit or copy the canonical file first, mirror it, add the batch
entry to `artifacts/intel-amx/README.md`, commit as "Preserve artifact: ...", push, then confirm with
`git ls-tree origin/main` that every file is tracked.

## 7. Verification notes

Three verifier agents and a completeness critic checked the findings above on 2026-09-19. They
corrected the draft in four places: the header comment is 6 lines, not 5; the page cites 301 files
and 271 are absent from the notebook (the draft said 298 and 268); the sizes were in MiB, not MB;
and 18 of the 22 rows first counted as "no numeric source" do have derived numbers in preserved
pages, handoffs or `codex-perf-audit.json`. The presence of per-run values for the six 2026-09-14
VNNI-K rows in `codex-perf-audit.json` was confirmed directly (the values 70.253, 70.246 and 70.338
each appear in the file).

## 8. Sources

- Page: `VNNIed-K-in-place/status/mirror-vs-VNNI-K.html` (canonical) and
  `artifacts/intel-amx/vnnied-k-in-place/status/mirror-vs-VNNI-K.html` (notebook).
- Generator: `exec/vnnik-20260914/gen_compare.py`, lines 19-20 (arguments), 30 (input read),
  284 (output write).
- Input: `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json`.
- Notebook policy: `artifacts/intel-amx/README.md` lines 44, 113-114, 202, 442-444.
- Workflow record of the extraction:
  `~/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/wf_9b0f456d-293.json`.
- Mount: `df -PT ~/workspace/intel-AMX` on claude-agentsrv, 2026-09-19.
