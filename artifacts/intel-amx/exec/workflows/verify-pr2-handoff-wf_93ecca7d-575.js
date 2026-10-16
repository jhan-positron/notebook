export const meta = {
  name: 'verify-pr2-handoff',
  description: 'Six independent checkers verify PR2-handoff.md against the repo, scripts and rules; each finding is then adversarially re-checked',
  phases: [
    { title: 'Check', detail: 'six lenses over the handoff' },
    { title: 'Refute', detail: 'one skeptic per must-fix or should-fix finding' },
  ],
}

const HANDOFF = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR2-handoff.md'
const FOLDER = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424'
const REPO = '/home/jhan/workspace/tron'
const EXEC = '/home/jhan/workspace/intel-AMX/exec'

const COMMON = `
You are checking a handoff document that another agent will execute to create PR-2 of a four-PR stack. The document: ${HANDOFF}. Read it fully first.
Ground rules: you check, you do not edit the handoff or any repo file. Read-only git commands in ${REPO} are allowed (git show, git diff, git log, git cat-file, git worktree list). You may create ONE scratch git worktree under /home/jhan/workspace/ai-runs/ (detached, name it verify-<lens>-<something>) if you need to test-apply a patch; remove it with 'git -C ${REPO} worktree remove --force <path>' before you finish, and never run 'git worktree prune'. Do not build tron. Do not push, commit, tag or change branches. On delphi-3bda only read-only ssh commands (ls, cat, git rev-parse, stat) are allowed; do not launch anything there. Do not create files at the top level of ~/workspace.
Report every claim in the document that is wrong, imprecise or unverifiable within your lens, with the exact evidence (file:line, command output). Severity: must-fix = the executor would do the wrong thing or a stated fact is false; should-fix = misleading or missing detail that costs time; nit = wording. Quote the handoff phrase you refer to. Propose the corrected text. If a claim is correct, do not list it, but keep a count of claims checked. Be concrete: a finding without a command output or a file:line that proves it is not a finding.
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
          location: { type: 'string', description: 'section and step of the handoff, plus the quoted phrase' },
          claim: { type: 'string', description: 'what the handoff says' },
          evidence: { type: 'string', description: 'command output or file:line that shows the problem' },
          fix: { type: 'string', description: 'the corrected text or instruction' },
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
    refuted: { type: 'boolean', description: 'true when the finding is wrong or not worth a change' },
    reason: { type: 'string' },
    corrected_fix: { type: 'string', description: 'the fix as it should be applied, if the finding stands (may refine the original fix)' },
  },
  required: ['refuted', 'reason'],
}

const LENSES = [
  {
    key: 'git-facts',
    prompt: `${COMMON}
Lens: git facts. Verify every commit id, branch name, file list, line number and quoted code/comment text in the handoff against the repository ${REPO}. In particular:
- The state table of section 0 and section 2 (82d05e94be, 72308ec90c, a711aeee83, c3334a079f, the six topical commits 06c9f48b8c..dc859f0cdc, the four review-fix commits dbe32b8af4 07f072bdf1 7633d56c8f 82d05e94be, 4d3a042225 and its parent 76a0160b72, 0a5334ccb6, origin/main 8ea71e472c and the claim that none of main's commits since 72308ec90c touches a PR-2 file).
- Step 1.2: re-do the probe: create a detached scratch worktree at 82d05e94be, run 'git apply --3way ${FOLDER}/handoff-material/ref/PR2-diff-76a0..4d3a.patch', and confirm the exact outcome the handoff states (which files clean, which conflict, the exact conflict block text, rerere messages). Then confirm step 1.3's three 'git diff --cached 4d3a042225 -- ...' expectations exactly (empty for the six files; only the listed residuals in kv_cache.hpp, tensor/k_vnni.hpp, t_llama_unit.cpp). Reset and remove the scratch worktree afterwards (git reset --hard, then worktree remove --force).
- Step 2: every 'old text' must occur exactly once in the tree after the apply, and every 'new text' must equal the wording of 0a5334ccb6 (or of 76a0160b72 / 4d3a042225 where 0a5334ccb6 carries PR-4 text). Compare against 'git show c3334a079f'. Also verify the claim that the patch restores the other items (consumer items 2 and 3, the Why paragraph, page::k_packed comment, the 'two layout-specific score kernels' sentences, the dispatch-test header and predicate, the gate, the README sentence) by grepping the applied tree.
- Step 2's grep list and section 5.2: run the greps on the applied+edited tree (make the five edits in your scratch worktree, do not commit) and report any count that differs from the handoff's expectation. Also run the 'present' greps.
- Section 3's size estimate '+286/-73': compute 'git diff --numstat jhan-vnnik-1-layout' in the scratch worktree after the edits and report the real numbers.
- The claim in step 4.4 that the restored diagram line is 78 columns.
- The claim that h/tron/kernels/k_vnni.hpp is not in the patch, and that the review-fix hunks are at tensor/k_vnni.hpp 283-330 and t_llama_unit.cpp 2725-2890.
- The claim that /var/tmp/jhan/tron-pr1 is at 82d05e94be with gen/runtron.pr1 and tron-main1010 at 72308ec90c (ssh delphi-3bda, read-only).`,
  },
  {
    key: 'machine-scripts',
    prompt: `${COMMON}
Lens: the delphi-3bda chain and the scripts. Verify every script name, variable, argument and behaviour the handoff attributes to the scripts under ${EXEC}: pr1-20261010/chain2.sh, chain3.sh, launch3.sh, wait-chain3.sh, build-branch.sh, fill-body.py; i4525-20260922/build2.sh and host-suite.sh; sync4424-20261002/smoke.sh and campaign.sh (the arm names base/head/new and their *off and *2 variants, RT_BASE/RT_HEAD/RT_NEW, ARM_ENV_<arm>, MUST_MATCH, SMOKE_ARMS, ARMS, WEDPERF_PAIRS, CELLS_ALL, DEADLINE_HHMM, NAME, the summary.md the campaign writes); q4b-fpga-20260921/dut.sh (serving-down / serving-up); bill-share.sh (take / release); lib-guard.sh (the functions ci_lease_busy, campaign_guard_acquire, ci_took_dut, rinzler_takeover_if_idle, rinzler_active, other_user_active: do they exist with those names?). Verify the configure lines CONF_VNNI / CONF_A3 / CONF_RM / CONF_BASE and the test lists. Verify the handoff's statements about the PR-1 chain's timings (597/284/292 s, 826 s first build, 59 min whole-machine, 14 min builds) against ${EXEC}/results/pr1b-20261010/steps.txt, ${EXEC}/results/pr1-20261010/steps.txt and the logs under ${EXEC}/logs/. Verify the step 6 table is executable as written: in particular that smoke.sh accepts the arm 'head' with RT_HEAD and 'new2'/'newoff' with RT_NEW, that campaign.sh accepts ARMS='base new newoff head' and the four WEDPERF_PAIRS, that build2.sh takes SUFFIX/CONFIGURE_ARGS/TARGETS/TESTS/TEST_ARGS/JOBS and copies gen/runtron to gen/runtron.SUFFIX, and that host-suite.sh takes RES/WT/SUFFIX. Verify the lease-schedule claims (03:30 UTC cron, 13:30 UTC, 02:30 UTC, 50400 s) against ~/workspace/notebook/handoffs/check-CI.md lines 258-270 and the memory file /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/3bda-shared-with-bill.md. Verify the mutation command of step M is a text that occurs exactly once in src/tron/kernels/amx_attn.cpp at 4d3a042225 and that the test-case name string is the exact TEST_CASE name. Verify that the matrix scripts' usage lines in step 4 are right (matrix.sh label argument, run.sh with O=).`,
  },
  {
    key: 'policy-consistency',
    prompt: `${COMMON}
Lens: consistency with the governing documents. Compare the handoff against ${FOLDER}/split-handoff.md (sections 0, 3, 4 step 2, 5, 6, 8, 9), ${FOLDER}/split-status.md (especially the section 'PR-1-only text that PR-2 reverts', eight numbered items: does the handoff's step 2 plus the patch cover every one of the eight, and does it wrongly list any as handled by the patch?), ${FOLDER}/create-PR1-handoff.md (the structure and rules the PR-2 file mirrors), ${REPO}/AGENTS.md (the PR CI policy lines about stacks, drafts, 'Skip benchmarks', 'Run CI', the test policy, bin/slice route), ${EXEC}/pr1-20261010/pr-body.md (the PR-1 body: the stack table row for PR-2, the measurements the handoff quotes: -6.4 %, -11.6 %, +26 %, +120 %, token 83, 93/1/1, 597/284/292 s, 4109/4, 2060/4, 1612/1), and ${FOLDER}/split-plan.md sections 3.1, 3.2, 6, U1A.3, U1A.4 (the expected numbers the handoff quotes: +5.3/+7.1/+10.1 %, TTFT -56 ms / -1.37 s, +2.2 %, the 2026-10-09 token-identity record). Every decision D1..D11 must be stated as split-handoff.md section 0 resolved it. Every deviation the handoff makes from split-handoff.md (it claims three: the dispatch fakes moved to the kernel commit, the A3 build, the mutation check) must be flagged as such in the handoff; find any deviation it does not flag. Check the handoff's claim about gcp-nix.yml draft filtering (which jobs run on a draft without 'Run CI') against ${REPO}/.github/workflows/gcp-nix.yml. Check the claim that the required CI runners carry labels fpga, test, avx512 and none for AMX. Check that the handoff does not ask the executor to do anything the 'Do not' lists of split-handoff.md forbid.`,
  },
  {
    key: 'code-reasoning',
    prompt: `${COMMON}
Lens: the code and test claims. Using 'git show 4d3a042225:<file>' and 'git show 82d05e94be:<file>' in ${REPO} (and the reference worktree /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K read-only), verify:
- The expected t_amx_numerics count '4621 / 5' (PR-1 measured 4109 assertions in 4 cases): count the REQUIRE/CHECK assertions the new identity case executes (seeds x heads x tokens; do CAPTURE or STATIC_REQUIRE count?), and whether other cases change. Also the kill-switch expectation (which cases print 'AMX unavailable' under TRON_AMX_DISABLE=1: does available() return false under the kill switch? find the implementation) and the expected kill-switch count.
- The claim that the identity case compiles and runs in the option-off (TRON_K_VNNI off) build: are tensor/k_vnni.hpp, k_vnni_tensor, store_row and qk_vnni_128x4 available without TRON_K_VNNI? Look for #ifdef TRON_K_VNNI guards in t/t_amx_numerics.cpp, h/tron/tensor/k_vnni.hpp, src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp at 4d3a042225.
- The A3 claim: with TRON_AMX_DISPATCH off and TRON_K_VNNI on, does the tree compile? Are qk_vnni_128x4's declaration, definition and all call sites (self_attention.hpp two sites, t_llama_unit.cpp probe, t_amx_dispatch_dtype.cpp fakes, t_amx_numerics.cpp) inside TRON_AMX_DISPATCH guards? The probe matrix handoff-material/probe-pr2/out/pr2-r1/summary.txt has gen-amxoff cells: confirm what they prove.
- The mutation of step M: changing the second panel load from '+ 1' to '+ 2' makes token block 1 read block 2's panel; confirm the exact text occurs once, that the first failing comparison would be at token t = 16 of head qi = 0 for seed 21 (reason about the loop order of the test), and that nothing else (for example a static_assert) would stop the build.
- The padding claim of step 5.2: amx_qpack slots zero-filled by resize(), pack_q_rows_128x4 writes rows 0..3 only (memcpy of 4 x 128 bf16), and no path writes rows 4..15; is the claim 'across calls and slot reuse' right (what happens when amx_qpack shrinks then grows; is a slot ever reused for a row-major geometry in the same build)?
- The claim that in the option-on build every eligible slot is a VNNI slot (so only pack_q_rows_128x4 runs): check eligible<>() and layout_on<> definitions.
- The 'A operand / B operand' and 'panel = 16 pair rows x 16 tokens = 1 KiB, 16 panels per plane' definitions against h/tron/tensor/k_vnni.hpp.
- The claim 'the restored diagram line is the line of 0a5334ccb6'.
- Step 3's reason for putting t_amx_dispatch_dtype.cpp in commit (a): does the fake translation unit define every amx_attn_h128g4 entry point, so that a commit adding pack_q_rows_128x4 and qk_vnni_128x4 to the interface and to the dispatch without the fakes fails to link t_amx_dispatch_dtype (or pulls the real object)? Check how t_amx_dispatch_dtype is linked in t/CMakeLists.txt.
- Section 5.4's expectation that newoff equals new: find any statement in the reference tree about the reader's add order versus the AMX kernel's (Note [AMX attention dispatch], kernels/k_vnni.hpp) and say whether the handoff words the expectation and its basis correctly.`,
  },
  {
    key: 'plain-english',
    prompt: `${COMMON}
Lens: the plain-english skill in Check mode, applied to ${HANDOFF}. The eight rules: 1 define every term at first use (code names, acronyms, metrics; a 'Words used here' list counts); 2 one claim per sentence; 3 numbers carry units and a plain meaning, estimates marked est.; 4 citations follow a sentence; 5 a Short version at the top (at most three sentences); 6 no idioms, metaphors, uncommon words; 7 bullets or blank lines separate points; 8 short sentences, no semicolons joining clauses. Imperative instructions are allowed to be terse. Report the violations that matter for a first-time reader (an engineer who has never seen this project): undefined terms that the Words list does not cover, sentences that carry several claims and would be misread, numbers without units, idioms. Group near-duplicates. Do not list every semicolon in a code-like list of files; do list semicolons that join two claims in prose. For each: the rule number, the exact phrase, the fix. Severity: should-fix for undefined terms and multi-claim sentences that could be misread, nit for the rest. Count the sentences you checked.`,
  },
  {
    key: 'completeness',
    prompt: `${COMMON}
Lens: completeness. Pretend you are the executor and walk the steps in order, from step 0 to step 8, asking at each step 'what would I need that this file does not give me, or where would I have to guess?'. Sources: ${FOLDER}/create-PR1-handoff.md and ${FOLDER}/split-status.md (what the PR-1 executor actually needed and recorded, including the traps it hit and the review items it got), ${FOLDER}/split-handoff.md, the scripts under ${EXEC}/pr1-20261010/. Look for: missing inputs (paths, variable values, expected outputs), unspecified choices (which commit id goes where, which base for which comparison, who writes what into split-status.md), ordering problems (a step that needs a result of a later step), unreachable instructions (a command that cannot run on claude-box or on delphi-3bda as written), contradictions inside the file (for example between the step 6 table and section 5.4 or 5.5, between section 3's invariants and step 2, between the 'Do not' list and a step), and claims the executor is told to make in the body that no step measures. Also check that every expectation the body must state has a provenance the executor can cite. Report each gap with the step, what is missing, and the text that would close it.`,
  },
]

phase('Check')
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (r, l) => {
    if (!r) return null
    const serious = r.findings.filter(f => f.severity !== 'nit')
    log(`${l.key}: ${r.claims_checked} claims checked, ${r.findings.length} findings (${serious.length} serious)`)
    return parallel(r.findings.map((f, i) => () =>
      (f.severity === 'nit'
        ? Promise.resolve({ refuted: false, reason: 'nit, not refuted' })
        : agent(`${COMMON}
Lens: refutation. A checker reported this finding about the handoff. Try to REFUTE it with evidence from the same sources (the repo ${REPO}, the folder ${FOLDER}, the scripts under ${EXEC}, delphi-3bda read-only). Default to refuted=true when the finding's evidence does not hold up or the proposed fix would make the handoff wrong. If the finding stands, say so and give the fix in its final form (you may sharpen it).
Finding (${f.severity}) at ${f.location}
Claim in the handoff: ${f.claim}
Evidence given: ${f.evidence}
Proposed fix: ${f.fix}`, { label: `refute:${l.key}:${i}`, phase: 'Refute', schema: VERDICT })
      ).then(v => ({ lens: l.key, finding: f, verdict: v }))
    ))
  },
)

const all = results.filter(Boolean).flat().filter(Boolean)
const kept = all.filter(x => x.verdict && !x.verdict.refuted)
const refuted = all.filter(x => x.verdict && x.verdict.refuted)
log(`${all.length} findings, ${kept.length} kept, ${refuted.length} refuted`)
return { kept, refuted }
