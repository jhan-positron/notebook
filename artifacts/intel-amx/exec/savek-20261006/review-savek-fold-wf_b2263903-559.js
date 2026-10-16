export const meta = {
  name: 'review-savek-fold',
  description: 'Review the fold of save_k_helper into save_k(worker_ix) on branch jhan-amx-vnniK-savek-worker from five lenses, then adversarially verify every finding',
  phases: [
    { title: 'Find', detail: 'five lenses over commit 19ae84d95a' },
    { title: 'Verify', detail: 'two refuters per finding' },
    { title: 'Synthesize', detail: 'one ranked list' },
  ],
}

const W = '/home/jhan/workspace/ai-runs/tron-vnnik-savek'
const COMMIT = '19ae84d95ac484b209197df9af378c366a02b222'
const BASE = '30c4ac82cbb6959f7e4f66b29efb36f5e0749b48'

const CONTEXT = `
Repository worktree: ${W} (git worktree of positron-ai/tron; branch jhan-amx-vnniK-savek-worker).
Commit under review: ${COMMIT} (one commit on top of ${BASE} = PR #4424 head "VNNI K", branch jhan-amx-vnniK).
Show it with: git -C ${W} show ${COMMIT}   (do not modify any file; this is a read-only review).
What the commit does: PR #4424 had two functions, save_k (main thread) and save_k_helper (main helpers) for the
shared K store window (Note [Shared block save] in h/tron/models/model.hpp). Reviewer bgamari asked
(discussion r4065141577): "Why do we need to introduce a new function for this? Why not simply extend save_k itself
with a worker_ix argument and call it consistently from both the main thread and the helpers?" The commit does that:
save_k(q_batch, ks, worker_ix = 0, n_workers = 1) and save_k(q_batch, operation, ks, worker_ix = 0, n_workers = 1);
save_k_impl branches on worker_ix == 0 (main: cut units, open window, claim, join, mark) vs >= 1 (helper: wait for
its window, claim, finished++, return); the generator ingest/src/TronCpp.hs emits save_k on both sides (main passes
LiteralExpr (IntLit 0), helpers pass worker_ix); ingest/test/LoopyTronSpec.hs and t/t_llama_unit.cpp updated.
Build tools are NOT available on this machine (no nix, no clang that compiles tron); reason from the source.
Return raw findings only. Each finding must name file:line, state the concrete failure (inputs/state -> wrong
behaviour) or the exact rule violated, and be something the author could act on. Do not report style preferences
without a rule. If you find nothing for your lens, return an empty list.`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
          claim: { type: 'string', description: 'one-sentence defect statement' },
          evidence: { type: 'string', description: 'the code lines or facts that show it' },
          failure: { type: 'string', description: 'concrete input/state -> wrong output, or the rule violated' },
          fix: { type: 'string' },
        },
        required: ['title', 'file', 'line', 'severity', 'claim', 'evidence', 'failure', 'fix'],
      },
    },
    notes: { type: 'string', description: 'what you checked and found correct (one paragraph)' },
  },
  required: ['findings', 'notes'],
}

const LENSES = [
  { key: 'protocol', prompt: `${CONTEXT}
LENS: concurrency protocol correctness of the unified save_k_impl in h/tron/models/model.hpp. Read the whole function,
Note [Shared block save], k_store_shared, k_store_cut_units, store_k_block, and batch::k_store_window_t in
h/tron/models/common.hpp. Compare the new control flow against the removed save_k_helper line by line (git show).
Check: every memory order (release/acquire pairs) is unchanged; a helper never reads n_units before main published it
(opened release / acquire); the helper's early return when the store is not shared; the helper never reaches the
mark/credit/latch code; main's join counts n_workers - 1 helpers and every helper that could enter increments
finished exactly once; worker_ix validity assert (0..n_workers-1) and what happens with n_workers == 0; the layout-off
build (k_vnni::layout_on false): the old helper had "if constexpr (!layout_on) return;", the new code evaluates
k_store_shared (which is constexpr-false in that case) - does any code now compile or run that must not (e.g.
helper_windows indexing) and does the helper still return at once; TRACE_EVENT("model","Save K") now also fires on
helper threads inside a shared window - is that a behaviour change that matters (perfetto trace, timing stats)?
Also check: when a helper enters with worker_ix >= helper_windows.size() can it happen (k_store_shared bounds n_workers)?` },
  { key: 'generator', prompt: `${CONTEXT}
LENS: the code generator and its tests. Read ingest/src/TronCpp.hs around runHelperStatement (AttentionStmt case),
submitAttentionOperation (saveKv), attentionRuntimeCall, kernelCall, runLaunchWorkers/runHelpMethod, and
ingest/src/Cpp.hs (how LiteralExpr (IntLit 0) and ExprLit print; how TemplateMethodCall prints its arguments; the
compactCpp helper in ingest/test/LoopyTronSpec.hs or wherever it is defined). Verify that the generated main-side
text is exactly what LoopyTronSpec now expects ("...q_batch->outer_batch,k,0,n_workers);" after compactCpp) and the
helper-side text "...q_batch->outer_batch,k,worker_ix,n_workers);". Verify Txt.count "outer_state.template save_k<"
is 2 in BOTH updated test cases (count the KV-writing operations in each test's input; a second operation that shares
the slot must emit nothing on either side). grep the whole ingest/test directory (and ingest/src) for every other
occurrence of "save_k" / "save_k_helper" / "save_v" counts or prefixes that the commit did not update (e.g. other
spec files, golden files, ingest/doc, README.*, weeder.toml, COVERAGE.md). Check the GNUmakefile Note-reference
checker (INGEST_NOTE_SOURCES, around line 41) still passes: every "Note [...]" referenced in the changed Haskell
comments must exist. Check fourmolu-style line length is not an issue for the one long list line
[Var $ asCpp $ attentionKey kvWrite, LiteralExpr (IntLit 0), ExprLit "n_workers"] (fourmolu.yaml column limit).` },
  { key: 'callers', prompt: `${CONTEXT}
LENS: every caller and overload of save_k in the repository. grep -rn "save_k" over h/ src/ t/ ingest/ (exclude
gen/ and dist-newstyle). For each call: does it still compile with the new signatures (two overloads:
<geometry, operation_ix>(q_batch, ks, worker_ix = 0, n_workers = 1) and <geometry>(q_batch, operation, ks,
worker_ix = 0, n_workers = 1))? Look for overload ambiguity or accidental matches: could a call like
save_k<geometry>(q_batch, operation, ks, N) that previously meant n_workers = N now silently mean worker_ix = N
(semantic change through positional defaults)? List every such call in the repo. Check h/tron/plugins/llama.hpp
(call around line 1024 and the pseudo-code comments at lines ~82 and ~111), t/heterogeneous_scheduler_compile.cpp,
t/t_llama_unit.cpp (both sections of the save_k TEST_CASE), and any other handwritten plugin (h/tron/plugins/*.hpp,
src/). Also check save_v for symmetry expectations in comments. Check the C++ coding guide of the repo
(doc/ or README.code-org.md or CLAUDE.md in the worktree: search for the named-literal / magic-number rule) and say
whether the defaults "= 0" / "= 1" and the comparison "worker_ix == 0" in save_k_impl need a named constant under
that guide, citing the guide text; also whether MAIN_WORKER_IX_0 in t/t_llama_unit.cpp follows the local idiom of
that test file (look at how the file names other constants).` },
  { key: 'prose', prompt: `${CONTEXT}
LENS: comments and prose of the commit, against the project's plain-English rules you were given (define terms at
first use, one claim per sentence, short sentences, no idioms) and against accuracy. Read every changed comment in
git show ${COMMIT}: Note [Shared block save] (both edited passages), the comment above save_k_impl, the comment above
the public save_k overloads, the watchdog assert message, the TronCpp.hs comments (runHelperStatement and saveKv),
the LoopyTronSpec.hs comments, and the t_llama_unit.cpp comment. For each: is every statement true of the code as it
now is (e.g. "stores its share and leaves", "the N-th window a helper enters in a pass is the N-th window main opens",
"Main is worker 0, as in kernelCall")? Are there leftover references to save_k_helper anywhere in the repo text
(grep -rn save_k_helper over the worktree excluding gen/ and dist-newstyle; include README.*, doc/, ingest/doc,
h/tron/models/common.hpp comment at the k_store_window_t declaration, h/tron/plugins/llama.hpp)? Does
batch::k_store_window_t's comment in common.hpp ("The main helpers join it from the generated run_main_help")
still describe the mechanism precisely enough, or should it now say "through save_k with worker_ix >= 1"? Is the
commit message accurate (git log -1 --format=%B ${COMMIT})? Report prose defects as 'nit' unless a statement is
false (then 'should-fix').` },
  { key: 'reviewer', prompt: `${CONTEXT}
LENS: the Wade-style and Ben-style review of this commit (you are the reviewers Wade and Ben of positron-ai/tron).
Ben's original ask: one function, called consistently from both sides. Does the commit fully satisfy that, or is
there residual asymmetry a reviewer would still flag (e.g. the main-side call in the generator passes a bare 0 where
the helper passes worker_ix; the descriptor overload runs validate_operation on helpers too; the comment says "one
function serves both sides" but save_k_impl has two code paths)? Would Ben prefer worker_ix before n_workers or a
single struct/pair? Is the TRON_ASSERT(worker_ix < n_workers) message format consistent with neighbouring asserts?
Wade's checks: tests that pin incidental values (does the LoopyTronSpec "count == 2" or the t_llama_unit
MAIN_WORKER_IX_0 pin something incidental?), test names that contradict assertions (the t_llama_unit SECTION names
and TEST_CASE name: still accurate?), duplicate coverage, unrelated hunks (is every hunk in the diff needed for the
fold? e.g. the re-wrapped Note paragraph), shared-header changes (model.hpp and TronCpp.hs are shared files: any
behaviour change for non-VNNI builds or non-AMX hosts, e.g. gpt-oss 64-dim heads where layout is off), and whether
the commit message makes claims the diff does not support. Also: is there a test that would FAIL if someone
reintroduced the asymmetry or broke the helper path (e.g. helper passed worker_ix 0 by mistake: both threads would
act as main - what happens? is that caught?). Report what a test should additionally assert, if anything.` },
]

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean', description: 'true if the finding is wrong, not actionable, or not a real problem' },
    reason: { type: 'string' },
    corrected_severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
  },
  required: ['refuted', 'reason', 'corrected_severity'],
}

phase('Find')
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  (r, l) => {
    if (!r) return []
    log(`lens ${l.key}: ${r.findings.length} findings`)
    return r.findings.slice(0, 8).map(f => ({ ...f, lens: l.key }))
  },
  fs => parallel(fs.map(f => () =>
    parallel([0, 1].map(i => () => agent(`${CONTEXT}
You are refuter ${i + 1} of 2. A reviewer (lens "${f.lens}") claims the following finding about commit ${COMMIT}.
Try hard to REFUTE it by reading the actual code (git show, the files). A finding is refuted when the claimed
failure cannot happen, the rule cited does not exist or does not apply, the code already handles it, or the
"fix" would make things worse. If the finding is real but the severity is wrong, keep refuted=false and give the
corrected severity. Default to refuted=true when you cannot confirm the failure from the code.
${i === 1 ? 'Additionally, as refuter 2, check whether the proposed fix would break any caller or test in the repo.' : ''}
FINDING:
title: ${f.title}
file:line: ${f.file}:${f.line}
severity: ${f.severity}
claim: ${f.claim}
evidence: ${f.evidence}
failure: ${f.failure}
fix: ${f.fix}`, { label: `verify:${f.lens}:${i + 1}`, phase: 'Verify', schema: VERDICT })))
      .then(vs => {
        const votes = vs.filter(Boolean)
        const survives = votes.length > 0 && votes.filter(v => !v.refuted).length === votes.length
        const sev = survives ? (votes.map(v => v.corrected_severity).includes('must-fix') ? 'must-fix' : votes.map(v => v.corrected_severity).includes('should-fix') ? 'should-fix' : 'nit') : f.severity
        return { ...f, survives, severity: sev, verdicts: votes.map(v => v.reason) }
      })))
)

const all = results.flat().filter(Boolean)
const confirmed = all.filter(f => f.survives)
const refuted = all.filter(f => !f.survives)
log(`${confirmed.length} confirmed, ${refuted.length} refuted`)

phase('Synthesize')
const synthesis = await agent(`${CONTEXT}
You are the synthesizer. Below are the CONFIRMED findings (both refuters agreed they are real) and the REFUTED ones
(at least one refuter rejected). Produce one ranked list: merge duplicates, order must-fix > should-fix > nit, and for
each give: title, file:line, the one-sentence claim, the concrete fix. Then list the refuted findings in one line each
with the refuter's reason (so the author knows what was considered). Then say in two sentences whether the commit is
ready to go to a draft PR after the must-fix/should-fix items are applied. Plain English, no idioms.
CONFIRMED: ${JSON.stringify(confirmed, null, 1)}
REFUTED: ${JSON.stringify(refuted.map(f => ({ title: f.title, file: f.file, line: f.line, lens: f.lens, verdicts: f.verdicts })), null, 1)}`,
  { label: 'synthesize', phase: 'Synthesize' })

return { confirmed, refuted: refuted.map(f => ({ title: f.title, file: f.file, line: f.line, verdicts: f.verdicts })), synthesis }