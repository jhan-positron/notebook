<!--
DRAFT. Not posted. Posting needs jhan's go. Delete this block before posting.
Written 2026-11-23 by the session that wrote the handoff.
Target: a comment on https://github.com/positron-ai/tron/issues/5433
Before posting:
- Replace "draft PR #5572" by the PR that then holds the block kernel. The split closes PR #5572. Its branch
  `jhan-gdn-amx` stays.
- Replace the values marked "est." by measured values (questions N1 and N4 of the handoff), or keep them marked.
- jhan decides whether a comment or a chat message carries this.
-->

## A second use of one of these roundings: the AMX block kernel for GatedDeltaNet (draft PR #5572)

**Short version.** The issue names one known use of the 14 roundings. Draft PR #5572 holds a second use of one of them: its AMX kernel for the recurrence reads the normalized key and query as bf16 values. One question follows: is the rounding of the normalized product among the six that are removed in every outcome?

**Words used here.** AMX is Intel's tile-matrix instruction set. A tile product is one execution of TDPBF16PS, which multiplies two tiles of bf16 values and adds the products into FP32 values. bf16 is the 16-bit float format with 8 significant bits. FP32 is the 32-bit float format. The block kernel is the AMX kernel of draft PR #5572. It advances a full window of 32 prompt tokens. The chain kernel is the AVX-512 kernel of the same PR. Its results are bit-identical to those of `gdn_recurrence`. TTFT is the time to first token. Prefill is the processing of the prompt.

### Which rounding, and how the kernel uses it

- The rounding is the last one of `normalize_gdn`: the normalized product, which the recurrence reads as key and query.
- The block kernel packs the key and the query for the tile products by keeping the upper 16 bits of each FP32 value. This loses nothing only when the value is already a bf16 value.
- The other operands do not depend on a rounding. The kernel reads the value, the decay and beta as FP32. It splits the recurrent matrix into three bf16 pieces that add up exactly.

### What the block kernel gains today

Measured on a Xeon 6962P with 4 FPGA cards, Qwen3.5 4B, on 2026-11-22. Both columns come from one binary. It was built from a local earlier version of commit `775bba7661` of the PR (the two differ in comments, tests and two README files only), on the head of #3696 (`72e1191804`). The chain column sets a switch that turns only the block kernel off. Medians of 3 runs. With 8 users the time is that of the slowest user.

| Users | Prompt length (tokens) | TTFT with the chain kernel (s) | TTFT with the block kernel (s) | Fall |
|---|---|---|---|---|
| 1 | 1,024 | 0.330 | 0.293 | 11.2 % |
| 1 | 4,096 | 1.683 | 1.537 | 8.7 % |
| 1 | 8,192 | 4.288 | 3.990 | 6.9 % |
| 8 | 1,024 | 2.486 | 2.184 | 12.1 % |
| 8 | 4,096 | 12.596 | 11.384 | 9.6 % |
| 8 | 8,192 | 32.415 | 29.939 | 7.6 % |

- The block kernel runs in prefill only. Decode speed does not change.
- The server is shared. Before each run the CPUs of the test were at most 0.1 % busy, and the other CPU socket was 42.4 to 42.5 % busy.
- The description of PR #5572 has no column for this switch. Its chain-kernel column is another binary, so its values differ by up to 0.02 s.

### What happens without that rounding

- As the kernel is written, it would truncate the key and the query: each value moves toward zero by less than 2^-7 of itself (0.78 %).
- est., from a float64 model of the recurrence, not from a run of the kernel: the recurrent matrix then differs from the chain kernel by about 0.3 % (3e-3 as the length of the difference divided by the length of the matrix). The measured difference today is 5e-8 to 4e-7.

### Ways to adapt, on our side

| Way | Tile products per value head per token | Difference of the key and query from their FP32 values |
|---|---|---|
| today | 18.5 | none, because they are bf16 values |
| our kernel rounds its own copy of the key and the query to nearest. The layer does not change. | 18.5 | at most 2^-8 of a value |
| the key and query are split into 2 bf16 pieces | 38.0 | at most 2^-15 |
| the key and query are split into 3 bf16 pieces | 58.5 | none |

- The counts are derived from the loops of the kernel. They hold for 2 value heads per key head, as in Qwen3.5 4B. The time of the last two ways is not measured.
- est., from a float64 model, not from a run of the kernel: with the second way about half of the bf16 output words differ from the chain kernel (46 to 54 %). Today the share is 0.006 to 0.034 % (measured).
