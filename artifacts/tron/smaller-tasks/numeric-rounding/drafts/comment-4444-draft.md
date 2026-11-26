<!--
DRAFT. Not posted. Posting needs jhan's go. Delete this block before posting.
Written 2026-11-23 by the session that wrote the handoff.
Target: a comment on https://github.com/positron-ai/tron/issues/4444
jhan asked for an update of our issue "if you believe it is tightly related". The session's judgment: the two
issues are related through item 3 only, not tightly. So nothing was posted. This text is a cross-reference
with the data of the 2026-10-16 runs, in case jhan wants it on the issue.
Note for jhan: a comment that names #5433, #5571 and #4600 adds a "mentioned" entry with a link on those pages.
Every number was recomputed on 2026-11-23 from the per-step files of the campaign records td-20261016,
td2-20261016 and glimext-20261018.
-->

## Related: issue #5433 (GatedDeltaNet rounding) holds a written rule of the kind that item 3 asks for (2026-11-23)

**Short version.** Issue #5433 removes six bf16 roundings of the GatedDeltaNet layer of Qwen3.5 and decides by measurement whether eight more go. Its second comment fixes the decision rule before any run: speed tests, a limit on the mean TVD, and tests on the loss. Item 3 of this issue (a model-level bound) has no such rule, the forced runs made for this issue give data in the same unit, and the two issues share no code and no decision.

**Words used here.** TVD is the total variation distance between two next-token probability distributions (0 means identical). A forced run feeds two binaries the same tokens, so they score the same text at every step. P are the softmax weights of attention. The kill switch is `TRON_AMX_DISABLE=1`. The margin is the gap between the two best scores of a step. The Transformers model is the Hugging Face reference implementation of a model. A golden-logit test compares the scores of a tron run with stored scores of that reference. The loss is the mean negative log-probability of the next token of a given text.

### What is shared, and what is not

| | This issue | #5433 |
|---|---|---|
| Code | attention: the AVX-512 dotter, the AMX kernels, the weights-times-values loop | the GatedDeltaNet host code |
| What is compared | two tron paths: AMX on against the kill switch or the row-major binary | tron against the Transformers model in BF16, and three tron builds against each other |
| The numeric difference | the order of the fp32 adds, and P truncated to bf16 (AVX-512) against P rounded to nearest (AMX) | a round-to-bf16 call that is present or absent at 14 points |
| Decision rule | none written | written before the runs ([comment](https://github.com/positron-ai/tron/issues/5433#issuecomment-7083755152)) |
| State | item 2 (kill-switch contract) and item 3 are open | nothing is measured yet |

### Data from the forced runs of this issue, in the unit of that TVD test

These values are new on this issue. Mean TVD per forced step over 256 steps, 1 user, CPU attention. The qwen3-4b rows come from forced runs of 2026-10-16: main `72308ec90c` and the PR #4959 implementation commit `ea94e95a4e`. The test build of the second and third rows is that commit with one change: the AMX kernel truncates P, as the AVX-512 path does. The Glimmer row comes from the forced runs of the [comment of 2026-10-18](https://github.com/positron-ai/tron/issues/4444#issuecomment-6255615621). The records are with the author.

| Model, prompt length, pair | What differs | Mean TVD | Largest TVD | Steps with another best token |
|---|---|---|---|---|
| qwen3-4b, prompt 1,024: AMX on against the kill switch, main | add order and rounding of P | 0.0059 | 0.032 | 2 of 256 |
| qwen3-4b, prompt 1,024: P rounded against P truncated, same add order | rounding of P only | 0.0060 | 0.057 | 0 |
| qwen3-4b, prompt 1,024: AMX add order against AVX-512 add order, P truncated in both | add order only | 0.0053 | 0.049 | 1 |
| qwen3-4b, prompt 1,024: row-major binary against main with the kill switch | nothing | 0 | 0 | 0 |
| qwen3-4b, prompt 1,024: AMX on against the kill switch, commit `ea94e95a4e` | add order and rounding of P | 0.0060 | 0.055 | 1 |
| qwen3-4b, prompt 8,192: the same pair, the same commit | add order and rounding of P | 0.0000081 | 0.0017 | 0 |
| Muse Glimmer 30B, prompt 1,024: AVX-512 against AMX (PR #5015) | add order and rounding of P | 0.018 | 0.49 | 3 |

What the table says:

- A change of the add order alone gives nearly the same mean TVD as the change of the rounding of P alone (0.0053 against 0.0060).
- The same pair of runs gives a mean TVD about 700 times smaller at prompt 8,192 than at prompt 1,024. The median margin is 19.75 logit units at prompt 8,192 and 3.9 at prompt 1,024. So the mean TVD of one pair depends strongly on the text.
- Hypothesis, not measured: a rule of the form "one tenth of a reference distance" can give different verdicts on two texts. The measurement that would test it is the reference distance on both texts.
- Every row is a distance between two tron runs. Our records hold no distance of a tron run to a Transformers model on a text with full 64-token pages.

### What item 3 needs before it can adopt that rule

1. The pair: AMX on against the kill switch of one binary. This is valid for row-major K only. At main `72308ec90c` the kill-switch run equals the row-major binary in all 256 compared score vectors. With the VNNI K layout the kill switch does not give the numerics of the row-major binary (item 2), so there the pair needs the row-major binary itself.
2. The reference distance: a kill-switch run against a Transformers reference on the same text. It is not measured. The weights and the number format of that reference must be stated (#5433 uses BF16 for Qwen3.5). The golden-logit tests `t_generate_ingest_1_llama` and `t_generate_ingest_1_muse_glimmer` force 21 and 9 tokens, so they reach no AMX kernel. Other golden-logit tests on main were not checked for this.
3. A text with full pages, and a stated choice of its positions, for the reason in the second bullet above.
4. A given text for the loss tests. The forced runs above fed the model its own output, so they hold no loss.

### Links

- #4600 is the open issue for the truncation of P on the AVX-512 path. It names this issue. The truncation is still on main (`f454423b09`).
- #5433 and its trial, draft PR #5571, change no attention file.
