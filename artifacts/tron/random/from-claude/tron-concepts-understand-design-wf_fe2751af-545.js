export const meta = {
  name: 'tron-concepts-understand-design',
  description: 'Read TRON source for 5 attention concepts, synthesize a concept map, then judge-panel a page design',
  phases: [
    { title: 'Read', detail: '7 readers, one per TRON subsystem, citation-grounded' },
    { title: 'Synthesize', detail: 'merge into one hierarchy + timeline + mock scenario' },
    { title: 'Design', detail: '3 independent page designs from different angles' },
    { title: 'Judge', detail: '2 judges with distinct lenses score the designs' },
  ],
}

const TRON = '/home/jhan/workspace/tron'

const CITE = { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, quote: { type: 'string' } }, required: ['file', 'line', 'quote'] }

const READER_SCHEMA = {
  type: 'object',
  properties: {
    subsystem: { type: 'string' },
    concepts: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' },
      plain_definition: { type: 'string', description: 'one or two short sentences a newcomer can follow' },
      code_identifiers: { type: 'array', items: { type: 'string' } },
      parent_concept: { type: 'string', description: 'the bigger concept that owns this one' },
      child_concepts: { type: 'array', items: { type: 'string' } },
      lifecycle_stage: { type: 'string', description: 'when it exists: persistent-across-passes | request-arrival | token-tree-build | traversal | forward-setup | layer-loop | attention-kernel | join | sampling' },
      citations: { type: 'array', items: CITE },
    }, required: ['name', 'plain_definition', 'code_identifiers', 'parent_concept', 'lifecycle_stage', 'citations'] } },
    relationships: { type: 'array', items: { type: 'object', properties: {
      from: { type: 'string' }, to: { type: 'string' },
      relation: { type: 'string', description: 'short verb phrase, e.g. "is partitioned into", "is checked inside", "restricts"' },
      explanation: { type: 'string' },
      citations: { type: 'array', items: CITE },
    }, required: ['from', 'to', 'relation', 'explanation', 'citations'] } },
    numbers: { type: 'array', items: { type: 'object', properties: {
      what: { type: 'string' }, value: { type: 'string' }, unit: { type: 'string' }, meaning: { type: 'string' }, citation: CITE,
    }, required: ['what', 'value', 'unit', 'citation'] } },
    sequence: { type: 'array', items: { type: 'object', properties: {
      step: { type: 'integer' }, what_happens: { type: 'string' }, concepts_involved: { type: 'array', items: { type: 'string' } }, citation: CITE,
    }, required: ['step', 'what_happens', 'concepts_involved', 'citation'] } },
    mock_data_ideas: { type: 'array', items: { type: 'string' } },
    unclear: { type: 'array', items: { type: 'string' } },
  },
  required: ['subsystem', 'concepts', 'relationships', 'numbers', 'sequence', 'unclear'],
}

const PREAMBLE = `You are reading the TRON inference engine source at ${TRON} (git main, commit 9b11a912ba, 2026-09-08). TRON runs LLMs on Positron FPGA hardware plus host CPU.
STRICTLY READ-ONLY: do not edit files, do not build, do not run any binary, test, or workload. Use grep, sed -n, cat, and Read only.

Purpose: a page that gives an engineer an intuitive, holistic picture of how these five concepts fit together in TRON:
  1. attention (the Q.K softmax P.V computation and how TRON splits it into work)
  2. KV cache page (fixed-size block of K/V entries; book; kv_pages[])
  3. sliding window (layer attends only to the most recent N tokens)
  4. visible range of K/V (ranged mask: token_range with visible(job_ix), SW_REQUIRED, HW_AVAILABLE)
  5. minibatch (q_batch / minibatch_size: grouping of queries inside one forward pass)
The user knows attention and KV cache well. They want: (a) relationships between the five, (b) the PARENT and GRANDPARENT concepts that own them (token tree, traversal, forward pass, scheduler, layer, etc.) so relationships can be explained through the parents, (c) sequencing/timing: which concepts exist at the same time and which only exist during one stage of a forward pass, (d) clarity on the individually unclear ones: sliding window, visible range, minibatch.

Start with ${TRON}/doc/attention-glossary.md (canonical terms; reuse its wording). Then read your assigned files. Follow references into other files when needed to answer your questions.

Rules for your report:
- Every concept, relationship, number, and sequence step MUST carry at least one citation with file path (relative to ${TRON}), line number, and a short verbatim quote. Verify line numbers with grep -n or sed -n; do not guess.
- Report defaults, constants, and limits with units and a one-clause meaning.
- Distinguish "what the code does today" from "what a doc says is planned" (say which).
- If two sources disagree, report both with citations.
- Put anything you could not confirm in "unclear" instead of guessing.
- Plain English: short sentences, one claim per sentence, define code names on first use.
Return the structured report only.`

const READERS = [
  { key: 'attention-kernel', focus: `ASSIGNMENT: the software attention kernel and its work split.
Files: h/tron/models/self_attention.hpp (all of it; especially lines ~1250-1450 where visible(), page_begin_hint, sliding_window_size, run_visible_in_software appear), doc/how_to_customize_cpu_attention.md, doc/attention-scheduling.md, doc/explicit-attention-operations.md, doc/hw-kv-attn-work.md.
Questions: How is one query's attention over the KV pages computed in software? What are kv_section, attention worker, scratchpad, join_work, vo_from_attn, qs_for_attn, and how do they partition the work? Exactly where in the kernel loop are (i) page.count()/lo used, (ii) the ranged-mask visible() check applied (page-level gate vs per-entry), (iii) the sliding window applied? Which of these buffers or schedules are per-minibatch (q_batch)? What is the online-softmax / partial-max merge scheme across workers?` },
  { key: 'kv-pages-token-tree', focus: `ASSIGNMENT: KV cache pages, books, and the token tree that owns them.
Files: h/tron/models/kv_cache.hpp, h/tron/scheduler/token_tree.hpp, doc/hw-kv-token-tree.md, doc/token_tree_v2.md, doc/hw-kv-design.md, and page-related parts of doc/pos_heap_v2.md and doc/memory_pressure_governor.md.
Questions: What exactly is a page (page_size default and where set; what one entry holds; per layer/head layout; bytes if derivable)? What is a book? What are lo, offset_bound, count(), and how do they define the live entries of a page in a pass? How are pages attached to token-tree nodes, and how do shared prefixes share pages? How is kv_pages[] ordered and built? Which of these persist across forward passes and which are rebuilt every pass? How are pages freed or evicted (briefly)? How does a page relate to token_id vs token_job_id?` },
  { key: 'ranged-mask-visibility', focus: `ASSIGNMENT: the ranged mask, i.e. the "visible range of K/V" for each query.
Files: h/tron/models/ranged_mask.hpp, src/tron/models/ranged_mask.cpp, doc/hw-kv-ranged-mask.md, doc/golden-ranged-mask.md, h/tron/plugins/mock.hpp (reference attention using visible()), and build_edge_ranges / compute_forward_args in h/tron/scheduler/full.hpp.
Questions: Define token_range [tok_lo, tok_hi), visible(job_ix), SW_REQUIRED, HW_AVAILABLE, mask bit = token_job_id, max mask width. How does the ranged mask encode causality (a query sees only earlier tokens) AND tree-branch separation (a query does not see a sibling branch)? Walk through how, for one query, the set of KV token indices it may attend to is derived from the ranges. How does this relate to pages (page-level gate page_begin_hint->visible vs per-entry range_hint)? How does it combine with the sliding window? Give a tiny worked example (e.g., 2 branches, 3 queries) with the resulting ranges and masks, citing the doc example if one exists.` },
  { key: 'sliding-window', focus: `ASSIGNMENT: sliding window attention in TRON.
Start with: grep -n -i sliding in h/tron/models/model.hpp, h/tron/models/self_attention.hpp, h/tron/models/kv_cache.hpp, h/tron/models/ranged_mask.hpp, h/tron/models/config.hpp, h/rinzler/model-metadata.hpp, src/tron/gof.cpp, h/libpos.hpp, and h/tron/plugins/*.hpp; also grep for sliding_window in ingest/ and config/ to find which models use it and typical window sizes.
Questions: What is the parent concept of sliding window (per-layer attention type? model config field? layer pattern like "every Nth layer is full attention")? Where is sliding_window_size configured and what values appear for real models? How is it enforced: in the kernel per KV entry, at page level, or by trimming kv_pages? Confirm or refute the glossary claim "All pages stay in kv_pages; the window constraint is applied in the kernel." How does it interact with the ranged mask visible() (union of both masks?), with HW offload (run_visible_in_software), and with the model.hpp code near line 2416 ("older than sliding_window_size for every visible item")? Does the window count tokens by token_id position, by tree depth, or by something else? Any memory saving today, or is that planned only?` },
  { key: 'minibatch-forward', focus: `ASSIGNMENT: minibatch (q_batch) and the forward function that creates it.
Files: h/tron/models/model.hpp (grep -n -i minibatch; read forward() and the q_batch construction), h/tron/models/common.hpp, h/tron/models/config.hpp, h/tron/plugins/llama.hpp, h/tron/plugins/mock.hpp, h/tron/gof.hpp, h/runtron/stream_generate.hpp, and the CLI flag handling in src/runtron.cpp and src/rinzler.cpp.
Questions: What does "minibatch" mean in TRON (it is NOT the training-time minibatch: say precisely what is grouped)? What is minibatch_size, its default, its CLI flag, and its unit (queries? tokens? requests?)? What is the relationship between minibatch, q_batch, items[], token_job_id, and token_jobs[]? Why does TRON split queries into minibatches (buffer sizing, parallel software attention, matmul shape, cache footprint)? When is minibatching disabled (HW offload puts all queries in one batch?) and why? Does a minibatch cross request boundaries (can queries from different requests share one minibatch)? Are the non-attention layers (matmuls, MLP) also run per minibatch or on all queries at once?` },
  { key: 'lifecycle-scheduler', focus: `ASSIGNMENT: the end-to-end sequence of one forward pass, so the page can show WHEN each concept exists.
Files: h/tron/scheduler/full.hpp (compute_forward_args and how a pass is assembled from requests), doc/hw-kv-sched.md, doc/hw-kv-sched-detailed.md, doc/tron_design_document.md, doc/attention-scheduling.md, h/runtron/stream_generate.hpp, h/tron/scheduler/token_tree.hpp.
Questions: Produce the ordered sequence: request arrives -> tokens inserted into token tree -> traversal (DFS) builds tokens[], token_jobs[], kv_pages[], ranged mask, sets lo/offset_bound -> forward() groups queries into minibatches -> per layer: QKV projection, KV write into pages, attention (SW workers / HW), join -> MLP -> logits -> sampling -> tree grows -> next pass. For each step name the concepts created, consumed, or destroyed. Classify each concept as persistent-across-passes (token tree, pages, books) or per-pass (ranged mask, token_jobs, minibatches, schedules). How do prefill (many new tokens) and decode (one new token per request) differ in the sizes of these structures? How many requests share one forward pass?` },
  { key: 'hw-attention-offload', focus: `ASSIGNMENT: FPGA (hardware) attention offload, only as far as it touches pages, masks, sliding window, and minibatch.
Files: h/pos/hwattention.hpp, doc/hw_attention.md, doc/hw-kv-design.md, doc/hw-kv-rules.md, doc/hw-kv-examples.md, doc/shard_based_hw_attention_api.md, and the HW branches in h/tron/models/self_attention.hpp and h/tron/models/model.hpp.
Questions: How does the hardware consume KV pages (page list, page_size constraints, head size constraints)? What do HW_AVAILABLE vs SW_REQUIRED mean operationally: which queries/ranges go to FPGA and which stay on CPU, and why can a range be SW-only (tree branching? sliding window? too-recent tokens still being written)? Why is q_batch/minibatching disabled when HW offload is active? How is a sliding-window layer handled with HW (run_visible_in_software)? What is the shard concept and is it live today or a stub? Keep to what relates to the five target concepts.` },
]

phase('Read')
log('Reading 7 TRON subsystems in parallel')
const reports = (await parallel(READERS.map(r => () =>
  agent(`${PREAMBLE}\n\n${r.focus}`, { label: `read:${r.key}`, phase: 'Read', schema: READER_SCHEMA })
))).filter(Boolean)
log(`${reports.length}/7 reader reports returned`)

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    words_used_here: { type: 'array', items: { type: 'object', properties: { term: { type: 'string' }, definition: { type: 'string' }, code_identifier: { type: 'string' } }, required: ['term', 'definition'] } },
    hierarchy: { type: 'array', description: 'concept tree, one row per concept, parent named; roots have parent ""', items: { type: 'object', properties: {
      concept: { type: 'string' }, parent: { type: 'string' }, level: { type: 'integer' }, one_line: { type: 'string' }, is_target: { type: 'boolean' }, citations: { type: 'array', items: CITE },
    }, required: ['concept', 'parent', 'level', 'one_line', 'is_target', 'citations'] } },
    target_relationships: { type: 'array', description: 'every pair among the 5 targets plus each target to its parent', items: { type: 'object', properties: {
      a: { type: 'string' }, b: { type: 'string' }, relation: { type: 'string' }, through_parent: { type: 'string', description: 'the parent concept the relation goes through, or ""' }, explanation: { type: 'string' }, citations: { type: 'array', items: CITE },
    }, required: ['a', 'b', 'relation', 'through_parent', 'explanation', 'citations'] } },
    timeline: { type: 'array', items: { type: 'object', properties: {
      step: { type: 'integer' }, stage: { type: 'string' }, what_happens: { type: 'string' }, concepts_alive: { type: 'array', items: { type: 'string' } }, concepts_created: { type: 'array', items: { type: 'string' } }, concepts_destroyed: { type: 'array', items: { type: 'string' } }, citations: { type: 'array', items: CITE },
    }, required: ['step', 'stage', 'what_happens', 'concepts_alive', 'concepts_created', 'concepts_destroyed', 'citations'] } },
    persistence: { type: 'array', items: { type: 'object', properties: { concept: { type: 'string' }, lifetime: { type: 'string', description: 'persistent-across-passes | per-forward-pass | per-layer | per-minibatch | per-worker' }, citations: { type: 'array', items: CITE } }, required: ['concept', 'lifetime', 'citations'] } },
    numbers: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, value: { type: 'string' }, unit: { type: 'string' }, meaning: { type: 'string' }, citation: CITE }, required: ['what', 'value', 'unit', 'citation'] } },
    mock_scenario: { type: 'object', description: 'ONE concrete small scenario every diagram on the page will share', properties: {
      description: { type: 'string' },
      page_size: { type: 'integer' }, sliding_window_size: { type: 'integer' }, minibatch_size: { type: 'integer' },
      requests: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, tokens: { type: 'string' }, shares_prefix_with: { type: 'string' } }, required: ['name', 'tokens'] } },
      token_ids: { type: 'string', description: 'the flattened tokens[] with which token_id each token gets' },
      token_jobs: { type: 'string', description: 'which token_ids are queries this pass and their token_job_id' },
      pages: { type: 'string', description: 'which token_ids land on which page, with lo and count' },
      ranges: { type: 'string', description: 'the resulting token_ranges with masks' },
      minibatches: { type: 'string' },
      sliding_window_effect: { type: 'string' },
      caveats: { type: 'array', items: { type: 'string' }, description: 'where the mock simplifies real TRON' },
    }, required: ['description', 'page_size', 'sliding_window_size', 'minibatch_size', 'requests', 'token_ids', 'token_jobs', 'pages', 'ranges', 'minibatches', 'sliding_window_effect', 'caveats'] },
    clarifications: { type: 'array', description: 'for sliding window, visible range, minibatch: the single most important thing a confused engineer is probably getting wrong', items: { type: 'object', properties: { concept: { type: 'string' }, common_confusion: { type: 'string' }, correct_picture: { type: 'string' }, citations: { type: 'array', items: CITE } }, required: ['concept', 'common_confusion', 'correct_picture', 'citations'] } },
    conflicts: { type: 'array', items: { type: 'string' } },
    unresolved: { type: 'array', items: { type: 'string' } },
  },
  required: ['words_used_here', 'hierarchy', 'target_relationships', 'timeline', 'persistence', 'numbers', 'mock_scenario', 'clarifications', 'conflicts', 'unresolved'],
}

phase('Synthesize')
const synthesis = await agent(`You are synthesizing 7 citation-grounded reader reports about the TRON inference engine (source at ${TRON}, READ-ONLY: you may open files to check a citation or resolve a conflict, but do not edit, build, or run anything).

Target concepts the final page must relate: attention, KV cache page, sliding window, visible range of K/V (ranged mask), minibatch (q_batch).
The user's questions: (1) how do the five relate; (2) which bigger parent/grandparent concepts own them, so relationships can be explained through those parents; (3) sequencing/timing: which concepts co-exist and which exist only during one stage; (4) make sliding window, visible range, and minibatch individually clear.

Do:
- Build ONE concept hierarchy (tree). Include parents and grandparents: e.g. request/scheduler -> token tree -> traversal -> forward pass -> layer -> attention -> ...; KV cache -> book -> page -> kv entry; ranged mask -> token_range -> masks. Mark the 5 targets.
- Give every pairwise relationship among the 5 targets and name the parent concept the relationship goes through.
- Build the lifecycle timeline of one forward pass with created/alive/destroyed concepts per step, and a persistence table.
- Collect all numbers (defaults, limits) with units and meaning; keep only cited ones.
- Design ONE small mock scenario that every diagram on the page will share. Requirements: 2 requests that share a system-prompt prefix and then diverge (so the token tree has a branch); a small page_size (e.g. 4) so pages are visible; a sliding window smaller than the context (e.g. 6) so the window visibly cuts old tokens; a minibatch_size small enough (e.g. 2 or 3) that queries split into 2+ minibatches; a mix of prefill (several new tokens) and decode (one new token). Work out concretely: tokens[] with token_ids, token_jobs with token_job_ids, pages with lo/count, the ranged mask token_ranges with SW/HW masks as bit strings, minibatches, and which KV entries each query sees with and without the sliding window. Make it internally consistent with the cited TRON rules. List where the mock simplifies reality.
- For sliding window, visible range, and minibatch: state the most likely misconception and the correct picture, with citations.
- Where readers disagree, resolve by opening the source; otherwise record the conflict.
- Keep the glossary's wording where it exists. Plain English: short sentences, one claim per sentence, define code names on first use.

READER REPORTS (JSON):
${JSON.stringify(reports)}`, { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, effort: 'max' })

if (!synthesis) throw new Error('synthesis returned null')
log(`synthesis: ${synthesis.hierarchy.length} concepts, ${synthesis.target_relationships.length} relationships, ${synthesis.timeline.length} timeline steps`)

const BRIEF = `# motivation
I know the following TRON and LLM concepts individually, but I do not have a holistic intuition fitting them all together. E.g.:
- what are their relationship?
- maybe there are some bigger scoped concepts which own them individually, and the relationship are at or through those parent concepts. If so, please include the parent, grand parent concepts
- maybe the concepts do not co-exist at the same time. If so, what are their relationship at the context of sequencing or timing?
- some concepts are not clear to me even individually
I am looking for some intuitive illustration to help clarifying, and more important, help internalizing.
# concepts
- attention: I know attention well, I am looking for its relationship with other concepts
- KV cache page: I know attention well, I am looking for its relationship with other concepts
- sliding window: what are its parent concepts
- visible range of K/V
- minibatch
# output
Generate TRON-concepts-claude.html. Use plain-english skill to check verbose. Use diagrams, animations, mock data. Generate table of concept at top. Include this prompt file content.`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    angle: { type: 'string' },
    page_title: { type: 'string' },
    short_version: { type: 'string', description: 'at most 3 sentences a newcomer can follow' },
    sections: { type: 'array', items: { type: 'object', properties: {
      order: { type: 'integer' }, heading: { type: 'string' }, purpose: { type: 'string' },
      prose_points: { type: 'array', items: { type: 'string' } },
      diagram: { type: 'object', properties: {
        type: { type: 'string', description: 'e.g. nested-boxes hierarchy, timeline lanes, grid of pages, bitmask table, animated stepper, small multiples' },
        what_it_shows: { type: 'string' },
        mock_data_used: { type: 'string' },
        annotations: { type: 'array', items: { type: 'string' }, description: 'direct labels / callouts drawn on the figure' },
        takeaway_line: { type: 'string', description: 'one line under the figure' },
        animation: { type: 'string', description: 'what moves, what the controls are, or "none"' },
        implementation_notes: { type: 'string', description: 'inline SVG / CSS / vanilla JS approach; keep single-file' },
      }, required: ['type', 'what_it_shows', 'mock_data_used', 'annotations', 'takeaway_line', 'animation', 'implementation_notes'] },
    }, required: ['order', 'heading', 'purpose', 'prose_points', 'diagram'] } },
    concept_table_columns: { type: 'array', items: { type: 'string' } },
    concept_table_rows: { type: 'array', items: { type: 'object', properties: { concept: { type: 'string' }, cells: { type: 'array', items: { type: 'string' } } }, required: ['concept', 'cells'] } },
    why_this_helps_internalize: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['angle', 'page_title', 'short_version', 'sections', 'concept_table_columns', 'concept_table_rows', 'why_this_helps_internalize', 'risks'],
}

const ANGLES = [
  { key: 'hierarchy-first', text: 'HIERARCHY-FIRST: lead with the parent/grandparent ownership tree (nested boxes or an indented tree), then explain each pairwise relationship by walking up to the shared parent. The reader should be able to answer "who owns what" from one figure.' },
  { key: 'timeline-first', text: 'TIMELINE-FIRST: lead with the lifecycle of one forward pass as horizontal lanes (one lane per concept; a bar shows when the concept exists; persistent concepts span all passes, per-pass concepts appear and vanish). Use the "wall-clock lanes" idea: solid = exists/working, dashed = waiting. Then explain relationships as "created by / consumed by" edges along the timeline.' },
  { key: 'worked-example-first', text: 'WORKED-EXAMPLE-FIRST: lead with ONE concrete mock conversation (two requests sharing a prefix) and drive an animated stepper through it: tokens arrive -> token tree -> pages fill -> traversal assigns token_job_ids -> ranged mask ranges -> minibatches -> attention with/without sliding window. Every concept is introduced at the moment it appears in the example. The reader learns by watching the same 12 tokens move through every structure.' },
]

phase('Design')
const designs = (await parallel(ANGLES.map(a => () =>
  agent(`You are designing a single-file HTML teaching page (inline SVG + CSS + vanilla JS, no build step, LIGHT theme only) that helps a TRON engineer internalize how five attention-related concepts fit together. You are NOT writing the HTML. You are producing a detailed page design that another author will implement.

USER BRIEF:
${BRIEF}

YOUR ASSIGNED ANGLE: ${a.text}

HARD REQUIREMENTS from the user and their house rules:
- A table of concepts at the TOP of the page (columns your choice, but include: concept, plain definition, parent, when it exists, key code identifier).
- Use diagrams, animations, and the shared mock scenario below. Every diagram must use the SAME mock scenario so the reader tracks one example across all figures.
- Every chart or diagram: direct labels on the data, the key point annotated on the figure, a one-line takeaway under it. Draw tiny things tiny (to-scale where sizes matter).
- Plain English: short sentences, one claim per sentence, every code name defined at first use, numbers with units and meaning, no idioms/metaphors.
- Start with a "Short version" of at most three sentences.
- Must answer the user's four questions: relationships; parents/grandparents and relationships THROUGH parents; co-existence/sequencing in time; make sliding window, visible range, and minibatch individually clear.
- Each of the 5 target concepts should get its own explanatory section or panel; the hard ones (sliding window, visible range of K/V, minibatch) need a "common confusion vs correct picture" callout.
- Aim for 6 to 9 sections. Each section: purpose, prose points, one primary diagram spec (with what animates and how the user controls it), takeaway line.
- Feasibility: everything must be buildable as inline SVG/CSS/JS in one file without external libraries.

SYNTHESIZED CONCEPT MAP (ground truth; do not invent facts beyond it; if you need a fact it lacks, say so in risks):
${JSON.stringify(synthesis)}

Return the structured design only.`, { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA })
))).filter(Boolean)
log(`${designs.length}/3 designs returned`)

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    scores: { type: 'array', items: { type: 'object', properties: {
      design_index: { type: 'integer' }, angle: { type: 'string' },
      internalization: { type: 'integer', description: '0-10: will a confused engineer come away with a durable mental model' },
      answers_four_questions: { type: 'integer', description: '0-10' },
      accuracy_vs_synthesis: { type: 'integer', description: '0-10: no claims beyond the concept map' },
      feasibility: { type: 'integer', description: '0-10: buildable as single-file inline SVG/CSS/JS' },
      total: { type: 'integer' },
      strongest_sections: { type: 'array', items: { type: 'string' } },
      weakest_points: { type: 'array', items: { type: 'string' } },
    }, required: ['design_index', 'angle', 'internalization', 'answers_four_questions', 'accuracy_vs_synthesis', 'feasibility', 'total', 'strongest_sections', 'weakest_points'] } },
    winner_index: { type: 'integer' },
    graft_from_others: { type: 'array', description: 'specific sections/diagrams from non-winning designs worth grafting into the winner', items: { type: 'object', properties: { from_design_index: { type: 'integer' }, what: { type: 'string' }, where_in_winner: { type: 'string' } }, required: ['from_design_index', 'what', 'where_in_winner'] } },
    recommended_section_order: { type: 'array', items: { type: 'string' } },
    must_fix: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'scores', 'winner_index', 'graft_from_others', 'recommended_section_order', 'must_fix'],
}

const LENSES = [
  { key: 'newcomer', text: 'LENS: NEWCOMER COMPREHENSION. You are an engineer who knows attention and KV caches from the literature but has never read TRON. Judge purely on whether each design would leave you with a durable, correct mental model of how the five concepts and their parents fit, and of the timing. Penalize designs that require the reader to already know TRON internals. Reward designs where one figure answers one of the user\'s four questions completely.' },
  { key: 'accuracy-feasibility', text: 'LENS: TECHNICAL ACCURACY AND FEASIBILITY. You know TRON (source at ' + TRON + ', READ-ONLY; you may grep to check a fact). Judge whether each design\'s prose points and diagrams stay within the synthesized concept map and its citations, whether the mock scenario is used consistently and correctly, and whether every diagram/animation is realistically buildable in one HTML file with inline SVG/CSS/vanilla JS and light theme. Flag any diagram whose form does not fit its data (e.g. a pie for a sequence).' },
]

phase('Judge')
const verdicts = (await parallel(LENSES.map(l => () =>
  agent(`You are judging 3 independent page designs for a TRON concept-internalization page.

${l.text}

USER BRIEF:
${BRIEF}

SYNTHESIZED CONCEPT MAP (ground truth):
${JSON.stringify(synthesis)}

DESIGNS (array index = design_index):
${JSON.stringify(designs)}

Score each design 0-10 on the four criteria, total them, pick a winner, and list concrete sections or diagrams from the other designs that should be grafted into the winner (say where). Give a recommended final section order and a must-fix list. Be specific: name the section headings and diagram types.`, { label: `judge:${l.key}`, phase: 'Judge', schema: JUDGE_SCHEMA })
))).filter(Boolean)
log(`${verdicts.length}/2 judge verdicts returned`)

return { readers: reports.length, synthesis, designs, verdicts }