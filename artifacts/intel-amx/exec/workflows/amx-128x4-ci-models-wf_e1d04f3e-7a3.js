export const meta = {
  name: 'amx-128x4-ci-models',
  description: 'Verify which nightly-CI models have head size 128 and kv_mul 4 (AMX shape), with adversarial refutation',
  phases: [
    { title: 'Derive', detail: 'one agent per base model: geometry from tron plugin + HF config' },
    { title: 'Refute', detail: 'one skeptic per model tries to overturn the verdict' },
    { title: 'Critic', detail: 'completeness check on the 12-model list and caveats' },
  ],
}

const MODELS = args.models
const CTX = args.context

const DERIVE_SCHEMA = {
  type: 'object',
  properties: {
    model_slug: { type: 'string' },
    tron_plugin: { type: 'string' },
    tron_evidence: { type: 'string', description: 'file:line citations for n_heads, n_kv_heads, head_size in tron' },
    n_heads: { type: 'integer' },
    n_kv_heads: { type: 'integer' },
    head_size: { type: 'integer' },
    kv_mul: { type: 'integer' },
    per_kernel_geometries: { type: 'array', items: { type: 'object', properties: {
      n_heads: { type: 'integer' }, n_kv_heads: { type: 'integer' }, head_size: { type: 'integer' }, kv_mul: { type: 'integer' }, layers_using_it: { type: 'integer' } }, required: ['n_heads','n_kv_heads','head_size','kv_mul'] } },
    hf_n_heads: { type: 'integer' },
    hf_n_kv_heads: { type: 'integer' },
    hf_head_dim: { type: 'integer' },
    hf_evidence: { type: 'string' },
    hf_matches_tron: { type: 'boolean' },
    ci_executors: { type: 'array', items: { type: 'string' } },
    executor_stores_bf16: { type: 'boolean' },
    fits_128x4: { type: 'boolean' },
    reason: { type: 'string' },
    caveats: { type: 'array', items: { type: 'string' } },
  },
  required: ['model_slug','tron_plugin','tron_evidence','n_heads','n_kv_heads','head_size','kv_mul','per_kernel_geometries','hf_n_heads','hf_n_kv_heads','hf_head_dim','hf_evidence','hf_matches_tron','ci_executors','executor_stores_bf16','fits_128x4','reason','caveats'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    model_slug: { type: 'string' },
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high','medium','low'] },
    what_was_checked: { type: 'array', items: { type: 'string' } },
    reasoning: { type: 'string' },
    evidence: { type: 'string', description: 'file:line citations' },
    extra_caveats: { type: 'array', items: { type: 'string' } },
  },
  required: ['model_slug','refuted','confidence','what_was_checked','reasoning','evidence','extra_caveats'],
}

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    twelve_run_list_confirmed: { type: 'boolean' },
    twelve_run_list: { type: 'array', items: { type: 'string' } },
    other_ci_model_lists: { type: 'array', items: { type: 'string' }, description: 'functional/soak/mmlu lists and whether they add any base model not in the perf list' },
    issues: { type: 'array', items: { type: 'string' } },
    caveats_for_answer: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'string' },
  },
  required: ['twelve_run_list_confirmed','twelve_run_list','other_ci_model_lists','issues','caveats_for_answer','evidence'],
}

function derivePrompt(m) {
  return `You are verifying attention geometry for ONE model that the Positron nightly CI runs on delphi-3bda. Work read-only. Do not modify any file. Do not ssh anywhere.

Question being answered: does this model have the "128x4" attention shape that tron's AMX attention kernel serves, meaning head size 128 (dims per head) AND kv_mul 4 (query heads per KV head)?

The gate in tron: ${CTX.gate_file} lines 145-165: shape_ok(model_head_size, model_kv_mul) = head_size == 128 && kv_mul == 4; eligible() also requires the executor's activation scalar to be bf16 (tp*/perm_tp*/host_bf16 are bf16; host is float; host_fp16 is fp16). The dispatch site (${CTX.dispatch_file} ~lines 1236-1238) passes PER-ATTENTION-KERNEL geometry: geometry.kv.head_size and geometry.kv_mul(). self_attention.hpp:207 defines kv_mul = n_heads / n_kv_heads.

Model to check:
- CI shape slug(s): ${m.slugs.join(', ')}  (CI executors: ${m.executors.join(', ')})
- tron model name (config/models.yaml): ${m.tron_name}
- Where tron defines its compiled geometry: ${m.tron_def}
- HuggingFace config.json for the weights the CI uses: ${m.hf_config}
- tron repo checkout: ${CTX.tron_repo} (branch jhan-amx-p0)

Steps:
1. Read the tron definition. For TRON_LLAMA_CONFIG lines the field order is (name, type, dim, hidden_dim, n_layers, n_heads, n_kv_heads, vocab_size, head_size, attention_scale, n_experts, n_shared_experts, n_routed_experts_chosen, rope_scaling) — verify that order yourself against the llm_configuration struct at ${CTX.tron_repo}/h/tron/plugins/llama.hpp lines 140-153 before trusting it. For generated headers read n_heads, n_kv_heads, head_size AND the attention_kernels array (there may be more than one kv_geometry; report each, and count how many attention_operations use each kernel id).
2. Read the HF config.json (use text_config if present). Record num_attention_heads, num_key_value_heads, head_dim (or hidden_size/num_attention_heads when head_dim is absent). For gemma-4 also record global_head_dim and num_global_key_value_heads.
3. Confirm the CI executors' activation scalar is bf16: check ${CTX.tron_repo}/h/tron/models/common.hpp lines 85-100 (tp2/tp4/perm_tp2/perm_tp4 definitions) and the query_scalar_ok comment in the gate file.
4. Decide fits_128x4 per the gate: true only if at least one attention kernel geometry has head_size 128 and kv_mul 4. If the model has several geometries, say which ones fit.
5. List caveats you noticed that a careful reader should know (for example: the compiled plugin is generated from a different HF id than the weights; a per-layer geometry mix; force_hw_attn set true in the plugin; hardware capability markers).

Return only the structured result. Cite file:line for every number.`
}

function refutePrompt(d, m) {
  return `You are an adversarial reviewer. A previous agent claimed the following about the nightly-CI model ${m.slugs.join(', ')} (tron model ${m.tron_name}):

${JSON.stringify(d, null, 2)}

The claim under test: fits_128x4 = ${d.fits_128x4}, meaning "${d.fits_128x4 ? 'this model HAS' : 'this model does NOT have'} an attention kernel geometry with head size 128 and kv_mul 4 (query heads per KV head), which is the only shape tron's AMX attention kernel serves (${CTX.gate_file} lines 145-165)".

Try hard to REFUTE the claim. Work read-only in ${CTX.tron_repo} (branch jhan-amx-p0), ${CTX.systems_test_repo}, and the HF cache ${CTX.hf_cache}. Do not modify files. Do not ssh anywhere.

Check at least these angles, and report each one you checked:
a) Wrong source: is ${m.tron_def} really the plugin the CI slug compiles to? Follow config/models.yaml (model name -> variant slug -> executors) and gen/src/tron/h/tron/plugins.hpp / gen/selected_models.cmake. If the CI slug maps to a different plugin (for example an "ingested_" generated variant instead of the hand-written TRON_LLAMA_CONFIG), re-derive from the right one.
b) Wrong arithmetic or field order: recompute kv_mul = n_heads / n_kv_heads from the raw source text yourself.
c) Tensor parallelism: does tp2/tp4/perm_tp2/perm_tp4 change the head_size or kv_mul that reaches the gate? Look at how self_attention.hpp gets n_heads/n_kv_heads (compile-time from the plugin, lines ~200-215) and whether any executor divides heads per device.
d) Multiple geometries: does the plugin declare more than one attention kernel geometry (heterogeneous cache, sliding vs global layers)? Does any of them fit 128x4 when the claim says none do, or vice versa?
e) HF config disagreement: does the HF config.json for the CI weights disagree with tron's compiled numbers? If so, which one governs the gate? (The gate uses compile-time plugin constants.)
f) Any enforce_config / json_enforce check that would reject the model at load if geometry disagreed (llama.hpp lines 335-350).

Default to refuted=true only if you find concrete evidence (file:line) that the fits_128x4 boolean is wrong. If the boolean is right but a detail (a number, a citation, a caveat) is wrong, set refuted=false and put the correction in extra_caveats.

Return only the structured result.`
}

phase('Derive')
const results = await pipeline(
  MODELS,
  m => agent(derivePrompt(m), { label: `derive:${m.tron_name}`, phase: 'Derive', schema: DERIVE_SCHEMA }),
  (d, m) => d ? agent(refutePrompt(d, m), { label: `refute:${m.tron_name}`, phase: 'Refute', schema: VERDICT_SCHEMA, effort: 'high' })
      .then(v => ({ model: m, derived: d, verdict: v })) : null,
)

const rows = results.filter(Boolean)
log(`derived+refuted ${rows.length}/${MODELS.length} models`)
const dropped = MODELS.filter(m => !rows.find(r => r.model.tron_name === m.tron_name)).map(m => m.tron_name)
if (dropped.length) log(`DROPPED (agent returned null): ${dropped.join(', ')}`)

phase('Critic')
const critic = await agent(`You are a completeness critic for this question from the user: "Of the 12 models which the nightly CI runs, which are 128x4 shape to fit AMX? KV head size = 12, kv_mul = 4" (we read "KV head size = 12" as head size 128, the tron AMX kernel's constant HEAD_SIZE_128).

Facts already gathered (verify them, do not assume):
- Nightly CI on delphi-3bda = GitHub workflow ${CTX.systems_test_repo}/.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml, PLATFORM_TYPE granite_rapids_72_rinzler, runs 'uv run system_ci'.
- The perf phase iterates 'configs' in ${CTX.systems_test_repo}/scripts/perf.py (12 entries). goal.tps for granite_rapids_72_rinzler in scripts/system_ci.py has 12 keys. thresholds/system_ci_perf.yaml lists 11 for that platform (gemma-4 absent).
- Per-model verdicts so far: ${JSON.stringify(rows.map(r => ({ slugs: r.model.slugs, tron: r.model.tron_name, fits_128x4: r.derived.fits_128x4, head_size: r.derived.head_size, kv_mul: r.derived.kv_mul, refuted: r.verdict && r.verdict.refuted })))}
${dropped.length ? `- Models with no verdict (agent failure): ${dropped.join(', ')}` : ''}

Tasks (read-only; do not modify files; do not ssh):
1. Confirm the "12 models" interpretation: list the 12 perf configs exactly (slug + users) from scripts/perf.py, and check whether the perf phase filters any out for this platform (search system_ci.py / perf.py for platform-specific skips, PLATFORM_TYPE checks, or 'configs' filtering). State how many DISTINCT base models the 12 entries cover.
2. Check the other CI model lists in scripts/system_ci.py (FUNCTIONAL_TEST_MODELS, SOAK_MODELS, MMLU list in thresholds/system_ci_mmlu_pro.yaml or test_mmlu) and report whether any base model appears there that is not in the perf list.
3. Look for anything that would make the shape answer misleading for the user's purpose (they care about which CI models can use the AMX attention path). Examples to check in ${CTX.tron_repo} (branch jhan-amx-p0): TRON_AMX_DISPATCH is a CMake option default OFF (h/tron/kernels/amx_attn_iface.hpp Note [AMX attention dispatch]); the CI installs the apt 'tron' package (check whether ${CTX.tron_main_repo} on main even contains src/tron/kernels/amx_attn.cpp); plugins with force_hw_attn = true or attention_hardware_capability values that route attention to FPGA hardware instead of the software path where the AMX gate lives (check the 3 models flagged fits_128x4=true: their generated/hand-written plugins and what 'legacy_uniform_cache' vs 'software_only' means in h/tron/models/model.hpp Note [Hardware attention eligibility]).
4. Report issues with the gathered facts, and a short list of caveats the final answer should carry. Cite file:line.

Return only the structured result.`, { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA, effort: 'high' })

return { rows, dropped, critic }