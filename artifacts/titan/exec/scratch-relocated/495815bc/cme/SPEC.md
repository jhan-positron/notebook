# SPEC: asimov-cme-perf.html, written from scratch

## Goal

A new page `/home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf.html`, title
"Asimov CME Memory Performance". It reports the memory performance of the CME (the Arm
C1-SME2 matrix engine unit) as measured on the two latest boots:

- boot F1: `results/membench-jibin-011/results/bootF1/` (L3 on, hardware prefetchers on, core rows and CME rows)
- boot F2: `results/membench-jibin-012/results/bootF2/` (L3 on, hardware prefetchers off, CME rows only)

The reader is an engineer who has never seen the project (chip architects, the emulator operator).

## Hard rules

1. FROM SCRATCH. Do not open `asimov-cme-perf*.html`, `asimov-cme-run4.html`, `asimov-c1nano-*.html`,
   `outliners.html`, `gen_perf*.py`, `gen_run*.py`, `gen_brief.py`, `gen_outliers.py`, `gen_hierarchy.py`.
   No text, number or code is taken from them.
2. NO HISTORY. The page describes what the two boots measure, in the present tense. Never write
   "run 3", "run 4", "run 6", "boot A..E", "earlier", "previously", "now", "no longer", "changed",
   "settled", "was thought", "new in". The boots are named "boot F1 (prefetchers on)" and
   "boot F2 (prefetchers off)". Folder names appear only in the References section.
   One exception: the section "Not measured on these boots" may cite ONE earlier-boot row when the
   two boots have no such row (the address-order chain), with its conditions stated and its number
   computed from that file. Nothing else from earlier folders.
3. EVERY measured number on the page is computed at build time from the CSV files by the generator.
   No measured number is typed into prose as a literal: prose is built with f-strings from the data
   layer. Facts that exist only in the operator's README or in a document are typed, carry a [RefN],
   and say "(operator's README)" or name the document.
4. Every claim is tied to rows (file named in the caption or by [RefN]). A cause that no counter
   proves is labelled "Hypothesis:" and is paired with the measurement that would confirm or reject it.
   Anything unknown is "Insufficient data: <what would resolve it>". Estimates carry "est.".
5. The fact sheets in `scratchpad/cme/facts/` are the research input. `critic.md` OVERRIDES the other
   sheets (its sections 1 and 2 are binding corrections; its section 3 lists content the page must add:
   G1, G2, G3, G4 as est., G5, G6, G7, G8, G9, G10 and the definitions of G19; G11 to G18 go to the
   open / not-measured section).
   Binding points: cite the measured cycles/ns ratio for the 2 GHz clock (not BogoMIPS); the L3 hit/miss
   events are exploratory, their fit (29.8 ns est.) may appear only inside a block labelled Hypothesis,
   never as a headline; "stores are not waited for by the span" is a hypothesis; the fit rule is "largest
   residual over 2 % of the smallest pass time voids the intercept"; a void intercept or rate is never
   quoted as a result; the SLC is "3.75 MiB est. after the OCM ways are taken out (operator's README)";
   an inner refill beyond the L3 hits is "a snoop of a core's cache (operator's README)"; an all-five OCM
   bandwidth pass is five kernel calls; DSU 1 at crosspoint (2,3) is a hypothesis; no write row may be
   labelled "to the L3 / SLC / DRAM"; DRAM is an emulator memory model, not silicon timing.
6. Wording (the page owner's rules):
   - never "hop": a chain step is "a load"; a mesh move is "a step".
   - never "chase": the per-load number is the "chain load"; the loop is "the latency test".
   - the DUP+LASTB row is the "round-trip baseline" (never "register control", never "floor").
   - chain kinds: "walked many times", "walked once", "every line flushed first", "address order".
   - OCM chain shapes: "one line per 4 KiB page", "every line". Never sparse / dense / fresh / flushed as nouns.
   - L1 bandwidth forms: "looped form" (one kernel call per pass), "single-call form" (all passes of a
     rep in one assembly call). Never "asm form".
   - "kernel" means the test loop in cme_kern.S, not Linux: define it once.
   - one term per thing: "span time" / "bracket time" / "outside-span time"; a "pass" is one walk over
     the buffer or chain, a "rep" is one timed measurement.
   - plain English per the plain-english skill: one claim per sentence, short sentences, no idioms or
     metaphors, no semicolons, units on every number, every code name / acronym / metric defined at first
     use in the section or in "Words used here".
   - citations: `[RefN]` after the sentence; all file:line and document references live in the
     References section at the end.
7. HTML: one self-contained file, `<meta charset="utf-8">` right after `<title>`, LIGHT theme only
   (no dark mode, no prefers-color-scheme), ASCII only inside SVG text (no middle dot, no micro sign:
   write "us", "x", "-"), no external resources. It must read well at 1100 px wide and print.
8. Visual first: every result section leads with a chart or diagram whose form fits the data, direct
   labels on the points that matter, the key difference annotated on the figure, a one-line takeaway
   under it, and a compact table with the exact numbers beside or under it. Follow the dataviz skill
   (load it: Skill "dataviz"): one axis per chart, thin marks, legend for 2+ series, hover tooltips,
   recessive grid, text in ink colors not series colors, honest axes (a truncated axis is said so).
   Fixed series colors everywhere: boot F2 (prefetchers off) = blue #2a78d6, boot F1 (prefetchers on)
   = orange #eb6834, the core on boot F1 = aqua #1baf7a; a fourth series, if one is unavoidable,
   = violet #6250d6. Red #e34948 is reserved for the critical-path slice of a wall-clock lanes diagram.
   Reference lines and capacity markers are grey.
   Chart forms to use: line chart with log2 footprint axis for sweeps; dumbbell (two dots joined, gap
   labelled) for F1-against-F2 or core-against-CME pairs; horizontal bars for magnitudes; a
   "wall-clock lanes" diagram for timing of a call (one lane per actor, X = time TO SCALE, solid block =
   work, dashed outline = waiting, the serial slice in red with its cost written on it, caption states
   any simplification); a box-and-arrow diagram, left to right, for the data path and for the mesh map.

## Code layout (all under /home/jhan/workspace/titan/cache-perf/asimov/)

- `gen_cme_perf.py`: entry point. `python3 gen_cme_perf.py` writes `asimov-cme-perf.html`. Standard
  library only, Python 3.10. It inserts its own folder in `sys.path` and imports the package.
- `cme_page/__init__.py` (empty), `cme_page/data.py`, `cme_page/viz.py`, `cme_page/shell.py`,
  `cme_page/API.md`, and one module per section `cme_page/sec_<key>.py`.
- `cme_page/data.py` (the data layer): parses every CSV of F1 and F2 that the page uses (CME files of
  both boots, the core twins and cmn-counts.csv of F1 and F2, log.txt command lines, the header
  comment lines) and exposes them through one `load()` call that returns an object `D`. It offers
  generic row access (`D.lat(boot, file, size, ...)`, `D.bw(...)`, `D.cmn(...)`) AND named derived
  tables that sections share (chain load by footprint with counters, L3-event rows, bandwidth sweeps
  bracket and span, per-pass times and fits with the plan rule verdict, call-cost rows, OCM per region,
  mesh counts per node, repeatability, clock ratio, command counts). Row rules: the program's own
  `-best` rows. Span and counters come from the first rep whose value equals the best. `data.py` has
  a `selftest()` (run by `python3 -m cme_page.data` from the project folder) that asserts at least 60
  values against the critic's corrected numbers and the "numbers to quote" list (G20).
- `cme_page/viz.py`: SVG builders returning strings: `line_chart`, `dumbbell`, `hbar`, `lanes`,
  `boxes` (box-and-arrow), small multiples helper, legend, hover tooltip (one small inline script,
  emitted once by the shell). Number formatting helpers (`ns`, `gbps`, `kib` footprint labels
  "4 KiB", "1.5 MiB"). Every builder takes plain Python lists, never reads files.
- `cme_page/shell.py`: the page object `S`: CSS, `S.h2(id, title)` / `S.h3` (auto-numbered),
  `S.fig(svg, caption, takeaway)` (auto "Figure N"), `S.table(headers, rows, caption, note)` (auto
  "Table N", right-aligned numbers), `S.ref(key, text)` -> "[RefN]" (numbered by first use, same key
  = same number), `S.term(name, definition)` (collects "Words used here": first definition wins),
  `S.bullets([...])`, `S.hyp(text, test)` (a Hypothesis block with its test), `S.insufficient(text)`,
  `S.callout(...)`, `S.render(sections) -> html` with a table of contents, the Short version on top,
  "Words used here" as section 1 and "References" last.
- A section module exposes `KEY`, `TITLE` and `build(D, V, S) -> str` (html of the section body; it
  calls S.h3 / S.fig / S.table / S.ref / S.term). A section module may hold its own extra derived
  computations. Section authors do NOT edit data.py, viz.py or shell.py (several authors work at
  once): if something is missing they write it in their own module and report it.
- Scripts for checking go under `scratchpad/cme/scripts/`, screenshots under `scratchpad/cme/shots/`.
  Nothing else in the project folder is created or edited. The results folders are read-only.

## Page outline

Short version (at most three sentences) and one headline figure: "What a CME chain load costs, by
where the line comes from" (critic G1: CME L1, inside the cluster, outside the cluster, OCM, DRAM
model; boot F2 demand-only values with the boot F1 values beside them), plus the bandwidth headline
numbers (single-call L1 read and write, read above the L1 on both boots).

1. Words used here (collected by S.term).
2. `setup`: What was measured. The platform (cores, cluster, CME, caches, mesh, OCM, DRAM model) with
   a left-to-right data-path diagram of one CME load, each box marked "on disk" or "document not on
   disk" for its source. The two boots and their differences. How the latency test and the bandwidth
   test work: kernels, chain kinds, bracket time against span time, the counters and their event
   numbers, the "-best" rule, the clock. Data integrity: checksums (computed at build time with
   hashlib against SHA256SUMS), command counts, failures, counter coverage.
3. `glance`: Results at a glance: the G1 table and figure in full, the "numbers to quote" list (G20)
   as a table, measured rates against documented limits (G2), repeatability (G8).
4. `latency`: Latency by footprint. Line chart: chain load against footprint, boot F2, boot F1, the
   core on boot F1, with the round-trip baseline and capacity markers. Chain load minus round-trip
   baseline. What serves each footprint: refill counters per load (read / prefetch, inner / outer) as
   small multiples under the same footprint axis. Prefetchers on against off (dumbbell). The 384 KiB
   to 512 KiB step and the chain kinds (G10). The flushed 8 MiB rows and the DRAM level. The
   once-per-rep refill observation (G5). Full table.
5. `l3`: The cluster L3 as seen by the CME: the exploratory L3-event rows of both boots (what the
   events are, that they are not validated), time against hit share on boot F2 (96 to 384 KiB), the
   fit inside a Hypothesis block with its condition number, what an L3-served load costs by rows
   alone, where the counts stop explaining the time (above 3 MiB), the timing repeat against the plain
   rows.
6. `bandwidth`: Bandwidth by footprint: read, write and copy on both boots, looped form and
   single-call form, bracket and span, bytes per cycle. Core against CME at equal footprint (dumbbell,
   incl. G3). The 64-byte forms (cme-ldr16 / cme-str16). The read fall-off above the CME L1. The write
   step between 256 KiB and 1 MiB (no cause claimed). Prefetchers on against off at large footprints.
   Lines in flight est. (G4).
7. `callcost`: The cost of one kernel call: a wall-clock lanes diagram of one looped read call to
   scale (span against outside-span). Time per pass against bytes for the four L1 forms (looped,
   single-call, no fold, DSB ST), the fits with the plan-rule verdict for each, the call-cost rows
   (1 KiB read and write, 2 / 4 / 8 KiB writes), the cme-call rows, a call alone in its bracket
   against calls back to back, the CME cycle counter gap (G6). What can be quoted and what cannot.
8. `ocm`: OCM through the CME: the mesh map (6 x 6 crosspoints, five home nodes, region to node id
   to position to steps: G9; DSU 1 position as a hypothesis), chain load per region on both boots
   (dumbbell: demand-only on F2, with prefetched lines on F1), order by mesh steps, the two chain
   shapes, pass spread, the core beside the CME on F1, OCM bandwidth read and write per region,
   mesh counters: requests per home node per load, that each command reached its intended node, the
   prefetcher's mesh traffic (G7).
9. `open`: Open items (each: observation with rows, why it is not explained, hypotheses, the
   measurement that would settle it) and "Not measured on these boots" (G11 to G18, plus the one
   permitted earlier-boot row).
10. References (collected by S.ref): files with line numbers, documents with their numbers,
    the operator's READMEs, the source files.

## Tools

- Python: `python3` (3.10). Use `python3 -I` for ad-hoc scripts that read the results folders.
- Screenshots: `/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell --no-sandbox --in-process-gpu --headless --window-size=1100,4000 --screenshot=<png> file://<html>`
  (the Bash sandbox must be off for it). For long pages slice by injecting a temporary copy with
  `body{margin-top:-Npx}`. Look at the PNGs with the Read tool.
