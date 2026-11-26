export const meta = {
  name: 'gdn-amx-understand',
  description: 'Read the Qwen3.5 4B GatedDeltaNet stack in tron from 7 angles, then adversarially verify each reading',
  phases: [
    { title: 'Read', detail: '7 parallel readers, one per subsystem or source' },
    { title: 'Verify', detail: 'one skeptic per reader re-checks every load-bearing claim' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-qwen35-4b'

const CONTEXT = `
SHARED CONTEXT (read fully before starting)
- tron is an LLM inference program written in C++. FPGA cards do the large matrix multiplies (linear projections, feed-forward layers). The host CPU does attention in software unless FPGA ("hardware") attention applies. runtron is tron's command-line tool. rinzler is the production server.
- AMX = Intel Advanced Matrix Extensions: tile registers (16 rows x 64 bytes) and tile instructions such as TDPBF16PS (bf16 x bf16 dot products accumulated into FP32). tron already has AMX kernels for software attention (src/tron/kernels/amx_attn.cpp and the callers in h/tron/models/self_attention.hpp). The test CPU is a 2-socket Intel Xeon 6962P (Granite Rapids, AVX-512 including AVX512-BF16 and AVX512-FP16, AMX-TILE, AMX-BF16, AMX-INT8, AMX-FP16).
- GDN = GatedDeltaNet, a recurrent "linear attention" layer type. Qwen3.5 uses it in 3 of every 4 layers. The 4th layer is ordinary full attention.
- Code to read: the git worktree ${WT}. It is tron PR #3696 head 72e1191804 ("Register Qwen3.5 4B"), 21 commits on top of main merge-base 54476c6581. It holds the whole open GDN stack. Treat it as READ ONLY: do not edit files, do not build, do not run any git command that changes state (no checkout, switch, reset, stash, gc, worktree prune). Plain reads (Read, grep, git log, git show, git diff, git blame) are fine. To see what the stack changed, use: git -C ${WT} diff 54476c6581..HEAD -- <path>.
- Model under study: Qwen3.5 4B, tron slug ingested-qwen-3.5-4b. Text config (from the checkpoint's config.json): num_hidden_layers 32; layer_types = [linear_attention x3, full_attention] repeated 8 times (so 24 GDN layers and 8 full-attention layers, full_attention_interval 4); hidden_size 2560; intermediate_size 9216; full attention: num_attention_heads 16, head_dim 256, num_key_value_heads 4, partial_rotary_factor 0.25, attn_output_gate true; GDN: linear_num_key_heads 16, linear_key_head_dim 128, linear_num_value_heads 32, linear_value_head_dim 128, linear_conv_kernel_dim 4, mamba_ssm_dtype float32; dtype bfloat16; vocab 248320.
- For comparison, llama-3.1-8b is a plain transformer: 32 layers, all full attention, 32 heads x 128 head_dim, 8 KV heads, hidden 4096.
- Overall project goal (yours is one part of it): find how AMX can speed up this model in tron, predict the gain from measured metrics, and write a design document. No code will be changed in this phase.

RULES FOR YOUR ANSWER
- Every finding needs evidence: file path relative to the worktree, line numbers, and a short verbatim quote. Open the file and read the lines yourself. Do not cite from memory.
- Mark each finding as 'fact' (the cited lines say it directly) or 'inference' (you derived it; give the derivation).
- When the code does not answer a question, write "Insufficient data" in open_questions and name the file, run, or measurement that would answer it. Never guess.
- Numbers carry units. Show the arithmetic in 'derivation'.
- Be exhaustive on your own topic. Do not drift into other topics; other readers cover them.
`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'At most 12 sentences. The answer to your topic questions in plain English.' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Short id such as K1, K2' },
          claim: { type: 'string' },
          kind: { type: 'string', enum: ['fact', 'inference'] },
          evidence: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                source: { type: 'string', description: 'file path relative to the worktree (or URL for web sources)' },
                lines: { type: 'string' },
                quote: { type: 'string' },
              },
              required: ['source', 'quote'],
            },
          },
          derivation: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['id', 'claim', 'kind', 'evidence', 'confidence'],
      },
    },
    numbers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          value: { type: 'string' },
          unit: { type: 'string' },
          derivation: { type: 'string' },
          source: { type: 'string' },
        },
        required: ['name', 'value', 'unit', 'source'],
      },
    },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'findings', 'numbers', 'open_questions'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'wrong', 'imprecise', 'unverifiable'] },
          correction: { type: 'string', description: 'Empty when confirmed. Otherwise the corrected statement.' },
          evidence: { type: 'string', description: 'file:line and quote that you read to decide' },
        },
        required: ['id', 'verdict', 'correction', 'evidence'],
      },
    },
    number_checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'wrong', 'imprecise', 'unverifiable'] },
          correct_value: { type: 'string' },
          note: { type: 'string' },
        },
        required: ['name', 'verdict', 'correct_value', 'note'],
      },
    },
    missed: {
      type: 'array',
      description: 'Important facts on this topic that the reader missed',
      items: {
        type: 'object',
        properties: { claim: { type: 'string' }, evidence: { type: 'string' } },
        required: ['claim', 'evidence'],
      },
    },
    corrected_summary: { type: 'string', description: 'The reader summary rewritten so every sentence holds. At most 12 sentences.' },
  },
  required: ['verdicts', 'number_checks', 'missed', 'corrected_summary'],
}

const TOPICS = [
  {
    key: 'kernel',
    prompt: `TOPIC: the GDN CPU kernels and their arithmetic.
Read: h/tron/kernels/gated_delta_net.hpp (all of it), h/tron/models/gdn_execution.hpp, h/tron/models/gdn_prepared_operation.hpp, h/tron/models/gdn_geometry.hpp, h/tron/simd/auto.hpp and h/tron/simd/fp32.hpp (for chunk_size, fp32s, fma, round_chunk_to), ingest/runtime/tron_ingest_runtime/ops.py (the Python reference gated_delta_net_with_state), and the parts of t/t_gated_delta_net.cpp that state contracts.
Answer:
1. The exact sequence of operations that one token goes through in one GDN layer on the host CPU, between the FPGA input projection and the FPGA output projection. For each step: function name, inputs, outputs, data type of each operand (BF16 value carried in FP32? true FP32? stored as what?), and where rounding to BF16 happens.
2. The recurrence math as equations (state update and output), in the code's own variable names, and which loops implement which term. State the memory layout of the recurrent state.
3. Costs for the Qwen3.5 4B geometry, per token per GDN layer: number of FP32 multiply-add operations in each loop, number of passes over the state, bytes of state read and written, size of the state per layer and per sequence (24 GDN layers). Show arithmetic.
4. How the code is vectorized today: what chunk_size is under AVX-512 on this build (find the definition), which SIMD instructions the loops map to (fma on 16 FP32 lanes?), whether anything is BF16-packed, any prefetch or streaming store.
5. Which operands are exactly BF16-representable when they enter the recurrence (query, key, value, decay, beta) and which are true FP32 (the state, decay, delta). This decides which AMX instruction could legally consume them. Be precise: quote Note [GatedDeltaNet BF16 rounding points] and Note [GatedDeltaNet recurrence].
6. Any parallelism inside one layer for one token (the stack commit "Parallelize the GDN recurrence across heads"): what unit of work is handed to which worker, how many workers.
7. What the unit tests pin down numerically: is the kernel required to be bit-exact against the Python reference? Which tolerance? Any statement about allowed reordering of FP32 additions.`,
  },
  {
    key: 'runtime',
    prompt: `TOPIC: how GDN layers are scheduled and executed at run time (prefill and decode), and where the recurrent state lives.
Read: h/tron/models/gdn_rolling_executor.hpp, h/tron/models/gdn_chain_plan.hpp, h/tron/models/gdn_execution.hpp, h/tron/models/gdn_registry.hpp, h/tron/models/recurrent_state_storage.hpp, h/tron/models/recurrent_slot.hpp, h/tron/scheduler/recurrent_endpoint.hpp, h/tron/scheduler/recurrent_reuse.hpp, and the stack's changes to h/tron/models/model.hpp, h/tron/scheduler/full.hpp, src/tron/scheduler/full.cpp, h/tron/scheduler/token_cache.hpp, h/tron/scheduler/forward_plan.hpp (use git -C ${WT} diff 54476c6581..HEAD -- <path>). Also doc/explicit-attention-operations.md sections that mention GatedDeltaNet or recurrent.
Answer:
1. Prefill: a prompt chunk of N tokens of one sequence reaches a GDN layer. In what order and on which threads are the N tokens processed? Is it one serial chain per sequence (token t waits for token t-1)? What is a "dependency chain", a "rolling executor", a "rolling checkpoint", a "sequence endpoint"? Can different sequences, different key-head groups, or different layers run in parallel? What bounds the number of tokens per forward (compare with max_minibatch_size for attention)?
2. Decode: U users each generate one token per step. How many GDN recurrence calls per step per layer, on how many workers, in what order?
3. State storage: where the recurrent state and the convolution history live (DMA blocks, hugepages, ordinary heap?), size per sequence, alignment, NUMA placement if stated, how many copies exist (live state, checkpoints, endpoint bundles). When is a state copied (checkpoint cadence, prefix reuse, conversation end)? Bytes copied per event.
4. How GDN work is joined with the rest of the forward pass: the FPGA projections before and after, the per-layer barrier or latch, and whether attention workers (the pool that runs software attention) also run GDN.
5. Which of these mechanisms are serial bottlenecks that a faster kernel would shorten, and which are waits that a faster kernel would not shorten. Mark these as inference and give the code basis.
6. Any counters, timers, trace spans or stats that the GDN runtime itself emits (names and what they measure).`,
  },
  {
    key: 'plugin',
    prompt: `TOPIC: the structure of one Qwen3.5 layer as tron runs it, and how it differs from a llama-3.1-8b layer.
Read: doc/explicit-attention-operations.md, ingest/export/qwen3_5_export.py, ingest/export/gdn_ops.py, ingest/runtime/tron_ingest_runtime/ops.py (gated_delta_net functions), ingest/src/GatedDeltaNet.hs, and how the lowering emits C++ for a GDN operation (search ingest/src for GatedDeltaNet in LoopyTron.hs, TronCpp.hs, Tron.hs, TronTron.hs; read enough to list the emitted runtime calls). Also README.models.md and config/models.yaml entry qwen_3p5_4b, and the test t/t_generate_mock_plugin.cpp if it shows the generated call sequence.
Answer:
1. The ordered list of operations in a "linear_attention" (GDN) layer of Qwen3.5 as exported: every projection (names such as in_proj_qkv, in_proj_z, in_proj_b, in_proj_a, out_proj, conv1d, norm), its input and output widths for the 4B geometry, and whether tron runs it on the FPGA or on the host CPU. Cover the output gate (attn_output_gate / z gate), the RMS norm after the recurrence, and the residual.
2. The same list for a "full_attention" layer of Qwen3.5 4B (16 heads x 256, 4 KV heads, partial rotary factor 0.25, output gate) and what differs from a llama-3.1-8b attention layer (32 heads x 128, 8 KV heads, full RoPE, no gate).
3. Which host-CPU operations exist in a GDN layer that have no counterpart in llama-3.1-8b (convolution with history, QK normalization, softplus decay, beta sigmoid, recurrence, norm, gate) and which llama operations a GDN layer does not have (KV cache, softmax, page walk).
4. How the generated plugin calls the GDN runtime: the C++ entry points the generated code invokes per layer, and with what template geometry.
5. What the registration says about readiness: support_level, executors tp1/tp2/tp4, tags, notes. What tp1/tp2/tp4 mean for how many FPGA cards one engine uses.
6. Whether the multi-token-prediction head (mtp_num_hidden_layers 1) or the vision tower is exported or dropped.`,
  },
  {
    key: 'fullattn',
    prompt: `TOPIC: the 8 full-attention layers of Qwen3.5 4B under tron's software attention, and whether the existing AMX attention kernels can serve them.
Read: src/tron/kernels/amx_attn.cpp, the AMX interface header (find it: grep -rn "amx_attn" h/ --include=*.hpp -l), h/tron/models/self_attention.hpp (the AMX dispatch gate and the AVX path; search for amx, try_score_k_amx, score_k, kv_mul, head_dim, dotter, apply_page_range, apply_page_tok), h/tron/models/kv_cache.hpp (page layout, K storage layouts such as the VNNI layout), h/tron/models/attn_stats.hpp (the visit_path enum tells which paths exist), cmake options TRON_AMX_DISPATCH and env TRON_AMX_DISABLE, and how hardware (FPGA) attention is refused for 256-wide heads (search for the head width check; the PR text says "hardware attention supports only 64- and 128-element heads").
The Qwen3.5 4B full-attention geometry: 16 query heads, 4 KV heads (so 4 query heads per KV head, "kv_mul 4"), head_dim 256, K and V stored as bf16, partial rotary factor 0.25.
Answer:
1. Exactly which geometries the AMX attention kernels accept today (head_dim, kv_mul / query heads per KV head, dtype, page conditions). Quote every static_assert, requires clause, template instantiation list, and runtime gate. Does head_dim 256 with kv_mul 4 take the AMX path or fall back to AVX? If it falls back, name the first check that rejects it.
2. How one KV page is laid out for head_dim 256 (tokens per page, bytes per page for K and for V) and how the AVX path computes QK scores and PV sums for it. How many bf16 multiply-adds per page per KV head.
3. How the AMX kernel tiles the work for the accepted geometry (rows, columns, how many TDPBF16PS per page) and what would have to change for a 256-wide head (for example two 128-wide halves accumulated into the same result tile). State this as inference with the code basis.
4. Whether the generated plugin's attention geometry ("operation-local attention geometry") flows into these templates, so that the Qwen3.5 instantiation exists at all, and where sliding windows or other gates could block the dense AMX path for this model.
5. What the model-level consequences are of FPGA attention being unavailable: every full-attention layer of this model always runs software attention on the host CPU, at every prompt length. Confirm or refute from code.
6. Also check main: git -C /home/jhan/workspace/tron show origin/main:src/tron/kernels/amx_attn.cpp and the same for the interface header, to see whether main (0af590c21e) differs from this stack's merge-base in the accepted geometries.`,
  },
  {
    key: 'metrics',
    prompt: `TOPIC: which measurements exist for this model without changing code: the attention path statistics (env TRON_ATTN_STATS), the GDN state statistics, trace spans, and runtron's own throughput and latency numbers.
Read: h/tron/models/attn_stats.hpp (Note [Attention path stats]), README.stats.md (attention section), the stack's changes to src/system/fuse_tronstats_manifest.cpp and src/rinzler.cpp (git -C ${WT} diff 54476c6581..HEAD -- <path>), .agents/skills/analyze-tron-perfetto-trace/references/span-dictionary.md (GDN spans the stack added), README.perfetto.md, and runtron's source (find it: grep -rn "prompt-length" src/ --include=*.cpp -l; read how it prints tokens per second, time to first token, prefill and decode numbers, and the flags that control users, prompt length, generated tokens, temperature, determinism, attention on CPU vs FPGA such as USE_HW_ATTN).
Answer:
1. TRON_ATTN_STATS: how to turn it on, every counter and timer it reports (names, units, exact meaning; the timers are called T1 to T5 in the Note), where the report goes (stderr summary at exit, FUSE leaves), and its two forward classes.
2. For a hybrid model with 24 GDN layers and 8 full-attention layers: which of these counters and timers see the GDN layers? Trace the hooks: is the GDN recurrence inside any attention timer (for example the per-forward wall T1, or the attention-job busy time T2), or is it invisible to this instrument? What does the "layer" index mean for this model (model layer number or attention-operation ordinal)?
3. What can be derived for a prediction: the share of a forward's wall time spent in software attention jobs, per layer, per worker, and the split between the AMX path and the AVX path. Give the formula in terms of the reported fields.
4. GDN-specific statistics or spans in this stack: names, what they measure, how to read them (FUSE path, trace category, env var). If the stack has none that time the recurrence, say so plainly.
5. runtron: the exact definition of each printed performance number (decode tokens per second, prefill tokens per second, time to first token), which clock and which token count each uses, and whether multi-user runs report a sum or a per-user value.
6. The cheapest way to get the time spent in the GDN host kernels per layer without code changes (perfetto trace? existing phase timers such as TRON_ATTN_PHASE?), and its overhead if stated.`,
  },
  {
    key: 'priors',
    prompt: `TOPIC: measured constants from this team's earlier AMX work that a prediction for the new model can reuse. This is a reading task over existing reports, not over the tron code.
Read (HTML and markdown reports; use grep and targeted reads, the files are long): /home/jhan/workspace/intel-AMX/perf-model/index.html (or its generator inputs under /home/jhan/workspace/intel-AMX/exec/perf-model-20260903/ and results under /home/jhan/workspace/intel-AMX/exec/results/perf-model-20260903/), /home/jhan/workspace/intel-AMX/tron-amx-distilled.html, /home/jhan/workspace/intel-AMX/amx-design.md, pages under /home/jhan/workspace/intel-AMX/muse-glimmer/ (the 128x16 shape work) and /home/jhan/workspace/intel-AMX/CI-test/ and /home/jhan/workspace/intel-AMX/PR3879/ that report AMX-on versus AMX-off throughput by prompt length for qwen-3-4b and llama-3.1-8b, and /home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/ (the page that compares the machines delphi-3b35 and delphi-3bda). ls the directories first.
Answer with numbers, each with unit, date, machine, and the file that states it:
1. Instruction-level costs measured on Xeon 6962P: cycles per TDPBF16PS tile product and multiply-adds per product; cycles per AVX-512 VDPBF16PS; tile load/store costs; the core clock under AMX load versus AVX-512 load; the kernel-level speedup of the AMX attention unit over the AVX unit when data is cache-hot and when data comes from DRAM.
2. Memory facts: per-core read rate under multi-thread load (GB/s), L2 and L3 sizes per core and per socket, time to read 32 KiB, and the "data wait" share of an attention unit at prompt 8192.
3. End-to-end AMX gains measured so far: decode tokens per second AMX-on versus AMX-off by model, users, and prompt length (qwen-3-4b, llama-3.1-8b, Glimmer), and prefill gains. Note which machine (3bda or 3b35) and which date.
4. Known differences of delphi-3b35 versus delphi-3bda that change absolute numbers (TSX off, no flat-frequency service, C6 on, clock readings).
5. Any earlier statement in these files about FP32 work, AMX-FP16, or a workload where one operand is FP32 (relevant because the GDN state is FP32). If none, say none found.
6. The method those reports used to predict a gain before measuring it (the data-wait model: unit time = max(compute, memory) + (1 - eta) x min(compute, memory)), its inputs, and how close the prediction came to the measurement.`,
  },
  {
    key: 'literature',
    prompt: `TOPIC: the published GatedDeltaNet algorithm and its known fast forms. Use the web (load WebSearch and a web fetch tool through ToolSearch if they are not already available) and the in-repo reference.
PRIVACY RULE: web queries must be generic. Never put a company name, a person's name, a project name, a host name or a file path from this workspace into a search query or a fetched URL.
Read in the repo: ${WT}/ingest/runtime/tron_ingest_runtime/ops.py (gated_delta_net functions) and ${WT}/ingest/export/gdn_ops.py.
Find on the web: the paper "Gated Delta Networks: Improving Mamba2 with Delta Rule" (Yang, Kautz, Hatamizadeh; arXiv 2412.06464) and its predecessor "Parallelizing Linear Transformers with the Delta Rule over Sequence Length" (DeltaNet, arXiv 2406.06484); the flash-linear-attention library's gated delta rule code (the recurrent form and the chunkwise form, chunk size, data types); and the Hugging Face Transformers Qwen3.5 model code if it is public (function names like torch_chunk_gated_delta_rule and torch_recurrent_gated_delta_rule, which one is used for a single decode token and which for a long prompt, and the dtype of the recurrent state).
Answer:
1. The recurrence in the paper's notation: S_t = S_{t-1} (alpha_t (I - beta_t k_t k_t^T)) + beta_t v_t k_t^T, o_t = S_t q_t, with the exact definitions of alpha (decay gate) and beta (writing strength), and the L2 normalization of q and k. Map each symbol to the tron variable names found in ops.py.
2. The chunkwise parallel form: the algebra that turns C sequential rank-one updates into a few dense matrix products per chunk (the WY or UT-transform representation), written out step by step: which products are C x C (Gram matrices from Q and K), which are C x d_k times d_k x d_v (they touch the state), the triangular solve or forward substitution, and how the gates alpha enter (cumulative products of decays inside the chunk). State the cost in multiply-adds per chunk as a function of C, d_k, d_v, and how many times the state is read and written per chunk compared with the per-token form.
3. Which operands of each dense product are low-precision inputs (q, k, v after rounding) and which are the full-precision state or derived full-precision terms. This decides whether a bf16 x bf16 tile dot product instruction can compute the product exactly, approximately, or not at all.
4. Numerical remarks in the papers or the library about the chunkwise form versus the recurrent form: are the results bitwise equal or only close? Any note on precision (float32 required? bf16 instability?), on chunk size 64, on clamping.
5. Any published CPU-side or accelerator-side kernel work for delta-rule recurrences (SIMD, AVX-512, AMX, or CUDA/Triton kernels), and any known inference engines (for example llama.cpp or vLLM) that run this layer type, with what they do for decode versus prefill.
6. What limits parallel prefill for this layer type in general: the sequential dependence over tokens, and how chunking changes it.
Give URLs as evidence sources with verbatim quotes. If a source cannot be fetched, say so and do not paraphrase from memory as fact; mark such items confidence low and kind inference.`,
  },
]

const results = await pipeline(
  TOPICS,
  t => agent(`${CONTEXT}\n${t.prompt}`, { label: `read:${t.key}`, phase: 'Read', schema: FINDINGS_SCHEMA }),
  (reading, t) => {
    if (!reading) return { key: t.key, reading: null, check: null }
    return agent(
      `${CONTEXT}\nYOU ARE THE VERIFIER for the topic below. Another agent produced the findings that follow. Your job is to try to REFUTE them.\n` +
      `For every finding: open the cited source, read the cited lines and their surroundings, and decide: confirmed, wrong, imprecise, or unverifiable. A finding whose quote does not appear at the cited place is 'wrong' or 'imprecise' until you locate the true text. Recompute every number from the source values. For web sources, fetch the URL again (same privacy rule: generic queries only, no company, person, project, host or path names from this workspace). Default to 'unverifiable' when you cannot read the source; never confirm on plausibility.\n` +
      `Then list important facts on this topic that the reader missed (with evidence), and rewrite the summary so that every sentence holds.\n\n` +
      `THE TOPIC AND ITS QUESTIONS:\n${t.prompt}\n\nTHE READER'S OUTPUT (JSON):\n${JSON.stringify(reading)}`,
      { label: `verify:${t.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }
    ).then(check => ({ key: t.key, reading, check }))
  }
)

const out = results.filter(Boolean)
log(`readers returned: ${out.filter(r => r.reading).length}/${TOPICS.length}; verified: ${out.filter(r => r.check).length}`)
return out
