export const meta = {
  name: 'verify-pr2-handoff-v2',
  description: 'Three checkers re-verify the rewritten PR2-handoff.md (Update 1) for regressions and new false statements; serious findings are refuted adversarially',
  phases: [
    { title: 'Check', detail: 'three lenses over the rewritten handoff' },
    { title: 'Refute', detail: 'one skeptic per must-fix or should-fix finding' },
  ],
}

const HANDOFF = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR2-handoff.md'
const UPDATE = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR2-handoff-update1.md'
const FOLDER = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424'
const REPO = '/home/jhan/workspace/tron'
const EXEC = '/home/jhan/workspace/intel-AMX/exec'

const COMMON = `
You are checking the second version (Update 1) of a handoff document that another agent will execute to create PR-2 of a four-PR stack: ${HANDOFF}. Read it fully first. ${UPDATE} records what the first review round changed and why; read its sections 1 to 3 so that you do not re-raise what was settled, unless the settlement itself is wrong.
Ground rules: you check, you do not edit any file. Read-only git commands in ${REPO} are allowed. You may create ONE scratch git worktree under /home/jhan/workspace/ai-runs/ (detached, name it verify2-<lens>-<something>) if you need to test-apply the patch; remove it with 'git -C ${REPO} worktree remove --force <path>' before you finish, never 'git worktree prune'. Do not build tron. Do not push, commit, tag or change branches. On delphi-3bda only read-only ssh commands (ls, cat, git rev-parse, stat). Do not create files at the top level of ~/workspace.
Report every statement that is false, contradicted elsewhere in the document, or would make the executor do the wrong thing, with the exact evidence (file:line or command output). Severity: must-fix = a false fact or a wrong instruction; should-fix = misleading or missing detail that costs time; nit = wording. Quote the handoff phrase. Propose the corrected text. A finding without proof is not a finding. Count the statements you checked.
`

const FINDINGS = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    claims_checked: { type: 'integer' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
          location: { type: 'string' },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['severity', 'location', 'claim', 'evidence', 'fix'],
      },
    },
  },
  required: ['lens', 'claims_checked', 'findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    corrected_fix: { type: 'string' },
  },
  required: ['refuted', 'reason'],
}

const LENSES = [
  {
    key: 'repo-facts',
    prompt: `${COMMON}
Lens: repository and code facts, with emphasis on statements that are NEW in this version. Verify against ${REPO} (git show at 82d05e94be, 4d3a042225, 76a0160b72, 0a5334ccb6, 28064e6f84, c3334a079f) and the reference worktree /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K (read-only):
- Words: the definitions of slot / VNNI slot / query-pack slot (amx_qpack_slot, attn_accum::amx_qpack, resize), the per-row scatter store (4 scatters of 16 dwords, 64 lines vs 4 lines), panel/token block/dimension step, amx_attn_h128g4, PR 3879 (branch jhan-amx-p0, merged 2026-09-15, what it added), the three tests (the identity case's name string, 2 seeds, 4 x 64, the WARN; the fakes include available(); six STATIC_REQUIRE lines in the named t_llama_unit case), Catch2 facts (STATIC_REQUIRE counts as one assertion; the summary line forms), the kill switch definition (available() false, no pack).
- Section 1: the CI-gap bullet (nix/cmake-tron-test-build.nix passes neither switch; the runner labels at gcp-nix.yml 464/555/622 and cmake-single-platform.yml 151/382/511; README.ci.md's FPGA runner group with delphi-17cf-0, delphi-3bd6-0, delphi-3bda-0 and three AMD Genoa hosts; no label routes to AMX).
- Step 1.2: the conflict block text, 84 columns, line 61 in 0a5334ccb6 and 4d3a042225, the 100-column pre-image in 76a0160b72, commit 28064e6f84 as the rewrap, 85 and 88 columns. Step 1.3's four expectations (re-do the test apply in a scratch worktree). Step 2: the five old texts occur once at 82d05e94be; the new texts equal 4d3a042225; the line numbers 3-5 and 45-47; the claim that the patch restores the listed first-group rewordings; the claim that c3334a079f made six comment edits (count them). The grep list expectations after the edits (run them). Section 3's +285/-72 over 10 files.
- Step 3 (a): the link argument (fakes define every entry point; t_amx_dispatch_dtype links tron static; amx_attn.cpp in libtron only under TRON_AMX_DISPATCH; the call sites are if-constexpr branches in the option-off build).
- Step 6 A and M: 4621/5 and 2060/5 expectations; the three cases that WARN under the kill switch; the mutation text occurs once; first failure seed 21 / qi 0 / t 16; "1 failed assertion of 17".
- Section 5.2: the 12 hits of '!k_vnni::layout_on' in kv_cache.hpp at 4d3a042225 are requires-constraints, not the gate.
- Section 5.4: Note [AMX attention dispatch] names the PV rounding (AVX truncates, AMX rounds to nearest even) and the fp32 add order as differences; the 2026-10-09 record facts (which cells had a newoff arm: exec/results/merge4737-precheck/smoke/*/smoke.txt); PR-1's token-83 result (exec/results/pr1b-20261010/smoke/*/smoke.txt).`,
  },
  {
    key: 'machine-scripts',
    prompt: `${COMMON}
Lens: delphi-3bda, the scripts and the schedule, with emphasis on statements that are NEW in this version. Verify against the scripts under ${EXEC} (pr1-20261010/chain2.sh, chain3.sh, launch3.sh, wait-chain3.sh, build-branch.sh, fill-body.py, control-a.log, control-b.log; i4525-20260922/build2.sh, host-suite.sh; sync4424-20261002/smoke.sh, campaign.sh, summarize.py; q4b-fpga-20260921/dut.sh; bill-share.sh; bill-watch.sh; lib-guard.sh), the logs under ${EXEC}/logs/ and results under ${EXEC}/results/ (pr1-20261010, pr1b-20261010, pr1b-E-cpu, merge4737-precheck, vnnik-20260914, vnnik2-20260915), ~/workspace/notebook/handoffs/check-CI.md (lines 53, 61, 170, 258-270) and /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/3bda-shared-with-bill.md, and tron's doc/dice.md and AGENTS.md:
- Step 6 intro: the STEP line format and every marker name and producer; "M and F have no marker".
- Step 6 table D: the smoke.sh verdict facts and the "smoke token rows" / "smoke <arm> rc=" line formats; table E: WEDPERF_ARMS default, EARLY-STOP; the head row: the reuse condition.
- The deadlines bullet: chain2/chain3 END_BY defaults, DEADLINE_HHMM at chain2.sh 163 and 174, campaign.sh's "today or tomorrow" deadline logic and the 01:40-03:45 UTC pre-CI hold, smoke.sh sharing that code, check-CI.md's 02:30 UTC rule. The budget bullet: 826+314+309 s, 597+284+292 s, D 9 min, E 41 min, C 5 min, marker 16:54:15 to 17:51:10 UTC, lease freed 13:19 UTC (find each in the logs/results).
- Section 5.3: the build2.sh description (nice, taskset, nix develop --command, cmake then cmake --build, runtron copy, the files it writes), CONF_* lines, the marker paragraph (bill-share.sh:12 text; the memory file's text; PR-1's take/release times in exec/logs/bill-share.log or the chain logs; take exits 2 while Bill is active; chain.done=stopped-marker), the lease schedule sentences, the tests paragraph ("build rc=0 in N s" line in build-<suffix>.log).
- Words: bill-watch.sh's description, Dice and the route verdicts (names and meanings per AGENTS.md and doc/dice.md), the lcheck mirror description (~/workspace/ai-runs/lcheck/mirror and its README), draft filtering job names (gcp-nix.yml), "deb-smoke.yml and slice.yml run on drafts too".
- Step 4.1: the two control commands as written (paths, ERRLIM, the expected rc and error counts from control-a.log / control-b.log; does lcheck-vnni.sh accept 'gen t/probe_bad.cpp <worktree>' in that order?). Step 4.1's 38-cell command with O=.
- Step 7: fill-body.py's scope; "build rc=0 in N s" in build-<suffix>.log. Section 8: the metric sentences (summarize.py's parsed line; smoke.txt's recorded line), rt-results.txt sha256 lines.
- Section 5.5: exec/results/vnnik-20260914 and the numbers +6.1/+7.1/+10.4 %, TTFT +2.2/0.0/-1.8 % tp2 and +7.8 % tp4; tip 5e45ae55ae; the 10fc7c724c / 9928cb2849 rows.`,
  },
  {
    key: 'consistency-english',
    prompt: `${COMMON}
Lens: internal consistency and plain English of the rewritten document, plus consistency with ${FOLDER}/split-handoff.md, ${FOLDER}/split-status.md, ${FOLDER}/create-PR1-handoff.md, ${EXEC}/pr1-20261010/pr-body.md and ${REPO}/AGENTS.md. Check:
- Every cross-reference inside the handoff resolves (a "deviation N" number matches the list in section 3; "section 5.5" pairs match step 6 E's WEDPERF_PAIRS; the arms named in 5.4 match step 6 D's SMOKE_ARMS; section 6 item 5 matches 5.5; the step 8 rules match section 6 rule 2; the Words list covers every term used; no two places give different numbers for the same thing, for example END_BY, the chain budget, the test counts, the line widths, the file counts).
- Every "Do not" of split-handoff.md section 9 that applies to PR-2 is carried; nothing in the steps violates AGENTS.md's PR CI policy or test policy, or the "Do not" list.
- The Short version is at most three sentences and uses no undefined term.
- Plain-English rules on the NEW text of this version (Words entries, section 0's first paragraph, section 1 bullet 3, step 1.2, step 2 intro, step 3 (a), step 4.1, step 6 intro and bullets, section 5.3's marker paragraph, section 5.4's newoff bullet, section 5.5, step 8): undefined terms, sentences carrying two claims that could be misread, numbers without units, idioms. Report only what matters to a first-time reader; group near-duplicates. Do not list semicolons inside enumerations of files or steps.
- Anything the executor would still have to guess (name the step and the missing fact).`,
  },
]

phase('Check')
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `check2:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (r, l) => {
    if (!r) return null
    const serious = r.findings.filter(f => f.severity !== 'nit')
    log(`${l.key}: ${r.claims_checked} statements checked, ${r.findings.length} findings (${serious.length} serious)`)
    return parallel(r.findings.map((f, i) => () =>
      (f.severity === 'nit'
        ? Promise.resolve({ refuted: false, reason: 'nit, not refuted' })
        : agent(`${COMMON}
Lens: refutation. A checker reported this finding about the handoff. Try to REFUTE it with evidence from the same sources (the repo ${REPO}, the folder ${FOLDER}, the scripts and results under ${EXEC}, delphi-3bda read-only). Default to refuted=true when the finding's evidence does not hold up, when the handoff already says what the fix asks for, or when the proposed fix would make the handoff wrong. If the finding stands, say so and give the fix in its final form.
Finding (${f.severity}) at ${f.location}
Claim in the handoff: ${f.claim}
Evidence given: ${f.evidence}
Proposed fix: ${f.fix}`, { label: `refute2:${l.key}:${i}`, phase: 'Refute', schema: VERDICT })
      ).then(v => ({ lens: l.key, finding: f, verdict: v }))
    ))
  },
)

const all = results.filter(Boolean).flat().filter(Boolean)
const kept = all.filter(x => x.verdict && !x.verdict.refuted)
const refuted = all.filter(x => x.verdict && x.verdict.refuted)
log(`${all.length} findings, ${kept.length} kept, ${refuted.length} refuted`)
return { kept, refuted }
