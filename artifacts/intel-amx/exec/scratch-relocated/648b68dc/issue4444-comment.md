## Muse Glimmer 30B (kv_mul 16, PR #5015): the same divergence pattern, with its near-tie measurement (2026-10-18)

**Short version.** PR #5015 makes the AMX kernels serve Muse Glimmer 30B (head size 128, 16 query heads per KV head), whose 39 sliding-window layers always run on the CPU. Against the merge-base binary (main 6198824246, AVX loop on those layers) the PR head generates different tokens after 5 to 53 steps, and the kill switch (`TRON_AMX_DISABLE=1`) reproduces the base tokens exactly in every cell. Teacher-forced logits at the first divergence show that the base binary's best token led by 1.31 logit units (21 bf16 ulps) at the divergence step and that the head binary moved that pair by -1.56, so the order flipped; in teacher-forced mode the two binaries disagree on the argmax at 3 of 256 steps.

**Words used here.** base = runtron built from main 6198824246 (row-major K, AVX dotter on every CPU-scored token, the AMX gate refuses Glimmer). head = runtron built from PR #5015's head 5061623a34 (the AMX kernel scores Glimmer's dense 64-token pages on the 39 sliding-window layers). headoff = head with the kill switch. head2 = head run a second time. Both binaries come from one build recipe on the Granite Rapids test machine (plain shell, clang 19.1.7, `-DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`). Every run: 1 user, temperature 0, `--pay-for-determinism`, seed 1, 256 generated tokens; FPGA attention = the model default (13 full layers on the card), CPU attention = `USE_HW_ATTN=0`.

### Token identity, base vs head

| Model, attention, prompt | head vs head2 (A/A) | headoff vs base (kill switch) | head vs base |
|---|---|---|---|
| Glimmer tp2, FPGA attention, prompt 1024 | identical, 256 of 256 | identical, 256 of 256 | first difference at generated token 5 (249 of 256 positions differ after it) |
| Glimmer tp2, CPU attention, prompt 1024 | identical | identical | first difference at token 53 (200 of 256 differ) |
| Glimmer tp2, FPGA attention, prompt 2048 | identical | identical | first difference at token 12 (243 of 256 differ) |
| Glimmer tp4, FPGA attention, prompt 1024 | identical | identical | first difference at token 30 (224 of 256 differ) |
| llama-3.1-8b tp2, CPU attention, prompt 1024 (kv_mul 4, the same AMX kernel in both binaries) | identical | base vs headoff: first difference at token 12 | identical, 256 of 256 |
| qwen3-4b tp2, FPGA attention, prompt 1024 | identical | identical | identical |
| gpt-oss-120b tp4, FPGA attention, prompt 1024 (head size 64, never AMX) | identical | identical | identical |

What the table says:

- On Glimmer the kill switch gives the base binary's tokens exactly, in all four cells. So the PR changes tokens only where the AMX kernel runs.
- The llama row is the same kernel in both binaries (the PR's 4-head instantiation compiles to the same instructions as main's kernel), so head equals base; its AMX-vs-AVX pair (base vs headoff) differs at token 12, the known pattern of this issue.
- qwen3-4b and gpt-oss-120b with FPGA attention are untouched by the PR: all pairs identical.
- Glimmer diverges earlier than qwen3-4b did on the stack PRs (step 83 at prompt 1024). Hypothesis, not measured: at kv_mul 16 the kernel scores 16 query heads per KV page, so each step has four times as many kernel-scored score rows as at kv_mul 4, which gives more chances for a near tie per step. The measurement that would test it is the per-step flip count of a forced run at both kv_mul values.

### Near tie at the first divergence (Glimmer tp2, CPU attention, prompt 1024)

Two teacher-forced runs (base and head), both fed the base arm's 256 free-running ids, with `--intermediates-file`, so every step's logits (vocabulary 202,048) are recorded. The runs took 847 s and 51 GB of records each. The prompt holds 1,025 tokens (the tokenizer adds a BOS token). Analysis: `exec/dd/dd_logits_step.py`, output `margin/steps-base-vs-head.json`.

| Quantity | Value |
|---|---|
| Steps where base and head pick a different argmax (forced mode) | 3 of 256: steps 54, 99, 104 |
| Step 54 (the free-running divergence): base top-1 minus top-2 | 1.3125 logit units = 21 bf16 ulps of the top logit 12.625 |
| Step 54: head's change of that pair | -1.5625 (the order flips; total variation distance between the two softmax rows 0.34) |
| Step 99: base margin | 0 (an exact tie); head picks the other token |
| Step 104: base margin | 4.5 logit units = 9 ulps; head's change of the pair -4.5; TVD 0.49 (the largest of the run) |
| Non-flip steps: median absolute change of the top pair | 0.75 logit units (95th percentile 3.1) |
| Non-flip steps: median of the mean absolute logit change over the vocabulary | 0.39 logit units |
| Median base margin over all steps | 69 logit units |
| Steps with identical logits | 0 of 256 |

What the numbers say:

- At the step where the free-running runs parted, the two best tokens were 21 ulps apart and the AMX path moved them by more than that. Two of the three forced-mode flips sit at wider margins than the 0 to 1 ulp ties recorded for qwen3-4b in the 2026-10-16 report of this issue (flips at steps 20, 84 and 248 there). So on Glimmer the per-step shift between the AMX and AVX paths is larger than on qwen3-4b, and the flips do not need an exact tie.
- Hypothesis, not measured: the larger shift comes from the number of layers on the changed path (39 AMX layers of 52, against 36 of 36 for qwen3-4b with CPU attention but at kv_mul 4) and from the AVX loop's truncation of the softmax weights to bf16 against the kernel's round-to-nearest (cause 2 of the 2026-10-16 report), which biases every one of those layers in the same direction. The measurement that separates the two is the one that report used: a build whose AVX path rounds like the kernel (branch jhan-td-trunc) run on Glimmer.
- None of this changes the PR #5015 verdict: the kill switch returns main's tokens exactly, and the 4-head kernel is unchanged (llama head equals base).

### Files

Scripts `exec/glimext-20261018/` (smoke.sh, margin.sh) and results `exec/results/glimext-20261018/{smoke/,margin/,identity.txt}` in the intel-AMX workspace of the test machine's NFS home; the token rows of every arm are kept (`<arm>.tokens`).
