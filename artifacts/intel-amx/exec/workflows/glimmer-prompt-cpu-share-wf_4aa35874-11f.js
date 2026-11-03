export const meta = {
  name: 'glimmer-prompt-cpu-share',
  description: 'Explain from tron source why Glimmer full layers score K tokens on the CPU (AMX + AVX) in prompt forwards at prompt 2048 but AVX-only at prompt 1024',
  phases: [{ title: 'Read' }, { title: 'Refute' }, { title: 'Synthesize' }],
}
const CTX = `
Context (facts measured 2026-10-16 on delphi-3bda, runtron with TRON_ATTN_STATS=1, branch jhan-amx-kvmul16 = tron main 6198824246 plus
AMX kernels generalized to kv_mul 16; source checkout: /home/jhan/workspace/ai-runs/tron-glimmer-amx, read only, do NOT edit or build).
Model: ingested-meta-models--Muse-Glimmer-30B-tp2 (52 layers; 39 sliding-window-2048 layers are software_only; the 13 full layers
3,7,11,...,51 are FPGA candidates; USE_HW_ATTN unset = FPGA on, 'HW attention enabled ... engagement=127 ...'). 8 users, 256 generated tokens.
The exit report counts K tokens per layer per path (amx/avx/fpga) separately for decode_like forwards and prompt_or_mixed forwards.
Observed, per FULL layer (e.g. layer 3), prompt_or_mixed class:
  prompt 1024: amx=0        avx=1056754  fpga=3670016
  prompt 2048: amx=933888   avx=2228210  fpga=15204352   (the campaign's gen_compare flags this 'UNEXPECTED: both AMX and FPGA on 13 layers')
Per SLIDING layer (e.g. layer 0), prompt_or_mixed: prompt 1024: amx=6422528 avx=1974258 fpga=0; prompt 2048: amx=29376512 avx=4194290 fpga=0.
Decode_like class, full layers: amx=0, avx=10240, fpga=2355200 (p1024) / 4452352 (p2048). No 'lose HW attention' or 'HBM bypass space
exhausted' warnings in either log. The logs: /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/rt/glm-tp2-8u-p2048-fpga__fpga__amxon__rep1.log
and ...p1024-fpga__fpga__amxon__rep1.log (grep for 'attn-stats', 'shard', 'chunk', 'prompt', 'engagement'; they are large, do not cat them whole).
Question: WHY do the full layers score K tokens on the CPU in prompt forwards, and why does the AMX kernel appear only at prompt 2048?
Candidate mechanisms to check in the code (h/tron/models/model.hpp, self_attention.hpp, kv_cache.hpp, hw_attn_config.hpp, the prompt
sharding / chunking code, the attention planner that decides per page between fpga/avx/amx): (a) positions below the engagement point 127
are scored on the CPU; (b) a prompt longer than one shard (1024 tokens?) is processed in shards and the later shard's queries attend to
earlier pages on the CPU (or only to pages not yet resident on the card); (c) the AMX dense-page predicate (is_dense_amx_page: full page,
inside the window, all tokens ready) is false for pages of the current shard but true for completed earlier-shard pages; (d) the FPGA
engagement rule applies per request position, so the first 127 positions of every user go to the CPU in both prompt lengths (that would be
the AVX-only p1024 share). Explain the exact arithmetic if you can: e.g. avx=1056754 per full layer at p1024 = 8 users x ? ; amx=933888 at
p2048 = 8 users x 2 KV heads x 58368 = 912 pages of 64 tokens per user per KV head. Cite file:line for every claim.`
const SCHEMA = { type: 'object', properties: {
  explanation: { type: 'string', description: 'the mechanism, 3-10 sentences, plain English, with file:line citations' },
  arithmetic: { type: 'string', description: 'how the observed numbers follow from the mechanism, or which part does not match' },
  confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  open: { type: 'string', description: 'what could not be verified and which measurement/log line would settle it' } }, required: ['explanation', 'arithmetic', 'confidence', 'open'] }
const LENSES = [
  'Trace the prompt (prefill) path: how a prompt of 1024 and of 2048 tokens is split into forwards/shards, and which K pages each query block attends to on the CPU vs the FPGA. Start from the stream-generate-text prompt handling and the model forward, then the attention dispatch.',
  'Trace the FPGA engagement and the per-page path decision: hw_attn_config engagement=127, is_hardware_attention_candidate, the planner in model.hpp that assigns pages to fpga/cpu, and the AMX dense-page predicate in self_attention.hpp. Determine exactly which pages of a full layer go to the CPU during prompt forwards.',
  'Work from the counters: read h/tron/kernels/attn_stats.hpp (or wherever TRON_ATTN_STATS counts k_tokens per layer per path) to learn exactly what each count means (ready vs pending, fpga_k_tokens_x_kv_heads), then reproduce the observed per-layer numbers arithmetically from the shapes (8 users, 2 KV heads, pages of 64, engagement 127, prompt 1024/2048) and the mechanism you find.',
]
const reads = await pipeline(LENSES,
  (lens, i) => agent(`${CTX}\n\nYour lens: ${lens}\nReturn the structured answer.`, { label: `read:${i}`, phase: 'Read', schema: SCHEMA }),
  (r, lens, i) => r && agent(`${CTX}\n\nA colleague proposed this explanation:\n${JSON.stringify(r, null, 1)}\n\nTry to REFUTE it from the source and the logs: check every cited file:line, check the arithmetic, look for an alternative mechanism. Return the corrected explanation (keep what holds, fix what does not) in the same structure; in 'open' say what you refuted.`, { label: `refute:${i}`, phase: 'Refute', schema: SCHEMA }))
const ok = reads.filter(Boolean)
const synth = await agent(`${CTX}\n\nThree independent read+refute passes produced these answers:\n${JSON.stringify(ok, null, 1)}\n\nWrite the final answer for a report: (1) the mechanism in plain English (define every code term at first use, one claim per sentence, file:line after the sentence), (2) the arithmetic check of the observed numbers, (3) what stays open and the measurement that would settle it. Where the passes disagree, verify in the source yourself and pick the one that holds; say which you rejected and why.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })
return { passes: ok, final: synth }