export const meta = {
  name: 'review-design-r4',
  description: 'Round-4 review of the codex design for issue #4525: grade the 79 open items against the third revision, find new defects, verify adversarially, judge implementability',
  phases: [
    { title: 'Dispositions', detail: '17 batches, each: one checker then two independent re-graders' },
    { title: 'Find', detail: '10 finders, one lens each, in parallel with the dispositions' },
    { title: 'Merge', detail: 'one agent dedupes all candidates' },
    { title: 'Verify', detail: 'three refuters per candidate; survives when at least two cannot refute' },
    { title: 'Critic', detail: 'completeness critic, then the same verification' },
    { title: 'Judge', detail: 'three independent implementability verdicts' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/9a0c3ca8-75c1-4ba0-8af2-e929fafddbfc/scratchpad'
const ISSUE = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525'
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'

const COMMON = `
CONTEXT (read first, in this order):
1. ${S}/facts-r4.md  -- the lead's verified facts for THIS round: what the design is, what changed, live GitHub/main state, verified source facts, section line map, and TRAPS. Read it fully.
2. ${S}/design-r4.txt -- the plain-text extraction of the design under review (683 lines). Cite it as design-r4.txt:<line>. Table rows look like "| cell | cell |"; links look like "text <href>".
3. ${S}/facts-r3.md, ${S}/facts-r2.md and ${S}/facts-r1.md -- verified source facts from the earlier rounds (line numbers at 2880c3aa9b and f46e48ba). facts-r4.md corrects one error in facts-r3.md (self_attention.hpp block is 30-36).
Other material: ${S}/design-wdiff.txt (word diff round-3 text -> round-4 text, 210 OLD:/NEW: segments), ${S}/design-r4-links.tsv (every link of the design: text TAB href), ${S}/design-r3.txt (the round-3 design text),
${S}/r3-findings.md (round-3 findings; grep "### G01 " etc.), ${S}/r2-findings.md (round-2 findings; grep "### N13 "), ${S}/r1-findings.md (round-1 findings; grep "### F13"), ${ISSUE}/evidence/github-review.json (Ben's three comments + issue JSON),
${ISSUE}/status/design-new-tensor-type.html (the design HTML, for anchors and links).
tron source: read ONLY with  git -C ${WT} show <commit>:<path>  or  git -C ${WT} grep -n <pattern> <commit> -- <path>. Commits: f46e48bab498 (design snapshot, S1-S13), 2880c3aa9b (round-2 main, cited by S15-S17 and S19-S21), 0a51385e95 (LIVE main; identical to 2880c3aa9b for every file the design touches except one inserted line in model.hpp at 891), 30c4ac82cb (PR 4424 head, "the child"), c7844ca2ce (merge base).
HARD RULES: never checkout/reset/modify/build/run anything in that worktree; write nothing under ${ISSUE} or ${WT}; do not post to GitHub (read-only gh is fine); do not read /home/jhan/.claude. You may write scratch notes under ${S}/agent-notes/ only.
TERMS: F../C.. = round-1 finding ids; N../M.. = round-2 finding ids; G../H.. = round-3 finding ids; "the design" = the round-4 (third) revision you are reading; "the child" = PR 4424; "the parent" = the new PR the design specifies; "resolved/partly/deferred/unresolved/regressed" = disposition statuses defined below.
STATUS MEANINGS: resolved = the design TEXT now specifies what the (corrected) recommendation or the STILL NEEDED text asked and every checkable fact in the fix is right. partly = the substance is there but a concrete part of the recommendation is missing, or a small factual slip remains. deferred = the design explicitly leaves it to separate work or to a named person; say whether that is acceptable. unresolved = not addressed, or addressed only in the section-9 table without a matching body change. regressed = the fix introduced a new error or a contradiction.
SEVERITY MEANINGS: blocker = an implementing agent would build the wrong thing, or the parent PR could not merge; major = the design text must change before implementation starts; minor = the design text should change, low risk if it does not; note = worth knowing, no change required.
WRITING: plain English, short sentences, one claim per sentence, define any term not in the facts files, every number with a unit, every claim with a citation (design-r4.txt:<line>, or <file>@<commit>:<lines>). Your final output is data for a report generator, not a chat message.`

const BATCHES = {
  B01: ['G01', 'G13', 'G21', 'G12', 'F35'],
  B02: ['G02', 'G15', 'G35', 'G36', 'F23', 'N44'],
  B03: ['G03', 'G32', 'G50', 'G51'],
  B04: ['G04', 'G08', 'G09', 'G10', 'G40', 'N20'],
  B05: ['G05', 'G06', 'G07', 'N42'],
  B06: ['F19', 'F20', 'F21', 'M06'],
  B07: ['G14', 'G47', 'M01', 'G27'],
  B08: ['G16', 'G17', 'G48', 'H03', 'N59'],
  B09: ['G18', 'G20', 'N28', 'C06'],
  B10: ['H01', 'F57', 'F58', 'G33'],
  B11: ['G19', 'G42', 'M04', 'C01'],
  B12: ['G22', 'G30', 'M03', 'N50'],
  B13: ['G23', 'H02', 'G34', 'N33', 'F29', 'N30'],
  B14: ['G24', 'G26', 'G25', 'G28', 'G29', 'F16'],
  B15: ['G49', 'G31', 'F38'],
  B16: ['G37', 'G45', 'N56', 'G44', 'G46'],
  B17: ['G38', 'G39', 'G41', 'F54', 'N11'],
}
const BATCH_KEYS = Object.keys(BATCHES)
const STATUSES = ['resolved', 'partly', 'deferred', 'unresolved', 'regressed']
const SEVS = ['blocker', 'major', 'minor', 'note']

const DISPO_SCHEMA = { type: 'object', required: ['items'], properties: { items: { type: 'array', items: { type: 'object',
  required: ['id', 'status', 'design_evidence', 'assessment', 'residual', 'new_defect_severity'],
  properties: {
    id: { type: 'string' },
    status: { type: 'string', enum: STATUSES },
    design_evidence: { type: 'string', description: 'verbatim design-r4.txt quotes with line numbers that address the item, or "omission"' },
    assessment: { type: 'string', description: 'why this status; name every checked fact and its source' },
    residual: { type: 'string', description: 'what the design text still needs, as exact wording where possible; empty when resolved' },
    new_defect_severity: { type: 'string', enum: ['none', 'blocker', 'major', 'minor', 'note'] },
    new_defect_title: { type: 'string' },
    new_defect: { type: 'string', description: 'a NEW error the fix introduced (not the residual): claim, design quote with line, source evidence, recommendation' },
  } } } } }

const REGRADE_SCHEMA = { type: 'object', required: ['items'], properties: { items: { type: 'array', items: { type: 'object',
  required: ['id', 'status', 'reason'],
  properties: { id: { type: 'string' }, status: { type: 'string', enum: STATUSES }, reason: { type: 'string' }, correction: { type: 'string', description: 'a correction to the checker or to the design fix, with citations; empty if none' } } } } } }

const FINDINGS_SCHEMA = { type: 'object', required: ['findings'], properties: { findings: { type: 'array', items: { type: 'object',
  required: ['title', 'section', 'kind', 'claim', 'design_quote', 'evidence', 'recommendation', 'severity'],
  properties: {
    title: { type: 'string', description: 'at most 12 words' },
    section: { type: 'string', description: 'design section and design-r4.txt line(s)' },
    kind: { type: 'string', enum: ['factual error', 'omission', 'contradiction', 'ambiguity', 'scope', 'process', 'page quality'] },
    claim: { type: 'string' },
    design_quote: { type: 'string', description: 'verbatim design text, or "omission"' },
    evidence: { type: 'string', description: 'source citations at pinned commits, computations, or GitHub facts' },
    recommendation: { type: 'string', description: 'the exact change to the design text' },
    severity: { type: 'string', enum: SEVS },
    relates_to: { type: 'string', description: 'earlier finding ids this touches, or empty' },
  } } } } }

const MERGE_SCHEMA = { type: 'object', required: ['merged', 'dropped'], properties: {
  merged: { type: 'array', items: { type: 'object',
    required: ['title', 'section', 'kind', 'claim', 'design_quote', 'evidence', 'recommendation', 'severity', 'lenses', 'members'],
    properties: {
      title: { type: 'string' }, section: { type: 'string' }, kind: { type: 'string' }, claim: { type: 'string' }, design_quote: { type: 'string' },
      evidence: { type: 'string' }, recommendation: { type: 'string' }, severity: { type: 'string', enum: SEVS },
      lenses: { type: 'array', items: { type: 'string' } }, members: { type: 'array', items: { type: 'string' }, description: 'candidate keys merged into this one' },
      relates_to: { type: 'string' },
    } } },
  dropped: { type: 'array', items: { type: 'object', required: ['member', 'reason'], properties: { member: { type: 'string' }, reason: { type: 'string' } } } },
} }

const VERDICT_SCHEMA = { type: 'object', required: ['refuted', 'confidence', 'severity', 'reason'], properties: {
  refuted: { type: 'boolean' }, confidence: { type: 'string', enum: ['low', 'medium', 'high'] }, severity: { type: 'string', enum: SEVS },
  reason: { type: 'string' }, correction: { type: 'string', description: 'how the finding text should be narrowed or fixed; empty if none' } } }

const CRITIC_SCHEMA = { type: 'object', required: ['candidates', 'strengths', 'overall'], properties: {
  candidates: FINDINGS_SCHEMA.properties.findings,
  strengths: { type: 'array', items: { type: 'string' }, description: 'what the revision gets right, each with a design-r4.txt line' },
  overall: { type: 'string' },
  disputes: { type: 'array', items: { type: 'string' }, description: 'confirmed findings or dispositions you think are wrong, with reasons' },
} }

const JUDGE_SCHEMA = { type: 'object', required: ['judge', 'verdict', 'implementable_now', 'reasons', 'top_three_edits', 'must_fix_before_implementation', 'questions_block_adequate'], properties: {
  judge: { type: 'string' },
  verdict: { type: 'string', enum: ['accept as is', 'accept with minor edits', 'accept with changes', 'redo'] },
  implementable_now: { type: 'boolean' },
  reasons: { type: 'string' },
  top_three_edits: { type: 'array', items: { type: 'string' } },
  must_fix_before_implementation: { type: 'array', items: { type: 'string' } },
  questions_block_adequate: { type: 'boolean', description: 'is the Q1-Q4 + D5 decision record adequate for Ben and jhan' },
} }

// ------------------------------------------------------------------ phase 1: dispositions
function checkerPrompt(b) {
  return `You are the CHECKER for disposition batch ${b} of the round-4 design review.
${COMMON}

YOUR BATCH: read ${S}/batches/${b}.md. It holds ${BATCHES[b].length} items: ${BATCHES[b].join(', ')}. Each item is either a round-3 NEW finding (G../H..) with its recommendation, lead note and verifier corrections, or an older finding (F../C../N../M..) that round 3 graded partly/deferred with a "STILL NEEDED after round 3" residual.
TASK, for EVERY item:
1. Find where the round-4 design addresses it. Search design-r4.txt (grep key words; read the whole relevant section; also read the section-9 row that names the id, lines 544-646). Quote the exact sentences with line numbers. If nothing in the BODY addresses it, say "omission" and note whether section 9 claims it anyway.
2. Verify every checkable fact in the design's fix against the primary source (git show at the pinned commit; Ben's JSON; the facts files only as a guide). Name each fact you checked and where.
3. Decide the status (resolved / partly / deferred / unresolved / regressed) against the recommendation AS CORRECTED by the round-3 verifiers (for G../H..) or against the STILL NEEDED text (for residual items). Do not demand more than the corrected recommendation asked. Where round 3 offered two options (for example G01 A or B, G12 A or B, G14 adopt or decline, N59/G48 revert or state the choice), either option with its reason stated resolves the item. Do not accept a section-9 claim without body text.
4. residual: what the design text still needs, as exact wording where possible. Empty when resolved.
5. new_defect: if the FIX itself introduced a new error, contradiction, or misleading sentence, describe it as a finding (claim, design quote with line, source evidence, recommendation) and grade it. Otherwise new_defect_severity = "none".
Return one item per id, in the batch order. Be precise and skeptical in both directions: a wrong "resolved" and a wrong "unresolved" are equally bad.`
}

function regradePrompt(b, lens, chk) {
  const lensText = lens === 'source'
    ? `LENS = source truth. For each item, independently verify every factual claim in the design's fix against the primary source (git show at the pinned commit, Ben's JSON, gh read-only). A fix that states a wrong file, line, name, number, flag, rule, or mechanism is at best "partly". A fix whose facts are all right and that covers the corrected recommendation (or the STILL NEEDED text) is "resolved". Check the checker's design_evidence quotes exist at the cited lines (grep design-r4.txt).`
    : `LENS = fairness to the design. For each item, grade the design TEXT against the recommendation AS CORRECTED by the round-3 verifiers, or against the STILL NEEDED text for residual items (the batch file carries both). Do not demand implementation, test runs, GitHub posts, or anything the recommendation did not ask; do not penalize explicit, reasoned deferrals or an explicitly stated choice between two offered options; do not accept a section-9 claim that has no body text; do not accept a vague sentence where the recommendation asked for exact wording, a name, a number, or a rule. Read the design sections yourself; the checker's quotes may be incomplete.`
  return `You are an independent RE-GRADER (${lens} lens) for disposition batch ${b} of the round-4 design review.
${COMMON}
${lensText}

YOUR BATCH: read ${S}/batches/${b}.md (${BATCHES[b].length} items: ${BATCHES[b].join(', ')}).
The checker already located design text for each item. Its quotes are below so you do not have to search from zero; its status and assessment are deliberately withheld so your grade is independent. Search beyond the quotes if you suspect they are incomplete.
CHECKER'S DESIGN EVIDENCE:
${chk.items.map(i => `- ${i.id}: ${i.design_evidence}`).join('\n')}

Return one item per id with your status, a reason with citations, and a correction (to the design's fix or to the checker's evidence) when you found one. Be exact: "partly" needs the missing piece named; "regressed" needs the new error quoted.`
}

// ------------------------------------------------------------------ phase 2: finders
const FINDERS = [
  { key: 'cpp-interface', lens: `C++ interface and types (design sections 5 and 7 "Child storage and access", the AMX numerics fixture migration, the worker-index paragraph). Check every declaration, alias, template rule, static_assert rule, const rule, inheritance claim, forward-declaration claim, include-boundary rule, DMA rule, detail::v_vnni_access rule, and expression-interface requirement against the tron headers at 2880c3aa9b (view.hpp, views.hpp, seq.hpp, expr.hpp, tensor.hpp, slice.hpp, bf16.hpp, kv_cache.hpp, amx_attn_iface.hpp) and the child at 30c4ac82cb (k_vnni.hpp, kv_cache.hpp, model.hpp). Would the declarations compile as specified? Are the contracts consistent with each other (section 5 table vs bullets vs section 7 vs section 8 checks)? Are names (v_packed, k_packed, append_v_row, load_row, copy_token, store_row, store_block, const_native_k_view) used consistently across sections?` },
  { key: 'behavior-arena', lens: `Behavior the implementation must preserve and arena construction (design section 6, plus the section 4 constraints and the section 5 scaled_v_expr row). Check the NaN bit table by computation, the partner-zeroing rules against kv_cache.hpp set_v/append_v/scaled_v_expr, the scaled_v_expr constructor rule (pair-tile base once through detail::v_vnni_access; preserved _mm512_load_si512/_mm512_dpbf16_ps loop), the array-new construction rules, the uniform/heterogeneous enumeration (for_each_active_slot, kv_storage_offset, storage_location, slot_base, allocate_kv_group, refresh_kv_blocks_alias, restore_reclaimable_kv_storage), the EAGLE rules (eagle_storage_offset, x_data), the copy rules (copy_storage_slot, append_v), the GOF/page_info rules (gof.hpp, full.hpp, gof.cpp), the comment-replacement wording (:379-380) against the actual comments at the cited lines, and every comment-site line range.` },
  { key: 'process-ci', lens: `Process, CI, commands and hosts (design sections 3 and 8: build configurations, CI ownership and execution evidence, log preservation, AMX proof, commands and hosts, instruction comparison, definition of done). Check every CMake flag, preset, Make target (format, lint, lint-notes, format-haskell, build-test, test-host, iwyu-check), Nix fact (lint-toolchain check, ingest-tests check, cmake-tron-test-build.nix), workflow step name and print string (gcp-nix.yml, bin/ci/tron-build/test_runtime.py, bin/slice Logs/run-NNNN/RETENTION), README.ci.md rule, AGENTS.md / ingest/AGENTS.md / .github/AGENTS.md rule, run-tron-tests skill rule, lib-guard.sh and bill-share.sh rule (files under /home/jhan/workspace/intel-AMX/exec/), bin/slice bench --update/--new/--check fact, and evidence rule against the source at 2880c3aa9b. Note: sw-dev-01 is codex's user rule, not a defect. Check that the definition of done is checkable and that its new bullets (:536-537) are consistent with the rest of section 8.` },
  { key: 'handoff', lens: `Handoff actionability. Read the whole design as the implementing agent who must build the parent PR from this page alone. List every place where you could not act: an instruction with two readings, a missing decision, a contradiction between sections (e.g. section 5 vs 6 vs 7 vs 8 vs 9), an undefined name, a step whose completion check cannot be performed, a file the steps forget, or a dependency order that is wrong. Pay attention to the newly added text: the AMX numerics fixture migration (:397-407), the two rg commands (:405-407), the K header split and forward declarations (:416-418), the test-cost record bullet (:420), the LoopyTronSpec sentence (:451), the Debug row (:482), the log-preservation and AMX-proof subsections (:500-508). Prefer concrete "at line X the agent cannot know Y" findings over style remarks.` },
  { key: 'fidelity', lens: `Fidelity to Ben and to jhan. Compare design section 2 (the three comments table, the retained/chosen/limited bullets including the new "Child scope" bullet at :83, the decision record Q1-Q4 + D5, the proposed issue text :112-131) against Ben's three comments verbatim in ${ISSUE}/evidence/github-review.json, against jhan's request ${ISSUE}/../input-2-ai/codex-add-tensor-type.md and ${ISSUE}/../input-2-ai/claude-review-add-tensor-type.md, and against issue #4525 (gh issue view 4525 -R positron-ai/tron). Does the design misstate what Ben asked or reserved? Does the question block cover what an implementer must know before coding? Does the proposed issue text, applied exactly as its instructions say, respect jhan's rule (no names in issues Claude/agents draft; roles plus links only), keep the five Scope bullets and the PR order list, and carry the three GitHub links? Is "Part of #4525" and the closing rule right? Is the Words table's identification of the reviewer and of jhan's three roles right?` },
  { key: 'simplicity', lens: `Simplicity and scope. The parent should be the smallest change that gives typed access to today's packed V and native K with expression reads and the existing bulk operations. Find anything the design adds that no caller needs, any deferral that is actually needed by a named caller, any child-scope creep into the parent, any duplicated mechanism (two ways to do one thing), and any contract stricter or looser than today's code without a stated reason. Cite the design line and the caller in tron source. Consider whether the new fixture rules (:397-403), the two rg commands, the class-body static_assert rule, and the K forward declarations are the smallest adequate choice.` },
  { key: 'formulas-page', lens: `Formulas, numbers, links and page quality. Recompute every formula and number in the design (section 4 mapping formulas including the new panel decomposition at :222 against k_vnni::index at 30c4ac82cb, the size table, byte sizes, bit patterns, panel/tile sizes, chunk sizes, bounds (count+1)/2*2, the 16,384-byte owner, commit counts, dates, comment ids and times, the seven LoopyTronSpec assertions, RETENTION 10). Check the Words table: is every term used in the design defined, and is every definition right (:23-62)? Check links (${S}/design-r4-links.tsv, 526 links): does each GitHub link's line range contain what the anchor text says? Spot-check at least 30, prioritizing the 31 new S21 labels (:675) and the S15-S20 labels. Check that section-9 bracket links ([Words], [Access contract], ...) go to anchors whose section holds the claimed response. Report only real errors and undefined or wrongly defined terms; do not grade prose style.` },
  { key: 'child-needs', lens: `The child's needs (design section 7 "Then adapt PR #4424", "Child storage and access", "Worker-index request and code that stays outside the K type", plus section 8 "Child only" rows and the 8-lane child sentence :441). Compare against the child source at 30c4ac82cb (kv_cache.hpp K paths 1683-1770 and 2093-2141 and the #error at 35-39, k_vnni.hpp, model.hpp 2806-3079, self_attention.hpp qk paths, gof.hpp/full.hpp/gof.cpp scratch, TronCpp.hs 2325-2410, LoopyTronSpec.hs 2795-2820 and 3218-3236, t_k_vnni_layout.cpp, t_llama_unit.cpp 2772-2781, config/test-benchmarks.json granite_rapids_6962p block, src/tron/CMakeLists.txt 201-213). Does the parent give the child everything it needs (owner selection, views, row/block stores, plane copy via owner assignment, kernel arguments, K forward declarations, scratch, worker index, cost records)? Is anything specified for the child wrong about the child's actual code? Is the port order (retarget, focused commits, README/workflow flag, ingest/AGENTS.md, format-haskell) right per AGENTS.md, ingest/AGENTS.md and .github/AGENTS.md?` },
  { key: 'regression-diff', lens: `Regression hunter on the round-3 -> round-4 changes. Read ${S}/design-wdiff.txt (210 OLD:/NEW: segments) end to end. For every changed or added segment ask: did the edit introduce a factual error, an internal contradiction, an ambiguity, or drop a correct round-3 statement that an implementer needs? Confirm each suspected error against the source at the pinned commit before reporting. Also check the new "Short version" (:13-15) and the header line (:3) for accuracy. Do not report pure rewording.` },
  { key: 'section9-audit', lens: `Section-9 honesty audit (design-r4.txt lines 544-646: the round-3 table :548-574, the round-1-residuals table :576-597, the round-2 table :599-621, the round-1 table :623-643, the rejected-candidates sentence :644). For every row of the round-3 and round-1-residuals tables, check that each "Design response" claim is actually present in the design BODY (name the body line) and that the "Implementation or external work still pending" column is accurate and complete (does it hide an unaddressed part?). Check that the bracket links of each row point at the sections that hold the response. Check that every id listed exists and that no round-3 id is missing (the 52 are G01-G51 without G11 and G43, plus H01-H03; G52 and H04 were dropped by the lead and need no row) and that the 23 round-1 residual ids are exactly F08 F12 C01 F15 F16 F19 F20 F21 F23 F25 F29 F30 F35 F38 F41 F48 F49 F54 F57 F58 C02 C06 C07. Check the rejected sentence (:644). Check the round-2 and round-1 tables for rows whose text changed in this revision (see ${S}/design-wdiff.txt) and whether the change is accurate. Report rows whose response is not in the body, rows whose remaining-work column is incomplete, and any id mismatch. Do not re-grade the fixes themselves; the disposition checkers do that.` },
]

function finderPrompt(f) {
  return `You are a FINDER (lens: ${f.key}) in the round-4 review of the codex design for issue #4525.
${COMMON}

YOUR LENS: ${f.lens}

SCOPE RULES:
- The 79 known items (52 round-3 findings G../H.. and 27 older residuals: M01 N56 N59 F29 N11 M06 N44 F23 F57 F58 F54 F35 N20 N50 F38 N30 M04 C01 N28 C06 N33 F16 N42 F19 F20 F21 M03) are graded by separate disposition checkers. Do NOT re-raise a known item as such. You MAY report a defect in a known item's FIX when the round-4 edit introduced a NEW error or contradiction; then set relates_to to that id and say what is new.
- Do not re-raise the 18 rejected candidates (round 1: F06 F07 F09 F18 F22 F33 F36 F44 F53 F55; round 2: N10 N19 N21 N26 N47 N54; round 3: G11 G43) or the two lead-dropped ones (G52, H04) without new evidence (reasons in ${S}/r3-findings.md, ${S}/r2-findings.md, ${S}/r1-findings.md).
- The design compiled nothing and ran nothing, posts nothing and edits no issue; those are not findings. sw-dev-01 is codex's user rule; not a finding. Main moving to 0a51385e95 (one inserted model.hpp line) is not a finding.
- Confirm every claim against the primary source before reporting. A finding you cannot cite is not a finding.
- Report at most 14 findings, the most consequential first. Each needs: a title (<= 12 words), the section and design-r4.txt line(s), the kind, the claim, a verbatim design quote (or "omission"), the evidence with citations, a concrete recommendation (exact replacement wording where possible), a severity per the meaning table, and relates_to ids if any.
Return the findings array (empty if you truly found nothing; do not pad).`
}

// ------------------------------------------------------------------ helpers
function majority(chk, votes) {
  const all = [chk.status, ...votes.map(v => v.status)]
  const counts = {}
  for (const s of all) counts[s] = (counts[s] || 0) + 1
  let best = chk.status, n = 0
  for (const [s, c] of Object.entries(counts)) if (c > n) { best = s; n = c }
  const split = n === 1
  return { final: split ? chk.status : best, split, unanimous: n === 3 }
}

// ------------------------------------------------------------------ run
log('Starting: 10 finders in parallel with 17 disposition batches (79 open items)')
const findersP = parallel(FINDERS.map(f => () => agent(finderPrompt(f), { label: `find:${f.key}`, phase: 'Find', schema: FINDINGS_SCHEMA }).then(r => ({ key: f.key, findings: (r && r.findings) || [] }))))

const dispoBatches = await pipeline(BATCH_KEYS,
  b => agent(checkerPrompt(b), { label: `check:${b}`, phase: 'Dispositions', schema: DISPO_SCHEMA }),
  (chk, b) => {
    if (!chk) return null
    return parallel(['source', 'fairness'].map(lens => () =>
      agent(regradePrompt(b, lens, chk), { label: `regrade-${lens}:${b}`, phase: 'Dispositions', schema: REGRADE_SCHEMA }).then(r => ({ lens, items: (r && r.items) || [] }))))
      .then(votes => ({ batch: b, checker: chk, votes: votes.filter(Boolean) }))
  })

const dispositions = []
const dispoNewDefects = []
for (const db of dispoBatches.filter(Boolean)) {
  for (const id of BATCHES[db.batch]) {
    const chk = db.checker.items.find(i => i.id === id)
    if (!chk) { dispositions.push({ id, batch: db.batch, status: 'unresolved', final_status: 'unresolved', assessment: 'checker returned no item', design_evidence: '', residual: '', votes: [], split: false, unanimous: false, missing: true }); continue }
    const votes = db.votes.map(v => { const it = v.items.find(i => i.id === id); return it ? { lens: v.lens, status: it.status, reason: it.reason, correction: it.correction || '' } : null }).filter(Boolean)
    const m = majority(chk, votes)
    dispositions.push({ id, batch: db.batch, status: chk.status, final_status: m.final, split: m.split, unanimous: m.unanimous,
      design_evidence: chk.design_evidence, assessment: chk.assessment, residual: chk.residual || '', votes,
      new_defect: chk.new_defect || '', new_defect_severity: chk.new_defect_severity || 'none', new_defect_title: chk.new_defect_title || '' })
    if (chk.new_defect_severity && chk.new_defect_severity !== 'none' && chk.new_defect) {
      dispoNewDefects.push({ title: chk.new_defect_title || `New defect in the fix of ${id}`, section: `fix of ${id}`, kind: 'factual error', claim: chk.new_defect, design_quote: 'see evidence', evidence: chk.design_evidence, recommendation: '(see claim)', severity: chk.new_defect_severity, relates_to: id })
    }
  }
}
const scounts = {}
for (const d of dispositions) scounts[d.final_status] = (scounts[d.final_status] || 0) + 1
log(`Dispositions done: ${JSON.stringify(scounts)}; ${dispoNewDefects.length} new defects raised by checkers`)

const finders = (await findersP).filter(Boolean)
const raw = []
for (const f of finders) f.findings.forEach((x, i) => raw.push({ key: `${f.key}#${i + 1}`, lens: f.key, ...x }))
dispoNewDefects.forEach((x, i) => raw.push({ key: `checker#${i + 1}`, lens: 'disposition-checker', ...x }))
log(`Finders done: ${raw.length} raw candidates from ${finders.length} finders + checkers`)

// ------------------------------------------------------------------ phase 3: merge
phase('Merge')
const mergeRes = await agent(`You are the MERGE agent of the round-4 design review.
${COMMON}
Below are ${raw.length} candidate findings from 10 finders (each key = lens#n) and from the disposition checkers (key = checker#n). Deduplicate them:
- Merge candidates that describe the same defect (same design sentence or same missing item), even if worded differently or graded differently. Keep the clearest claim, the strongest evidence, the most concrete recommendation, and the severity best supported by the evidence (say when you lowered or raised it). List all merged keys in members and all lenses in lenses.
- Drop a candidate only when it (a) is a duplicate you merged, (b) merely re-raises one of the 18 rejected or 2 dropped candidates without new evidence, (c) is one of the 79 known items re-raised as such (not a new error in its fix), or (d) contradicts the facts file without evidence. Record each drop with the reason.
- Do NOT verify or refute; that is the next stage. Do not invent findings.
- Order the merged list by severity (blocker, major, minor, note), then by design section.
CANDIDATES (JSON):
${JSON.stringify(raw)}`, { label: 'merge', phase: 'Merge', schema: MERGE_SCHEMA })
const merged = ((mergeRes && mergeRes.merged) || []).map((m, i) => ({ ...m, id: `J${String(i + 1).padStart(2, '0')}` }))
log(`Merge done: ${merged.length} merged candidates, ${((mergeRes && mergeRes.dropped) || []).length} dropped`)

// ------------------------------------------------------------------ phase 4: verify
const LENSES = [
  { lens: 'source', text: 'LENS = source truth: check every factual claim of the finding against the primary source at the pinned commit (git show), the design text at the cited lines, Ben\'s JSON, or gh read-only. A finding whose central fact is wrong is refuted. A finding whose central fact is right but whose details are off holds with a correction.' },
  { lens: 'design-text', text: 'LENS = fairness to the design text: read the whole design section the finding cites, and the other sections that touch the same topic (the design often states a rule once and relies on it elsewhere; section 9 is only a summary). A finding is refuted if the design already says what the finding says it lacks, if it explicitly and reasonably defers the item, if it states a choice between options the earlier review offered, or if the finding misreads the text. It holds if the omission, error, contradiction or ambiguity is really there for an implementer reading the page.' },
  { lens: 'intent', text: 'LENS = intent and consequence: does the defect matter for jhan\'s goal, an implementable parent PR that Ben will accept and that PR 4424 can be rebased onto? Refute findings that are true but inconsequential ONLY by lowering the severity to note (set refuted=false, severity=note) unless the claim is also wrong. Refute findings that demand things outside the design\'s stated scope (implementation, runs, posts) or that contradict jhan\'s or Ben\'s stated wishes.' },
]
function verifyPrompt(f, L) {
  return `You are a VERIFIER (${L.lens} lens) in the round-4 design review. Your job is to try to REFUTE the candidate finding below.
${COMMON}
${L.text}
Default to refuted=true if you cannot confirm the finding's central claim after checking. Give the severity you would assign if it holds. Give a correction whenever the finding is partly right: narrow the claim, fix the citation, or reword the recommendation, with citations.
CANDIDATE FINDING ${f.id}:
${JSON.stringify(f)}`
}
const verified = await pipeline(merged,
  f => parallel(LENSES.map(L => () => agent(verifyPrompt(f, L), { label: `verify-${L.lens}:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA }).then(v => v ? { lens: L.lens, ...v } : null)))
    .then(votes => ({ ...f, votes: votes.filter(Boolean), survives: votes.filter(Boolean).filter(v => !v.refuted).length >= 2 })))
const confirmed = verified.filter(Boolean).filter(f => f.survives)
const rejected = verified.filter(Boolean).filter(f => !f.survives)
log(`Verify done: ${confirmed.length} confirmed, ${rejected.length} rejected`)

// ------------------------------------------------------------------ phase 5: critic
phase('Critic')
const dispoSummary = dispositions.map(d => `${d.id}: ${d.final_status}${d.split ? ' (split)' : ''}${d.residual ? ' | still needed: ' + d.residual.slice(0, 300) : ''}`).join('\n')
const critic = await agent(`You are the COMPLETENESS CRITIC of the round-4 design review.
${COMMON}
Below are (1) the disposition results for the 79 known items and (2) the ${confirmed.length} confirmed new findings and the ${rejected.length} rejected candidates (titles and claims). Your job:
A. What is MISSING? Read the whole design yourself. Name defects no finder raised: a design section nobody checked, a claim nobody verified, a source file the design cites that nobody opened, a consequence for the implementer nobody drew, a mismatch between sections. Confirm each against the source before listing. Return them as candidates (same fields as a finding), at most 12, most consequential first.
B. STRENGTHS: list what the revision gets right, each with a design-r4.txt line (8 to 14 items). Be specific: name the rule, table, or sentence.
C. OVERALL: two or three sentences on whether an implementing agent can build the parent from this page now, and what the single most important remaining gap is.
D. DISPUTES: any confirmed finding or disposition status you believe is wrong, with the reason and citation.
(1) DISPOSITIONS:
${dispoSummary}
(2) CONFIRMED:
${confirmed.map(f => `${f.id} [${f.severity}] ${f.title}: ${f.claim.slice(0, 400)}`).join('\n')}
REJECTED:
${rejected.map(f => `${f.id} ${f.title}: ${(f.votes.find(v => v.refuted) || {}).reason || ''}`.slice(0, 500)).join('\n')}`, { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA })
const criticCands = ((critic && critic.candidates) || []).map((c, i) => ({ ...c, id: `L${String(i + 1).padStart(2, '0')}`, lenses: ['completeness critic'], members: [`critic#${i + 1}`] }))
const criticVerified = await pipeline(criticCands,
  f => parallel(LENSES.map(L => () => agent(verifyPrompt(f, L), { label: `verify-${L.lens}:${f.id}`, phase: 'Critic', schema: VERDICT_SCHEMA }).then(v => v ? { lens: L.lens, ...v } : null)))
    .then(votes => ({ ...f, votes: votes.filter(Boolean), survives: votes.filter(Boolean).filter(v => !v.refuted).length >= 2 })))
const criticConfirmed = criticVerified.filter(Boolean).filter(f => f.survives)
const criticRejected = criticVerified.filter(Boolean).filter(f => !f.survives)
log(`Critic done: ${criticConfirmed.length} more confirmed, ${criticRejected.length} rejected`)

// ------------------------------------------------------------------ phase 6: judges
phase('Judge')
const allConfirmed = [...confirmed, ...criticConfirmed]
const judgeSummary = `DISPOSITION COUNTS: ${JSON.stringify(scounts)} of ${dispositions.length} known items.
ITEMS NOT RESOLVED:
${dispositions.filter(d => d.final_status !== 'resolved').map(d => `${d.id} ${d.final_status}: ${(d.residual || d.assessment).slice(0, 350)}`).join('\n')}
CONFIRMED NEW FINDINGS (${allConfirmed.length}):
${allConfirmed.map(f => `${f.id} [${f.severity}] ${f.title} -- ${f.recommendation.slice(0, 350)}`).join('\n')}
CRITIC OVERALL: ${(critic && critic.overall) || ''}`
const JUDGES = [
  { judge: 'implementer', text: 'You are the IMPLEMENTING AGENT. Could you build the parent PR from this page alone, right now, without asking anyone? Where would you stop? Judge implementability, not polish.' },
  { judge: 'maintainer', text: 'You are the tron MAINTAINER who wrote the three PR 4424 comments (read them verbatim in evidence/github-review.json). Does this design answer your review and your sketch? Would you accept the interface and the decision record? Is anything attributed to you that you did not say?' },
  { judge: 'risk', text: 'You are the RISK REVIEWER. What could go wrong if the parent is built exactly as specified: numerics (NaN, padding, conversions), object lifetime (array construction, restore), concurrency (pair writes, K lanes), CI (required lanes, evidence, caches), process (stack rules, labels, retarget order, cost records)? Weigh the confirmed findings and residuals by consequence.' },
]
const judges = await parallel(JUDGES.map(J => () => agent(`${J.text}
${COMMON}
Read the design fully. Then read the review summary below. Give: your verdict (accept as is / accept with minor edits / accept with changes / redo), whether the design is implementable now, reasons (one paragraph with citations), the top three edits in order, the must-fix list before implementation starts (may be empty), and whether the Q1-Q4 + D5 decision record is adequate.
REVIEW SUMMARY:
${judgeSummary}`, { label: `judge:${J.judge}`, phase: 'Judge', schema: JUDGE_SCHEMA }).then(v => v ? { ...v, judge: J.judge } : null)))

return {
  dispositions, dispo_batches: dispoBatches.filter(Boolean), raw, merge_dropped: (mergeRes && mergeRes.dropped) || [], merged,
  confirmed: allConfirmed, rejected: [...rejected, ...criticRejected],
  critic_overall: (critic && critic.overall) || '', critic_strengths: (critic && critic.strengths) || [], critic_disputes: (critic && critic.disputes) || [],
  judges: judges.filter(Boolean),
}