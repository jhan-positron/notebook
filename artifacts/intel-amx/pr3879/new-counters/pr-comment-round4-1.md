## Review round 4: all five comments addressed, head 04da001cb5

**CPU-attention runtron run of the head** (delphi-3bda, our half, qwen-3-4b tp2, 8 users, prompt 1024, 256 tokens, `USE_HW_ATTN=0`, `TRON_ATTN_STATS=1`, 2026-09-29):

| quantity | decode class | prefill class |
|---|---|---|
| forwards | 255 | 8 (one 128-token chunk of every user per forward) |
| token jobs | 2,040 | 8,192 |
| listener jobs / KV-only jobs | 2,040 / 0 | 64 / 8,128 |
| split (n_attn_workers min / max) | 20 / 20 | 20 / 20 |
| T1 per forward | 12.5 ms | 398 ms |
| T2 per attention job | 193 us | 3.40 ms |
| T5 per job, share of T2 | 4.1 us, 2.1 % | 345 us, 10.2 % |

The visit and K-token counts equal the 2026-09-24 run of the first commit (10,278,144 ready AMX visits in decode, 16,515,072 in prefill). The forward and token-job counts equal the earlier exit reports, so `forward_scope` files every forward. The same cell read T5 = 0 before the software-join fix. In the worker leaves, pool workers 0 to 6 (the main helpers) read zero and 7 to 26 carry the attention rows. The leaf samples and the changed definitions follow in the next two comments; the PR description keeps the samples of the first commit.
