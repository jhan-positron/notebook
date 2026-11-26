export const meta = {
  name: 'w120-7200-report',
  description: 'Fix the last facts-sheet defects, build the HTML comparison report of the 7200 MT/s whole-chip rerun, review it from five angles, fix',
  phases: [
    { title: 'Facts fix', detail: 'apply the 22 open round-3 defects to the facts sheet, then check the fix' },
    { title: 'Build report', detail: 'generator script and HTML page with two charts' },
    { title: 'Review', detail: 'five independent reviewers: numbers, claims and rules, plain English, visual, cold reader' },
    { title: 'Fix', detail: 'report author verifies and fixes each finding' },
  ],
}

const S = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
const R = '/home/jhan/workspace/titan/cache-perf/crb/results'
const OUT = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
const GEN = S + '/make_report.py'
const DV = '/tmp/claude-0/bundled-skills/2.1.326/8cf8fd823b22dd3142aedd684b32e402/dataviz'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const COMMON = `
Context (read this first).
- Machine under test: CRB, a 128-CPU Arm reference server. Tests use 120 threads (CPUs 0-119: 64 on mesh 0, 56 on mesh 1), 256 MiB per thread.
- On 2026-11-17 the user asked: "Given that the DIMM issue is resolved at 7200 MT/s, let's rerun the whole chip test. Please run old kernel which used portable C code and had read and add, and run new kernel which performed worse than old kernel. Compare the results".
- The rerun is done. Raw result folders are under R = ${R}. Scripts and the facts sheet are under S = ${S}.
- S/FACTS.md (about 900 lines) and S/facts.json are the verified facts sheet, built by S/build_facts.py from the raw files. S/baselines-and-rules.txt holds the baseline list and the comparison rules that were fixed BEFORE the run (rules V1-V4, F1, F2). They are binding.
- Q1: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much. Q2: did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s.
- HARD LIMITS: do not use ssh. Do not run any benchmark. Do not change any file under R. Do not create files outside S, except the one report file named in your task. Do not send any project detail to an outside service. No network.
- The user's CLAUDE.md rules apply to all prose (plain-english skill rules, "Interpret test results with proof", light HTML theme). A shell "cd" prints a directory listing here; use absolute paths or "cd X >/dev/null".
`

const DEFECT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    checked: { type: 'string', description: 'what you checked and how (scripts, counts)' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['wrong-number', 'unsupported-claim', 'rule-violation', 'missing', 'wording', 'visual'] },
          where: { type: 'string' },
          quote: { type: 'string' },
          problem: { type: 'string' },
          correct: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['id', 'severity', 'where', 'problem', 'correct'],
      },
    },
  },
  required: ['lens', 'checked', 'defects'],
}

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    actions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          action: { type: 'string', enum: ['fixed', 'rejected', 'partly'] },
          note: { type: 'string' },
        },
        required: ['id', 'action', 'note'],
      },
    },
    build_ok: { type: 'boolean' },
    open_points: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'actions', 'build_ok'],
}

// ------------------------------------------------------------------ facts track
async function factsTrack() {
  const fix = await agent(`${COMMON}
Your task: apply the 22 open defects of verification round 3 to the facts sheet.
- The defects are in ${S}/review-w2.json under history[2].defects (fields id, severity, where, quote, problem, correct, evidence). Read them all with a script.
- The facts sheet is generated: edit the generator (S/build_facts.py, S/facts_data.py, S/facts_text.py, S/facts_text4.py), never FACTS.md or facts.json by hand. Rebuild with "python3 ${S}/build_facts.py".
- For each defect: check it against the raw files first. If it is right, fix it the way "correct" says (or better). If it is wrong, reject it and say why with evidence. Every fact that you add must be read from a raw file by the script or be checked by you against the raw file, and must carry its [RefN]. A sentence added in a correction is a new claim: check it as strictly as the old text.
- CONTRACT (another agent's script reads facts.json at the same time): do not rename or remove any field of the "intervals" records or of meta.launches. Do not change any GBps value, n, or line number of an existing record. The only allowed change to "intervals" values is the field kernel_before of the 3 A-3 records named in defect partA-r3-PA-5. You may add fields and you may change the text under "verdicts" and "meta".
- Keep the hardware-error-record facts of defect partL-r3-partL-1 and the firmware-settings facts of defect state-r3-S3-1 exact: read the journal file and the settings files that the defects name, and quote line numbers.
- After the rebuild: all integrity checks of the sheet must pass, and two builds in a row must give identical files.
Return the list of actions (one per defect id), whether the build is ok, and open points.`,
    { label: 'facts-fix', phase: 'Facts fix', schema: FIX_SCHEMA })

  const check = await agent(`${COMMON}
Your task: verify the fix of the 22 round-3 defects of the facts sheet. You did not write the fix. Try to refute it.
- The defects: ${S}/review-w2.json, history[2].defects. The fixer reported: ${JSON.stringify(fix ? fix.actions : 'no report (agent failed)').slice(0, 6000)}
- Snapshot before the fix: /tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e/scratchpad/facts.before.json and FACTS.before.md (same folder). Current files: ${S}/FACTS.md and ${S}/facts.json.
- Checks: (1) for each of the 22 defects: is it fixed in FACTS.md and, where it applies, in facts.json? For a rejected defect: is the rejection right? (2) Diff the "intervals" lists of the two facts.json files by script: no field removed or renamed, no GBps / line / n value changed, only kernel_before of the 3 A-3 records may differ. Report every other difference. (3) Diff FACTS.before.md against FACTS.md and check EVERY added or changed sentence as a new claim: recompute each new number from the raw file it cites (own script, not build_facts.py), check that each cited [RefN] exists in section 7 and that the file exists, check units, dates on times, labels (control I "added after the first numbers were seen", F72d12 "not part of the rerun"), and the binding rules in ${S}/baselines-and-rules.txt. (4) "python3 ${S}/build_facts.py" runs clean twice with identical output.
Report only real defects, each with evidence. An empty list is a valid result.`,
    { label: 'facts-check', phase: 'Facts fix', schema: DEFECT_SCHEMA })

  let fix2 = null
  if (check && check.defects && check.defects.length) {
    fix2 = await agent(`${COMMON}
Your task: fix the defects that a checker found in the last correction of the facts sheet.
- Generator files: S/build_facts.py, S/facts_data.py, S/facts_text.py, S/facts_text4.py. Never edit FACTS.md or facts.json by hand. Rebuild with "python3 ${S}/build_facts.py".
- CONTRACT: do not rename or remove any field of the "intervals" records or of meta.launches in facts.json, and do not change any GBps value, n, or line number (another script reads them).
- For each defect: verify it against the raw files, then fix it or reject it with evidence. A sentence that you add is a new claim: check it against the raw file.
Defects:
${JSON.stringify(check.defects, null, 1)}
Return one action per defect id, whether the build is ok (all integrity checks pass, two builds identical), and open points.`,
      { label: 'facts-fix-2', phase: 'Facts fix', schema: FIX_SCHEMA })
  }
  return { fix, check, fix2 }
}

// ------------------------------------------------------------------ report track
const REPORT_SPEC = `
THE REPORT.
Output: ${OUT} (one self-contained HTML file), written by the generator ${GEN} (Python 3 standard library only). Edit the generator, never the HTML.
Reader: an engineer who has never seen the project. The reader wants: (1) is the new read kernel still worse than the old one at 7200 MT/s, and by how much, (2) did anything change against the 8000 MT/s runs, (3) how far the data can be trusted.

Data rules.
- Every measured number on the page (text, tables, chart labels, tooltips) is computed by the generator from the "intervals" records of ${S}/facts.json (fields dataset, part, role, speed_MTps, modules, tag, session, process, proc_key, round, pos, interval, kernel, kernel_before, binary, GBps, mesh0_GBps, mesh1_GBps, passes, load1_at_launch, launch_utc, folder, file, line, start_state ...) and meta.launches. No measured number is typed by hand. Another agent rebuilds facts.json from time to time during your work (only text fields change): if a read fails, retry.
- The generator asserts the expected record counts (for example 18 intervals of bw_old read in part A, 6 oldread intervals in part L) and stops with an error when a count is wrong. Fail loud, no silent fallback.
- Cross-check: the values that your generator computes must equal the values in ${S}/FACTS.md (sections 0, 3.1-3.4, 4.2-4.6, 4.9) to 0.01 GB/s and 0.1 %. Print a short self-check list at the end of the build and exit with status 1 on a mismatch of the headline values listed below.
- Headline values that FACTS.md gives (your script must reproduce them, not copy them):
  Q1, part C (runner bwx12, 6 s, common stop, kernel "read" = new read kernel, "oldread" = old read kernel, drop computed inside the same process and round): read directly after oldread 30.5 % to 31.2 % lower (4 pairs / 2 processes T72C1, T72C3); read directly after asmread 29.7 % to 31.1 % lower (4 pairs / 2 processes T72C2, T72C4). read 320.89 to 324.98 and 322.22 to 326.27 GB/s; oldread 464.00 to 468.14 GB/s.
  Q1, part L (asmread = hand-written load-only loop with the same 8 "ldp q" loads per 256 B, used in place of the new read kernel): 29.2 % to 30.5 % lower (6 pairs / 3 processes / 3 sessions). oldread 461.61 to 464.29, asmread 321.65 to 327.93 GB/s.
  Q1, part A (the repeat of the 2026-11-13 test: binaries bw_old and bw_new, kernel "read", 0.5 s intervals, whole-pass stop; ratio of process medians per session and round): 28.5 % to 31.8 % lower (6 pairs / 3 sessions). Less exact than parts L and C (pass-count steps).
  Control I (the part L line from an idle start, 2 processes, ADDED AFTER THE FIRST NUMBERS WERE SEEN, not part of the plan fixed before the run): 31.9 % to 32.8 %. F72d12 (one earlier process of the same line in the same boot at 20:02 UTC, NOT PART OF THE RERUN): 35.4 %.
  Q2, old read kernel: part A 459.90 to 474.15 GB/s (18 intervals / 6 processes / 3 sessions / 1 boot) against 463.58 to 469.03 GB/s (pool A-1 to A-3, 21 intervals / 7 processes / 1 boot): "no difference seen", the test cannot exclude about 1.2 % (est. from one boot). Part C 464.00 to 468.14 against pool L-1 to L-4 465.53 to 470.05 GB/s (11 intervals / 7 processes / 1 boot): "no difference seen", cannot exclude about 1.0 % (est.). Part L 461.61 to 464.29 against 465.53 to 470.05: "differs between the 8000 MT/s boot and the 7200 MT/s boot", lower by 1.24 GB/s at the nearest ends (0.3 %) and by 6.27 GB/s between the medians (1.3 %). Give both distances, never only one. F72d12 467.46 to 468.44 and control I 466.30 to 469.20 GB/s overlap the 8000 MT/s range.
  Q2, load-only loop: part L asmread 321.65 to 327.93 against pool L-1 to L-4 288.54 to 309.17 GB/s: "differs between the 8000 MT/s boot and the 7200 MT/s boot" (12.48 GB/s at the nearest ends). Part A, bw_new read, session 1: outside (above) the 8000 MT/s range of the same round in both rounds (round 1: 330.09 to 333.25 against 279.66 to 297.34; round 2: 326.68 to 332.82 against 294.02 to 316.31 GB/s); the pass counts differ (664 against mostly 600), so part A gives no exact size. Part C kernel read: Insufficient data, no 8000 MT/s run of kernel read with bwx12. Same boot: F72d12 asmread 301.90 to 302.78 GB/s (inside the 8000 MT/s pool range; 1.73 GB/s above L-1 alone); control I 313.78 to 317.60 GB/s. The three visits of the one 7200 MT/s boot (F72d12, part L, control I) do not overlap each other and span 301.90 to 327.93 GB/s (26.03 GB/s). That is more than the 12.48 GB/s between part L and the 8000 MT/s pool. Each memory speed has exactly one boot. So: "Insufficient data: whether a difference of the new read kernel comes from the memory speed. Runs in several boots per speed would resolve it (needs reboots and a change of the firmware setting)."
- BINDING RULES for the wording (from ${S}/baselines-and-rules.txt; read the file):
  * Never give a percent change of a load-only kernel (bw_new read, bwx12 read, asmread) between 8000 and 7200 MT/s, and never present any change as an effect of the memory speed. Differences in GB/s between named ranges are allowed.
  * Compare min-to-max ranges. Use the fixed wordings "no difference seen" (with the size the test cannot exclude = width of the 8000 MT/s range, est.) and "differs between the 8000 MT/s boot and the 7200 MT/s boot".
  * State n as intervals / processes / sessions / boots wherever a range is compared across speeds. 1 boot per speed.
  * Part A, load-only kernels: rounds kept apart, session 1 only against the 8000 MT/s processes of the same round, wording "inside"/"outside", no percent.
  * Part C is grouped by the kernel that ran directly before. No range over all read intervals of part C in a cross-speed statement. (Within 7200 MT/s the drop per group is fine.)
  * Control I is labelled at every use: added after the first numbers were seen. F72d12 is labelled: earlier run of the same boot, not part of the rerun. Neither is pooled with part L in a range test.
  * In part L and control I, asmread stands in for the new read kernel: say so in the row label.
  * The drop in percent between old and new kernel AT 8000 MT/s may be shown per row for context (same computation inside one process and round, or process medians for part A), but the page must then also show that the gap moved inside the one 7200 MT/s boot (29.2 % to 35.4 %), and must not call the smaller gap an effect of the memory speed.

Page content, in this order. Keep the prose short: about 700 to 1000 words outside tables, captions, word list and references.
1. Title "Whole-chip read test at 7200 MT/s: old read kernel against new read kernel" and one line: date 2026-11-17, machine, 120 threads, 12 memory modules.
2. "Short version": AT MOST 3 sentences, short, a newcomer can follow them. Sentence 1 answers Q1 directly with the measured range. Sentence 2: old read kernel against 8000 MT/s. Sentence 3: the load-only loop was higher than in the 8000 MT/s runs, and the data do not show that the memory speed is the cause.
3. "Words used here" as a <details> element, folded by default: every project name, abbreviation and metric used on the page (reuse the definitions of the word list at the top of FACTS.md; only the terms the page uses).
4. Figure 1, a dumbbell chart, the main picture for Q1: one row per process (or per session and round for part A); on each row one dot for the old read kernel and one dot for the load-only kernel of the same row (median of the row's intervals), a thin line between them, the drop in percent written on that line (range of the per-pair drops of the row, 1 decimal), a short min-to-max whisker per dot, a direct value label on each dot. x axis: rate in GB/s, starting at 0 (the picture shows a ratio). Two blocks of rows with block labels:
   Block "6 s measurements, runner bwx12, all threads stop together": 8000 MT/s: L-1 (2026-11-17 02:05 UTC, row with the identical argument line; asmread in place of the new read kernel). 7200 MT/s: F72d12 (20:02 UTC, earlier run of the same boot, not part of the rerun; asmread), part L sessions 1, 2, 3 (asmread), part C processes T72C1 (cfwd), T72C2 (crev), T72C3 (cfwd), T72C4 (crev) (kernel read = the new read kernel), control I T72I1, T72I2 (asmread; added after the first numbers were seen).
   Block "0.5 s measurements, the two binaries of 2026-11-13, each thread finishes its pass": 8000 MT/s: A-1 round 1, A-1 round 2, A-2 round 1, A-2 round 2. 7200 MT/s: session 1 round 1, round 2; session 2 round 1, round 2; session 3 round 1, round 2 (bw_old read against bw_new read).
   The memory speed of a row is shown by the block/row-group label and by the marker fill (for example hollow markers for 8000 MT/s, filled for 7200 MT/s), not by a new colour. Colour = kernel: one colour for the old read kernel, one for the load-only loop (new read kernel or asmread). Legend present. Under the figure one takeaway line in plain words (which dot stays, which dot moves, measured span of each).
5. A compact table for Q1 (one row per part: pair, lowest and highest drop in %, rates, n).
6. Figure 2, the picture for Q2: every interval as one small dot, in two panels side by side with their own zoomed x axes (left panel: old read kernel, right panel: load-only loop; each panel's axis labelled in GB/s, with a visible note that the axis does not start at 0). Rows grouped as in Figure 1 by method and by memory speed: for the 0.5 s block rows A-1, A-2, A-3 (8000 MT/s; A-3 has bw_old read only) and sessions 1, 2, 3 (7200 MT/s), with round 1 and round 2 on separate rows in the load-only panel; for the 6 s block rows L-1, L-2, L-3, L-4 (8000 MT/s; oldread at position 0 and asmread at position 1 only), F72d12, part L, part C (oldread; read after oldread, read after asmread; asmread groups), control I (7200 MT/s). Behind the rows of each block a shaded band shows the min-to-max range of the 8000 MT/s pool of that block (A-1 to A-3, or L-1 to L-4), so the reader sees which 7200 MT/s rows overlap it. For the load-only panel of the 0.5 s block the band is per round (rule V3). Same colours and hollow/filled convention as Figure 1. One takeaway line under it.
7. A compact table for Q2: one row per comparison (kernel, part, 7200 MT/s range, 8000 MT/s range, n of both, overlap yes/no, distance of the nearest ends in GB/s, fixed wording).
8. "What the data do not show" (bullets, each starts with "Insufficient data:" and names the measurement that would resolve it): effect of the memory speed on the load-only loop; why the load-only loop moved between the three visits of the one boot; why old read was lower in part L; no 8000 MT/s run of bwx12 kernel read; hardware error records during the rerun were not read (the kernel log needs root, which was not approved for this task); no direct reading of the memory speed during the rerun (needs root).
9. "Machine state and system load": 12 modules at 7200 MT/s and how it is proven (MemTotal 395392808 kB in every state line; boot id 3bfc57a1-e235-4fe5-8c09-a94642f9b60b equal to the boot whose record ${R}/dimm7200-20261117/try6.txt shows 12 x "Configured Memory Speed: 7200 MT/s"), with the limit (speed not read during the rerun). A compact table with the 1-minute load average at the first launch of every step (meta.launches: T72A1 ... T72C4, T72I1, T72I2) and the load at launch of the 8000 MT/s rows used. Say that the first launch was at load 0.07, that the later values (28 to 113) are 1-minute averages taken while the rerun's own earlier 120-thread processes were still counted, and that the state lines of ${R}/go-T72-20261117T221209Z.log list no process of another user (verify this in the log before you write it). Run facts: go.sh ran 22:12:09 to 22:22:18 UTC, 10 of 10 steps with exit status 0; control I ran afterwards (go2 log).
   Three facts from the open defect list (${S}/review-w2.json, history[2].defects, ids partL-r3-partL-1, state-r3-S3-1, state-r3-S3-2) belong in this section or in the limits, each ONLY after you verified it yourself in the raw file the defect names: (a) the 8000 MT/s journal holds corrected hardware error records during baseline rows L-1 and L-2, and the lowest asmread value of the pool (288.54 GB/s) comes from an interval with 2 such records; without that one interval the pool spans 298.61 to 309.17 GB/s, and part L still lies above it; (b) the TXREQ firmware settings changed for another test on 2026-11-17 were set back before the rerun, and the only later change on record is DIMM Frequency = 7200 MT/s; (c) why F72d12 belongs to boot 3bfc57a1.
10. "References": numbered list [Ref1] ... Each reference = one file path (with line numbers where a single line carries the claim) or one script. In the body, a reference index follows the sentence that carries the claim; it never replaces the sentence. Include FACTS.md as the detailed record, baselines-and-rules.txt, the run scripts (go.sh, ra.sh, go2.sh, specs), the two run logs, each result folder used, try6.txt. Every path must exist: the generator checks os.path.exists for each reference and fails otherwise.

Form rules.
- LIGHT theme only (background #fcfcfb or similar, one theme, no prefers-color-scheme). No external font, script, image or stylesheet. Inline SVG charts drawn by the generator. Layout works at 1280 px and at a 420 px wide window (charts may scroll sideways inside their own box at 420 px; the page itself must not scroll sideways).
- Follow the dataviz skill at ${DV}: read SKILL-level rules in ${DV}/references/choosing-a-form.md, color-formula.md, marks-and-anatomy.md, interaction.md, anti-patterns.md. Validate the two series colours against the light surface with "python3 ${DV}/scripts/validate_palette.py" (read its usage first) and fix any FAIL. The earlier report of this project used blue #2a78d6 and orange #eb6834 on #fcfcfb: start from these and keep them if they pass. Text is ink-coloured, never series-coloured. Direct labels plus a legend. Every mark has an SVG <title> with the row name, the exact value(s), n and the source file (native hover tooltip; no script needed). No dual axis.
- Label estimates "est.". Units on every number. Times in UTC. Define each term at first use or in the word list.
- Style of the page: the earlier report ${'/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html'} and its generator ${'/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/easy_read.py'} show the house style (system-ui font, ink #0b0b0b, muted #52514e, grid #e4e3df). Match it.
- Render check: a headless Chrome exists. Read ${MEM}/headless-chrome-offline-render.md for the exact command. Take screenshots at window widths 1280 and 420, LOOK at them with the Read tool, and fix every overlap, clipped label and unreadable mark. Keep the screenshots under ${S}/render/.
`

async function buildReport() {
  return agent(`${COMMON}
Your task: write the generator and build the report page.
${REPORT_SPEC}
Work order: (1) read FACTS.md sections 0, 3, 4.1-4.6, 4.9, 6 and baselines-and-rules.txt; (2) explore facts.json; (3) write ${GEN}; (4) build; (5) render and look; (6) run the plain-english self-check of the user's CLAUDE.md over the whole visible text; (7) run the self-check list of the generator.
Return: the paths, the Short version text as built, the list of self-checks with their results, the palette validator output, and open points (anything you could not verify, any scope cut).`,
    { label: 'report-build', phase: 'Build report', schema: {
      type: 'object',
      properties: {
        html: { type: 'string' }, generator: { type: 'string' },
        short_version: { type: 'string' },
        self_checks: { type: 'array', items: { type: 'string' } },
        palette_validation: { type: 'string' },
        open_points: { type: 'array', items: { type: 'string' } },
      },
      required: ['html', 'generator', 'short_version', 'open_points'],
    } })
}

const LENSES = [
  { key: 'numbers', prompt: `Lens NUMBERS. Recompute EVERY measured number on the page from the RAW csv files under R with your own parser (not facts.json, not build_facts.py, not make_report.py): text, table cells, chart labels, <title> tooltips, n counts, percent values, ranges, medians, distances, load values, times. Raw formats: part A files threads120.csv hold "-- binary ... kernel ... round ... load ..." header lines followed by one csv row per interval (column aggregate_GBps); bwx12 csv files hold rows of kind I/T/P/C, total of an interval = sum over its T rows of bytes / elapsed_s / 1e9 (S/stat_bwx.py and S/stat_k120.py show the formats; write your own code). Also check that the dot positions in the SVG match their values (read cx/x attributes and the axis scale). Report each mismatch above 0.01 GB/s or 0.1 % with both values and the raw file and line.` },
  { key: 'claims', prompt: `Lens CLAIMS AND RULES. Take the visible text sentence by sentence. For each claim: is it tied to named test data or a source, and does that source say it? Check against the binding rules in S/baselines-and-rules.txt (V1-V4, F1, F2) and against the verdicts of S/FACTS.md sections 0, 3.4, 4.9 and 6: no percent change of a load-only kernel across memory speeds, nothing presented as an effect of the memory speed, fixed wordings used, n given as intervals / processes / sessions / boots at cross-speed comparisons, rounds of part A kept apart for load-only kernels, part C grouped by the kernel before, control I labelled "added after the first numbers were seen" at every use, F72d12 labelled as not part of the rerun, asmread named as standing in for the new read kernel, part L old read given with BOTH distances (1.24 GB/s nearest ends, 6.27 GB/s medians), "Insufficient data" items named with the resolving measurement, estimates labelled est. Then sweep the page with the claim defect classes in ${MEM}/review-loop-claim-defect-classes.md (read the file). Also: does the page give a direct verdict on the user's request, and is any hypothesis presented as a fact?` },
  { key: 'english', prompt: `Lens PLAIN ENGLISH. Extract the visible text of the page (including table headers, captions, legend, tooltips' wording, word list, references) and run the plain-english skill of the user's CLAUDE.md in Check mode over all of it: idioms or uncommon words (rule 1), two claims in one sentence (rule 2), long sentences and semicolons (rule 3), paragraphs that need bullets (rule 4), citations that replace a sentence or stand alone, reference list at the end, every [RefN] in the body present in the list and every list entry used (rule 5), numbers without unit or meaning, estimates without "est." (rule 6), Short version of at most 3 sentences that a newcomer can follow (rule 7), every project name, abbreviation, metric defined at first use or in the folded "Words used here" list (rule 8). Give the exact phrase and a corrected phrase for each violation. Do not invent violations.` },
  { key: 'visual', prompt: `Lens VISUAL. Render the page with the headless Chrome described in ${MEM}/headless-chrome-offline-render.md (own --user-data-dir under S/render/) at window widths 1280, 900 and 420, and LOOK at the screenshots with the Read tool (crop tall pages into parts so that text is legible). Check: light background, one theme; no overlapping or clipped labels; every dot label legible; the drop labels sit on their rows; legend present and correct; hollow/filled convention explained; axis titles with unit; Figure 1 axis starts at 0; Figure 2 states that its axes do not start at 0; shaded 8000 MT/s bands are in the right place (compare with the numbers in the table); tables readable and not wider than the page at 1280; at 420 the page itself does not scroll sideways; <details> word list folded by default; no external resource (grep for http, @import, <script src, <link). Run "python3 ${DV}/scripts/validate_palette.py" on the series colours against the page surface and report FAILs. Check the charts against ${DV}/references/anti-patterns.md and marks-and-anatomy.md. Check that every mark has a <title> tooltip. Report each defect with the screenshot file and position.` },
  { key: 'reader', prompt: `Lens COLD READER AND COMPLETENESS. Part 1: read ONLY the HTML page first, as an engineer who has never seen the project, before any other file. Write down every sentence, label or chart element that you could not follow or that left a question open, and whether the first screen (Short version and Figure 1) answers "is the new read kernel still worse than the old one at 7200 MT/s, and by how much". Part 2: completeness against the request and the standing rules: the system load is reported for every test step and for the 8000 MT/s rows; the memory module count (12) and speed (7200 MT/s) are stated with proof and limit; the comparison old against new AND 7200 against 8000 MT/s is there; limits and scope cuts are stated (root not used, kernel log not read, control I added later, one boot per speed); each reference path exists on disk (check every path) and the cited lines hold what the sentence says (sample at least 15 references, name them); the generator runs clean ("python3 ${GEN}") and writes an identical file on a second run; the page length is fit for its purpose (flag padding and repetition, and flag anything essential that is missing).` },
]

function reviewPrompt(lens, round, rejected) {
  return `${COMMON}
You are an independent reviewer of the report page ${OUT} (generator ${GEN}). You did not write it. Try to find real defects; do not approve by default.
The specification the author worked from:
${REPORT_SPEC}
${lens.prompt}
Round ${round}. ${rejected.length ? 'The author rejected these earlier findings with reasons; do not report them again unless you have new evidence: ' + JSON.stringify(rejected).slice(0, 5000) : ''}
Do not edit the report or the generator. You may write scratch scripts under ${S}/review-scratch/${lens.key}/ only.
Report only defects that are present in the current file, each with where, the exact quote, the problem, the correct text or value, and evidence (file and line, or screenshot). An empty list is a valid result. Give ids of the form r${round}-${lens.key}-N.`
}

// ------------------------------------------------------------------ run
phase('Facts fix')
const [facts, built] = await parallel([
  () => factsTrack(),
  () => buildReport(),
])
log('facts track and first build finished')

const history = []
let rejected = []
for (let round = 1; round <= 3; round++) {
  const reviews = (await parallel(LENSES.map(l => () =>
    agent(reviewPrompt(l, round, rejected), { label: `review-${l.key}-r${round}`, phase: 'Review', schema: DEFECT_SCHEMA })
  ))).filter(Boolean)
  const defects = reviews.flatMap(r => r.defects || [])
  log(`round ${round}: ${defects.length} findings from ${reviews.length} reviewers`)
  const entry = { round, checked: reviews.map(r => ({ lens: r.lens, checked: r.checked, n: (r.defects || []).length })), defects }
  history.push(entry)
  if (!defects.length) break
  const fix = await agent(`${COMMON}
You are the author of the report page ${OUT}, generated by ${GEN}. Five reviewers returned the findings below (round ${round}).
The specification:
${REPORT_SPEC}
For EACH finding: verify it yourself first (raw file, rule text, screenshot). If it is right, fix it in the generator. If it is wrong, reject it and give the evidence. If two findings contradict each other, pick the one that the binding rules and the raw data support, and say so. Do not add new claims while fixing; a sentence that you add is a new claim and needs its own tie to data and its [RefN]. Keep the page short. Never edit the HTML by hand.
After the fixes: rebuild (python3 ${GEN}), run the generator's self-check, render at widths 1280 and 420 with the headless Chrome (${MEM}/headless-chrome-offline-render.md), look at the screenshots, and run the plain-english self-check over changed text. The facts sheet ${S}/FACTS.md was corrected in the meantime; where the page and the sheet now disagree, follow the raw data and report the disagreement.
Findings:
${JSON.stringify(defects, null, 1)}
Return one action per finding id (fixed / rejected / partly, with a note), whether the build is ok, and open points.`,
    { label: `report-fix-r${round}`, phase: 'Fix', schema: FIX_SCHEMA })
  entry.fix = fix
  if (fix && fix.actions) rejected = rejected.concat(fix.actions.filter(a => a.action === 'rejected'))
}

return { facts, built, history }
