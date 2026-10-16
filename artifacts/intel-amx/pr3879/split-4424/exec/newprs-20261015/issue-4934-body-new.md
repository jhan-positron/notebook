## Short version

With the AMX kill switch (`TRON_AMX_DISABLE=1`), the binary of PR #4959 (the row-major tail block, the last PR of the four-PR stack that replaces PR #4424) decodes qwen-3-4b 2.7 to 3.7 % slower at tp2 than the binary of its parent PR #4958, in three runs on three days. Against `main` with the same switch, PR #4959 is inside the noise band in decode TPS in every measured cell, so the stack does not lose decode throughput against `main` on the kill-switch path, but PR #4959 gives up most of the gain PR #4958 had there. A probe build that defers the construction of the dotters recovers 2.0 to 2.3 points at tp2 with prompt 1,024 tokens, and 1.3 to 1.8 % against the parent remains without a measured cause.

## Words used here

| Term | Meaning |
|---|---|
| the stack | Four PRs, each based on the preceding one: #4956 (VNNI K layout and its AVX-512 reader), #4957 (AMX QK kernel), #4958 (shared 16-token block saves), #4959 (row-major tail block, option on in the `deb` preset). |
| kill switch | `TRON_AMX_DISABLE=1`: the AMX kernels are off at run time inside the same binary. The same software path serves a host without AMX. |
| the reader, the dotter | The reader is `k_vnni::qk_group`, the AVX-512 routine that scores a query group against the VNNI-packed blocks of a page. The dotter is the per-token dot product over a row-major K row (`h/tron/kernels/dotter.hpp`), which scores the rows of a row-major tail block through `row_major_row`. |
| tail block | PR #4959 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes and converts it to the VNNI layout at the forward end of the pass that saves its 16th row (`convert_pending_k_blocks` in `h/tron/models/model.hpp`). |
| baseoff, headoff, newoff, lazyoff | runtron builds with the kill switch: `main` at `72308ec90c`, PR #4958 at `dfafd13dce`, PR #4959 at `ea94e95a4e`, and the deferred-dotter probe `ca6456b7dc` (on `ea94e95a4e`). |
| cell, band | A cell is qwen-3-4b, 8 users, 256 generated tokens, software attention (`USE_HW_ATTN=0`), at tp2 with prompt 1,024 or 8,192 tokens, or tp4 with prompt 1,024 tokens, 3 repetitions in alternating order. The band is twice the larger sample standard deviation of the two arms, at least 0.40 TPS or 0.15 s. A difference beyond it counts as a change. |
| TPS, TTFT | Decode tokens per second per user, and the prefill time of the whole prompt in seconds. |

## Measurements

All on delphi-3bda (Xeon 6962P), half of the machine, by runtron. The decode loss of PR #4959 against PR #4958, both with the kill switch (`newoff` vs `headoff`):

| date | record | tp2, prompt 1,024 | tp2, prompt 8,192 | tp4, prompt 1,024 | TTFT at tp2, prompt 8,192 |
|---|---|---|---|---|---|
| 2026-10-12 | `exec/results/pr4-E-cpu/summary.md` | -3.4 % (band 0.46 TPS, beyond) | -2.9 % (band 0.40, beyond) | -2.0 % (band 1.00, beyond) | +453 ms (beyond 0.21 s) |
| 2026-10-13 | `exec/results/pr4lazy-E-cpu/summary.md` | -3.7 % (beyond) | -3.1 % (beyond) | -1.2 % (band 1.16, beyond) | +521 ms (beyond) |
| 2026-10-14 | `exec/results/pr4off-E-cpu/summary.md` | -3.3 % (75.83 to 73.36 TPS, band 0.60, beyond) | -2.7 % (15.37 to 14.96 TPS, band 0.40, beyond) | -0.5 % (111.63 to 111.07 TPS, band 0.80, inside) | +587 ms (117.27 to 117.86 s, beyond 0.20 s) |

The same binaries with AMX on (`new` vs `head`, 2026-10-12): -0.7 %, +0.2 % and -0.5 % TPS, all inside the band. The loss is specific to the kill-switch path.

Against `main` with the kill switch (2026-10-14, the same record):

| pair | tp2, prompt 1,024 | tp2, prompt 8,192 | tp4, prompt 1,024 |
|---|---|---|---|
| PR #4958 vs `main` (`headoff` vs `baseoff`) | +4.1 % (beyond) | +5.5 % (beyond) | -0.0 % (inside) |
| PR #4959 vs `main` (`newoff` vs `baseoff`) | +0.7 % (inside) | +2.7 % (0.39 TPS, under the 0.40 TPS floor, inside) | -0.5 % (inside) |
| probe vs `main` (`lazyoff` vs `baseoff`) | +2.7 % (beyond) | +3.6 % (beyond) | -0.4 % (inside) |

TTFT of PR #4959 against `main` with the kill switch: 79 ms and 68 ms faster at prompt 1,024 (inside the 0.15 s floor), 4.98 s faster at prompt 8,192 (beyond the 0.44 s band).

Only qwen-3-4b (128-dimension heads, 4 query heads per KV head) is measured. Other models with 128-dimension heads (llama-3.1-8b, llama-3.2-3b, qwen-3-30b-a3b) are not measured with the kill switch at PR #4959. gpt-oss-120b has 64-dimension heads, for which the layout is compiled out.

## What was tried

The probe build `ca6456b7dc` (19 insertions, 7 deletions in `h/tron/models/self_attention.hpp`) constructs the dotters of a page at its first row-major token instead of at every page visit. Against PR #4959 with the kill switch it recovers +2.3 %, +1.6 % and +0.2 % TPS (2026-10-13) and +2.0 %, +0.9 % and +0.2 % (2026-10-14) in the three cells, the first beyond the band each time. It costs nothing measurable with AMX on. From the 2026-10-14 means it still trails PR #4958 by 1.3 %, 1.8 % and 0.3 %. It is not in PR #4959. Its code comment is wrong for the measured specialization: the bf16, 128-dimension dotter does not convert the query row to fp32 at construction (`dotter.hpp`, the four 512-bit loads), so the comment needs a fix before the change joins a PR.

## Leads

The kill-switch path differs between the two binaries only in the software scoring loop of `h/tron/models/self_attention.hpp` (68 insertions, 17 deletions between `dfafd13dce` and `ea94e95a4e`), in the per-row store, and in the forward-end conversion. Each lead below is a hypothesis with the measurement that settles it.

1. Dotter construction per page visit (H2). PR #4958 built no dotters for a VNNI slot. PR #4959 builds one dotter per query head of the group at every page visit, for every page of every layer. Measured by the probe: it explains 2.0 to 2.3 points at tp2 with prompt 1,024 and 0.9 to 1.6 points with prompt 8,192. Fix candidate: the probe change, with its comment corrected.
2. A layout test per relevant token (H1). The loop now tests the block's layout bit for every relevant token (`vnni_blocks & block_bit(i / 16)`) and branches between the live mask and the dotter, and it tests `plane` for every token. PR #4958 only set a bit per token. At prompt 8,192 this is about 19 million extra tests per decode step over the 8 users (8,192 tokens, 8 KV heads, 36 layers), est. a few tenths of a percent of a 67 ms step if the branches predict well. Settling measurement: a probe build that expands the 4 block bits into a 64-bit token mask once per page, scores the VNNI tokens through the mask and the row-major rows after the loop, run in the three cells with the kill switch.
3. The forward-end conversion (H3). `convert_pending_k_blocks` runs on the main thread after the join and converts every block a decode step completed, for every KV head. With 8 users it rewrites about 0.6 MiB per step in place (est.: 16 rows, 8 KV heads, 36 layers, 256 bytes per row, one block per user per 16 steps). It is serial, so its cost is est. 0.1 to 0.9 % of a step at tp2 with prompt 1,024 (13.6 ms per step) and less at prompt 8,192. Settling measurement: a Perfetto trace of the existing `convert_k_blocks` span (`model.hpp`) in a kill-switch run.
4. Not a lead: the per-step K store. PR #4959 writes a decode token's K row as one row-major row of 4 cache lines, where PR #4958 wrote it across 64 lines of the VNNI layout. The store got cheaper, and the conversion in lead 3 is its counterpart.

A Perfetto trace of the attention spans of the three binaries in one kill-switch cell (tp2, prompt 1,024) attributes the remainder between leads 2 and 3 in one run.

Related observation from the same binaries: the prefill of 8,192 tokens is 453 to 587 ms slower than PR #4958 with the kill switch (both go through the shared block save of PR #4958), and PR #4958 itself was 599 ms slower than PR #4957 there. Neither has a measured cause. The same trace run covers the K-store spans.

## Records

Results and per-run logs: `exec/results/pr4-E-cpu/`, `exec/results/pr4lazy-E-cpu/`, `exec/results/pr4off-E-cpu/` (summary.md and rt-results.txt with the binaries' sha256 and version lines) in jhan's intel-AMX workspace. The PR #4959 description, section Performance, carries the 2026-10-12 and 2026-10-14 numbers.

