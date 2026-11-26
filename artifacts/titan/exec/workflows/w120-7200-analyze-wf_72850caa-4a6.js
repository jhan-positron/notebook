export const meta = {
  name: 'w120-7200-analyze',
  description: 'Build the facts sheet of the 7200 MT/s whole-chip rerun from raw files, then verify every number and verdict independently',
  phases: [
    { title: 'Facts', detail: 'one author builds FACTS.md and facts.json by script' },
    { title: 'Verify', detail: 'five independent checkers recompute and try to refute' },
    { title: 'Fix', detail: 'author corrects confirmed defects; loop until clean' },
  ],
}

const ROOT = '/home/jhan/workspace/titan/cache-perf/crb'
const R = ROOT + '/results'
const S = ROOT + '/tmp/agent-scratch/w120-7200-2026-11-17'
const CTX = `
CONTEXT (read this first).
- Project folder: ${ROOT}. Results: R = ${R}. Scratch folder of this task: S = ${S}.
- Machine "CRB" = an Arm reference server with 128 CPUs. CPUs 0-63 sit on mesh 0, CPUs 64-127 on mesh 1. Our runs use CPUs 0-119 only: 120 threads = 64 on mesh 0 + 56 on mesh 1, 256 MiB per thread, read from DRAM. GB = 1e9 bytes.
- HARD RULES: do NOT ssh to CRB or any machine. Run no benchmark. Never change a file under R. Write only the files your task names (all under S).
- The user's request of today (2026-11-17): "Given that the DIMM issue is resolved at 7200 MT/s, let's rerun the whole chip test. Please run old kernel which used portable C code and had read and add, and run new kernel which performed worse than old kernel. Compare the results."
  Question 1 (Q1): at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much.
  Question 2 (Q2): did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s.
- History: R/kernels-20261113T181222Z (the original "whole chip test" of 2026-11-13: binaries bw_old and bw_new of bench/bandwidth.c; script ${ROOT}/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh). bw_old "read" = old read kernel: portable C, 16 running sums, each load is followed by an add. bw_new "read" = new read kernel: NEON intrinsics, loads only. "asmread" = hand-written load-only loop with the same 8 "ldp q" loads per 256 B. The earlier investigation of the drop: ${ROOT}/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md (runner bwx12: kernels oldread, read, asmread, read_nop96, read_nop256, read_1pl).
- Memory modules: with the memory speed at 8000 MT/s CRB booted with either 12 or 10 modules. On 2026-11-17 about 19:43 UTC the speed was set to 7200 MT/s. Records: /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/crb-memory-module-count-varies-per-boot.md , /home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md , R/dimm-check-20261117/ , R/dimm7200-20261117/ (try6.txt: boot id 3bfc57a1-e235-4fe5-8c09-a94642f9b60b, 12 modules, 12 x "Configured Memory Speed: 7200 MT/s").
- THE RERUN OF TODAY (all in boot 3bfc57a1..., run 22:12:09 to 22:22:18 UTC, then a control 22:23:35 to 22:33:34 UTC). Scripts in S: go.sh (driver), ra.sh (part A), like.spec, cfwd.spec, crev.spec (spec files for ${ROOT}/tmp/agent-scratch/w120-2026-11-15/rx.sh with runner bwx12), go2.sh (control). Logs with machine-state lines: R/go-T72-20261117T221209Z.log and R/go2-T72-20261117T222335Z.log.
  Part A = the 120-thread part of the 2026-11-13 test with the same two binaries (whole-pass stop, 0.5 s, 3 intervals per process, 24 processes per session): R/k120-T72A1-20261117T221209Z, R/k120-T72A2-20261117T221518Z, R/k120-T72A3-20261117T221827Z (threads120.csv, probe.txt).
  Part L = bwx12, common stop, 6 s, 2 rounds, sequence oldread,asmread,read_nop96,read_nop256,read_1pl (the same argument line as R/w120-R8-20261117T020549Z/a6456.csv): R/w120-T72L1-20261117T221329Z, R/w120-T72L2-20261117T221638Z, R/w120-T72L3-20261117T221947Z.
  Part C = bwx12, common stop, 6 s, 2 rounds, sequence oldread,read,asmread (cfwd) or asmread,read,oldread (crev): R/w120-T72C1-20261117T221436Z (cfwd), R/w120-T72C2-20261117T221745Z (crev), R/w120-T72C3-20261117T222054Z (cfwd), R/w120-T72C4-20261117T222136Z (crev).
  Control I = the part L line started from an idle machine (1-minute load average below 1.0), twice: R/w120-T72I1-20261117T222700Z, R/w120-T72I2-20261117T223227Z. The control was ADDED AFTER the first numbers of parts A, L and C were seen (reason: an earlier run of the same line in the same boot, R/w120-w120-F72d12-20261117T200231Z at 20:02 UTC, gave a lower asmread total than part L). It is therefore not part of the plan fixed before the run; label it so.
  Order of one session in go.sh: A, L, C. Three sessions, then one more C process (T72C4).
- RULES FIXED BEFORE THE RUN: S/baselines-and-rules.txt (written 22:11:51 UTC, 18 s before go.sh started). It holds the fixed list of valid 8000 MT/s baselines per part, the folders that are NOT baselines, and the rules for the Q2 wording (compare min-max ranges; when to write "differs between the 8000 MT/s boot and the 7200 MT/s boot", when "no difference seen"; never give a percent change of the new read kernel as an effect of the memory speed; group part C by the kernel that ran directly before; part A per process, not pooled, for the load-only kernels). These rules are binding. Note inside the file: with the fourth C process, crev has 2 processes (T72C2, T72C4). The record of the review that produced the rules is S/review-w1.json.
- Existing tools in S: stat_k120.py (statistics of a threads120.csv; prints pass counts), stat_bwx.py (statistics of bwx csv files: totals as the sum over threads of bytes / elapsed_s / 1e9, sums per mesh), base8000/ (converted copies of the 8000 MT/s baselines A-2 and A-3 of part A, readable by stat_k120.py).
- The user's rule for results: every claim cites specific test data (file, and row or interval) or an external source. A claim without such a tie is a labelled hypothesis with the measurement that would confirm or reject it. A gap is flagged "Insufficient data" with the measurement or source that would resolve it. Estimates are labelled "est.". Every number has a unit. System load at each launch must be reported. The memory module count must be stated.
- Not available: root on CRB was not approved for this task. So the kernel log (hardware error records) of the rerun was not read, and the memory speed during the rerun is proven only through the boot id (equal to try6.txt).
`

const DEFECTS = {
  type: 'object',
  properties: {
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['wrong-number', 'unsupported-claim', 'rule-violation', 'missing', 'wording'] },
          where: { type: 'string' },
          quote: { type: 'string' },
          problem: { type: 'string' },
          correct: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['id', 'severity', 'where', 'quote', 'problem', 'correct', 'evidence'],
      },
    },
    numbers_checked: { type: 'number' },
    confirmed_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['defects', 'numbers_checked', 'confirmed_ok'],
}
const AUTHOR = {
  type: 'object',
  properties: {
    facts_md: { type: 'string' },
    facts_json: { type: 'string' },
    scripts: { type: 'array', items: { type: 'string' } },
    q1_verdict: { type: 'string' },
    q2_verdict: { type: 'string' },
    open_points: { type: 'array', items: { type: 'string' } },
  },
  required: ['facts_md', 'facts_json', 'scripts', 'q1_verdict', 'q2_verdict', 'open_points'],
}
const FIXED = {
  type: 'object',
  properties: {
    handled: {
      type: 'array',
      items: {
        type: 'object',
        properties: { id: { type: 'string' }, applied: { type: 'boolean' }, note: { type: 'string' } },
        required: ['id', 'applied', 'note'],
      },
    },
    q1_verdict: { type: 'string' },
    q2_verdict: { type: 'string' },
  },
  required: ['handled', 'q1_verdict', 'q2_verdict'],
}

phase('Facts')
const author = await agent(`${CTX}
YOUR TASK: build the facts sheet of the rerun. Two files: S/FACTS.md (for people) and S/facts.json (for the report generator). Every number must come out of a script that you keep in S (for example S/build_facts.py, which reads the raw files under R and S/base8000 and writes facts.json, and which prints the tables that you paste into FACTS.md). Type no number by hand. You may call or import stat_k120.py and stat_bwx.py.
Read first: S/baselines-and-rules.txt (binding), go.sh, ra.sh, go2.sh, the two logs, FINDINGS.md (sections "The question", F1, F2), and the format of the csv files.
FACTS.md must hold, in this order:
0. "Short version": at most three sentences that answer Q1 and Q2.
1. Run record. Times (UTC) of every step from the logs and launch lines. Machine state with its proof: boot id and MemTotal of every state line and every probe.txt (12 modules), the proof of 7200 MT/s through try6.txt, kernel command line, governor, huge page setting, logins, processes per user, marker state. The 1-minute load average at EVERY process launch (part A: the "load" field of each "-- binary" line, min and max per session, and the load at the first process; parts L, C, I: launches.txt). Integrity checks with their result, each as one line: 24 processes x 3 intervals per threads120.csv; number of "I" rows per bwx csv (10 for L and I, 6 for C); "rc 0" for every launch; 0 bytes in every stderr.txt; every interval of L, C, I has 120 threads = 64 on CPUs 0-63 + 56 on CPUs 64-119; the flags column of the T rows; the "P" rows (were the buffers on 2 MiB pages?); binary sha256 values (probe.txt, env.txt) against the earlier runs. The gap in seconds between the end of the previous 120-thread process and each launch of L, C, I and each session of A. List the differences between the procedure of 2026-11-13 and part A (see finding F9 and F1 in S/review-w1.json) as limits.
2. Decisions made by the agent for this run (state them as decisions, not as facts about the machine): (a) "whole chip test" was read as the 120-thread part of run_kernels.sh of 2026-11-13; the one-thread part was not repeated. (b) "old kernel" = read of bw_old, "new kernel" = read of bw_new, same binaries by sha256. (c) Part A ran all six kernels to keep the process order of 2026-11-13; statements are made for the read kernels only (rule V3). (d) Parts L and C were added because FINDINGS.md F1 shows that the 0.5 s whole-pass stop rule of bandwidth.c distorts totals. (e) Three sessions back to back plus a fourth C process. (f) No root: speed proven through the boot id; kernel log not read. (g) Control I added after the first numbers were seen. (h) Baseline list and rules fixed 18 s before the run.
3. Q1, old against new at 7200 MT/s. Part A: one row per session and round (= one process, 3 intervals with pass counts) for bw_old read, bw_new read, bw_old asmread, bw_new asmread; the ratio new/old per session and round. Parts L and I: per process and round oldread, asmread, the drop in percent computed inside the same process and round, and the sums per mesh. Part C: oldread, read, asmread, grouped by the kernel that ran directly before (rule V2), the drop of read against oldread inside the same process and round. Then the Q1 verdict with the smallest and largest drop per part, and n as intervals / processes / sessions / boots.
4. Q2, 7200 against 8000 MT/s, strictly by the fixed rules: per part and kernel the min-max range of the 7200 MT/s intervals, the min-max range of each like-for-like 8000 MT/s baseline (each baseline as its own row; recompute them from the raw files named in baselines-and-rules.txt, including the supporting and "other binary" rows with their labels), overlap yes or no, and the wording that the rule prescribes. Show R/w120-w120-F72d12-20261117T200231Z and control I as separate 7200 MT/s rows beside part L (same boot, idle start), never pooled with part L. State what the same-boot rows show about the spread of the load-only loop between visits inside one boot at one memory speed, and what follows for Q2 (rule V1 point 3). Also give, as record only, read_nop96, read_nop256 and read_1pl of parts L and I against R8 and F72d12.
5. Record only, no statement: write, copy, asmwrite, asmcopy of part A per session (n, min, median, max) beside 2026-11-13.
6. What is established, what is not established ("Insufficient data" with the resolving measurement), labelled hypotheses.
7. Files: every raw file and script used, with one line each.
facts.json must hold every per-interval value that FACTS.md uses, with its source (folder, file, session or tag, round, position, kernel, binary, kernel before, speed, modules, load at launch, sums per mesh where they exist, pass count where it exists), plus the verdict strings. Keep it one flat list of interval records plus a small "meta" and "verdicts" object, so that a chart script can filter it.
Write in plain English: short sentences, one claim per sentence, no idioms, every code name explained at first use, units on every number. Return the two file paths, the script paths, the two verdicts, and open points.`, { label: 'author:facts', phase: 'Facts', schema: AUTHOR })

if (!author) return { error: 'author failed' }

const LENSES = [
  { key: 'partA', prompt: `Check every number and statement of FACTS.md and facts.json that concerns PART A (the three k120-T72A* folders) and its 8000 MT/s baselines (R/kernels-20261113T181222Z/threads120.csv, R/partA-20261113T205055Z/A1.csv and A3.csv). Recompute from the RAW csv files with your OWN parser (do not use stat_k120.py, stat_bwx.py or the author's scripts, and do not read S/base8000): per process the three aggregate_GBps values, pass counts (total_bytes / bytes_per_thread), per-thread min and max, the "load" of each header line, the ratios new/old, n, min, median, max, and each range comparison of Q2 for part A.` },
  { key: 'partL', prompt: `Check every number and statement of FACTS.md and facts.json that concerns PART L (w120-T72L1..3), CONTROL I (w120-T72I1..2), the same-boot run R/w120-w120-F72d12-20261117T200231Z and the bwx12 baselines named for part L in S/baselines-and-rules.txt (R/w120-R8-20261117T020549Z and the supporting rows). Recompute from the RAW csv files with your OWN parser (do not use stat_bwx.py, an.py or the author's scripts): per interval the total = sum over the T rows of bytes / elapsed_s / 1e9, the sums for CPUs 0-63 and CPUs 64-119, thread counts, the drop of asmread against oldread inside the same process and round, n, min, median, max, the range comparisons of Q2, the load at each launch from launches.txt, and the record rows of read_nop96, read_nop256, read_1pl.` },
  { key: 'partC', prompt: `Check every number and statement of FACTS.md and facts.json that concerns PART C (w120-T72C1..4): totals per interval, sums per mesh, the grouping by the kernel that ran directly before (rule V2 in S/baselines-and-rules.txt: read after oldread, read after asmread, asmread after read, asmread first in the process, asmread after oldread), the drop of read against oldread inside the same process and round, and every baseline or reference number that FACTS.md cites for part C (for example the "other binary" references R/B7-*, R/C3-*, R/B5-*; if FACTS.md cites them, recompute them). Use your OWN parser on the RAW csv files (do not use stat_bwx.py, an.py or the author's scripts). Check that no 8000 MT/s value of asmread is shown as a value of the kernel read.` },
  { key: 'state', prompt: `Check the RUN RECORD of FACTS.md (section 1) and every statement about machine state, times, load, integrity and procedure against the raw records: R/go-T72-20261117T221209Z.log, R/go2-T72-20261117T222335Z.log, probe.txt of the k120 folders, env.txt, launches.txt and stderr.txt of the w120-T72* folders, the csv header lines, the "P" rows and the flags column of the "T" rows, R/dimm7200-20261117/try6.txt and boots.txt, the scripts go.sh, ra.sh, go2.sh, rx.sh. Recompute every count, every time, every gap in seconds and every load value yourself. Check the sha256 statements. Check that the statement "12 modules at 7200 MT/s" is tied to its proof and that its limit is stated (speed proven through the boot id only; kernel log not read). Check the decisions list (section 2) against the scripts and logs: is each decision described as it was really carried out?` },
  { key: 'rules', prompt: `Check the VERDICTS and the LOGIC of FACTS.md (sections 0, 3, 4, 6) against the binding rules in S/baselines-and-rules.txt, rule by rule (V4 baseline list: is every valid baseline shown as its own row, is any non-baseline folder used as a baseline; V1: wording of Q2, n stated as intervals / processes / sessions / boots, no percent change of the new read kernel given as an effect of the memory speed; V2: grouping of part C; V3: part A per process for the load-only kernels, no statement from write and copy rows; F1, F2). Then sweep every sentence for the kinds of claim defect listed in /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/review-loop-claim-defect-classes.md (for example: a range assigned to runs it does not belong to; an observed rate written as a limit; a universal statement not covered by the files; an estimate not labelled "est."; a hypothesis written as a fact; a sample written as "all"; a missing direct answer to Q1 or Q2). Check also that the Short version follows from the tables, and that the same-boot evidence (F72d12 at 20:02 UTC, control I at 22:27 and 22:32 UTC, part L after part A) is used correctly for Q2. You may recompute numbers where a verdict depends on them.` },
]

function verifyPrompt(l, round) {
  return `${CTX}
YOUR TASK (independent check, round ${round}, angle "${l.key}"). The facts sheet S/FACTS.md and S/facts.json were written by another agent from the raw files. Do not trust them. ${l.prompt}
Report a defect for: a number that differs from your recomputation by more than the printed precision; a number in FACTS.md that differs from facts.json; a claim without a tie to a named file; a claim that the data do not support; a rule that is not followed; something the task of the sheet requires and that is missing in your area. Quote the exact text. Give the correct value with the file and row that prove it. Do not report matters of taste. If you find no defect, return an empty list. State how many numbers you checked and what you confirmed. Do not edit FACTS.md or facts.json. Keep any script you write in your own scratch area, not in S.`
}

const history = []
let q1 = author.q1_verdict, q2 = author.q2_verdict
for (let round = 1; round <= 3; round++) {
  phase('Verify')
  const res = (await parallel(LENSES.map(l => () =>
    agent(verifyPrompt(l, round), { label: `verify:${l.key}:r${round}`, phase: 'Verify', schema: DEFECTS })
      .then(r => r ? { lens: l.key, ...r } : null)
  ))).filter(Boolean)
  const defects = res.flatMap(r => r.defects.map(d => ({ ...d, id: `${r.lens}-r${round}-${d.id}`, lens: r.lens })))
  history.push({ round, checked: res.map(r => ({ lens: r.lens, numbers_checked: r.numbers_checked, defects: r.defects.length })), defects })
  log(`round ${round}: ${defects.length} defects from ${res.length} checkers`)
  if (defects.length === 0) break
  if (round === 3) { log('round 3 still has defects: they are returned unresolved'); break }
  phase('Fix')
  const fix = await agent(`${CTX}
YOUR TASK: correct the facts sheet. S/FACTS.md and S/facts.json were built by scripts kept in S (see section 7 of FACTS.md). Independent checkers reported the defects below. For each defect: check it yourself against the raw files. If it is real, correct the generating script and regenerate (preferred), or correct the text, so that FACTS.md and facts.json agree with the raw files and with the binding rules in S/baselines-and-rules.txt. If it is not real, leave the sheet and say why. Add no new claim that a defect did not ask for; a sentence added in a correction is a new claim and must have its own tie to a file. After all corrections re-read the Short version and the verdicts of Q1 and Q2 and make them agree with the corrected tables. Return one entry per defect id, and the final Q1 and Q2 verdict texts.
DEFECTS: ${JSON.stringify(defects)}`, { label: `fix:r${round}`, phase: 'Fix', schema: FIXED })
  if (fix) { history[history.length - 1].fix = fix.handled; q1 = fix.q1_verdict; q2 = fix.q2_verdict }
}
return { author, q1, q2, history }
