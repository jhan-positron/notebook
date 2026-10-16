export const meta = {
  name: 'verify-pr3-handoff',
  description: 'Seven-lens adversarial verification of PR3-handoff.md with two refuters per must-fix/should-fix finding',
  phases: [
    { title: 'Review', detail: 'seven independent lenses over the handoff' },
    { title: 'Refute', detail: 'two refuters per must-fix or should-fix finding' },
  ],
}

const FILE = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR3-handoff.md'
const COMMON = `
You are verifying a handoff document that an autonomous agent will execute: ${FILE} (about 70 KB). Read it fully first.
Context the document assumes (all on disk; read what your lens needs):
- the folder /home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/: PR2-handoff.md (the previous handoff, the model for this one), PR2-handoff-update1.md, create-PR1-handoff.md, split-handoff.md, split-plan.md (sections 3.1 and U2.1 are about PR-3), split-status.md (the PR-1 and PR-2 execution record), handoff-material/ref/S-diff-4d3a..ba69.patch (the PR-3 patch), handoff-material/probe-pr3/ (the probe of this handoff: conflicts.txt, resolve.py, numstat files, diff-vs-ba69-9files.patch, out-22, out-38, pr3probe-38.log, lcheck-edit/).
- the shared git repository /home/jhan/workspace/tron (branches jhan-vnnik-1-layout 82d05e94be, jhan-vnnik-2-amx 0ee8671d35, jhan-split-probe-pr2 4d3a042225, jhan-amx-vnniK 0a5334ccb6; commits ba69cb513e, 45e6bb266d, 72308ec90c, be0d5565b3). Use "git -C /home/jhan/workspace/tron show <rev>:<path>" and "git diff" to read any revision.
- the scratch worktree /home/jhan/workspace/ai-runs/tron-split-probe-pr3: the PR-2 head 0ee8671d35 with the PR-3 patch applied, the three conflicts resolved and the step-2 edit applied, all STAGED (git diff --cached). READ ONLY: never modify, commit, reset, checkout or clean it; never create or remove git worktrees; never run a build.
- the worktrees /home/jhan/workspace/ai-runs/tron-split-pr2 (PR-2 head) and tron-split-pr1 (PR-1 head): read only.
- the scripts and results under /home/jhan/workspace/intel-AMX/exec/ (pr2-20261011/, pr1-20261010/, i4525-20260922/, sync4424-20261002/, savek2-20261008/, merge4737-20261008/, vnnik2-20260915/, results/pr2-20261011/, results/pr2-E-cpu/, results/savek2-20261008/, results/vnnik2-20260915/, results/vnnik2-trace-20260915/, logs/, lib-guard.sh, bill-share.sh).
- the tron repository rules: AGENTS.md, ingest/AGENTS.md, lefthook.yml, .github/workflows/gcp-nix.yml in the worktrees.
- the notebook rules: /home/jhan/workspace/notebook/handoffs/check-CI.md; the memory file /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/3bda-shared-with-bill.md.
- delphi-3bda (ssh delphi-3bda) may be used for LIGHT read-only checks only (ls, cat, sha256sum, git rev-parse, grep over files, strings); no builds, no runtron, no writes, nothing that takes more than a few seconds of CPU.
Rules for your findings:
- Every finding must quote the exact phrase of the handoff it concerns, name the section, state what is wrong or missing, give the evidence (file:line, command output, commit id) and propose the exact replacement text or addition. A finding without evidence is a nit at most.
- Severity: must-fix = the executor would do the wrong thing, lose data, break a rule, or report a false result; should-fix = the executor would waste time, guess, or produce a weaker PR; nit = wording.
- Do not report things the handoff states as estimates ("est.") as wrong because they are estimates; report them only when a measurement exists that contradicts them.
- Do not invent findings to fill the list. Zero findings is a valid result.
- Do not modify any file anywhere except your own scratch files under /tmp/claude-0/ (make a directory for yourself there). Do not create git worktrees. Do not push, commit or run gh commands that write.
Your final output is the structured list only.`

const FINDINGS = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    checked: { type: 'string', description: 'one paragraph: what you verified and how (commands run, files read)' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
          section: { type: 'string' },
          quote: { type: 'string', description: 'the exact handoff text concerned' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string', description: 'exact replacement text or addition' },
        },
        required: ['id', 'severity', 'section', 'quote', 'problem', 'evidence', 'fix'],
      },
    },
  },
  required: ['lens', 'checked', 'findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    evidence: { type: 'string' },
    better_fix: { type: 'string', description: 'if the finding stands but its proposed fix is wrong or incomplete, the corrected fix; else empty' },
  },
  required: ['refuted', 'reason', 'evidence', 'better_fix'],
}

const LENSES = [
  {
    key: 'git-facts',
    prompt: `${COMMON}
LENS: git and patch facts. Verify every commit id, branch name, head, PR number and state, numstat figure, file list, line number, conflict description and resolution text in the handoff against the repository, the patch and the probe worktree. In particular: the three conflict blocks and the four resolutions of step 1.3 (compare with probe-pr3/conflicts.txt and resolve.py and with the staged files of the probe worktree); the residual-difference list of step 1.4 (run git diff --cached ba69cb513e in the probe worktree for the 9 files and classify every hunk); the step-2 edit (old and new texts, occurrence counts, the k_destination_row signature); the numstat figures (+682/-78 and +678/-78); the claims about what PR-1's and PR-2's commits changed in the conflicting files; the test-file facts (the block-save case is not under #ifdef, the save_k case's two sections, blob 522acb4792); the Haskell helper names and line numbers; the section 5.2 symbol lists (run the greps). Use gh pr view for PR #4868 and #4887 (read-only). Report every discrepancy.`,
  },
  {
    key: 'machine-scripts',
    prompt: `${COMMON}
LENS: the delphi-3bda scripts and the chain. Verify every claim the handoff makes about exec scripts and result files: exec/pr2-20261011/chain.sh (variables, steps, markers, the STEP line, the verdict rule, the head-reuse logic, CONF lines 67-70, cells() helper, D and E exports), build2.sh, campaign.sh (placement 2 and 4, HPFILE, CELLS_ALL format, ARMS/WEDPERF handling, arm_bin for head/new), smoke.sh (SMOKE_ARMS, MUST_MATCH, its verdict), summarize.py (WEDPERF_ARMS, WEDPERF_PAIRS, the summary.md row formats fill-body.py parses), validate-smoke.py, host-suite.sh, dut.sh, bill-share.sh, lib-guard.sh, launch.sh, wait-chain.sh, savek2-20261008/build-test.sh (the A2 command, the fourmolu command, the plugin grep and why it counted 0), results/savek2-20261008/plugin-calls.txt, results/pr2-20261011/build-pr2.txt (the sha256), results/pr2-E-cpu/rt-results.txt, logs/pr2-E-cpu.log (the 47.7 min). Check the proposed changes for the PR-3 fork are sufficient and correct: WT_HEAD/RT_HEAD, the head-reuse comparison, the tp4 cell line and the cells() helper, WEDPERF_PAIRS, MUST_MATCH, the plugin-check rule (verify the generated call text on delphi-3bda in /var/tmp/jhan/tron-pr2/gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp and, if present, /var/tmp/jhan/tron-savek2/...: one line? argument tail?), the A2 command and its grep, the fourmolu command (is fourmolu in the default nix develop shell? the 2026-10-08 format-savek2.txt says so), the M1/M2 rebuild commands (cmake --build gen --target ...), the deadlines and the two launch windows versus DEADLINE_HHMM and the pre-CI hold, the budget arithmetic, the step-0 checks on 3bda. Report every discrepancy and every missing instruction an executor would need to fork the chain.`,
  },
  {
    key: 'code-and-tests',
    prompt: `${COMMON}
LENS: code and test reasoning. Read the staged diff of the probe worktree (git -C /home/jhan/workspace/ai-runs/tron-split-probe-pr3 diff --cached jhan-vnnik-2-amx) and verify every technical claim of the handoff about the code: the window protocol description (Words, step 5.2), k_store_shared's three conditions, the unit-cut rule, store_block's behaviour (masks, null rows, the transpose stages, whether c is bound-checked inside store_block), set_k_block's assert, the decode claim (8 users = 8 items per decode pass, not more than 16, so no window; is that true for the 8-user cells of this campaign? consider how items relate to users in decode), the per-commit compile claims of step 3 (do commits (a) and (b) compile on their own by inspection: who calls set_k_block, what the generated plugins call before (c), whether the Note in kv_cache.hpp at (a) references anything undefined), the step-2 edit equivalence (k_destination_row returns the same view type as the replaced expression; check tensor/k_vnni.hpp), the mutation predictions M1 and M2 (read t/t_k_vnni_layout.cpp lines 207-290 and t/t_llama_unit.cpp lines 3790-4050 of the probe worktree: does M1 fail at the first REQUIRE on block 0 with the full mask? does M2's mutation compile without an unused-variable warning, keep the values right, and fail at the block REQUIRE as described? which unit crosses a block boundary first?), the expected assertion count of t_k_vnni_layout (218 added: derive it from the test code), the claim that both tests run with the option off, the claim that the save_k case's three-thread section runs with n_workers = 3 and the helpers return early when not shared, the Catch2 claims (a failed REQUIRE ends the case; the expected summary lines of M1; whether Catch2 would re-enter the case for the unvisited SECTION; cite Catch2 source if available in the nix store on delphi-3bda or your knowledge, and mark the confidence), the Haskell claims (attentionRuntimeCall's signature at the PR-2 head accepts what the patch passes; run_main_help's parameters; the generated call text), the plugin-check rule (main_k == helper_k == kv_ops: is one save_v per KV-writing operation always true?), the "every helper-side host kernel call also ends in worker_ix, n_workers" comment in the spec, and the watchdog arithmetic. Report every claim that is false or unsupported, with the code evidence.`,
  },
  {
    key: 'policy-consistency',
    prompt: `${COMMON}
LENS: policy and consistency. Verify the handoff against: split-handoff.md section 0 (every decision D1 to D11 and its default), section 3 (the stack table, the PR-3 row), step 3 (the PR-3 construction: patches, conflicts expected, commits, the save_k test blob, the Haskell check, the chain row, the tp4 cell), sections 5.2, 5.3, 5.4, 6, 7, 8, 9; split-plan.md 3.1 (the PR-3 paragraph) and U2.1 (D10); PR2-handoff.md (every rule or step PR3-handoff.md says it repeats or deviates from; the deviation list of section 3 must name every departure from split-handoff.md step 3 and from the PR-2 pattern); split-status.md (the PR-1 and PR-2 records: heads, binaries, sha256, results, the marker takes, the codex round, the watcher state); create-PR1-handoff.md section 6 (the body rules); the tron AGENTS.md rules on stacks, labels and the test policy; lefthook.yml and gcp-nix.yml (the CI claims: draft filtering, which jobs run on a draft, Test ingest's dependency on Build ingest, Lint running lefthook with fourmolu and lint-notes, slice.yml's path filter); ingest/AGENTS.md; check-CI.md's rules and the nightly schedule lines cited; the marker rule memory file. Check that the Words list defines every term the handoff uses (a term used before its definition or never defined is a finding) and that no name of a person appears where the rules forbid it (the body rules forbid names in the PR body; the handoff itself may name jhan and Bill). Check the Do-not list and the stop-and-ask list for gaps against PR2-handoff.md's. Report every inconsistency with its evidence.`,
  },
  {
    key: 'measurements',
    prompt: `${COMMON}
LENS: measurement provenance. Verify every number and every record the handoff cites: the 2026-09-15 summary (exec/results/vnnik2-20260915/summary.md: ab vs vnni0 and ab vs base at tp2 and tp4, prompt 1024, 2048, 8192, the n per cell, the TPS spread claim), the trace analysis (exec/results/vnnik2-trace-20260915/analysis.md: Save K us/layer and ns/row per arm and tp; the 274/281 us of main's row-major store, which the handoff attributes to the PR 4424 body and the 2026-09-14 trace: find exec/results/vnnik-trace-20260914/analysis.md and check), the 2026-09-15 smoke (exec/results/vnnik2-20260915/smoke/smoke.txt: arms, prompt, tokens, verdicts), the 2026-10-08 record (exec/results/savek2-20261008/: steps.txt, tests counts 1011650/5, ingest-test counts 17290/1351/0, plugin-calls.txt rows, format-savek2.txt), PR-2's results (exec/results/pr2-20261011/steps.txt and tests-*.txt: the counts 1011432/4, 1618/1, 6669/5, 266459/66, 2783/3, 6220/64, 796 s; exec/results/pr2-E-cpu/summary.md: +5.4/+9.5 % TPS, +100 ms/-523 ms TTFT, newoff vs new -11.0/-18.3 % and +674 ms/+64.9 s; the smoke results token 83 / 247 and the ids 624/13; the marker times 13:55:03 and 15:00:55; the E duration 47.7 min and 95 s per run), the PR-2 body (exec/pr2-20261011/pr-body.md: the stack table row for PR-3, the Open item on the scatter store, the Words rows), the PR 4424 body snapshot (handoff-material/pr4424-body-20261009.md: the "Use shared block" section, the 274/281 and 80/60 us sentence, the helper counts 7 and 8), the sha256 of runtron.pr2, the free space and the machine state claims (verify on delphi-3bda with light commands: ls -la, sha256sum of runtron.pr2, df -h /var/tmp, ls /var/tmp/jhan/tron-pr3*, the lease file, the marker, systemctl is-active rinzler@0 rinzler@1). Report every number that does not match its source, with the source line.`,
  },
  {
    key: 'completeness',
    prompt: `${COMMON}
LENS: executor completeness. Read the handoff as the agent who must execute it with no other context than the files it names. For every step, ask: is every command runnable as written (paths, variables, order)? Is every expected output stated so that pass and fail are distinguishable? Where would the executor have to guess, and what would it guess? What is missing that PR2-handoff.md had for PR-2 (compare section by section: steps 0 to 8, sections 5.1 to 5.5, 6, 7, 8, 9) and that PR-3 needs too? What is stated twice with different values? Which instruction could be executed in two materially different ways? Which referenced file, script, line number or record does not exist (check each path and line reference on disk; the probe worktree and exec/ are available)? Is the chain fork described precisely enough (every variable, every new step with its command, every verdict condition)? Is the body section list complete and consistent with the measurements the chain produces (every placeholder has a source)? Are the launch windows and deadlines consistent with the current date and time (2026-10-11 about 20:00 UTC) and with the scripts' DEADLINE_HHMM and pre-CI hold? Report gaps as should-fix with the exact text to add; ambiguities that would lead to a wrong action as must-fix.`,
  },
  {
    key: 'plain-english',
    prompt: `${COMMON}
LENS: plain English, Check mode, per the plain-english skill rules in your instructions (define every code name, acronym and metric at first use or in "Words used here"; one claim per sentence; numbers with units and, where needed, a meaning clause; estimates marked est.; citations after a sentence; a Short version of at most three sentences at the top; no idioms, metaphors or uncommon words; bullets or blank lines between separate points; short sentences without several subordinate clauses; no semicolon joins in prose). The handoff is an engineering document with many code names, so apply Rule 1 with the Words list as the definition place: a term is defined if it appears in "Words used here" or is defined inline before its first use; a term used only inside a code block or a command is exempt. Rule 2 and Rule 8 apply to prose sentences, not to table cells that list items, and not to commands. Report the violations that matter most for an executor's comprehension: undefined terms (list each), sentences with two claims that could be misread, numbers without units or meaning, idioms, clock times written in a form the rules forbid, and the Short version length. Group small wording items into one nit each. Severity: an undefined term that changes what the executor does = should-fix; most others = nit.`,
  },
]

const refuterPrompts = (f, lens) => [
  `${COMMON}
You are a REFUTER. A review lens ("${lens}") produced this finding about the handoff:
${JSON.stringify(f, null, 2)}
Try to refute it: re-check the claimed problem against the actual files, revisions, scripts and results it concerns (read them yourself; do not trust the finding's evidence). The finding is refuted when the handoff text is correct as written, or when the proposed fix would make the handoff wrong, or when the problem is already handled elsewhere in the handoff (quote where). Default to refuted=true when you cannot confirm the problem with your own evidence. If the problem is real but the proposed fix is wrong or incomplete, set refuted=false and write the corrected fix in better_fix.`,
  `${COMMON}
You are a REFUTER with the executor's and jhan's perspective. A review lens ("${lens}") produced this finding about the handoff:
${JSON.stringify(f, null, 2)}
Judge it on two questions, with evidence: (1) Would the proposed fix conflict with any rule the handoff must follow (split-handoff.md section 0 decisions, the tron AGENTS.md stack and label rules, jhan's body rules in create-PR1-handoff.md section 6, the machine rules in check-CI.md and the marker rule, the PR-2 precedent in PR2-handoff.md and split-status.md), or widen the executor's scope beyond PR-3? (2) Would an executor who follows the handoff as written actually hit the problem the finding describes, or is the finding hypothetical? Set refuted=true if the fix conflicts with a rule, or widens scope, or the problem would not occur in execution, or it is a matter of taste. Otherwise refuted=false; if the fix needs narrowing to stay within the rules, write the narrowed fix in better_fix.`,
]

phase('Review')
const results = await pipeline(
  LENSES,
  lens => agent(lens.prompt, { label: `review:${lens.key}`, phase: 'Review', schema: FINDINGS }),
  async (review, lens) => {
    if (!review) return { lens: lens.key, checked: 'agent failed', findings: [] }
    const serious = review.findings.filter(f => f.severity !== 'nit')
    const nits = review.findings.filter(f => f.severity === 'nit')
    log(`${lens.key}: ${review.findings.length} findings (${serious.length} must/should-fix, ${nits.length} nits)`)
    const judged = await parallel(serious.map(f => async () => {
      const votes = await parallel(refuterPrompts(f, lens.key).map((p, i) => () =>
        agent(p, { label: `refute${i + 1}:${lens.key}:${f.id}`, phase: 'Refute', schema: VERDICT })))
      const v = votes.filter(Boolean)
      const refutedCount = v.filter(x => x.refuted).length
      return { ...f, kept: v.length > 0 && refutedCount === 0, votes: v }
    }))
    return { lens: lens.key, checked: review.checked, serious: judged.filter(Boolean), nits }
  },
)
const out = results.filter(Boolean)
const kept = out.flatMap(r => r.serious.filter(f => f.kept))
const refuted = out.flatMap(r => r.serious.filter(f => !f.kept))
log(`kept ${kept.length} serious findings, refuted ${refuted.length}, nits ${out.reduce((n, r) => n + r.nits.length, 0)}`)
return { kept, refuted, nits: out.map(r => ({ lens: r.lens, nits: r.nits })), checked: out.map(r => ({ lens: r.lens, checked: r.checked })) }