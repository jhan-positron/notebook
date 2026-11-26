export const meta = {
  name: 'gdn-amx-design',
  description: 'Design how AMX can speed up Qwen3.5 4B in tron: 3 independent designs plus a numeric prototype, a synthesis, then adversarial verification',
  phases: [
    { title: 'Propose', detail: '3 independent designers and one numeric prototype of the block-form math' },
    { title: 'Synthesize', detail: 'merge the designs into one specification with claims' },
    { title: 'Verify', detail: '3 skeptics: math and numerics, cost model, fit to the tron code' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-qwen35-4b'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120'
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/be74f0ef-9ecd-4d0b-b01e-43155cd9bc79/scratchpad/design'

const FACTS = `
PROJECT
We must design how Intel AMX (tile matrix instructions on the Xeon 6962P) can speed up the model Qwen3.5 4B in tron (an LLM inference program; FPGA cards do the big matrix multiplies, the host CPU does attention and other per-token work). The deliverable of this phase is a DESIGN and a PREDICTION. No tron code is changed in this phase. You may write and run small stand-alone scripts (python3 with numpy is installed; no torch needed) under ${SCRATCH}/<your-name>/ to check math. Do not build tron. Do not use ssh. Do not touch any other directory.

CODE TO READ (read only)
- ${WT} = tron PR #3696 head 72e1191804 (the open GatedDeltaNet stack). Never edit it and never run a state-changing git command there.
- ${RES}/plugin/qwen_3p5_4b.hpp = the C++ plugin that tron's ingest tool generated for this model (8,642 lines; search it for run_gdn_operation and attention_kernels).
- Key files: h/tron/kernels/gated_delta_net.hpp (the GDN kernels), h/tron/models/gdn_rolling_executor.hpp (one step of one key-head group; checkpoints), h/tron/models/gdn_execution.hpp (run_gdn_operation: deals work items to workers), h/tron/models/gdn_chain_plan.hpp, src/tron/kernels/amx_attn.cpp and h/tron/kernels/amx_attn_iface.hpp (the existing AMX attention kernels and their gate), h/tron/models/self_attention.hpp (AMX dispatch at about lines 1533-1720, AVX path apply_page_tok), h/tron/kernels/dotter.hpp, h/tron/models/kv_cache.hpp (page layout, scaled_v_expr), t/t_gated_delta_net.cpp, t/t_amx_numerics.cpp (how the existing AMX kernels are tested).

VERIFIED FACTS ABOUT THE MODEL AND THE CODE (each was read from the code by one agent; treat as true unless you find the code says otherwise)
F1. Qwen3.5 4B: 32 layers = [GDN, GDN, GDN, full attention] x 8. Hidden width 2560. GDN = GatedDeltaNet, a recurrent layer.
F2. Full attention geometry: 16 query heads, 4 KV heads (4 query heads per KV head), head width 256, K and V stored as bf16, 64 tokens per KV page. K plane row-major (one 256-wide bf16 row per token, 512 bytes). V plane pair-interleaved (VNNI layout). One (page, KV head) block = 32 KiB K + 32 KiB V.
F3. The existing AMX attention kernels (namespace amx_attn_h128g4) accept ONLY head width 128 with 4 query heads per KV head. The gate shape_ok (amx_attn_iface.hpp:150) is a compile-time constant, so for this model every software attention visit takes the AVX-512 path (dotter<bf16,256> for QK, scaled_v_expr accumulate_16_chunks for PV). FPGA attention is refused for 256-wide heads (model.hpp model_shape_is_hwattn_eligible needs 128 or 64). So all 8 full-attention layers run AVX-512 software attention at every prompt length.
F4. Tiling of the existing 128x4 kernels, per (query token, page, KV head): QK = 16 TDPBF16PS (K row-major as A operand, 16 tokens x 32 dims per tile; packed Q as B operand, 4 real columns of 16), PV = 16 TDPBF16PS (P weights rounded to bf16 as A, rows 0..3 real; packed V read in place as B). 40 tile loads, 12 tile stores. Only 4 of 16 tile rows or columns carry data in decode.
F5. A GDN layer per token: 4 FPGA projections of the 2560-wide hidden vector (mixed q,k,v 8192 wide; gate z 4096; decay input a 32; update input b 32) -> host CPU operation -> FPGA output projection (4096 -> 2560). GDN geometry: 16 key heads x 128, 32 value heads x 128 (2 value heads per key head), 4-tap convolution.
F6. The host CPU operation for one token and one key-head group (1 key head + its 2 value heads), in gdn_rolling_executor::step: gather 512 channels; 4-tap convolution + SiLU with bf16 rounding (history of 3 earlier inputs); L2-normalize q and k (bf16-rounded results); per value head: decay = exp(-A_exp * softplus(bf16(a) + dt_bias)) (true FP32 scalar), beta = bf16(sigmoid(bf16(b))); then the recurrence on that value head's state S (FP32, 128 key rows x 128 value columns = 64 KiB):
      loop 1: r[c] = sum_i k[i] * (S[i][c] * decay)                       (k = normalized key, bf16-exact values held in FP32)
      delta[c] = (bf16(v[c]) - r[c]) * beta
      loop 2: S[i][c] = fma(k[i], delta[c], S[i][c] * decay);  o[c] = sum_i (q[i] * scale) * S_new[i][c]     (scale = 1/sqrt(128); q = normalized query, bf16-exact before scaling)
    then postprocess: round o to bf16, RMS norm per value head, times weight, times SiLU(z), each rounded to bf16.
    The loops use AVX-512 FP32 FMAs on 16 lanes. No prefetch, no streaming store. The state is true FP32 ("mamba_ssm_dtype": "float32").
F7. Counts per token per GDN layer (all 32 value heads): 1,572,864 FP32 FMAs + 1,048,576 FP32 multiplies; the 2 MiB state is read twice and written once. In decode a third read pass scans the state for NaN (validate_checkpoint_values in start_from_checkpoint).
F8. State per sequence: 24 layers x (2,097,152 bytes state + 98,304 bytes convolution history) = 52,690,944 bytes, in DMA hugepage memory. One key-head group owns 131,072 bytes of state.
F9. Scheduling (run_gdn_operation): a work item = one (chain, key-head group); a chain = one sequence's consecutive tokens in this forward pass. Work items are dealt round-robin to n_workers = 1 + main helpers. Inside one item the tokens run strictly in order on one thread. Decode: chain of 1 token, state advanced IN PLACE in the DMA block. Prefill: chain of up to 128 tokens (default prompt chunk; env TRON_PER_USER_PROMPT_CHUNK_LIMIT), state advanced in a per-worker WORKING COPY (131,072 bytes + history) and copied back after the chain's last token. One pass holds at most 1024 token jobs (one minibatch). Attention workers never run GDN.
F10. On the test machine (our half of delphi-3b35: 56 app CPUs on socket 1, 4 FPGA cards, executor tp4): app pool 55 workers, of which 15 are main helpers (so 16 threads run GDN) and 40 are attention workers. This split is floor(2P/7) helpers.
F11. Tests: the FP32 recurrence output and state are checked with absolute tolerance 1e-7 against a double-precision oracle and against torch literals. ONE executor test pins 320 final bf16 output words (4th token of a chain, small geometry) to torch bit for bit. The Python reference is checked against Hugging Face Transformers with rtol 1e-6, atol 1e-6. No test or comment fixes the order of the recurrence sums. The convolution, normalization and beta are bit-exact against torch.
F12. The C++ kernel is already not bit-identical to the Python reference in FP32 (it uses fma; Python rounds each product), by the kernel reader's analysis.

MEASURED ON delphi-3b35, 2026-11-20 (socket 1 idle before each run; the other socket runs two unrelated servers at 43 % busy; CPU clock reads 2.70 GHz; TSX off)
M1. Stand-alone kernel benchmark of the existing code, 1 thread: gdn_recurrence<16,32,128,128> step = 102.1 us per token per layer for all 32 value heads (3.19 us per value head = about 8,600 cycles per value head at 2.70 GHz; a compute-only count at 2 FMA per cycle would be about 2,600 cycles, so the kernel is bound by moving the 64 KiB state between L2 and L1, not by arithmetic). gdn_conv1d_silu<8192> = 8.15 us per token per layer.
M2. Baseline, executor tp4, runtron, 256 generated tokens, one repetition so far (decode tokens/s per user | time to first token | mean decode forward | mean prefill pass):
      1 user,  prompt 1024: 276 | 0.385 s  | 3.58 ms  | 48.1 ms per 128-token pass
      1 user,  prompt 4096: 252 | 1.895 s  | 3.90 ms  | 59.1 ms per 128-token pass
      8 users, prompt 1024: 121 | 2.90 s   | 8.09 ms  | 361 ms per 1024-token pass
      8 users, prompt 4096: 77.4| 14.28 s  | 12.47 ms | 445 ms per 1024-token pass
M3. Attention statistics (TRON_ATTN_STATS=1): every K token is scored on the AVX path (AMX visits = 0). Attention wall on attention worker 0 as a share of the forward wall: decode 12.9 % (1 user, prompt 1024), 18.1 % (1 user, 4096), 18.0 % (8 users, 1024), 41.2 % (8 users, 4096); prefill 18.1 %, 33.3 %, 14.8 %, 31.0 % in the same order. The rest of a forward is FPGA matmul time plus GDN host work plus small host kernels. A trace that splits GDN from FPGA time is being taken; it is not available to you.

AMX INSTRUCTION COSTS measured earlier on the same CPU model (Xeon 6962P, sister machine delphi-3bda)
C1. TDPBF16PS: 16.2 cycles per tile product = 8,192 bf16 multiply-adds (16 rows x 16 columns x 32 products), accumulated into an FP32 16x16 tile. Operands: A tile 16 rows x 32 bf16; B tile 16 rows x 32 bf16 arranged as 16 pairs per row; C[m][n] += sum_k A[m][2k]*B[k][2n] + A[m][2k+1]*B[k][2n+1].
C2. TILELOADD of a 1 KiB tile from L1: 8.4 cycles. TILESTORED: 16.1 cycles. TILEZERO: 0.5 cycles. LDTILECFG + TILERELEASE pair: about 229 cycles. 8 tile registers.
C3. AVX-512 VDPBF16PS: 2.0 cycles for 32 multiply-adds. FP32 FMA on zmm: assume 2 per cycle (est., two 512-bit FMA units; not measured by us).
C4. The core clock drops under AMX work: 3.60 GHz under the sparse AMX attention kernel against 3.90 GHz under AVX-512 on delphi-3bda (-7.7 %), and 3.00 GHz in a pure tile-product loop (-23 %). On delphi-3b35 busy cores read 2.70 GHz today; the clock under AMX there is not measured.
C5. The CPU also has AMX-FP16 (TDPFP16PS: fp16 x fp16 accumulated into FP32) and AVX512-FP16; never used or timed by us. There is no FP32 tile product. The Intel optimization manual describes emulating an FP32 operand with 3 bf16 pieces.
C6. Earlier measured results of the 128x4 AMX attention kernel inside tron (model qwen-3-4b, sister machine): per-unit speedup over AVX 1.26x (data from DRAM, prompt 8192) to 2.1-2.6x (data in cache); decode gain +12 to +18 % at 8 users; prefill time -20 % (prompt 1024) to -56 % (prompt 8192), because in prefill many query tokens fill the tile rows.

RULES FOR YOUR ANSWER
- Separate what you verified (by reading code or running a script) from what you estimate. Mark every estimate "est." and give its arithmetic.
- Cite file:line for claims about the tron code.
- Numbers carry units.
- If AMX cannot help somewhere, say so plainly and give the reason. A correct "no gain" is a valid design result.
- Plain English, short sentences. No idioms.
`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'At most 10 sentences' },
    components: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          target: { type: 'string', description: 'which work it speeds up (e.g. GDN prefill, GDN decode, full attention decode, full attention prefill)' },
          idea: { type: 'string' },
          algorithm: { type: 'string', description: 'Step-by-step, with equations where needed' },
          amx_mapping: { type: 'string', description: 'Which operand is tile A, tile B, tile C; rows, columns, tile counts; or why AMX does not apply' },
          numerics: { type: 'string', description: 'What changes in the arithmetic and which tests or contracts are affected' },
          cost_estimate: { type: 'string', description: 'Cycles or time per token or per page with arithmetic; baseline for comparison' },
          expected_kernel_speedup: { type: 'string' },
          code_changes: { type: 'string', description: 'Files, functions, new entry points, gates, switches, tests' },
          risks: { type: 'string' },
          verdict: { type: 'string', enum: ['recommend', 'optional', 'reject'] },
        },
        required: ['name', 'target', 'idea', 'algorithm', 'amx_mapping', 'numerics', 'cost_estimate', 'expected_kernel_speedup', 'code_changes', 'risks', 'verdict'],
      },
    },
    staging: { type: 'string', description: 'Order of work and what to measure after each step' },
    open_questions: { type: 'array', items: { type: 'string' } },
    scripts: { type: 'array', items: { type: 'string' }, description: 'Paths of scripts you wrote and what each printed (key numbers)' },
  },
  required: ['summary', 'components', 'staging', 'open_questions', 'scripts'],
}

const PROTO_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    script_path: { type: 'string' },
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          check: { type: 'string' },
          setup: { type: 'string' },
          result: { type: 'string', description: 'Numbers with units, copied from the script output' },
          passed: { type: 'boolean' },
        },
        required: ['check', 'setup', 'result', 'passed'],
      },
    },
    algorithm_as_implemented: { type: 'string', description: 'The exact block-form equations the script uses, step by step' },
    limits: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'script_path', 'results', 'algorithm_as_implemented', 'limits'],
}

const SPEC_SCHEMA = {
  type: 'object',
  properties: {
    short_version: { type: 'string', description: 'At most 3 sentences' },
    components: DESIGN_SCHEMA.properties.components,
    block_algorithm: { type: 'string', description: 'The final step-by-step algorithm of the GDN block kernel, with equations and the role of each matrix product' },
    tile_mapping: { type: 'string', description: 'For each tile product of each kernel: A, B, C operands, shapes, counts of TDPBF16PS, tile loads and stores per chunk and per page' },
    numerics_contract: { type: 'string' },
    software_structure: { type: 'string', description: 'Files, functions, call path, gates, switches, state layout changes, tests, in the order a reviewer would read them' },
    staging: { type: 'string' },
    disagreements: { type: 'array', items: { type: 'string' }, description: 'Where the designers disagreed and which side you took, with the reason' },
    claims: {
      type: 'array',
      description: 'Every load-bearing claim of the specification, for the verifiers',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          kind: { type: 'string', enum: ['math', 'numerics', 'cost', 'code', 'other'] },
          claim: { type: 'string' },
          basis: { type: 'string' },
        },
        required: ['id', 'kind', 'claim', 'basis'],
      },
    },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['short_version', 'components', 'block_algorithm', 'tile_mapping', 'numerics_contract', 'software_structure', 'staging', 'disagreements', 'claims', 'open_questions'],
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
          verdict: { type: 'string', enum: ['holds', 'wrong', 'imprecise', 'unverifiable'] },
          correction: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['id', 'verdict', 'correction', 'evidence'],
      },
    },
    new_problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: { problem: { type: 'string' }, evidence: { type: 'string' }, severity: { type: 'string', enum: ['blocks the design', 'changes a number', 'minor'] } },
        required: ['problem', 'evidence', 'severity'],
      },
    },
    corrected_numbers: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, value: { type: 'string' }, arithmetic: { type: 'string' } }, required: ['name', 'value', 'arithmetic'] } },
    scripts: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdicts', 'new_problems', 'corrected_numbers', 'scripts'],
}

const DESIGNERS = [
  {
    key: 'kernel',
    brief: `YOUR ANGLE: the arithmetic. Work out from first principles which of the host-CPU products in this model AMX tile products can compute, and how.
Cover at least: (a) the GDN recurrence for ONE token (decode): can TDPBF16PS or TDPFP16PS serve it given that the state is FP32 and only 1 or 2 "query-like" rows exist per state matrix? Count useful products per tile product. (b) the GDN recurrence for a CHAIN of C tokens of one sequence (prefill): is there an algebraically equal block form that turns C serial rank-one updates into a few dense matrix products (derive it yourself from the equations in F6, including the per-token decay and beta; check it with a numpy script against the token-by-token loop)? Which operands are bf16-exact and which are FP32? How can an FP32 operand be fed to a bf16 tile product (for example an exact split of each FP32 value into 3 bf16 values; check the exactness claim with a script, including the edge cases of rounding)? Give the tile mapping (A, B, C operands, rows, columns) and count TDPBF16PS, tile loads and tile stores per chunk for chunk sizes 16, 32 and 64, and the remaining AVX-512 work. Estimate cycles per token per value head and compare with M1. (c) the full-attention layers with 256-wide heads: how the 128x4 kernels extend to 256x4, with counts. (d) the convolution, normalization and postprocess: is anything worth AMX?
Give the block algorithm in enough detail that a C++ engineer could implement it, and state exactly where its arithmetic differs from the token-by-token kernel.`,
  },
  {
    key: 'integration',
    brief: `YOUR ANGLE: how a faster kernel fits into the tron code. Read gdn_rolling_executor.hpp, gdn_execution.hpp, gdn_chain_plan.hpp, the generated plugin (search run_gdn_operation), amx_attn_iface.hpp, amx_attn.cpp, and the AMX dispatch in self_attention.hpp.
Cover at least: (a) where a multi-token GDN chain could take a "block" path that processes C tokens of one key-head group at once (which function, what its inputs are: the per-token rows mixed_qkv[job], decay[job], update[job], output_gate[job], output[job]; note the convolution and normalization must still produce per-token q, k, v first), what new entry point the kernel needs, what scratch memory per worker, and what stays unchanged (decode chains of 1 token, checkpoints, scheduler). (b) how the existing AMX attention code is gated and switched (build option TRON_AMX_DISPATCH, env TRON_AMX_DISABLE, available(), eligibility constexpr, tile configuration lifetime, per-thread permission) and how a GDN AMX kernel and a 256-wide attention kernel should reuse that, including the attention statistics (attn_stats.hpp) and what counter or trace slice a GDN AMX path needs so that its use can be measured. (c) the list of files and functions to change for a 256x4 attention kernel. (d) tests: which existing tests constrain the change (t_gated_delta_net.cpp, t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp, t_llama_unit.cpp) and what new tests are needed; what a numerics contract for a reordered GDN recurrence should say given F11 and F12. (e) threading: 16 threads run GDN and 40 attention workers idle during a GDN operation; does the design change that, and is that an AMX question or a separate one?
You may propose the kernel math only as far as you need it; another designer derives it in depth.`,
  },
  {
    key: 'skeptic',
    brief: `YOUR ANGLE: alternatives and risks. Assume a colleague claims "AMX can speed up GDN". Find out where that is true and where it is not, and what else would give the same gain more cheaply.
Cover at least: (a) decode: one token per sequence per layer, state FP32, 2 MiB per layer per sequence, read twice and written once per token, plus a NaN scan. Is the decode step bound by arithmetic or by memory traffic (use M1 and the cache sizes: L1d 48 KiB, L2 2 MiB per core, L3 432 MiB per socket shared by 72 cores; per-core DRAM read rate 13 to 20 GB/s)? What can AMX do there? What non-AMX changes would cut the traffic (list them, with the arithmetic)? (b) prefill: a chain of 128 tokens per key-head group; compare three options with estimated cycles per token: today's kernel, a block form in AVX-512 FP32 only, a block form with AMX tile products. Be explicit about what is gained by the block form itself and what AMX adds on top. (c) the AMX costs that could cancel the gain: the clock drop under AMX (C4), tile configuration per thread, splitting FP32 into bf16 pieces, tile load and store traffic, only 16 threads running GDN. (d) AMX-FP16 or a reduced-precision state as alternatives: what they would change in accuracy and in the tests (F11). (e) the full-attention layers: is extending the existing kernels to 256-wide heads the larger and safer win for this model? Use M3. (f) what to measure first, in what order, to confirm or reject each part with the least work.
Write small scripts where a number can be computed rather than argued.`,
  },
]

phase('Propose')
const proposeThunks = DESIGNERS.map(d => () =>
  agent(`${FACTS}\n${d.brief}\nYour scratch directory: ${SCRATCH}/${d.key}/ (create it).`, { label: `design:${d.key}`, phase: 'Propose', schema: DESIGN_SCHEMA }))
proposeThunks.push(() =>
  agent(`${FACTS}\nYOUR TASK: a numeric prototype, in Python with numpy, of the GDN recurrence in two forms. Your scratch directory: ${SCRATCH}/proto/ (create it).
1. Token-by-token reference, exactly as F6 states it and as h/tron/kernels/gated_delta_net.hpp implements it (read the file; reproduce the bf16 rounding points with a round-to-nearest-even bf16 helper on float32 bit patterns; use np.float32 arithmetic; emulate fma with float64 where a product is fused).
2. A block form that processes a chunk of C tokens at once. Derive it yourself: with gamma_t = product of the decays up to token t, the state after t tokens is S_t = gamma_t*S_0 + sum over u<=t of (gamma_t/gamma_u) * k_u (outer) delta_u, so r_t and o_t need only K*S_0, Q*S_0 (C x 128 times 128 x 128), the Gram matrices K*K^T and Q*K^T (C x C), a forward substitution over t for delta_t, and one rank-C state update S_C = gamma_C*S_0 + K^T * (w * Delta). Avoid dividing by gamma (use ratios gamma_t/gamma_u built by products). Implement it in float32.
3. A variant of the block form in which every product that has an FP32 operand (S_0, Delta) is computed the way an AMX kernel would: split each FP32 value x into three bf16-representable float32 values hi + mid + lo = x (hi = round_bf16(x), mid = round_bf16(x - hi), lo = x - hi - mid) and sum the three products. Check with exhaustive-style random tests (at least 10 million random float32 values across exponents, plus edge cases: values near powers of two, ties, tiny values, large values) whether hi + mid + lo == x exactly and whether lo is always bf16-representable. Report the failure cases if any.
Checks to run and report (C = 8, 16, 32, 64, 128; head geometry 128 x 128; realistic random inputs: unit-norm bf16 k and q, v of magnitude about 0.01 to 1, decay in 0.9 to 1.0 and also a hard case 0.3 to 1.0, beta in 0 to 1; start from a random state of magnitude about 0.01; run chains of at least 1024 tokens so that drift can show):
 a. max absolute and max relative difference between block form and token-by-token form, for the outputs o_t and for the final state, in float32, and the same with float64 arithmetic (to prove the algebra);
 b. how many of the bf16-rounded outputs (round o_t to bf16, as the postprocess does first) differ between the two forms, out of how many;
 c. the same for variant 3 (three-way split) against the token-by-token form;
 d. the same for a two-way split (hi + mid only), to show what the third piece buys;
 e. whether the 1e-7 absolute tolerance of F11 would hold at state and output magnitudes like the test's (outputs about 0.001 to 0.004, states about 0.006 to 0.024);
 f. what happens when the decays are small enough for gamma to underflow inside one chunk.
Return the numbers the script printed. Do not round them away. Say plainly which checks failed.`, { label: 'prototype:block-form', phase: 'Propose', schema: PROTO_SCHEMA }))

const proposed = await parallel(proposeThunks)
const designs = proposed.slice(0, DESIGNERS.length).map((r, i) => ({ key: DESIGNERS[i].key, design: r })).filter(x => x.design)
const proto = proposed[DESIGNERS.length]
log(`designs: ${designs.length}/${DESIGNERS.length}; prototype: ${proto ? 'ok' : 'missing'}`)

phase('Synthesize')
const spec = await agent(`${FACTS}\nYOU ARE THE LEAD DESIGNER. Three designers worked independently, and one engineer built a numeric prototype of the block-form math. Merge their work into ONE design specification.
Rules: keep what is supported by code citations, arithmetic, or the prototype's numbers. Where designers disagree, pick a side and record the disagreement and your reason. Where the prototype contradicts a designer, the prototype wins unless its setup is wrong (say why). Do not invent numbers: every cost number must show its arithmetic from the instruction costs C1-C3 or from M1. Keep estimates labeled "est.". Reject components whose gain is not supported. The specification must say plainly for each kind of work (GDN prefill, GDN decode, full attention prefill, full attention decode, other host kernels) whether AMX helps, by about how much at the kernel level (est.), and why.
List every load-bearing claim in 'claims' so that verifiers can attack each one.

DESIGNS (JSON):\n${JSON.stringify(designs)}\n\nPROTOTYPE (JSON):\n${JSON.stringify(proto)}`, { label: 'synthesize', phase: 'Synthesize', schema: SPEC_SCHEMA })

if (!spec) return { designs, proto, spec: null, checks: [] }

phase('Verify')
const LENSES = [
  { key: 'math', kinds: ['math', 'numerics'], brief: `LENS: math and numerics. Re-derive the block algorithm yourself from F6 and compare it with the specification line by line. Run the prototype script again (its path is in the prototype JSON) or write your own numpy check under ${SCRATCH}/verify-math/. Attack: the algebra (decay ratios, the order of updates, whether o_t uses the state after token t), the exactness claim of any FP32-to-bf16 split, the claimed error sizes, the effect on the 1e-7 test tolerance and on the bit-pinned bf16 words test (F11), underflow, and what the first token of a sequence (state zero) needs.` },
  { key: 'cost', kinds: ['cost'], brief: `LENS: the cost model. Recount every TDPBF16PS, tile load, tile store and AVX-512 operation of each kernel in the specification from the tile shapes (a tile is 16 rows x 64 bytes; TDPBF16PS takes A 16 x 32 bf16 and B 16 pair-rows x 16 columns). Check that 8 tile registers suffice for the loop order claimed. Recompute cycles per token with C1-C3, write the arithmetic, and compare with M1 (8,600 cycles per value head per token measured today). Attack: forgotten work (packing K, Q, Delta into tile layouts; the split passes; scaling by the decay; copies between tile buffers and vectors; the per-chunk start and end copies of the working state), memory traffic through L1 (48 KiB) and L2 (2 MiB), the clock drop C4, and whether the claimed speedup survives them. Put scripts under ${SCRATCH}/verify-cost/.` },
  { key: 'code', kinds: ['code', 'other'], brief: `LENS: fit to the tron code. Open every file and line the specification cites. Attack: whether a block path can really be entered where the specification says (what run_gdn_operation and gdn_rolling_executor::step receive per token, whether all C tokens' rows are available before the first step, whether convolution and normalization of the chunk can run first), whether the working copy and checkpoint rules still hold, how the existing AMX gate and tile configuration code can be reused from the GDN code (which runs on the main thread and main helpers, not on attention workers), which tests would fail, and whether the list of files for the 256-wide attention kernel is complete (compare with how head width and group size are hard-coded in amx_attn.cpp and amx_attn_iface.hpp).` },
]
const checks = await parallel(LENSES.map(l => () =>
  agent(`${FACTS}\nYOU ARE A VERIFIER. Try to REFUTE the design specification below through your lens. Default to 'unverifiable' when you cannot check a claim; never accept on plausibility.\n${l.brief}\nGive a verdict for every claim whose kind is one of [${l.kinds.join(', ')}], and for any other claim you find wrong. Then list new problems the specification missed.\n\nSPECIFICATION (JSON):\n${JSON.stringify(spec)}\n\nPROTOTYPE RESULT (JSON):\n${JSON.stringify(proto)}`, { label: `verify:${l.key}`, phase: 'Verify', schema: VERDICT_SCHEMA })
    .then(v => ({ lens: l.key, check: v }))))

return { designs, proto, spec, checks: checks.filter(Boolean) }
