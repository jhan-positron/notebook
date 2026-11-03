# Attention path stats: AMX kernel enabled vs disabled (glimpl-20261017)

## Short version

Tron branch jhan-amx-kvmul16 (6cda072924, the AMX attention kernels generalised to kv_mul 16) ran on our half of delphi-3bda with the attention path stats on (TRON_ATTN_STATS=1). Each cell ran with the AMX kernel enabled (amxon) and with it disabled by the kill switch (amxoff, TRON_AMX_DISABLE=1), 3 repetition(s) per arm. Cells: 4. Runs finished: 24. Runs failed or stopped: 0. The counter tables and identities below use repetition 1; section 6 uses every repetition.
- Glimmer-30B tp2, FPGA attention, prompt 1024, 8 users (glm-tp2-8u-p1024-fpga): AMX scored 72.1 % of the decode K tokens (177,076,224 of 245,473,280); decode TPS amxon vs amxoff +1.7 % (mean over 3 rep).
- Glimmer-30B tp4, FPGA attention, prompt 1024, 8 users (glm-tp4-8u-p1024-fpga): AMX scored 72.1 % of the decode K tokens (177,076,224 of 245,473,280); decode TPS amxon vs amxoff -0.8 % (mean over 3 rep).
- llama-3.1-8b tp2, CPU attention, prompt 1024, 8 users (l8b-tp2-8u-p1024-cpu): AMX scored 96.5 % of the decode K tokens (583,073,792 of 604,241,920); decode TPS amxon vs amxoff +0.1 % (mean over 3 rep).
- Glimmer-30B tp2, FPGA attention, prompt 2048, 8 users (glm-tp2-8u-p2048-fpga): AMX scored 69.5 % of the decode K tokens (308,126,208 of 443,049,984); decode TPS amxon vs amxoff +1.9 % (mean over 3 rep).

## Words used here

- tron = the inference program under test. runtron = its command-line tool. One runtron process per run prints the stats to stderr at exit.
- AMX, AVX = two CPU instruction sets. The AMX kernel scores dense KV pages. The AVX software loop scores every other page.
- FPGA attention (AoF, attention on the FPGA) = the FPGA card scores the keys it holds. The CPU scores the rest: the pending pages, queries below the engagement point (position 127), and any 1024-token shard the card could not hold (the 'lose HW attention' warning).
- amxon = TRON_AMX_DISABLE unset. The AMX kernel is available.
- amxoff = TRON_AMX_DISABLE=1, the kill switch. Same binary; every page goes to the AVX loop.
- attn=cpu = USE_HW_ATTN=0, software attention on the CPU for every model.
- attn=fpga = USE_HW_ATTN unset, the model default: Glimmer sends its 13 full-attention layers to the FPGA and its 39 sliding-window layers always run on the CPU; llama runs on the CPU.
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
- fitting shape = head size 128 and kv_mul 4 or 16, the geometries the branch compiles the AMX kernel for (shape_ok in h/tron/kernels/amx_attn_iface.hpp; main accepts kv_mul 4 only). llama-3.1-8b (kv_mul 4) and Muse Glimmer 30B (32 query heads, 2 KV heads, head 128: kv_mul 16) fit.
- amx_available = the process-level probe (CPU support and the kill switch). It is not the shape verdict.
- card layers = hw_slots of the 'HW attention enabled' line, the layers the FPGA serves. Glimmer has 52 layers: 13 full-attention layers (the card layers, hw_slots 13) and 39 sliding-window layers (window 2048 tokens = 32 KV pages) that always run in software. llama-3.1-8b has 32 layers, all software.
- Glimmer-30B = ingested-meta-models--Muse-Glimmer-30B (tp2 / tp4 executors), the production ingested plugin with the GPTQ weights.

## 1. What ran

| cell | model | kv heads / kv_mul / head size / layers | kernel shape | attention asked | card (log) | card layers | prompt | users | AMX compiled / available (amxon) | available (amxoff) | TPS amxon | TPS amxoff | TTFT amxon s | TTFT amxoff s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-fpga | Glimmer-30B tp2 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 1024 | 8 | yes / yes | yes | 42.62 | 41.90 | 14.89 | 14.83 |
| glm-tp4-8u-p1024-fpga | Glimmer-30B tp4 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 1024 | 8 | yes / yes | yes | 62.59 | 62.85 | 8.48 | 8.31 |
| l8b-tp2-8u-p1024-cpu | llama-3.1-8b tp2 | 8 / 4 / 128 / 32 | fitting | CPU attention | off | 0 | 1024 | 8 | yes / yes | yes | 119.40 | 119.54 | 3.41 | 3.41 |
| glm-tp2-8u-p2048-fpga | Glimmer-30B tp2 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 2048 | 8 | yes / yes | yes | 38.92 | 38.13 | 29.58 | 30.97 |

TPS = generated tokens per second per user, mean over users (runtron 'average tok/s'), repetition 1. TTFT = prompt parsing time in seconds, mean over users, repetition 1. Section 6 has the means and spreads over every repetition.

HW attention line and HBM warnings per cell (the line is the first 'HW attention' line of the run's log):

- glm-tp2-8u-p1024-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp2': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp4-8u-p1024-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp4': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- l8b-tp2-8u-p1024-cpu: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp2-8u-p2048-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp2': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.

## 2. K tokens by path, AMX enabled vs disabled

Per cell and class: the K tokens each path scored (software scale), the shares, and the visit counts. Shares are of the row's total K tokens (AMX + AVX + FPGA).

| cell | class | arm | K tokens AMX | share | K tokens AVX | share | K tokens FPGA (x kv heads) | share | visits AMX (ready+pending) | visits AVX | avx_full_page visits | empty visits | FPGA query passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep1 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep2 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep3 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep1 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep2 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep3 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep3 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep3 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep1 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep2 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep3 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep1 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep2 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep3 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep3 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep3 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep3 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep3 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep3 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep3 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep1 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep2 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep3 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep1 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep2 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep3 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep3 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep3 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |

## 3. Kill-switch identity

When both arms scored the same prompts, generated the same number of tokens (--dont-stop) and had the same HBM warning counts, every dense page the kernel took in amxon is an AVX full-page visit in amxoff. So avx_full_page(amxoff) must equal amx_visits(amxon) + avx_full_page(amxon). The AVX K tokens of amxoff must equal the AMX + AVX K tokens of amxon. A mismatch means the two runs did not score the same positions, or a counter defect. For a non-fitting shape both arms have 0 AMX visits and the identity degenerates to equal counts.

| cell | class | amx visits (on) | avx_full_page (on) | avx_full_page (off) | visits identity | K tokens AMX+AVX (on) | K tokens AVX (off) | K identity | FPGA K tokens on / off |
|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-fpga | decode_like | 2,766,816 | 29,016 | 29,016 | MISMATCH (-2,766,816) | 184,238,080 | 7,161,856 | MISMATCH (-177,076,224) | 61,235,200 / 61,235,200 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | 3,913,728 | 986,752 | 986,752 | MISMATCH (-3,913,728) | 341,212,456 | 90,733,864 | MISMATCH (-250,478,592) | 95,420,416 / 95,420,416 |
| glm-tp4-8u-p1024-fpga | decode_like | 2,766,816 | 29,016 | 29,016 | MISMATCH (-2,766,816) | 184,238,080 | 7,161,856 | MISMATCH (-177,076,224) | 61,235,200 / 61,235,200 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | 3,913,728 | 986,752 | 986,752 | MISMATCH (-3,913,728) | 341,212,456 | 90,733,864 | MISMATCH (-250,478,592) | 95,420,416 / 95,420,416 |
| l8b-tp2-8u-p1024-cpu | decode_like | 9,110,528 | 65,536 | 65,536 | MISMATCH (-9,110,528) | 604,241,920 | 21,168,128 | MISMATCH (-583,073,792) | 0 / 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | 14,450,688 | 1,282,048 | 1,282,048 | MISMATCH (-14,450,688) | 1,074,788,608 | 149,944,576 | MISMATCH (-924,844,032) | 0 / 0 |
| glm-tp2-8u-p2048-fpga | decode_like | 4,814,472 | 2,496 | 2,496 | MISMATCH (-4,814,472) | 327,288,832 | 19,162,624 | MISMATCH (-308,126,208) | 115,761,152 / 115,761,152 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | 18,091,008 | 1,849,536 | 1,849,536 | MISMATCH (-18,091,008) | 1,350,368,552 | 192,544,040 | MISMATCH (-1,157,824,512) | 395,313,152 / 395,313,152 |

## 4. Token jobs by path set

A token job is one token of one user inside one forward. During that forward the token's keys are scored layer by layer, KV head by KV head, page by page, and each (KV head, page) step takes one path: the AMX kernel, the AVX loop or the FPGA card. One token job therefore usually touches more than one path in a forward, for example the kernel for its full pages and the AVX loop for its pending page.

The table counts token jobs by the combination of paths that touched them. Each token job goes into exactly one column: the set of all paths it used in its forward, over all layers, KV heads and pages. The counts add up over every forward of the class, so the token jobs column equals forwards x jobs per forward (8 in decode here), and the eight path-set columns add up to it.

| cell | class | arm | token jobs | forwards | FPGA queries | none | avx | amx | avx+amx | fpga | fpga+avx | fpga+amx | fpga+avx+amx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep3 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep3 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep3 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep3 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep3 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep3 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep3 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep3 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep3 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep3 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep3 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep3 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep3 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep3 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep3 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep3 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |

## 5. Per-layer pattern

From the 'k_tokens per layer' line of the exit report (ready + pending, summed over workers). Layers with FPGA > 0 are the layers the card served. Layers with AMX > 0 are the layers where the kernel ran. AMX and AVX are K tokens per KV head. The FPGA value is per query (all KV heads at once); multiply it by n_kv_heads (2 for Glimmer, 8 for llama) to compare it with the other two.

Expected for Glimmer: amxon with attn=fpga shows AMX K tokens on the 39 sliding-window layers only, and FPGA K tokens plus a small AVX tail on the 13 full layers; amxon with attn=cpu shows AMX on all 52 layers; amxoff shows AMX on no layer. Each line below ends with that check.

- glm-tp2-8u-p1024-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep3 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep3 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep3 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep3 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep3 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep3 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep3 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep3 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- l8b-tp2-8u-p1024-cpu amxon rep1 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep1 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep2 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep2 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep3 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep3 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep1 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. UNEXPECTED: 32 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep1 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. UNEXPECTED: 32 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep2 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. UNEXPECTED: 32 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep2 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. UNEXPECTED: 32 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep3 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. UNEXPECTED: 32 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep3 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. UNEXPECTED: 32 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- glm-tp2-8u-p2048-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep3 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep3 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 52 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 52 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep3 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 39 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep3 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: 52 layers with AMX K tokens under the kill switch
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50

## 6. Performance (every repetition)

Per cell and arm over the 3 repetition(s): decode TPS per user = mean over the 8 users' 'average tok/s' lines of a run, then mean over repetitions, with the min-max over repetitions in brackets. Aggregate decode TPS = the sum over users. Prefill time = the slowest user's 'Parsing the prompt took' of a run. Prefill tokens/s per request = mean of the users' 'at R tokens/s'. Aggregate prefill rate = users x prompt tokens / the slowest user's prefill time. Delta = amxon relative to amxoff; a positive delta on a rate is a gain for the AMX kernel, a positive delta on the prefill time is a loss.

| cell | arm | reps | decode TPS per user (min-max) | aggregate decode TPS | prefill s, slowest user (min-max) | prefill tokens/s per request | aggregate prefill tokens/s | delta decode TPS | delta prefill time | delta aggregate prefill rate |
|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-fpga | amxon | 3 | 42.60 (42.58-42.62) | 340.8 | 14.888 (14.884-14.891) | 68.8 | 550.2 | +1.7 % | +0.4 % | -0.4 % |
| glm-tp2-8u-p1024-fpga | amxoff | 3 | 41.90 (41.87-41.94) | 335.2 | 14.825 (14.819-14.829) | 69.1 | 552.6 |  |  |  |
| glm-tp4-8u-p1024-fpga | amxon | 3 | 62.58 (62.57-62.59) | 500.6 | 8.473 (8.460-8.482) | 121.0 | 966.9 | -0.8 % | +2.1 % | -2.1 % |
| glm-tp4-8u-p1024-fpga | amxoff | 3 | 63.08 (62.85-63.20) | 504.6 | 8.298 (8.289-8.311) | 123.5 | 987.2 |  |  |  |
| l8b-tp2-8u-p1024-cpu | amxon | 3 | 119.56 (119.40-119.68) | 956.5 | 3.408 (3.406-3.409) | 300.8 | 2,403.9 | +0.1 % | -0.0 % | +0.0 % |
| l8b-tp2-8u-p1024-cpu | amxoff | 3 | 119.42 (119.25-119.54) | 955.4 | 3.408 (3.407-3.409) | 300.7 | 2,403.6 |  |  |  |
| glm-tp2-8u-p2048-fpga | amxon | 3 | 38.89 (38.86-38.92) | 311.1 | 29.582 (29.582-29.584) | 69.3 | 553.8 | +1.9 % | -4.4 % | +4.6 % |
| glm-tp2-8u-p2048-fpga | amxoff | 3 | 38.15 (38.13-38.18) | 305.2 | 30.931 (30.901-30.966) | 66.2 | 529.7 |  |  |  |

The same numbers are in results.json (per cell: arms -> reps, tps_user, tps_user_reps, tps_agg, prefill_s, prefill_s_reps, prefill_rate, prefill_agg; delta -> tps_user, prefill_s, prefill_agg in percent).

## 7. Time

Cycles are converted with tsc_hz of the run.

- T1 ms per forward = forward wall time per forward.
- busy s = T2 summed over all workers and jobs of the class. busy ms per job = T2 per attention job (both software passes and the join, without the upstream K/V wait).
- join wait share = T5 / T2.
- T4 ms per forward = the layer-to-layer periods on attention worker 0, summed per forward (n_layers - 1 periods).

| cell | class | arm | forwards | T1 ms per forward | busy s (all workers) | busy ms per job | join wait share | T4 ms per forward |
|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep1 | 256 | 23.30 | 14.29 | 0.054 | 15.8 % | 21.35 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep2 | 256 | 23.32 | 14.33 | 0.054 | 15.7 % | 21.37 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep3 | 256 | 23.32 | 14.34 | 0.054 | 15.7 % | 21.37 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep1 | 256 | 23.70 | 16.07 | 0.060 | 25.3 % | 21.75 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep2 | 256 | 23.72 | 16.08 | 0.060 | 25.5 % | 21.77 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep3 | 256 | 23.69 | 15.96 | 0.060 | 25.5 % | 21.73 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8 | 1,853.51 | 44.24 | 5.317 | 44.2 % | 1,793.91 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8 | 1,853.31 | 44.24 | 5.317 | 44.2 % | 1,793.81 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep3 | 8 | 1,852.69 | 44.05 | 5.295 | 44.2 % | 1,793.21 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8 | 1,845.89 | 43.08 | 5.178 | 43.4 % | 1,786.25 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8 | 1,844.44 | 43.09 | 5.179 | 43.4 % | 1,784.88 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep3 | 8 | 1,845.63 | 43.12 | 5.183 | 43.7 % | 1,786.05 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep1 | 256 | 15.81 | 25.21 | 0.040 | 34.1 % | 14.58 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep2 | 256 | 15.81 | 24.50 | 0.039 | 33.8 % | 14.58 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep3 | 256 | 15.81 | 25.27 | 0.040 | 33.0 % | 14.58 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep1 | 256 | 15.75 | 24.74 | 0.040 | 31.4 % | 14.51 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep2 | 256 | 15.66 | 24.19 | 0.039 | 31.4 % | 14.42 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep3 | 256 | 15.66 | 24.53 | 0.039 | 30.7 % | 14.42 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8 | 1,053.48 | 68.22 | 4.100 | 60.1 % | 1,013.21 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8 | 1,050.89 | 67.47 | 4.055 | 59.6 % | 1,010.73 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep3 | 8 | 1,052.94 | 68.07 | 4.091 | 59.9 % | 1,012.78 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8 | 1,032.27 | 61.79 | 3.714 | 56.8 % | 992.08 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8 | 1,030.08 | 61.14 | 3.674 | 56.6 % | 990.02 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep3 | 8 | 1,029.58 | 61.32 | 3.685 | 56.4 % | 989.42 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 256 | 8.26 | 33.70 | 0.089 | 5.9 % | 7.25 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 256 | 8.24 | 33.64 | 0.089 | 5.9 % | 7.24 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep3 | 256 | 8.25 | 33.83 | 0.090 | 5.9 % | 7.24 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 256 | 8.25 | 34.01 | 0.090 | 3.4 % | 7.26 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 256 | 8.26 | 33.66 | 0.089 | 3.4 % | 7.26 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep3 | 256 | 8.28 | 33.99 | 0.090 | 3.4 % | 7.28 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8 | 423.45 | 19.99 | 0.648 | 10.3 % | 395.85 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8 | 423.76 | 20.05 | 0.650 | 10.5 % | 396.12 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep3 | 8 | 423.87 | 19.99 | 0.648 | 10.3 % | 396.26 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8 | 423.83 | 19.55 | 0.634 | 10.4 % | 396.15 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8 | 423.71 | 19.55 | 0.634 | 10.1 % | 396.11 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep3 | 8 | 423.67 | 19.51 | 0.632 | 9.9 % | 396.07 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep1 | 256 | 25.43 | 24.25 | 0.091 | 13.2 % | 23.43 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep2 | 256 | 25.46 | 24.26 | 0.091 | 13.0 % | 23.46 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep3 | 256 | 25.47 | 24.41 | 0.092 | 13.0 % | 23.47 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep1 | 256 | 25.97 | 26.73 | 0.100 | 20.7 % | 23.96 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep2 | 256 | 25.93 | 26.60 | 0.100 | 20.8 % | 23.92 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep3 | 256 | 25.97 | 26.68 | 0.100 | 20.8 % | 23.96 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 16 | 1,842.45 | 88.86 | 5.340 | 28.4 % | 1,787.73 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 16 | 1,842.29 | 88.67 | 5.328 | 28.3 % | 1,787.54 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep3 | 16 | 1,842.29 | 89.29 | 5.366 | 28.5 % | 1,787.59 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 16 | 1,928.83 | 115.99 | 6.971 | 45.3 % | 1,874.03 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 16 | 1,924.74 | 115.00 | 6.911 | 45.1 % | 1,869.96 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep3 | 16 | 1,926.29 | 115.28 | 6.928 | 45.0 % | 1,871.47 |

## 8. Situations

### 8.1 Glimmer with FPGA attention (the production default: 13 card layers, 39 software layers)

- glm-tp2-8u-p1024-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 72.1 % of the K tokens (2,766,816 visits). AVX 2.9 %. FPGA 24.9 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 7,028,736 in the software-only layers.
  - amxoff: AVX 2.9 %, FPGA 24.9 %, avx_full_page visits 29,016.
  - Busy per job goes from 0.054 ms (amxon) to 0.060 ms (amxoff), 112.5 % of amxon.
- glm-tp2-8u-p1024-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 57.4 % of the K tokens (3,913,728 visits). AVX 20.8 %. FPGA 21.9 %.
  - AVX K tokens split by layer kind: 13,737,802 in the card layers, 76,996,062 in the software-only layers.
  - amxoff: AVX 20.8 %, FPGA 21.9 %, avx_full_page visits 986,752.
  - Busy per job goes from 5.317 ms (amxon) to 5.178 ms (amxoff), 97.4 % of amxon.
  - Decode TPS per user 42.60 (amxon) vs 41.90 (amxoff) over 3 rep: +1.7 % for the AMX kernel; prefill time +0.4 %.
- glm-tp4-8u-p1024-fpga (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 72.1 % of the K tokens (2,766,816 visits). AVX 2.9 %. FPGA 24.9 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 7,028,736 in the software-only layers.
  - amxoff: AVX 2.9 %, FPGA 24.9 %, avx_full_page visits 29,016.
  - Busy per job goes from 0.040 ms (amxon) to 0.040 ms (amxoff), 98.1 % of amxon.
- glm-tp4-8u-p1024-fpga (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 57.4 % of the K tokens (3,913,728 visits). AVX 20.8 %. FPGA 21.9 %.
  - AVX K tokens split by layer kind: 13,737,802 in the card layers, 76,996,062 in the software-only layers.
  - amxoff: AVX 20.8 %, FPGA 21.9 %, avx_full_page visits 986,752.
  - Busy per job goes from 4.100 ms (amxon) to 3.714 ms (amxoff), 90.6 % of amxon.
  - Decode TPS per user 62.58 (amxon) vs 63.08 (amxoff) over 3 rep: -0.8 % for the AMX kernel; prefill time +2.1 %.
- glm-tp2-8u-p2048-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 69.5 % of the K tokens (4,814,472 visits). AVX 4.3 %. FPGA 26.1 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 19,029,504 in the software-only layers.
  - amxoff: AVX 4.3 %, FPGA 26.1 %, avx_full_page visits 2,496.
  - Busy per job goes from 0.091 ms (amxon) to 0.100 ms (amxoff), 110.2 % of amxon.
- glm-tp2-8u-p2048-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 66.3 % of the K tokens (18,091,008 visits). AVX 11.0 %. FPGA 22.6 %.
  - AVX K tokens split by layer kind: 28,966,730 in the card layers, 163,577,310 in the software-only layers.
  - amxoff: AVX 11.0 %, FPGA 22.6 %, avx_full_page visits 1,849,536.
  - Busy per job goes from 5.340 ms (amxon) to 6.971 ms (amxoff), 130.5 % of amxon.
  - Decode TPS per user 38.89 (amxon) vs 38.15 (amxoff) over 3 rep: +1.9 % for the AMX kernel; prefill time -4.4 %.

### 8.2 Glimmer with CPU attention (all 52 layers in software)

- no finished cell in this group.

### 8.3 llama-3.1-8b regression cell (kv_mul 4, the unchanged kernel path)

- l8b-tp2-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 96.5 % of the K tokens (9,110,528 visits). AVX 3.5 %. FPGA 0.0 %.
  - amxoff: AVX 3.5 %, FPGA 0.0 %, avx_full_page visits 65,536.
  - Busy per job goes from 0.089 ms (amxon) to 0.090 ms (amxoff), 100.7 % of amxon.
- l8b-tp2-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 86.0 % of the K tokens (14,450,688 visits). AVX 14.0 %. FPGA 0.0 %.
  - amxoff: AVX 14.0 %, FPGA 0.0 %, avx_full_page visits 1,282,048.
  - Busy per job goes from 0.648 ms (amxon) to 0.634 ms (amxoff), 97.8 % of amxon.
  - Decode TPS per user 119.56 (amxon) vs 119.42 (amxoff) over 3 rep: +0.1 % for the AMX kernel; prefill time -0.0 %.

## 9. Failed or stopped runs

Runs with no complete attempt:

- none

## 10. Files

- results: exec/results/glimpl-20261017/ (rt-results.txt, rt/<run>.log, exit-reports.txt, results.json, tests.txt, preservation.txt, build.txt, leaves/<run>/ = in-flight FUSE leaf snapshots, not used by this report)
- scripts: exec/glimpl-20261017/ (build.sh, tests.sh, chain.sh, campaign.sh, gen_compare.py, launch.sh, README.md)
- binary: runtron.g16q built from branch jhan-amx-kvmul16 6cda072924 with --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON (see build.txt)
