# SPEC: asimov-c1nano-perf.html, written from scratch

Project folder (PROJ): `/home/jhan/workspace/titan/cache-perf/asimov`
Scratch folder (SCR): `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/44910dbc-316f-4921-a7fe-7178628c5666/scratchpad/core`

## Goal

A new page `PROJ/asimov-c1nano-perf.html`, title "Asimov C1-Nano Memory Performance". It reports the
memory latency and bandwidth seen by the Arm C1-Nano cores of the Asimov chip (emulated), as measured
by the cache-mem-perf benchmark. The reader is an engineer who has never seen the project (chip
architects, the emulator operator). A sibling page for the CME (`asimov-cme-perf.html`, generator
`gen_cme_perf.py` + `cme_page/`) was written the same way. This page covers the CORE rows only. CME
rows appear at most as one cross-reference sentence.

## The page owner's request (verbatim, binding)

- re-generate from scratch using existing test data, do not update existing page
- do not reference historical topics if they are already resolved
- do not reference historical data if latest data cover the same; if latest tests do not cover old
  tests' areas, use old test data as long as they are valuable
- Put section "Words used here" towards the end of the doc

## Data scope

Main boot (the latest boot with core rows):

- boot F1: `results/membench-jibin-011/results/bootF1/` (L3 on, hardware prefetchers on, `run_all.sh`).
  Boot F2 (012) has CME rows only. It gives nothing to this page.

Supplementary boots. A row of these may be used ONLY when boot F1 has no row that measures the same
thing, and only when the row is valuable to the reader. Each use states the boot's conditions next
to the number. The candidates (the critic confirms each one against the F1 file list):

- boot E: `results/membench-jibin-010/results/bootE/`. Same firmware state as F1 (L3 on, prefetchers
  on), follow-up command set. Candidates: the L3 hit-set rows (`latency-dram-small-l3.csv`), the
  address-order chain (`latency-dram-seq.csv`), the read variants with software prefetch
  (`bandwidth-read-prefetch.csv`), the two L1 bandwidth forms (`bandwidth-l1-passes.csv`,
  `bandwidth-l1-asmpasses.csv`), the TLB and page-walk counter rows, the OCM chain shapes.
- boot B (`membench-jibin-006`, prefetchers off, L3 of CPUs 2 to 9 held no data) and boot D
  (`membench-jibin-008`, as B plus OCM mapped with 2 MiB pages): candidates are the demand-only rows
  (OCM chain load per region and per CPU with no prefetched line, the mesh-step fit over the route
  rows, the address-order chain and the read stream with prefetchers off).
- boot C (`membench-jibin-007`, prefetchers on, L3 off, OCM mapped with 2 MiB pages): candidate is the
  page-mapping effect on the OCM rows (with D).
- the boot of `results/membench-jibin-004/results/19700101T000000Z/` (same core command set as F1,
  prefetchers on, L3 of CPUs 2 to 9 held no data). Page name "boot R3". Candidate use: ONE open item,
  the sequential-read rate with the L3 on against off (unresolved).

Boots 001, 002, 003, 005 (boot A) are not used unless the critic shows a valuable area that no later
boot covers.

Page names of the boots: "boot F1", "boot E", "boot B", "boot C", "boot D", "boot R3". Each is defined
in the boots table of section 1 and in "Words used here". The page never writes "run 3", "run 4",
"run 6", "round three". Folder names appear only in the boots table and in References.

## Hard rules

1. FROM SCRATCH. Do not open `asimov-c1nano-perf*.html`, `asimov-c1nano-run4.html`,
   `asimov-cme-*.html`, `outliners.html`, `run1-report.html`, `gen_perf*.py`, `gen_run*.py`,
   `gen_brief.py`, `gen_outliers.py`, `gen_hierarchy.py`, `l1_reader.py`. No text, number or code is
   taken from them. (Exception: the "open" researcher may read the open-item lists of
   `asimov-c1nano-perf.prev-2026-11-10.html` and `outliners.html` as a list of leads only.)
   Allowed inputs: the results folders (CSV, log.txt, sysinfo.txt, dmesg.txt, the operator's
   README.md, SHA256SUMS), the benchmark sources (`latency.c`, `bandwidth.c`, `common.h`,
   `cmncount.c`, `lib_run.sh`, `run_asimov.sh`, `run_followup.sh`, `run_all.sh`, `README.md`),
   `follow-up-run-plan.md`, `sequential-reads-L3-on-better-bandwidth.md`, the documents in `refs/`,
   and `cme_page/` (as a code model for viz, shell, refs, words, data layer).
2. NO HISTORY. The page describes what the boots measure, in the present tense. A topic that is
   resolved is stated as a plain fact with its rows, or left out. Never tell the story of how
   something was found. Never write "earlier", "previously", "now", "no longer", "changed",
   "settled", "was thought", "new in".
3. EVERY measured number on the page is computed at build time from the CSV files by the generator.
   No measured number is typed into prose as a literal: prose is built with f-strings from the data
   layer. Facts that exist only in the operator's README or in a document are typed, carry a [RefN],
   and say "(operator's README)" or name the document.
4. Every claim is tied to rows (file named in the note or by [RefN]). A cause that no counter proves
   is labelled "Hypothesis:" and is paired with the measurement that would confirm or reject it.
   Anything unknown is "Insufficient data: <what would resolve it>". Estimates carry "est." and units.
5. Lessons from the review of the sibling page (binding here too):
   - Bandwidth is loop throughput: bytes transferred over elapsed time. Never write that one load or
     one store "takes" N cycles. Write "effective cycles per 64 bytes transferred".
   - A control or baseline row is a separate measurement. A difference from it is "the measured
     difference between two loops", not memory-access time.
   - Aggregate refill counts do not give each line's history. "About one refill per load" does not
     prove where each line came from, and refill counters include prefetch fills.
   - A fit whose largest residual is over 2 % of the smallest pass time is void. A void intercept or
     rate is never quoted as a result.
   - Counter events that were not validated are "exploratory".
   - The DRAM level is an emulator memory model, not silicon timing (operator's README).
   - Figures of durations that are not nested intervals must not be drawn as nested.
6. Wording (the page owner's rules):
   - never "hop": a chain step is "a load"; a mesh move is "a step".
   - never "chase": the per-load number is the "chain load"; the loop is "the latency test".
   - chain kinds: "walked many times", "walked once", "every line flushed first", "address order".
   - OCM chain shapes: "one line per 4 KiB page", "every line", "one line per page at varied
     offsets". Never sparse / dense / fresh / flushed as nouns or labels.
   - L1 bandwidth forms: "looped form" (one kernel call per pass), "single-call form" (all passes of
     a rep in one call). Never "asm form".
   - "prefetcher" = the core's hardware data prefetchers. "prefetchers off" = firmware set the
     disable bit.
   - one term per thing; a "pass" is one walk over the buffer or chain, a "rep" is one timed
     measurement.
   - plain English per the plain-english skill: one claim per sentence, short sentences, no idioms
     or metaphors, no semicolons, units on every number with a plain meaning where needed, every
     code name / acronym / metric defined at first use or in "Words used here".
   - citations: `[RefN]` after the sentence; all file:line and document references live in the
     References section at the end.
7. HTML: one self-contained file, `<meta charset="utf-8">` right after `<title>`, LIGHT theme only,
   ASCII only inside SVG text, no external resources. It must read well at 1100 px wide and print.
8. Visual first: every result section leads with a chart or diagram whose form fits the data, direct
   labels on the points that matter, the key difference annotated on the figure, a one-line takeaway
   under it, and a compact table with the exact numbers. Follow the dataviz skill. Series colors:
   boot F1 = orange `#eb6834` (prefetchers on), a prefetchers-off boot = blue `#2a78d6`, a third
   series = aqua `#1baf7a`, a fourth (only if unavoidable) = violet `#6250d6`. Red `#e34948` only for
   the critical slice of a wall-clock lanes diagram. Reference lines and capacity markers are grey.
   Use a "wall-clock lanes" diagram (one lane per actor, time to scale, solid = work, dashed =
   waiting, critical slice in red with its cost) where timing of concurrent actors is explained
   (prefetch stream against dependent loads).
9. LENGTH. The sibling page grew to 65,000 words. This page must stay compact: at most about
   20,000 words of visible text, at most 32 figures and 40 tables. Prefer one figure plus one table
   per finding. No section restates another section. Budgets: setup 2,500 words; glance 1,000;
   latency 3,500; bandwidth 3,000; multicore 2,000; ocm 3,500; mesh 1,200; open 2,500.

## Page outline

Short version (at most three sentences) with one headline figure: "What one dependent load costs,
by where the line comes from" (L1, L2, L3, SLC over the mesh, OCM, DRAM model), plus the headline
bandwidth numbers.

1. `setup`: What was measured. Platform (cores, clusters, caches, mesh, home nodes, SLC, OCM, DRAM
   model) with a left-to-right data-path diagram and the mesh map. The boots table (which boot, its
   conditions, which sections use it and why boot F1 has no such row). How the latency test and the
   bandwidth test work, the counters and event numbers, the best-row rule, the clock. Data
   integrity (checksums computed at build time, command counts, failures, counter coverage).
2. `glance`: Results at a glance: the numbers to quote in one table, repeatability.
3. `latency`: Latency by footprint on CPU 2 (line chart, capacity markers, counters per load as
   small multiples). What an L3-served load costs (boot E hit-set rows). The chains from the other
   clusters (CPUs 4, 6, 8). The flushed row and the DRAM model. The address-order chain and the
   prefetcher (wall-clock lanes). Demand-only rows where a supplementary boot gives them.
4. `bandwidth`: One-core bandwidth by footprint (read, write, copy, 16-byte forms), bytes per cycle
   against the documented path widths, the L1 forms and the cost per call, software prefetch
   variants, lines in flight est.
5. `multicore`: Multi-core DRAM bandwidth (pair, per cluster, spread, all eight) and writer
   placement.
6. `ocm`: OCM latency by region and CPU (mesh map with steps, the chain shapes, which row to quote
   and why, demand-only rows and the mesh-step cost, page mapping), OCM bandwidth (per region, all
   five, write, four cores).
7. `mesh`: Mesh counters: requests per home node, that each command reached its intended node.
8. `open`: Open items (each: observation with rows, why it is not explained, hypotheses, the
   measurement that would settle it) and "Not measured".
9. Words used here (collected by S.term). 10. References (collected by S.ref).

The critic may merge or drop subsections. It may not add sections.

## Code layout (all under PROJ)

- `gen_c1nano_perf.py`: entry point. `python3 gen_c1nano_perf.py` writes `asimov-c1nano-perf.html`.
  Standard library only, Python 3.10. No time stamp: two builds give the same bytes.
- `c1nano_page/`: `__init__.py`, `data.py` (data layer with `selftest()`, `python3 -m c1nano_page.data`),
  `viz.py` and `shell.py` (copies of `cme_page/viz.py` and `cme_page/shell.py`, adapted: colors, the
  lint word list allows the boot names above), `refs.py`, `words.py`, `API.md`, one module per
  section `sec_<key>.py` exposing `KEY`, `TITLE`, `build(D, V, S)`.
- `cme_page/` and every other existing file in PROJ is read-only. The results folders are read-only.
- Scratch files go under SCR (`facts/`, `scripts/`, `shots/`, `review/`).

## Tools

- Python: `python3` (3.10). Use `python3 -I` for ad-hoc scripts that read the results folders.
- Screenshots: `/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell --no-sandbox --in-process-gpu --headless --window-size=1100,4000 --screenshot=<png> file://<html>`
  (the Bash sandbox must be off for it). For long pages slice by injecting a temporary copy with
  `body{margin-top:-Npx}`. Look at the PNGs with the Read tool.
- Do not use any remote machine. Do not run benchmarks. Do not use git.

## Leads from the owner's notes (UNVERIFIED: check each against the raw files before use)

- Controls: L1 chain load about 2.00 ns on every boot. Clock 2.0 GHz (cycles per ns from the rows).
- Boot F1 hit-size rows 192/256/384 KiB about 7.8/9.5/11.0 ns. Boot E the same within 1 %, with
  L3 hits per load 0.47/0.75/0.92. An L3-served load is about 10.6 to 11.0 ns est.
- `IMP_CLUSTERPWRSTAT_EL1` 0x70 = L3 fully on (F1, E). 0x0 = snoop-filter only (B, C, D, R3).
- SLC: 3.75 MiB est. after the OCM ways are taken out (operator's README). OCM: five regions of
  256 KiB, one per home node. Region to node ids 88, 160, 216, 288, 344 (`lib_run.sh`).
- Every-line all-five OCM chain is the OCM row to quote (about 26 ns). One-line-per-page rows on an
  L3-on boot are partly served by the L3.
- Boot B route fit: about 20.75 ns + 1.99 ns per X step + 0.95 ns per Y step (rms 0.09 ns). On L3-on
  boots the fit is unusable.
- Address-order 8 MiB chain: about 2.49 ns (E) against 52.8 ns with prefetchers off (B).
- One-core DRAM read about 24.5 GB/s on F1 against 9.2 on R3. Writes within 2 %.
- L1 forms on E: write fits pass (about 32 GB/s = 16 B per cycle), read fits fail the 2 % rule.
- DRAM model: Cadence AXI memory models with zero configured delay (operator's README of F1).
- Documented path widths: read dual 128-bit, write 128-bit (C1-Nano TRM, cited in the notes; the
  local documents are in `refs/`).
