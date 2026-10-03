# Attention path stats: AMX kernel enabled vs disabled (attnstats-20261002)

## Short version

Tron main dd0f942c75 ran on our half of delphi-3bda with the attention path stats on (TRON_ATTN_STATS=1). Each cell ran twice: with the AMX kernel enabled (amxon) and with it disabled by the kill switch (amxoff, TRON_AMX_DISABLE=1). Cells: 6. Runs finished: 12. Runs failed or stopped: 0.
- gpt-oss-120b tp4, FPGA attention, prompt 1024, 8 users (gptoss-8u-p1024-fpga): AMX scored 0.0 % of the decode K tokens (0 of 377,634,816); TPS with AMX disabled +0.2 %.
- llama-3.1-8b tp2, CPU attention, prompt 1024, 8 users (l8b-8u-p1024-cpu): AMX scored 96.5 % of the decode K tokens (583,073,792 of 604,241,920); TPS with AMX disabled -2.8 %.
- qwen3-4b tp2, CPU attention, prompt 1024, 8 users (q3-4b-8u-p1024-cpu): AMX scored 97.3 % of the decode K tokens (658,243,584 of 676,823,040); TPS with AMX disabled -10.4 %.
- qwen3-4b tp2, FPGA attention, prompt 1024, 8 users (q3-4b-8u-p1024-fpga): AMX scored 0.0 % of the decode K tokens (0 of 676,823,040); TPS with AMX disabled +0.9 %.
- llama-3.1-8b tp2, CPU attention, prompt 8192, 8 users (l8b-8u-p8192-cpu): AMX scored 98.9 % of the decode K tokens (4,312,268,800 of 4,362,338,304); TPS with AMX disabled -13.8 %.
- qwen3-4b tp2, FPGA attention, prompt 8192, 8 users (q3-4b-8u-p8192-fpga): AMX scored 0.0 % of the decode K tokens (0 of 4,888,166,400); TPS with AMX disabled +0.5 %.

## Words used here

- tron = the inference program under test. runtron = its command-line tool. One runtron process per run prints the stats to stderr at exit.
- AMX, AVX = two CPU instruction sets. The AMX kernel scores dense KV pages. The AVX software loop scores every other page.
- FPGA attention (AoF, attention on the FPGA) = the FPGA card scores the keys it holds. The CPU scores the rest: the pending pages, queries below the engagement point (position 127), and any 1024-token shard the card could not hold (the 'lose HW attention' warning).
- amxon = TRON_AMX_DISABLE unset. The AMX kernel is available.
- amxoff = TRON_AMX_DISABLE=1, the kill switch. Same binary; every page goes to the AVX loop.
- attn=cpu = USE_HW_ATTN=0, software attention on the CPU for every model.
- attn=fpga = USE_HW_ATTN unset, the model default: FPGA attention for generated plugins (gpt-oss, qwen3), CPU attention for llama.
- attn=fpga1 = USE_HW_ATTN=1, FPGA attention forced on (used for the llama control; the engagement point stays 127).
- visit = one (token job, KV head, page) scoring step of the software loop. K tokens = the keys that step scored.
- software scale = K tokens counted once per KV head, the unit of the AVX and AMX counters. The FPGA counts K tokens once per query (all KV heads at once). The report multiplies the FPGA count by n_kv_heads (fpga_k_tokens_x_kv_heads) to put it on the software scale.
- ready / pending = the two software passes of one attention job: the ready pass over pages whose K/V were written before this forward, and the pending pass, after the K/V wait, over the pages written in this forward.
- avx_full_page visits = AVX visits that scored a whole page (64 K tokens). With the kernel enabled these are full pages that failed the dense-page test, for example a page written in this forward. With the kill switch they also include every page the kernel would have taken. The identity in section 3 uses that.
- decode_like = forwards where every token job has a listener (decode steps). prompt_or_mixed = forwards with at least one job without a listener (prompt chunks).
- token_jobs_by_path_set = how many token jobs of the class touched which combination of paths in a forward.
- T1 = forward wall time.
- busy = T2, the time one worker spent inside one attention job: both software passes and the join, without the upstream K/V wait (the wait for the K/V of this forward before the pending pass).
- join wait = T5, the time inside busy spent waiting for peer workers or the card with no join progress.
- T4 per forward = the sum, over the layers of one forward, of the time from the first attention job of one layer to the first attention job of the next layer, as attention worker 0 sees it. The last layer has no successor, so the sum covers n_layers - 1 layers.
- kv_mul = query heads per KV head (GQA). head_size = elements per head.
- fitting shape = head size 128 and kv_mul 4, the only geometry the AMX kernel is compiled for (shape_ok in h/tron/kernels/amx_attn_iface.hpp:148-150 at main). llama-3.1-8b and qwen3-4b fit. gpt-oss-120b (head size 64, kv_mul 8) does not, so it cannot record an AMX visit in either arm.
- amx_available = the process-level probe (CPU support and the kill switch). It is not the shape verdict.
- card layers = hw_slots of the 'HW attention enabled' line, the layers the FPGA serves. gpt-oss has 18 card layers and 18 sliding-window layers (window 128) that always run in software.

## 1. What ran

| cell | model | kv heads / kv_mul / head size / layers | kernel shape | attention asked | card (log) | card layers | prompt | users | AMX compiled / available (amxon) | available (amxoff) | TPS amxon | TPS amxoff | TTFT amxon s | TTFT amxoff s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gptoss-8u-p1024-fpga | gpt-oss-120b tp4 | 8 / 8 / 64 / 36 | non-fitting | FPGA attention | on | 18 of 36 | 1024 | 8 | yes / yes | no | 96.07 | 96.22 | 2.73 | 2.73 |
| l8b-8u-p1024-cpu | llama-3.1-8b tp2 | 8 / 4 / 128 / 32 | fitting | CPU attention | off | 0 | 1024 | 8 | yes / yes | no | 113.87 | 110.66 | 3.42 | 3.58 |
| q3-4b-8u-p1024-cpu | qwen3-4b tp2 | 8 / 4 / 128 / 36 | fitting | CPU attention | off | 0 | 1024 | 8 | yes / yes | no | 79.48 | 71.20 | 3.19 | 3.99 |
| q3-4b-8u-p1024-fpga | qwen3-4b tp2 | 8 / 4 / 128 / 36 | fitting | FPGA attention | on | 36 of 36 | 1024 | 8 | yes / yes | no | 126.59 | 127.69 | 3.11 | 3.06 |
| l8b-8u-p8192-cpu | llama-3.1-8b tp2 | 8 / 4 / 128 / 32 | fitting | CPU attention | off | 0 | 8192 | 8 | yes / yes | no | 24.84 | 21.42 | 34.62 | 78.78 |
| q3-4b-8u-p8192-fpga | qwen3-4b tp2 | 8 / 4 / 128 / 36 | fitting | FPGA attention | on | 36 of 36 | 8192 | 8 | yes / yes | no | 60.53 | 60.86 | 26.73 | 26.79 |

TPS = generated tokens per second per user, mean over users (runtron 'average tok/s'). TTFT = prompt parsing time in seconds, mean over users. One repetition per cell: a TPS difference of a few percent cannot be separated from run-to-run variation here.

HW attention line and HBM warnings per cell (the line is the first 'HW attention' line of the run's log):

- gptoss-8u-p1024-fpga: HW attention enabled for model 'ingested-gpt-oss-120b-tp4': max_layers=36 engagement=127 kv_slot_extent=36 hw_attn_params { kv_head_size: 64 n_kv_heads: 8 n_heads: 64 gqa: 8 pre_attn_scalar: 0.125 hw_slots: 18 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- l8b-8u-p1024-cpu: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- q3-4b-8u-p1024-cpu: HW attention disabled for model 'ingested-qwen-3-4b-instruct-2507-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- q3-4b-8u-p1024-fpga: HW attention enabled for model 'ingested-qwen-3-4b-instruct-2507-tp2': max_layers=36 engagement=127 kv_slot_extent=36 hw_attn_params { kv_head_size: 128 n_kv_heads: 8 n_heads: 32 gqa: 4 pre_attn_scalar: 0.088388346 hw_slots: 36 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- l8b-8u-p8192-cpu: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- q3-4b-8u-p8192-fpga: HW attention enabled for model 'ingested-qwen-3-4b-instruct-2507-tp2': max_layers=36 engagement=127 kv_slot_extent=36 hw_attn_params { kv_head_size: 128 n_kv_heads: 8 n_heads: 32 gqa: 4 pre_attn_scalar: 0.088388346 hw_slots: 36 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.

## 2. K tokens by path, AMX enabled vs disabled

Per cell and class: the K tokens each path scored (software scale), the shares, and the visit counts. Shares are of the row's total K tokens (AMX + AVX + FPGA).

| cell | class | arm | K tokens AMX | share | K tokens AVX | share | K tokens FPGA (x kv heads) | share | visits AMX (ready+pending) | visits AVX | avx_full_page visits | empty visits | FPGA query passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gptoss-8u-p1024-fpga | decode_like | amxon | 0 | 0.0 % | 38,486,016 | 10.2 % | 339,148,800 | 89.8 % | 0 (0+0) | 1,187,136 | 299,520 | 0 | 36,864 |
| gptoss-8u-p1024-fpga | decode_like | amxoff | 0 | 0.0 % | 38,486,016 | 10.2 % | 339,148,800 | 89.8 % | 0 (0+0) | 1,187,136 | 299,520 | 0 | 36,864 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | amxon | 0 | 0.0 % | 217,716,768 | 29.2 % | 528,482,304 | 70.8 % | 0 (0+0) | 6,212,160 | 1,714,464 | 16,218 | 129,024 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | amxoff | 0 | 0.0 % | 217,716,768 | 29.2 % | 528,482,304 | 70.8 % | 0 (0+0) | 6,212,160 | 1,714,464 | 16,362 | 129,024 |
| l8b-8u-p1024-cpu | decode_like | amxon | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-8u-p1024-cpu | decode_like | amxoff | 0 | 0.0 % | 604,241,920 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 10,150,912 | 9,176,064 | 0 | 0 |
| l8b-8u-p1024-cpu | prompt_or_mixed | amxon | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-8u-p1024-cpu | prompt_or_mixed | amxoff | 0 | 0.0 % | 1,074,788,608 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 19,630,336 | 15,732,736 | 0 | 0 |
| q3-4b-8u-p1024-cpu | decode_like | amxon | 658,243,584 | 97.3 % | 18,579,456 | 2.7 % | 0 | 0.0 % | 10,285,056 (10,278,144+6,912) | 580,608 | 0 | 0 | 0 |
| q3-4b-8u-p1024-cpu | decode_like | amxoff | 0 | 0.0 % | 676,823,040 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 10,865,664 | 10,285,056 | 0 | 0 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | amxon | 1,056,964,608 | 87.4 % | 152,174,592 | 12.6 % | 0 | 0.0 % | 16,515,072 (16,515,072+0) | 3,538,944 | 1,216,512 | 0 | 0 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | amxoff | 0 | 0.0 % | 1,209,139,200 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 20,054,016 | 17,731,584 | 0 | 0 |
| q3-4b-8u-p1024-fpga | decode_like | amxon | 0 | 0.0 % | 1,465,344 | 0.2 % | 675,357,696 | 99.8 % | 0 (0+0) | 587,520 | 0 | 0 | 73,440 |
| q3-4b-8u-p1024-fpga | decode_like | amxoff | 0 | 0.0 % | 1,465,344 | 0.2 % | 675,357,696 | 99.8 % | 0 (0+0) | 587,520 | 0 | 0 | 73,440 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | amxon | 0 | 0.0 % | 152,174,592 | 12.6 % | 1,056,964,608 | 87.4 % | 0 (0+0) | 3,538,944 | 1,216,512 | 0 | 258,048 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | amxoff | 0 | 0.0 % | 152,174,592 | 12.6 % | 1,056,964,608 | 87.4 % | 0 (0+0) | 3,538,944 | 1,216,512 | 0 | 258,048 |
| l8b-8u-p8192-cpu | decode_like | amxon | 4,312,268,800 | 98.9 % | 50,069,504 | 1.1 % | 0 | 0.0 % | 67,379,200 (67,371,008+8,192) | 1,499,136 | 65,536 | 0 | 0 |
| l8b-8u-p8192-cpu | decode_like | amxoff | 0 | 0.0 % | 4,362,338,304 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 68,878,336 | 67,444,736 | 0 | 0 |
| l8b-8u-p8192-cpu | prompt_or_mixed | amxon | 66,750,251,008 | 97.1 % | 1,977,612,544 | 2.9 % | 0 | 0.0 % | 1,042,972,672 (1,040,449,536+2,523,136) | 53,793,024 | 10,672,128 | 0 | 0 |
| l8b-8u-p8192-cpu | prompt_or_mixed | amxoff | 0 | 0.0 % | 68,727,863,552 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 1,096,765,696 | 1,053,644,800 | 0 | 0 |
| q3-4b-8u-p8192-fpga | decode_like | amxon | 0 | 0.0 % | 1,465,344 | 0.0 % | 4,886,701,056 | 100.0 % | 0 (0+0) | 587,520 | 0 | 0 | 219,168 |
| q3-4b-8u-p8192-fpga | decode_like | amxoff | 0 | 0.0 % | 1,465,344 | 0.0 % | 4,886,701,056 | 100.0 % | 0 (0+0) | 587,520 | 0 | 0 | 219,168 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | amxon | 452,984,832 | 0.6 % | 1,217,396,736 | 1.6 % | 75,648,466,944 | 97.8 % | 7,077,888 (7,077,888+0) | 28,311,552 | 9,732,096 | 0 | 3,428,352 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | amxoff | 0 | 0.0 % | 1,670,381,568 | 2.2 % | 75,648,466,944 | 97.8 % | 0 (0+0) | 35,389,440 | 16,809,984 | 0 | 3,428,352 |

## 3. Kill-switch identity

When both arms scored the same prompts, generated the same number of tokens (--dont-stop) and had the same HBM warning counts, every dense page the kernel took in amxon is an AVX full-page visit in amxoff. So avx_full_page(amxoff) must equal amx_visits(amxon) + avx_full_page(amxon). The AVX K tokens of amxoff must equal the AMX + AVX K tokens of amxon. A mismatch means the two runs did not score the same positions, or a counter defect. For a non-fitting shape both arms have 0 AMX visits and the identity degenerates to equal counts.

| cell | class | amx visits (on) | avx_full_page (on) | avx_full_page (off) | visits identity | K tokens AMX+AVX (on) | K tokens AVX (off) | K identity | FPGA K tokens on / off |
|---|---|---|---|---|---|---|---|---|---|
| gptoss-8u-p1024-fpga | decode_like | 0 | 299,520 | 299,520 | holds | 38,486,016 | 38,486,016 | holds | 339,148,800 / 339,148,800 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | 0 | 1,714,464 | 1,714,464 | holds | 217,716,768 | 217,716,768 | holds | 528,482,304 / 528,482,304 |
| l8b-8u-p1024-cpu | decode_like | 9,110,528 | 65,536 | 9,176,064 | holds | 604,241,920 | 604,241,920 | holds | 0 / 0 |
| l8b-8u-p1024-cpu | prompt_or_mixed | 14,450,688 | 1,282,048 | 15,732,736 | holds | 1,074,788,608 | 1,074,788,608 | holds | 0 / 0 |
| q3-4b-8u-p1024-cpu | decode_like | 10,285,056 | 0 | 10,285,056 | holds | 676,823,040 | 676,823,040 | holds | 0 / 0 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | 16,515,072 | 1,216,512 | 17,731,584 | holds | 1,209,139,200 | 1,209,139,200 | holds | 0 / 0 |
| q3-4b-8u-p1024-fpga | decode_like | 0 | 0 | 0 | holds | 1,465,344 | 1,465,344 | holds | 675,357,696 / 675,357,696 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | 0 | 1,216,512 | 1,216,512 | holds | 152,174,592 | 152,174,592 | holds | 1,056,964,608 / 1,056,964,608 |
| l8b-8u-p8192-cpu | decode_like | 67,379,200 | 65,536 | 67,444,736 | holds | 4,362,338,304 | 4,362,338,304 | holds | 0 / 0 |
| l8b-8u-p8192-cpu | prompt_or_mixed | 1,042,972,672 | 10,672,128 | 1,053,644,800 | holds | 68,727,863,552 | 68,727,863,552 | holds | 0 / 0 |
| q3-4b-8u-p8192-fpga | decode_like | 0 | 0 | 0 | holds | 1,465,344 | 1,465,344 | holds | 4,886,701,056 / 4,886,701,056 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | 7,077,888 | 9,732,096 | 16,809,984 | holds | 1,670,381,568 | 1,670,381,568 | holds | 75,648,466,944 / 75,648,466,944 |

## 4. Token jobs by path set

How many token jobs of a class touched which paths within a forward (a job may use several paths across its pages and layers).

| cell | class | arm | token jobs | forwards | FPGA queries | none | avx | amx | avx+amx | fpga | fpga+avx | fpga+amx | fpga+avx+amx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gptoss-8u-p1024-fpga | decode_like | amxon | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| gptoss-8u-p1024-fpga | decode_like | amxoff | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | amxon | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | amxoff | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| l8b-8u-p1024-cpu | decode_like | amxon | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-8u-p1024-cpu | decode_like | amxoff | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| l8b-8u-p1024-cpu | prompt_or_mixed | amxon | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-8u-p1024-cpu | prompt_or_mixed | amxoff | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| q3-4b-8u-p1024-cpu | decode_like | amxon | 2,040 | 255 | 0 | 0 | 0 | 24 | 2,016 | 0 | 0 | 0 | 0 |
| q3-4b-8u-p1024-cpu | decode_like | amxoff | 2,040 | 255 | 0 | 0 | 2,040 | 0 | 0 | 0 | 0 | 0 | 0 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | amxon | 8,192 | 8 | 0 | 0 | 1,024 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | amxoff | 8,192 | 8 | 0 | 0 | 8,192 | 0 | 0 | 0 | 0 | 0 | 0 |
| q3-4b-8u-p1024-fpga | decode_like | amxon | 2,040 | 255 | 2,040 | 0 | 0 | 0 | 0 | 0 | 2,040 | 0 | 0 |
| q3-4b-8u-p1024-fpga | decode_like | amxoff | 2,040 | 255 | 2,040 | 0 | 0 | 0 | 0 | 0 | 2,040 | 0 | 0 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | amxon | 8,192 | 8 | 7,168 | 0 | 1,024 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | amxoff | 8,192 | 8 | 7,168 | 0 | 1,024 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| l8b-8u-p8192-cpu | decode_like | amxon | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-8u-p8192-cpu | decode_like | amxoff | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| l8b-8u-p8192-cpu | prompt_or_mixed | amxon | 65,529 | 64 | 0 | 0 | 1,017 | 0 | 64,512 | 0 | 0 | 0 | 0 |
| l8b-8u-p8192-cpu | prompt_or_mixed | amxoff | 65,529 | 64 | 0 | 0 | 65,529 | 0 | 0 | 0 | 0 | 0 | 0 |
| q3-4b-8u-p8192-fpga | decode_like | amxon | 2,040 | 255 | 2,040 | 0 | 0 | 0 | 0 | 0 | 2,040 | 0 | 0 |
| q3-4b-8u-p8192-fpga | decode_like | amxoff | 2,040 | 255 | 2,040 | 0 | 0 | 0 | 0 | 0 | 2,040 | 0 | 0 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | amxon | 65,536 | 64 | 64,512 | 0 | 1,024 | 0 | 0 | 0 | 61,440 | 0 | 3,072 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | amxoff | 65,536 | 64 | 64,512 | 0 | 1,024 | 0 | 0 | 0 | 64,512 | 0 | 0 |

## 5. Per-layer pattern

From the 'k_tokens per layer' line of the exit report (ready + pending, summed over workers). Layers with FPGA > 0 are the layers the card served. Layers with AMX > 0 are the layers where the kernel ran. AMX and AVX are K tokens per KV head. The FPGA value is per query (all KV heads at once); multiply it by n_kv_heads (8 for all three models) to compare it with the other two.

- gptoss-8u-p1024-fpga amxon decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 18 (layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/40,960/2,355,200 in layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35; 0/2,097,152/0 in layers 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34
- gptoss-8u-p1024-fpga amxon prompt_or_mixed: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 18 (layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/4,227,016/3,670,016 in layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35; 0/7,868,360/0 in layers 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34
- gptoss-8u-p1024-fpga amxoff decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 18 (layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/40,960/2,355,200 in layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35; 0/2,097,152/0 in layers 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34
- gptoss-8u-p1024-fpga amxoff prompt_or_mixed: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 18 (layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/4,227,016/3,670,016 in layers 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35; 0/7,868,360/0 in layers 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34
- l8b-8u-p1024-cpu amxon decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-8u-p1024-cpu amxon prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-8u-p1024-cpu amxoff decode_like: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 0/18,882,560/0 in layers 0-31
- l8b-8u-p1024-cpu amxoff prompt_or_mixed: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 0/33,587,144/0 in layers 0-31
- q3-4b-8u-p1024-cpu amxon decode_like: 36 layers; AMX K tokens > 0 in 36 (layers 0-35); FPGA > 0 in 0 (layers none); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 18,284,544/516,096/0 in layers 0-35
- q3-4b-8u-p1024-cpu amxon prompt_or_mixed: 36 layers; AMX K tokens > 0 in 36 (layers 0-35); FPGA > 0 in 0 (layers none); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 29,360,128/4,227,072/0 in layers 0-35
- q3-4b-8u-p1024-cpu amxoff decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/18,800,640/0 in layers 0-35
- q3-4b-8u-p1024-cpu amxoff prompt_or_mixed: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/33,587,200/0 in layers 0-35
- q3-4b-8u-p1024-fpga amxon decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/40,704/2,344,992 in layers 0-35
- q3-4b-8u-p1024-fpga amxon prompt_or_mixed: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/4,227,072/3,670,016 in layers 0-35
- q3-4b-8u-p1024-fpga amxoff decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/40,704/2,344,992 in layers 0-35
- q3-4b-8u-p1024-fpga amxoff prompt_or_mixed: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/4,227,072/3,670,016 in layers 0-35
- l8b-8u-p8192-cpu amxon decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 134,758,400/1,564,672/0 in layers 0-31
- l8b-8u-p8192-cpu amxon prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 2,085,945,344/61,800,392/0 in layers 0-31
- l8b-8u-p8192-cpu amxoff decode_like: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 0/136,323,072/0 in layers 0-31
- l8b-8u-p8192-cpu amxoff prompt_or_mixed: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32
  - distinct per-layer (amx/avx/fpga) triples: 0/2,147,745,736/0 in layers 0-31
- q3-4b-8u-p8192-fpga amxon decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/40,704/16,967,712 in layers 0-35
- q3-4b-8u-p8192-fpga amxon prompt_or_mixed: 36 layers; AMX K tokens > 0 in 36 (layers 0-35); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 12,582,912/33,816,576/262,668,288 in layers 0-35
- q3-4b-8u-p8192-fpga amxoff decode_like: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/40,704/16,967,712 in layers 0-35
- q3-4b-8u-p8192-fpga amxoff prompt_or_mixed: 36 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 36 (layers 0-35); AVX > 0 in 36
  - distinct per-layer (amx/avx/fpga) triples: 0/46,399,488/262,668,288 in layers 0-35

## 6. Time

Cycles are converted with tsc_hz of the run.

- T1 ms per forward = forward wall time per forward.
- busy s = T2 summed over all workers and jobs of the class. busy ms per job = T2 per attention job (both software passes and the join, without the upstream K/V wait).
- join wait share = T5 / T2.
- T4 ms per forward = the layer-to-layer periods on attention worker 0, summed per forward (n_layers - 1 periods).

| cell | class | arm | forwards | T1 ms per forward | busy s (all workers) | busy ms per job | join wait share | T4 ms per forward |
|---|---|---|---|---|---|---|---|---|
| gptoss-8u-p1024-fpga | decode_like | amxon | 256 | 10.26 | 11.88 | 0.032 | 16.8 % | 9.40 |
| gptoss-8u-p1024-fpga | decode_like | amxoff | 256 | 10.24 | 11.31 | 0.031 | 18.4 % | 9.38 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | amxon | 8 | 335.06 | 16.66 | 1.446 | 14.5 % | 278.64 |
| gptoss-8u-p1024-fpga | prompt_or_mixed | amxoff | 8 | 334.60 | 16.55 | 1.436 | 14.2 % | 278.17 |
| l8b-8u-p1024-cpu | decode_like | amxon | 256 | 8.66 | 34.34 | 0.091 | 3.3 % | 7.65 |
| l8b-8u-p1024-cpu | decode_like | amxoff | 256 | 8.92 | 40.48 | 0.103 | 4.2 % | 7.89 |
| l8b-8u-p1024-cpu | prompt_or_mixed | amxon | 8 | 425.79 | 19.70 | 0.639 | 10.5 % | 398.05 |
| l8b-8u-p1024-cpu | prompt_or_mixed | amxoff | 8 | 445.19 | 37.27 | 1.116 | 8.8 % | 420.07 |
| q3-4b-8u-p1024-cpu | decode_like | amxon | 255 | 12.48 | 35.36 | 0.193 | 2.0 % | 11.64 |
| q3-4b-8u-p1024-cpu | decode_like | amxoff | 255 | 13.93 | 41.96 | 0.229 | 2.3 % | 13.05 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | amxon | 8 | 397.92 | 19.38 | 3.364 | 9.9 % | 381.22 |
| q3-4b-8u-p1024-cpu | prompt_or_mixed | amxoff | 8 | 497.65 | 36.42 | 6.322 | 1.8 % | 478.20 |
| q3-4b-8u-p1024-fpga | decode_like | amxon | 255 | 7.75 | 7.81 | 0.043 | 57.5 % | 7.02 |
| q3-4b-8u-p1024-fpga | decode_like | amxoff | 255 | 7.68 | 7.82 | 0.043 | 58.5 % | 6.95 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | amxon | 8 | 381.90 | 8.60 | 1.493 | 1.8 % | 332.47 |
| q3-4b-8u-p1024-fpga | prompt_or_mixed | amxoff | 8 | 375.64 | 7.90 | 1.371 | 0.9 % | 326.83 |
| l8b-8u-p8192-cpu | decode_like | amxon | 256 | 39.64 | 244.59 | 0.574 | 1.8 % | 37.42 |
| l8b-8u-p8192-cpu | decode_like | amxoff | 256 | 46.05 | 289.35 | 0.679 | 0.9 % | 43.61 |
| l8b-8u-p8192-cpu | prompt_or_mixed | amxon | 64 | 538.63 | 695.33 | 1.919 | 4.5 % | 514.79 |
| l8b-8u-p8192-cpu | prompt_or_mixed | amxoff | 64 | 1,228.36 | 1,923.42 | 4.769 | 2.0 % | 1,184.29 |
| q3-4b-8u-p8192-fpga | decode_like | amxon | 255 | 15.96 | 44.45 | 0.242 | 88.4 % | 14.84 |
| q3-4b-8u-p8192-fpga | decode_like | amxoff | 255 | 15.87 | 44.63 | 0.243 | 88.5 % | 14.75 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | amxon | 64 | 409.36 | 110.16 | 2.391 | 23.4 % | 364.96 |
| q3-4b-8u-p8192-fpga | prompt_or_mixed | amxoff | 64 | 410.48 | 114.13 | 2.477 | 22.6 % | 366.32 |

## 7. Situations

### 7.1 Attention on the FPGA (gpt-oss, qwen3)

- gptoss-8u-p1024-fpga (gpt-oss-120b tp4, non-fitting shape: kv_mul 8, head size 64; card on, 18 of 36 layers; amx_available yes), decode_like, amxon: AMX 0.0 % of the K tokens (0 visits). AVX 10.2 %. FPGA 89.8 %.
  - AVX K tokens split by layer kind: 737,280 in the card layers, 37,748,736 in the software-only layers.
  - amxoff: AVX 10.2 %, FPGA 89.8 %, avx_full_page visits 299,520.
  - Busy per job goes from 0.032 ms (amxon) to 0.031 ms (amxoff), 95.2 % of amxon.
- gptoss-8u-p1024-fpga (gpt-oss-120b tp4, non-fitting shape: kv_mul 8, head size 64; card on, 18 of 36 layers; amx_available yes), prompt_or_mixed, amxon: AMX 0.0 % of the K tokens (0 visits). AVX 29.2 %. FPGA 70.8 %.
  - AVX K tokens split by layer kind: 76,086,288 in the card layers, 141,630,480 in the software-only layers.
  - amxoff: AVX 29.2 %, FPGA 70.8 %, avx_full_page visits 1,714,464.
  - Busy per job goes from 1.446 ms (amxon) to 1.436 ms (amxoff), 99.3 % of amxon.
  - TPS 96.07 (amxon) vs 96.22 (amxoff), +0.2 % for the kill switch.
- q3-4b-8u-p1024-fpga (qwen3-4b tp2, fitting shape: kv_mul 4, head size 128; card on, 36 of 36 layers; amx_available yes), decode_like, amxon: AMX 0.0 % of the K tokens (0 visits). AVX 0.2 %. FPGA 99.8 %.
  - amxoff: AVX 0.2 %, FPGA 99.8 %, avx_full_page visits 0.
  - Busy per job goes from 0.043 ms (amxon) to 0.043 ms (amxoff), 100.1 % of amxon.
- q3-4b-8u-p1024-fpga (qwen3-4b tp2, fitting shape: kv_mul 4, head size 128; card on, 36 of 36 layers; amx_available yes), prompt_or_mixed, amxon: AMX 0.0 % of the K tokens (0 visits). AVX 12.6 %. FPGA 87.4 %.
  - amxoff: AVX 12.6 %, FPGA 87.4 %, avx_full_page visits 1,216,512.
  - Busy per job goes from 1.493 ms (amxon) to 1.371 ms (amxoff), 91.9 % of amxon.
  - TPS 126.59 (amxon) vs 127.69 (amxoff), +0.9 % for the kill switch.
- q3-4b-8u-p8192-fpga (qwen3-4b tp2, fitting shape: kv_mul 4, head size 128; card on, 36 of 36 layers; amx_available yes), decode_like, amxon: AMX 0.0 % of the K tokens (0 visits). AVX 0.0 %. FPGA 100.0 %.
  - amxoff: AVX 0.0 %, FPGA 100.0 %, avx_full_page visits 0.
  - Busy per job goes from 0.242 ms (amxon) to 0.243 ms (amxoff), 100.4 % of amxon.
- q3-4b-8u-p8192-fpga (qwen3-4b tp2, fitting shape: kv_mul 4, head size 128; card on, 36 of 36 layers; amx_available yes), prompt_or_mixed, amxon: AMX 0.6 % of the K tokens (7,077,888 visits). AVX 1.6 %. FPGA 97.8 %.
  - amxoff: AVX 2.2 %, FPGA 97.8 %, avx_full_page visits 16,809,984.
  - Busy per job goes from 2.391 ms (amxon) to 2.477 ms (amxoff), 103.6 % of amxon.
  - TPS 60.53 (amxon) vs 60.86 (amxoff), +0.5 % for the kill switch.

### 7.2 Pure software attention (llama-3.1)

- l8b-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 96.5 % of the K tokens (9,110,528 visits). AVX 3.5 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 9,176,064.
  - Busy per job goes from 0.091 ms (amxon) to 0.103 ms (amxoff), 113.2 % of amxon.
- l8b-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 86.0 % of the K tokens (14,450,688 visits). AVX 14.0 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 15,732,736.
  - Busy per job goes from 0.639 ms (amxon) to 1.116 ms (amxoff), 174.7 % of amxon.
  - TPS 113.87 (amxon) vs 110.66 (amxoff), -2.8 % for the kill switch.
- l8b-8u-p8192-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 98.9 % of the K tokens (67,379,200 visits). AVX 1.1 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 67,444,736.
  - Busy per job goes from 0.574 ms (amxon) to 0.679 ms (amxoff), 118.3 % of amxon.
- l8b-8u-p8192-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 97.1 % of the K tokens (1,042,972,672 visits). AVX 2.9 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 1,053,644,800.
  - Busy per job goes from 1.919 ms (amxon) to 4.769 ms (amxoff), 248.5 % of amxon.
  - TPS 24.84 (amxon) vs 21.42 (amxoff), -13.8 % for the kill switch.

### 7.3 Fitting shape (llama-3.1, qwen3) vs non-fitting shape (gpt-oss), CPU attention controls

- l8b-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 96.5 % of the K tokens (9,110,528 visits). AVX 3.5 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 9,176,064.
  - Busy per job goes from 0.091 ms (amxon) to 0.103 ms (amxoff), 113.2 % of amxon.
- l8b-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 86.0 % of the K tokens (14,450,688 visits). AVX 14.0 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 15,732,736.
  - Busy per job goes from 0.639 ms (amxon) to 1.116 ms (amxoff), 174.7 % of amxon.
  - TPS 113.87 (amxon) vs 110.66 (amxoff), -2.8 % for the kill switch.
- q3-4b-8u-p1024-cpu (qwen3-4b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 97.3 % of the K tokens (10,285,056 visits). AVX 2.7 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 10,285,056.
  - Busy per job goes from 0.193 ms (amxon) to 0.229 ms (amxoff), 118.6 % of amxon.
- q3-4b-8u-p1024-cpu (qwen3-4b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 87.4 % of the K tokens (16,515,072 visits). AVX 12.6 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 17,731,584.
  - Busy per job goes from 3.364 ms (amxon) to 6.322 ms (amxoff), 188.0 % of amxon.
  - TPS 79.48 (amxon) vs 71.20 (amxoff), -10.4 % for the kill switch.
- l8b-8u-p8192-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 98.9 % of the K tokens (67,379,200 visits). AVX 1.1 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 67,444,736.
  - Busy per job goes from 0.574 ms (amxon) to 0.679 ms (amxoff), 118.3 % of amxon.
- l8b-8u-p8192-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 97.1 % of the K tokens (1,042,972,672 visits). AVX 2.9 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 1,053,644,800.
  - Busy per job goes from 1.919 ms (amxon) to 4.769 ms (amxoff), 248.5 % of amxon.
  - TPS 24.84 (amxon) vs 21.42 (amxoff), -13.8 % for the kill switch.

### 7.4 Other controls (llama with USE_HW_ATTN=1)

- no finished cell in this group.

## 8. Failed or stopped runs

Runs with no complete attempt:

- none

## 9. Files

- results: exec/results/attnstats-20261002/ (rt-results.txt, rt/<run>.log, exit-reports.txt, leaves/<run>/ = in-flight FUSE leaf snapshots for the worker and layer rows, possibly absent for short runs, not used by this report)
- scripts: exec/attnstats-20261002/ (chain.sh, campaign.sh, gen_compare.py, launch.sh, README.md)
- binary: runtron.main1002 built from main dd0f942c75 with -DTRON_AMX_DISPATCH=ON (see build-main1002.txt)
