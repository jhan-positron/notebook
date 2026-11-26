export const meta = {
  name: 'w120-7200-final-check',
  description: 'Independent check of the final state of the 7200 MT/s rerun report and of the last facts-sheet corrections, then fix confirmed defects',
  phases: [
    { title: 'Final review', detail: 'four reviewers: numbers of the whole page, changed claims, first screen as a newcomer, last facts-sheet corrections' },
    { title: 'Final fix', detail: 'verify and fix confirmed defects of substance' },
  ],
}

const S = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
const R = '/home/jhan/workspace/titan/cache-perf/crb/results'
const OUT = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
const GEN = S + '/make_report.py'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const COMMON = `
Context.
- Machine under test: CRB, a 128-CPU Arm reference server. Tests use 120 threads (CPUs 0-119), 256 MiB per thread.
- User request of 2026-11-17: "Given that the DIMM issue is resolved at 7200 MT/s, let's rerun the whole chip test. Please run old kernel which used portable C code and had read and add, and run new kernel which performed worse than old kernel. Compare the results".
- The rerun is done. Raw result folders: R = ${R}. Scratch folder with scripts, the facts sheet (FACTS.md, facts.json, built by build_facts.py) and the binding comparison rules written before the run (baselines-and-rules.txt): S = ${S}.
- The report page ${OUT} is written by the generator ${GEN} (never edit the HTML by hand). It went through three review rounds. The fixes of the third round and a later rewrite of the "Short version" (3 sentences and the first detail bullet under them) were NOT reviewed yet. State before the third-round fixes: ${S}/bak-before-r3fix/ (make_report.py and the HTML).
- Decisions of the orchestrator that are NOT defects: (1) sentence 1 of the Short version gives one range over the 8 pairs of part C (both kernel orders), and the first detail bullet gives the two orders apart; (2) sentence 2 says "no difference ... was seen" as the plain form of the fixed wording "no difference seen", with the sizes that the tests cannot exclude in a detail bullet; (3) the page length and the notes under Table 2 stay as they are; (4) one light theme only.
- HARD LIMITS: no ssh, no benchmark, no change under R, no file outside S (scratch scripts go under ${S}/final-check/<your lens>/), no network, no project detail to any outside service. A shell "cd" prints a directory listing here; use absolute paths.
- Report only defects of SUBSTANCE: a wrong number, a claim that the data or the rules do not support, a missing label that the rules require (control I "added after the first numbers were seen"; F72d12 "not part of the rerun"; asmread "in place of the new read kernel"), a percent change of a load-only kernel across memory speeds, a change presented as an effect of the memory speed, a broken reference, a sentence that a newcomer cannot follow, a rendering fault. Do not report style preferences. An empty list is a valid and welcome result.
`

const DEFECT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    checked: { type: 'string' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['wrong-number', 'unsupported-claim', 'rule-violation', 'missing', 'wording', 'visual'] },
          where: { type: 'string' }, quote: { type: 'string' }, problem: { type: 'string' }, correct: { type: 'string' }, evidence: { type: 'string' },
        },
        required: ['id', 'severity', 'where', 'problem', 'correct'],
      },
    },
  },
  required: ['lens', 'checked', 'defects'],
}

const LENSES = [
  { key: 'numbers', target: 'report', prompt: `Lens NUMBERS, whole page. Recompute every measured number of the page from the RAW csv files under R with your own parser (not facts.json, not build_facts.py, not make_report.py): body text, Short version and its detail bullets, all tables including the folded table views, chart labels and <title> tooltips, n counts, percent values, ranges, medians, distances, load values, launch times. Raw formats: part A files threads120.csv / A1.csv / A3.csv hold "-- binary ... kernel ... round ... load ..." header lines followed by csv rows per interval (column aggregate_GBps); bwx12 / bwx csv files hold rows of kind I, T, P, C, and the rate of an interval is the sum over its 120 T rows of bytes / elapsed_s / 1e9 (${S}/stat_bwx.py and ${S}/stat_k120.py show the formats; write your own code). Check that the dot positions in the two SVG figures match their values (axis scale from the tick labels). Report each mismatch above 0.01 GB/s or 0.1 % with both values, the raw file and the line.` },
  { key: 'claims', target: 'report', prompt: `Lens CHANGED CLAIMS. Extract the visible text of ${S}/bak-before-r3fix/whole-chip-rerun-7200.html and of the current page, and diff them sentence by sentence (own script). Every added or changed sentence, table cell, caption, note, tooltip wording and reference entry is a NEW CLAIM: check each against the raw files under R, against the binding rules in ${S}/baselines-and-rules.txt and against ${S}/FACTS.md. Check the three Short version sentences and the detail bullets under them with special care: each number, each "all N comparisons", "two of the three tests", the two percent values of part L (nearest ends against the lower end of the 8000 MT/s range; medians against the 8000 MT/s median), and whether a reader could take a sentence as a statement about the effect of the memory speed. Then sweep the changed text with the claim defect classes in ${MEM}/review-loop-claim-defect-classes.md. Also check that every [RefN] cited in a changed sentence exists in the list, that its path exists, and that the cited file holds what the sentence says.` },
  { key: 'reader', target: 'report', prompt: `Lens FIRST SCREEN AS A NEWCOMER. Read ONLY the HTML page first (render it with the headless Chrome described in ${MEM}/headless-chrome-offline-render.md at window widths 1280 and 420, own --user-data-dir under ${S}/final-check/reader/, and LOOK at the screenshots of the top of the page down to the end of Table 1 with the Read tool). As an engineer who has never seen the project: do the three Short version sentences and Figure 1 answer "is the new read kernel still worse than the old one at 7200 MT/s, by how much, and did anything change against 8000 MT/s"? List every term in the Short version, its detail bullets, the Figure 1 labels, legend and caption that is used before it is defined on the page (the folded word list counts as a definition only for terms that the first screen cannot reasonably define inline). Check the first screen for rendering faults: overlap, clipped text, a label on the wrong row, unreadable marks, sideways scroll of the page at 420. Then check the whole page once at 1280 for rendering faults in the tables and in Figure 2.` },
  { key: 'facts', target: 'facts', prompt: `Lens LAST FACTS-SHEET CORRECTIONS. Diff ${S}/bak-before-vfix-r3/FACTS.md against the current ${S}/FACTS.md (own script). Every added or changed sentence or table cell is a NEW CLAIM that no reviewer has checked: recompute each number in it from the raw file it cites with your own parser (not build_facts.py), check that each cited [RefN] exists in section 7 and that the file exists and holds what is said, check labels (control I, F72d12), dates on times of other days, units, and the binding rules in ${S}/baselines-and-rules.txt. One correction was made by hand in the generator after that diff base: the count of firmware settings with a readable value (604 readable, 883 "ValueUnavailable", 3 "VStoreError" of 1490 entries in ${R}/uefisettings-20261117/questions.json and ${R}/fwtest-20261117/revert/questions.json): verify it from the two raw files and check that no place of FACTS.md or facts.json still says 607. Also run "python3 ${S}/build_facts.py" twice and confirm that all integrity checks pass and that both builds give identical FACTS.md and facts.json, and compare the "intervals" list of ${S}/bak-before-vfix-r3/facts.json with the current one: no value may differ.` },
]

phase('Final review')
const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${COMMON}
You are an independent reviewer. You did not write the page or the facts sheet. Try to find real defects of substance; do not approve by default, and do not invent defects.
${l.prompt}
Do not edit the report, the generators or the facts sheet. Give ids of the form final-${l.key}-N, each with where, the exact quote, the problem, the correct text or value, and the evidence (file and line, or screenshot path).`,
    { label: `final-${l.key}`, phase: 'Final review', schema: DEFECT_SCHEMA })
))).filter(Boolean)

const defects = reviews.flatMap(r => r.defects || [])
log(`final review: ${defects.length} findings from ${reviews.length} reviewers`)
let fix = null
if (defects.length) {
  phase('Final fix')
  fix = await agent(`${COMMON}
You are the maintainer of the report generator ${GEN} and of the facts-sheet generator (${S}/build_facts.py, facts_data.py, facts_text.py, facts_text4.py). Four reviewers returned the findings below on the final state.
For EACH finding: verify it yourself first against the raw files, the rules file or a render. If it is right and of substance, fix it in the generator with the smallest change that corrects it. If it is wrong, or it contradicts one of the orchestrator decisions listed above, reject it with the evidence. Do not add new claims while fixing: where a sentence cannot be made right in a few words, remove the wrong part. Do not lengthen the Short version; it stays at 3 sentences that a newcomer can follow.
Contract for the facts sheet: do not rename or remove fields of "intervals" or meta.launches in facts.json and do not change any rate, n or line number there.
After the fixes: "python3 ${S}/build_facts.py" (all integrity checks pass, two builds identical) if you touched the facts generator; "python3 ${GEN}" (all self-checks pass, exit status 0); "python3 ${S}/test_make_report.py" (exit status 0); render with "bash ${S}/render/render_r3.sh" and LOOK at the tiles of every region you changed; write the sha256 of the page, both generators, FACTS.md and facts.json to ${S}/render/sha256-final.txt.
Findings:
${JSON.stringify(defects, null, 1)}
Return one action per finding id (fixed / rejected / partly, with a note that names the evidence), whether all builds and tests are ok, the Short version as built, and open points.`,
    { label: 'final-fix', phase: 'Final fix', schema: {
      type: 'object',
      properties: {
        summary: { type: 'string' },
        actions: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, action: { type: 'string', enum: ['fixed', 'rejected', 'partly'] }, note: { type: 'string' } }, required: ['id', 'action', 'note'] } },
        build_ok: { type: 'boolean' },
        short_version: { type: 'string' },
        open_points: { type: 'array', items: { type: 'string' } },
      },
      required: ['summary', 'actions', 'build_ok'],
    } })
}
return { reviews: reviews.map(r => ({ lens: r.lens, checked: r.checked, n: (r.defects || []).length })), defects, fix }
