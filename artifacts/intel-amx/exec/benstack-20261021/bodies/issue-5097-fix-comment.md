## Fix F2 measured: the cost is gone, and the first commit of PR #5047 alone carries it

### Short version

The dense-page fast path (fix F2) is on PR #5098 at head `b79dfb9fed`. Under the kill switch at prompt 8192 it makes prefill 3.135 s (3.9 %) shorter than PR #5047's head and 0.982 s (1.2 %) shorter than the base. PR #5047's first commit alone (the loop split, `e17a12ff09`) reproduces the whole cost, +2.513 s (+3.2 %), so the root cause above is confirmed at the commit level.

### The measurement

delphi-3bda, 2026-10-22, llama-3.1-8b-instruct, tensor parallel 2, CPU attention, 8 users per engine, prompt 8192, 256 generated tokens, 4 repetitions per arm. Binaries built from a plain shell with clang 19.1.7, preset native, `TRON_K_VNNI` off, `TRON_AMX_DISPATCH` on. Band: twice the larger standard deviation of the pair, at least 0.15 s prefill and 0.4 TPS decode. Result file: exec/results/i5097-20261021/results.md in the campaign record.

| arm | binary | prefill s (sd) | decode TPS per user (sd) |
|---|---|---|---|
| baseoff | PR #5047's base `a5697f86d3`, kill switch | 78.825 (0.067) | 21.37 (0.01) |
| c1off | PR #5047's first commit `e17a12ff09`, kill switch | 81.338 (0.028) | 21.42 (0.06) |
| headoff | PR #5047's head `ade89a9d9c`, kill switch | 80.977 (0.050) | 21.45 (0.03) |
| fixoff | PR #5098's head `b79dfb9fed`, kill switch | 77.842 (0.140) | 21.63 (0.02) |

| pair | prefill delta s | prefill delta % | band s | verdict |
|---|---|---|---|---|
| headoff against baseoff | +2.152 | +2.7 % | 0.150 | beyond the band (the cost this issue tracks, repeated) |
| c1off against baseoff | +2.513 | +3.2 % | 0.150 | beyond the band |
| fixoff against headoff | -3.135 | -3.9 % | 0.280 | beyond the band |
| fixoff against baseoff | -0.982 | -1.2 % | 0.280 | beyond the band |

What the table says:

- The fix removes the cost. The fix build's prefill is below the base's.
- The loop split is the cause. The first commit, which only splits the loop, costs +3.2 %. The second commit, which adds `page::score_k`, costs nothing on top of it (headoff is 0.361 s faster than c1off).
- Decode changes by at most +0.25 TPS per user (fixoff against baseoff), inside the band of 0.40.
- The fix build is faster than the base. Candidate mechanism: the split loop loads each K row once where the base's loop re-read it for every query head (9 against 20 load micro-operations per K token in the disassembly above), and the fast path removes the serial selection pass that cost more than that saving. A profile would confirm it, and the `perf stat` plan above still applies if anyone needs the counter-level proof.

### What the fix is

In `apply_page_tok`, when the page's last token is below the hint's `tok_hi`, the query sees the hint's range and the first token is inside the sliding window, the live mask is `n` ones shifted by `begin` and the per-token loop does not run. That is the test `is_dense_amx_page` makes for the AMX path, widened from a full page to the span `[begin, end)`. The per-token loop stays for every other page, and `relevant_k_tokens` is the popcount of the mask in both branches. A unit test in t/t_llama_unit.cpp scores one page as one range (the fast path) and as two ranges (the loop) for 2, 63 and 64 tokens and requires bit-identical attention state. Generated tokens are identical between the fix build and PR #5047's head, with and without the kill switch (1 user, temperature 0, 256 tokens).

### Shipped configuration

With AMX on, the software path scores 2.8 % of the K tokens at prompt 8192 and 10.2 % at prompt 1024. The fix build's prefill at prompt 8192 is 0.172 s (0.5 %) shorter than the head's, and at prompt 1024 the two are equal within 0.002 s. Decode is unchanged within the band in both cells.

### Open

Fix F1 (the counter through the stack) was not measured on its own: F2 makes the selection pass skip entirely on dense pages, so the counter chain no longer runs there. The issue closes when PR #5047's branch takes PR #5098.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
