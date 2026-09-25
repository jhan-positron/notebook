export const meta = {
  name: 'review-distilled-shared-save-page',
  description: 'Fact-check, faithfulness-check, plain-English-check and completeness-check the distilled shared-save page, then adversarially verify every finding with three skeptics',
  phases: [
    { title: 'Find', detail: 'six lenses over the distilled page against the full page, the code and the data' },
    { title: 'Verify', detail: 'three skeptics per finding, majority survives' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/154f65b5-9b50-4d8d-9e68-26b5f8c7d229/scratchpad'
const ROOT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place'
const CONTEXT = `
CONTEXT (read before anything else).
- Page under review (the DISTILLED page): ${ROOT}/status/shared-save-animation-distilled.html. Its visible text, extracted: ${SP}/distilled-text.txt (about 2990 visible words; the hard limit is 3000 visible words including SVG labels, counted by stripping tags; any fix you propose must be word-neutral or shorter, and you must say the word delta of your fix).
- Source it distils (the FULL page, revision 5, reviewed twice already and treated as ground truth unless the code or data contradict it): ${ROOT}/status/shared-save-animation.html. Its visible text, extracted: ${SP}/source-text.txt.
- Generators: ${ROOT}/exec/shared-save-animation/gen_distilled.py (the distilled page), gen_page.py and context_sections.py (the full page; the distilled generator imports both and reuses their data, SVGs and animation script).
- Code (tron worktree at commit 30c4ac82cb, the PR 4424 head): ${ROOT}/tron-VNNIed-K. Files cited: h/tron/models/model.hpp, h/tron/models/common.hpp, h/tron/models/kv_cache.hpp, h/tron/models/self_attention.hpp, h/tron/kernels/k_vnni.hpp, ingest/src/TronCpp.hs, t/t_llama_unit.cpp, h/tron/gof.hpp.
- Data: /home/jhan/workspace/intel-AMX/exec/results/vnnik2-trace-20260915/analysis.json and *.lanes.json; /home/jhan/workspace/intel-AMX/exec/results/vnnik-trace-20260914/; /home/jhan/workspace/intel-AMX/exec/results/vnnik2-20260915/summary.json (TTFT cells); ${ROOT}/exec/shared-save-animation/layout.json, units.json, savek_spans.json.
- The report the pages accompany: ${ROOT}/status/store-remedies-report.html.
- Known, intentional facts: the tp4 PREFILL split is main + 15 helpers + 40 attention workers (a decode pass has 8 + 47); the distilled page keeps the full page's section numbers (1..8) and skips 2.1 as a heading; the animation script is byte-identical to the full page's; the legend labels are h1..h15 instead of "helper N".
- Plain-English rules (the user's standard, applied to every page): define a term at first use (code names, acronyms, metrics), one claim per sentence, numbers with units and a plain meaning, citations follow a sentence in brackets, a "Short version" at the top, no idioms or metaphors, bullets for multi-point paragraphs, short sentences, no semicolons inside a sentence. A term defined once in the page (glossary or inline) needs no redefinition.
Return ONLY findings you have checked against the named source. Quote the exact distilled sentence or cell, name the source you checked (file, line or JSON key), state the defect in one sentence, and give a replacement text that keeps or lowers the word count. Do not report style preferences that are not rule violations. Do not report things that are correct but different from the full page's wording when the meaning is preserved.
`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string', description: 'section and exact quote of the distilled text' },
          claim: { type: 'string', description: 'what is wrong, one sentence' },
          evidence: { type: 'string', description: 'the source checked: file:line, JSON key, or full-page sentence' },
          fix: { type: 'string', description: 'replacement text, word-neutral or shorter' },
          word_delta: { type: 'integer', description: 'words added (positive) or removed (negative) by the fix' },
          severity: { type: 'string', enum: ['wrong-fact', 'misleading', 'rule-violation', 'missing', 'minor'] },
        },
        required: ['where', 'claim', 'evidence', 'fix', 'word_delta', 'severity'],
      },
    },
    checked: { type: 'string', description: 'what you checked and found correct, in a few lines' },
  },
  required: ['findings', 'checked'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean', description: 'true if the finding is wrong, not a real defect, or its fix is worse than the original' },
    reason: { type: 'string' },
    better_fix: { type: 'string', description: 'optional: a corrected replacement text if the finding is real but the proposed fix has a problem; empty otherwise' },
  },
  required: ['refuted', 'reason', 'better_fix'],
}

const LENSES = [
  { key: 'numbers', prompt: `${CONTEXT}\nLENS: NUMBERS. Check EVERY number in the distilled page (prose, glossary, tables, SVG labels are reused from the full page and need no check) against the full page text and, where the full page cites a data file, against that file: Save K spans, factors (2.48x etc.), TTFT differences (37, 100, 4, 22 ms), pass lengths (30.9 ms of 401 ms, 7.7%, 2.9 ms, 0.7%), lane milestones (2.4 us, 4051 us, 853 us, 0.2 us, 762 us, 771 us, 44 us, 6 us), thread counts, struct offsets (layout.json), unit costs, simulated lengths, trace means and sds, gaps, the 288 spans, 8192 rows, 2 MiB, 16 pages, 72/80 fetch_adds, 16 invalidations, unit_start list of the test. Also check that every number carries a unit or a plain meaning. Report at most 12 findings, the most important first.` },
  { key: 'code', prompt: `${CONTEXT}\nLENS: CODE CLAIMS. Check every function name, file:line citation and behavioural claim of the distilled page against the tron worktree at ${ROOT}/tron-VNNIed-K (commit 30c4ac82cb): save_k_impl, save_k_helper, store_k_block, k_store_cut_units, k_store_shared, k_store_window_t (alignas, field order), the sharing conditions (layout_on, n_workers range, items > 16), the watchdog (120 s), the latch (kvs_needed = 2, count_down from save_k and save_v), mark_k_complete readers, the statement order in TronCpp.hs (saveKv, runHelperStatement), the unit test line ranges in t/t_llama_unit.cpp (2572-2815, 2765-2810, expected unit_start list), is_dense_amx_page, the helper-count rule (model.hpp:1933-1935, 1950-1960, 1976-1982). Use grep -n and sed -n on the files. Report at most 12 findings.` },
  { key: 'faithful', prompt: `${CONTEXT}\nLENS: FAITHFULNESS. Compare each distilled sentence with the full page's corresponding sentence(s) in ${SP}/source-text.txt. Find: (a) claims that are stronger than the source (a model or est. or hypothesis presented as measured, "must" turned into "does", a single traced layer presented as a mean), (b) qualifiers lost in compression that change the meaning (which configuration, which tp, which chart, before vs after), (c) sentences that merge two facts into a wrong causal link, (d) new claims that the full page does not make, (e) label words (mock, est., model, hypothesis, measured) used differently than the full page's glossary defines them. Report at most 12 findings.` },
  { key: 'english', prompt: `${CONTEXT}\nLENS: PLAIN ENGLISH. Apply the user's rules to the distilled page as its own document (a term defined in its glossary or inline earlier on the page counts as defined): undefined terms or acronyms at first use (for example GOF, TTFT, AVX-512, AMX, FPGA, KV head, rope, ingest, minibatch, latch, alignas, fetch_add, sd), sentences with two claims, numbers without units or meaning, a citation standing alone as a sentence, idioms or metaphors, paragraphs carrying several points without bullets, sentences with more than one subordinate clause, semicolons inside sentences (table cells that list citations are fine), and a missing or over-long Short version (at most three sentences). Also check that "prompt 1024" style is used, never "ctx 1024". Report at most 12 findings, each with a fix that does not add more than 3 words (the page is at the word limit); if a term needs a definition, propose the shortest one or a place to fold it into an existing glossary row.` },
  { key: 'complete', prompt: `${CONTEXT}\nLENS: COMPLETENESS. The distilled page must let a reader who never saw the full page understand the shared block save: what it is, where it sits in a prefill layer, who does what, what it reads and writes, how it relates to the block store, what was measured, what the animation shows, what is model/est./mock, and what is still unknown. Read the full page text and list the facts a first-time reader needs that the distilled page dropped or garbled. For each, say why it matters and propose the shortest sentence that carries it AND name what to remove elsewhere to pay for it (the page is 2990 of 3000 words). Also flag anything on the distilled page that a first-time reader does not need (candidates to cut). Report at most 10 findings.` },
  { key: 'script', prompt: `${CONTEXT}\nLENS: ANIMATION SCRIPT AND PAGE MECHANICS. The animation script in the distilled page is byte-identical to the full page's. Check that the distilled DOM gives it everything it needs: every getElementById id, the select option values ('ab','b','tp2','tp4', speeds), the button ids, the status and selfcheck elements, CSS classes the script sets (read gen_page.py CSS and JS: which class names does the JS emit, are they all defined in the CSS the distilled page includes?), the legend (the JS may or may not write it), keyboard handlers, the __SIM_LENGTHS__ self-check. Also check that the two static SVGs are complete and that the page has no non-ASCII characters, a <title>, a viewport meta, light background. Check the header claims (revision 5, about 16,600 words, generated by gen_distilled.py) against the full page and the generator. Report at most 8 findings.` },
]

phase('Find')
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS_SCHEMA }),
  (found, l) => {
    if (!found) { log(`finder ${l.key} returned nothing`); return [] }
    log(`finder ${l.key}: ${found.findings.length} findings`)
    return parallel(found.findings.map(f => () =>
      parallel(['re-read the cited source and the full page: is the claim actually true, and is the quoted text really on the distilled page?',
                'is this a real defect under the stated rules, or a style preference or a difference that preserves meaning? Default to refuted if it is not a defect.',
                'is the proposed fix correct, ASCII, plain English, within its stated word delta, and not introducing a new error? Refute if the fix is worse than the original.'].map((angle, i) => () =>
        agent(`${CONTEXT}\nYou are skeptic ${i + 1} of 3 for one review finding about the distilled page. Your angle: ${angle}\nFINDING (lens ${l.key}):\n${JSON.stringify(f, null, 2)}\nCheck it against the files. Default to refuted=true if you are uncertain. If the finding is real but the fix has a problem, give better_fix.`,
          { label: `verify:${l.key}:${i + 1}`, phase: 'Verify', schema: VERDICT_SCHEMA })))
        .then(votes => {
          const vs = votes.filter(Boolean)
          const refutes = vs.filter(v => v.refuted).length
          const survives = vs.length > 0 && refutes * 2 < vs.length
          return { lens: l.key, ...f, survives, votes: vs }
        })
    )).then(list => list.filter(Boolean))
  }
)

const all = results.flat().filter(Boolean)
const confirmed = all.filter(x => x.survives)
const dropped = all.filter(x => !x.survives)
log(`${confirmed.length} confirmed of ${all.length} findings`)
return { confirmed, dropped: dropped.map(d => ({ lens: d.lens, where: d.where, claim: d.claim, reasons: d.votes.map(v => v.reason) })) }
