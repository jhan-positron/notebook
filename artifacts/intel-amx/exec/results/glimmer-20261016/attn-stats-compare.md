# Attention path stats: AMX kernel enabled vs disabled (glimmer-20261016)

## Short version

Tron branch jhan-amx-kvmul16 (5061623a34, the AMX attention kernels generalised to kv_mul 16) ran on our half of delphi-3bda with the attention path stats on (TRON_ATTN_STATS=1). Each cell ran with the AMX kernel enabled (amxon) and with it disabled by the kill switch (amxoff, TRON_AMX_DISABLE=1), 2 repetition(s) per arm. Cells: 9. Runs finished: 36. Runs failed or stopped: 0. The counter tables and identities below use repetition 1; section 6 uses every repetition.
- Glimmer-30B tp2, CPU attention, prompt 1024, 8 users (glm-tp2-8u-p1024-cpu): AMX scored 96.5 % of the decode K tokens (236,873,728 of 245,473,280); decode TPS amxon vs amxoff +13.4 % (mean over 2 rep).
- Glimmer-30B tp2, FPGA attention, prompt 1024, 8 users (glm-tp2-8u-p1024-fpga): AMX scored 72.1 % of the decode K tokens (177,076,224 of 245,473,280); decode TPS amxon vs amxoff +9.0 % (mean over 2 rep).
- Glimmer-30B tp4, CPU attention, prompt 1024, 8 users (glm-tp4-8u-p1024-cpu): AMX scored 96.5 % of the decode K tokens (236,873,728 of 245,473,280); decode TPS amxon vs amxoff +6.1 % (mean over 2 rep).
- Glimmer-30B tp4, FPGA attention, prompt 1024, 8 users (glm-tp4-8u-p1024-fpga): AMX scored 72.1 % of the decode K tokens (177,076,224 of 245,473,280); decode TPS amxon vs amxoff +4.4 % (mean over 2 rep).
- llama-3.1-8b tp2, CPU attention, prompt 1024, 8 users (l8b-tp2-8u-p1024-cpu): AMX scored 96.5 % of the decode K tokens (583,073,792 of 604,241,920); decode TPS amxon vs amxoff +5.2 % (mean over 2 rep).
- Glimmer-30B tp2, CPU attention, prompt 2048, 8 users (glm-tp2-8u-p2048-cpu): AMX scored 94.6 % of the decode K tokens (419,095,040 of 443,049,984); decode TPS amxon vs amxoff +21.2 % (mean over 2 rep).
- Glimmer-30B tp2, FPGA attention, prompt 2048, 8 users (glm-tp2-8u-p2048-fpga): AMX scored 69.5 % of the decode K tokens (308,126,208 of 443,049,984); decode TPS amxon vs amxoff +15.2 % (mean over 2 rep).
- Glimmer-30B tp4, CPU attention, prompt 2048, 8 users (glm-tp4-8u-p2048-cpu): AMX scored 94.6 % of the decode K tokens (419,095,040 of 443,049,984); decode TPS amxon vs amxoff +13.7 % (mean over 2 rep).
- Glimmer-30B tp4, FPGA attention, prompt 2048, 8 users (glm-tp4-8u-p2048-fpga): AMX scored 69.5 % of the decode K tokens (308,126,208 of 443,049,984); decode TPS amxon vs amxoff +10.2 % (mean over 2 rep).

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
| glm-tp2-8u-p1024-cpu | Glimmer-30B tp2 | 2 / 16 / 128 / 52 | fitting | CPU attention | off | 0 | 1024 | 8 | yes / yes | no | 42.17 | 37.11 | 14.68 | 15.78 |
| glm-tp2-8u-p1024-fpga | Glimmer-30B tp2 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 1024 | 8 | yes / yes | no | 41.90 | 38.42 | 14.84 | 15.26 |
| glm-tp4-8u-p1024-cpu | Glimmer-30B tp4 | 2 / 16 / 128 / 52 | fitting | CPU attention | off | 0 | 1024 | 8 | yes / yes | no | 62.55 | 58.95 | 8.45 | 8.55 |
| glm-tp4-8u-p1024-fpga | Glimmer-30B tp4 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 1024 | 8 | yes / yes | no | 63.21 | 60.55 | 8.32 | 8.37 |
| l8b-tp2-8u-p1024-cpu | llama-3.1-8b tp2 | 8 / 4 / 128 / 32 | fitting | CPU attention | off | 0 | 1024 | 8 | yes / yes | no | 119.23 | 113.41 | 3.41 | 3.64 |
| glm-tp2-8u-p2048-cpu | Glimmer-30B tp2 | 2 / 16 / 128 / 52 | fitting | CPU attention | off | 0 | 2048 | 8 | yes / yes | no | 37.77 | 31.14 | 30.97 | 36.20 |
| glm-tp2-8u-p2048-fpga | Glimmer-30B tp2 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 2048 | 8 | yes / yes | no | 38.12 | 33.13 | 30.91 | 33.87 |
| glm-tp4-8u-p2048-cpu | Glimmer-30B tp4 | 2 / 16 / 128 / 52 | fitting | CPU attention | off | 0 | 2048 | 8 | yes / yes | no | 58.87 | 51.62 | 17.43 | 19.53 |
| glm-tp4-8u-p2048-fpga | Glimmer-30B tp4 | 2 / 16 / 128 / 52 | fitting | FPGA attention | on | 13 of 52 | 2048 | 8 | yes / yes | no | 59.82 | 54.23 | 17.03 | 18.35 |

TPS = generated tokens per second per user, mean over users (runtron 'average tok/s'), repetition 1. TTFT = prompt parsing time in seconds, mean over users, repetition 1. Section 6 has the means and spreads over every repetition.

HW attention line and HBM warnings per cell (the line is the first 'HW attention' line of the run's log):

- glm-tp2-8u-p1024-cpu: HW attention disabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp2-8u-p1024-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp2': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp4-8u-p1024-cpu: HW attention disabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp4': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp4-8u-p1024-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp4': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- l8b-tp2-8u-p1024-cpu: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp2-8u-p2048-cpu: HW attention disabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp2': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp2-8u-p2048-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp2': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp4-8u-p2048-cpu: HW attention disabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp4': USE_HW_ATTN=0. HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.
- glm-tp4-8u-p2048-fpga: HW attention enabled for model 'ingested-meta-models--Muse-Glimmer-30B-tp4': max_layers=52 engagement=127 kv_slot_extent=52 hw_attn_params { kv_head_size: 128 n_kv_heads: 2 n_heads: 32 gqa: 16 pre_attn_scalar: 0.088388346 hw_slots: 13 } (model default). HBM warnings amxon lose=0 exhausted=0; amxoff lose=0 exhausted=0.

## 2. K tokens by path, AMX enabled vs disabled

Per cell and class: the K tokens each path scored (software scale), the shares, and the visit counts. Shares are of the row's total K tokens (AMX + AVX + FPGA).

| cell | class | arm | K tokens AMX | share | K tokens AVX | share | K tokens FPGA (x kv heads) | share | visits AMX (ready+pending) | visits AVX | avx_full_page visits | empty visits | FPGA query passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 236,873,728 | 96.5 % | 8,599,552 | 3.5 % | 0 | 0.0 % | 3,701,152 (3,697,824+3,328) | 422,656 | 26,624 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 236,873,728 | 96.5 % | 8,599,552 | 3.5 % | 0 | 0.0 % | 3,701,152 (3,697,824+3,328) | 422,656 | 26,624 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 0 | 0.0 % | 245,473,280 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 4,123,808 | 3,727,776 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 0 | 0.0 % | 245,473,280 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 4,123,808 | 3,727,776 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 375,717,888 | 86.0 % | 60,914,984 | 14.0 % | 0 | 0.0 % | 5,870,592 (5,218,304+652,288) | 2,104,232 | 520,832 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 375,717,888 | 86.0 % | 60,914,984 | 14.0 % | 0 | 0.0 % | 5,870,592 (5,218,304+652,288) | 2,104,232 | 520,832 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 436,632,872 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,974,824 | 6,391,424 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 436,632,872 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,974,824 | 6,391,424 | 0 | 0 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep1 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep2 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep1 | 0 | 0.0 % | 184,238,080 | 75.1 % | 61,235,200 | 24.9 % | 0 (0+0) | 3,148,288 | 2,795,832 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep2 | 0 | 0.0 % | 184,238,080 | 75.1 % | 61,235,200 | 24.9 % | 0 (0+0) | 3,148,288 | 2,795,832 | 0 | 26,624 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 341,212,456 | 78.1 % | 95,420,416 | 21.9 % | 0 (0+0) | 6,483,880 | 4,900,480 | 0 | 93,184 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 341,212,456 | 78.1 % | 95,420,416 | 21.9 % | 0 (0+0) | 6,483,880 | 4,900,480 | 0 | 93,184 |
| glm-tp4-8u-p1024-cpu | decode_like | amxon rep1 | 236,873,728 | 96.5 % | 8,599,552 | 3.5 % | 0 | 0.0 % | 3,701,152 (3,697,824+3,328) | 422,656 | 26,624 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxon rep2 | 236,873,728 | 96.5 % | 8,599,552 | 3.5 % | 0 | 0.0 % | 3,701,152 (3,697,824+3,328) | 422,656 | 26,624 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxoff rep1 | 0 | 0.0 % | 245,473,280 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 4,123,808 | 3,727,776 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxoff rep2 | 0 | 0.0 % | 245,473,280 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 4,123,808 | 3,727,776 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 375,717,888 | 86.0 % | 60,914,984 | 14.0 % | 0 | 0.0 % | 5,870,592 (5,218,304+652,288) | 2,104,232 | 520,832 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 375,717,888 | 86.0 % | 60,914,984 | 14.0 % | 0 | 0.0 % | 5,870,592 (5,218,304+652,288) | 2,104,232 | 520,832 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 436,632,872 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,974,824 | 6,391,424 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 436,632,872 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,974,824 | 6,391,424 | 0 | 0 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep1 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep2 | 177,076,224 | 72.1 % | 7,161,856 | 2.9 % | 61,235,200 | 24.9 % | 2,766,816 (2,766,816+0) | 381,472 | 29,016 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep1 | 0 | 0.0 % | 184,238,080 | 75.1 % | 61,235,200 | 24.9 % | 0 (0+0) | 3,148,288 | 2,795,832 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep2 | 0 | 0.0 % | 184,238,080 | 75.1 % | 61,235,200 | 24.9 % | 0 (0+0) | 3,148,288 | 2,795,832 | 0 | 26,624 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 250,478,592 | 57.4 % | 90,733,864 | 20.8 % | 95,420,416 | 21.9 % | 3,913,728 (3,913,728+0) | 2,570,152 | 986,752 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 341,212,456 | 78.1 % | 95,420,416 | 21.9 % | 0 (0+0) | 6,483,880 | 4,900,480 | 0 | 93,184 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 341,212,456 | 78.1 % | 95,420,416 | 21.9 % | 0 (0+0) | 6,483,880 | 4,900,480 | 0 | 93,184 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 583,073,792 | 96.5 % | 21,168,128 | 3.5 % | 0 | 0.0 % | 9,110,528 (9,102,336+8,192) | 1,040,384 | 65,536 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 0 | 0.0 % | 604,241,920 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 10,150,912 | 9,176,064 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 0 | 0.0 % | 604,241,920 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 10,150,912 | 9,176,064 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 924,844,032 | 86.0 % | 149,944,576 | 14.0 % | 0 | 0.0 % | 14,450,688 (12,845,056+1,605,632) | 5,179,648 | 1,282,048 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 1,074,788,608 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 19,630,336 | 15,732,736 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 1,074,788,608 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 19,630,336 | 15,732,736 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxon rep1 | 419,095,040 | 94.6 % | 23,954,944 | 5.4 % | 0 | 0.0 % | 6,548,360 (6,545,032+3,328) | 606,528 | 6,656 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxon rep2 | 419,095,040 | 94.6 % | 23,954,944 | 5.4 % | 0 | 0.0 % | 6,548,360 (6,545,032+3,328) | 606,528 | 6,656 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxoff rep1 | 0 | 0.0 % | 443,049,984 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,154,888 | 6,555,016 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxoff rep2 | 0 | 0.0 % | 443,049,984 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,154,888 | 6,555,016 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxon rep1 | 1,599,143,936 | 91.6 % | 146,537,768 | 8.4 % | 0 | 0.0 % | 24,986,624 (23,961,600+1,025,024) | 4,601,064 | 1,060,800 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxon rep2 | 1,599,143,936 | 91.6 % | 146,537,768 | 8.4 % | 0 | 0.0 % | 24,986,624 (23,961,600+1,025,024) | 4,601,064 | 1,060,800 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 1,745,681,704 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 29,587,688 | 26,047,424 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 1,745,681,704 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 29,587,688 | 26,047,424 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep1 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep2 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep1 | 0 | 0.0 % | 327,288,832 | 73.9 % | 115,761,152 | 26.1 % | 0 (0+0) | 5,324,488 | 4,816,968 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep2 | 0 | 0.0 % | 327,288,832 | 73.9 % | 115,761,152 | 26.1 % | 0 (0+0) | 5,324,488 | 4,816,968 | 0 | 26,624 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 1,350,368,552 | 77.4 % | 395,313,152 | 22.6 % | 0 (0+0) | 23,341,032 | 19,940,544 | 0 | 199,680 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 1,350,368,552 | 77.4 % | 395,313,152 | 22.6 % | 0 (0+0) | 23,341,032 | 19,940,544 | 0 | 199,680 |
| glm-tp4-8u-p2048-cpu | decode_like | amxon rep1 | 419,095,040 | 94.6 % | 23,954,944 | 5.4 % | 0 | 0.0 % | 6,548,360 (6,545,032+3,328) | 606,528 | 6,656 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxon rep2 | 419,095,040 | 94.6 % | 23,954,944 | 5.4 % | 0 | 0.0 % | 6,548,360 (6,545,032+3,328) | 606,528 | 6,656 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxoff rep1 | 0 | 0.0 % | 443,049,984 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,154,888 | 6,555,016 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxoff rep2 | 0 | 0.0 % | 443,049,984 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 7,154,888 | 6,555,016 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxon rep1 | 1,599,143,936 | 91.6 % | 146,537,768 | 8.4 % | 0 | 0.0 % | 24,986,624 (23,961,600+1,025,024) | 4,601,064 | 1,060,800 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxon rep2 | 1,599,143,936 | 91.6 % | 146,537,768 | 8.4 % | 0 | 0.0 % | 24,986,624 (23,961,600+1,025,024) | 4,601,064 | 1,060,800 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 1,745,681,704 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 29,587,688 | 26,047,424 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 1,745,681,704 | 100.0 % | 0 | 0.0 % | 0 (0+0) | 29,587,688 | 26,047,424 | 0 | 0 |
| glm-tp4-8u-p2048-fpga | decode_like | amxon rep1 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp4-8u-p2048-fpga | decode_like | amxon rep2 | 308,126,208 | 69.5 % | 19,162,624 | 4.3 % | 115,761,152 | 26.1 % | 4,814,472 (4,814,472+0) | 510,016 | 2,496 | 0 | 26,624 |
| glm-tp4-8u-p2048-fpga | decode_like | amxoff rep1 | 0 | 0.0 % | 327,288,832 | 73.9 % | 115,761,152 | 26.1 % | 0 (0+0) | 5,324,488 | 4,816,968 | 0 | 26,624 |
| glm-tp4-8u-p2048-fpga | decode_like | amxoff rep2 | 0 | 0.0 % | 327,288,832 | 73.9 % | 115,761,152 | 26.1 % | 0 (0+0) | 5,324,488 | 4,816,968 | 0 | 26,624 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 1,157,824,512 | 66.3 % | 192,544,040 | 11.0 % | 395,313,152 | 22.6 % | 18,091,008 (18,091,008+0) | 5,250,024 | 1,849,536 | 0 | 199,680 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 0 | 0.0 % | 1,350,368,552 | 77.4 % | 395,313,152 | 22.6 % | 0 (0+0) | 23,341,032 | 19,940,544 | 0 | 199,680 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 0 | 0.0 % | 1,350,368,552 | 77.4 % | 395,313,152 | 22.6 % | 0 (0+0) | 23,341,032 | 19,940,544 | 0 | 199,680 |

## 3. Kill-switch identity

When both arms scored the same prompts, generated the same number of tokens (--dont-stop) and had the same HBM warning counts, every dense page the kernel took in amxon is an AVX full-page visit in amxoff. So avx_full_page(amxoff) must equal amx_visits(amxon) + avx_full_page(amxon). The AVX K tokens of amxoff must equal the AMX + AVX K tokens of amxon. A mismatch means the two runs did not score the same positions, or a counter defect. For a non-fitting shape both arms have 0 AMX visits and the identity degenerates to equal counts.

| cell | class | amx visits (on) | avx_full_page (on) | avx_full_page (off) | visits identity | K tokens AMX+AVX (on) | K tokens AVX (off) | K identity | FPGA K tokens on / off |
|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-cpu | decode_like | 3,701,152 | 26,624 | 3,727,776 | holds | 245,473,280 | 245,473,280 | holds | 0 / 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | 5,870,592 | 520,832 | 6,391,424 | holds | 436,632,872 | 436,632,872 | holds | 0 / 0 |
| glm-tp2-8u-p1024-fpga | decode_like | 2,766,816 | 29,016 | 2,795,832 | holds | 184,238,080 | 184,238,080 | holds | 61,235,200 / 61,235,200 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | 3,913,728 | 986,752 | 4,900,480 | holds | 341,212,456 | 341,212,456 | holds | 95,420,416 / 95,420,416 |
| glm-tp4-8u-p1024-cpu | decode_like | 3,701,152 | 26,624 | 3,727,776 | holds | 245,473,280 | 245,473,280 | holds | 0 / 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | 5,870,592 | 520,832 | 6,391,424 | holds | 436,632,872 | 436,632,872 | holds | 0 / 0 |
| glm-tp4-8u-p1024-fpga | decode_like | 2,766,816 | 29,016 | 2,795,832 | holds | 184,238,080 | 184,238,080 | holds | 61,235,200 / 61,235,200 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | 3,913,728 | 986,752 | 4,900,480 | holds | 341,212,456 | 341,212,456 | holds | 95,420,416 / 95,420,416 |
| l8b-tp2-8u-p1024-cpu | decode_like | 9,110,528 | 65,536 | 9,176,064 | holds | 604,241,920 | 604,241,920 | holds | 0 / 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | 14,450,688 | 1,282,048 | 15,732,736 | holds | 1,074,788,608 | 1,074,788,608 | holds | 0 / 0 |
| glm-tp2-8u-p2048-cpu | decode_like | 6,548,360 | 6,656 | 6,555,016 | holds | 443,049,984 | 443,049,984 | holds | 0 / 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | 24,986,624 | 1,060,800 | 26,047,424 | holds | 1,745,681,704 | 1,745,681,704 | holds | 0 / 0 |
| glm-tp2-8u-p2048-fpga | decode_like | 4,814,472 | 2,496 | 4,816,968 | holds | 327,288,832 | 327,288,832 | holds | 115,761,152 / 115,761,152 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | 18,091,008 | 1,849,536 | 19,940,544 | holds | 1,350,368,552 | 1,350,368,552 | holds | 395,313,152 / 395,313,152 |
| glm-tp4-8u-p2048-cpu | decode_like | 6,548,360 | 6,656 | 6,555,016 | holds | 443,049,984 | 443,049,984 | holds | 0 / 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | 24,986,624 | 1,060,800 | 26,047,424 | holds | 1,745,681,704 | 1,745,681,704 | holds | 0 / 0 |
| glm-tp4-8u-p2048-fpga | decode_like | 4,814,472 | 2,496 | 4,816,968 | holds | 327,288,832 | 327,288,832 | holds | 115,761,152 / 115,761,152 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | 18,091,008 | 1,849,536 | 19,940,544 | holds | 1,350,368,552 | 1,350,368,552 | holds | 395,313,152 / 395,313,152 |

## 4. Token jobs by path set

A token job is one token of one user inside one forward. During that forward the token's keys are scored layer by layer, KV head by KV head, page by page, and each (KV head, page) step takes one path: the AMX kernel, the AVX loop or the FPGA card. One token job therefore usually touches more than one path in a forward, for example the kernel for its full pages and the AVX loop for its pending page.

The table counts token jobs by the combination of paths that touched them. Each token job goes into exactly one column: the set of all paths it used in its forward, over all layers, KV heads and pages. The counts add up over every forward of the class, so the token jobs column equals forwards x jobs per forward (8 in decode here), and the eight path-set columns add up to it.

| cell | class | arm | token jobs | forwards | FPGA queries | none | avx | amx | avx+amx | fpga | fpga+avx | fpga+amx | fpga+avx+amx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxon rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxon rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxoff rep1 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | decode_like | amxoff rep2 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 7,168 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 7,168 | 0 | 1,017 | 0 | 0 | 0 | 7,168 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8,185 | 8 | 0 | 0 | 1,017 | 0 | 7,168 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8,185 | 8 | 0 | 0 | 8,185 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxon rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxon rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxoff rep1 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | decode_like | amxoff rep2 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxon rep1 | 16,377 | 16 | 0 | 0 | 1,017 | 0 | 15,360 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxon rep2 | 16,377 | 16 | 0 | 0 | 1,017 | 0 | 15,360 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxoff rep1 | 16,377 | 16 | 0 | 0 | 16,377 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxoff rep2 | 16,377 | 16 | 0 | 0 | 16,377 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 15,360 | 0 | 0 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 15,360 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxon rep1 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxon rep2 | 2,048 | 256 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxoff rep1 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | decode_like | amxoff rep2 | 2,048 | 256 | 0 | 0 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxon rep1 | 16,377 | 16 | 0 | 0 | 1,017 | 0 | 15,360 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxon rep2 | 16,377 | 16 | 0 | 0 | 1,017 | 0 | 15,360 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxoff rep1 | 16,377 | 16 | 0 | 0 | 16,377 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxoff rep2 | 16,377 | 16 | 0 | 0 | 16,377 | 0 | 0 | 0 | 0 | 0 | 0 |
| glm-tp4-8u-p2048-fpga | decode_like | amxon rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p2048-fpga | decode_like | amxon rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,048 |
| glm-tp4-8u-p2048-fpga | decode_like | amxoff rep1 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp4-8u-p2048-fpga | decode_like | amxoff rep2 | 2,048 | 256 | 2,048 | 0 | 0 | 0 | 0 | 0 | 2,048 | 0 | 0 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 0 | 0 | 15,360 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 15,360 | 0 | 0 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 16,377 | 16 | 15,360 | 0 | 1,017 | 0 | 0 | 0 | 15,360 | 0 | 0 |

## 5. Per-layer pattern

From the 'k_tokens per layer' line of the exit report (ready + pending, summed over workers). Layers with FPGA > 0 are the layers the card served. Layers with AMX > 0 are the layers where the kernel ran. AMX and AVX are K tokens per KV head. The FPGA value is per query (all KV heads at once); multiply it by n_kv_heads (2 for Glimmer, 8 for llama) to compare it with the other two.

Expected for Glimmer: amxon with attn=fpga shows AMX K tokens on the 39 sliding-window layers only, and FPGA K tokens plus a small AVX tail on the 13 full layers; amxon with attn=cpu shows AMX on all 52 layers; amxoff shows AMX on no layer. Each line below ends with that check.

- glm-tp2-8u-p1024-cpu amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 4,555,264/165,376/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,225,344/1,171,442/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 4,555,264/165,376/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,225,344/1,171,442/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/4,720,640/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,396,786/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/4,720,640/0 in layers 0-51
- glm-tp2-8u-p1024-cpu amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,396,786/0 in layers 0-51
- glm-tp2-8u-p1024-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/4,720,640/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,396,786/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/4,720,640/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p1024-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,396,786/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-cpu amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 4,555,264/165,376/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,225,344/1,171,442/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 4,555,264/165,376/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,225,344/1,171,442/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/4,720,640/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,396,786/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/4,720,640/0 in layers 0-51
- glm-tp4-8u-p1024-cpu amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,396,786/0 in layers 0-51
- glm-tp4-8u-p1024-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 4,540,416/180,224/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 6,422,528/1,974,258/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/4,720,640/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,396,786/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/2,355,200 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/4,720,640/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p1024-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/1,056,754/3,670,016 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,396,786/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- l8b-tp2-8u-p1024-cpu amxon rep1 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep1 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep2 decode_like: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 18,221,056/661,504/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxon rep2 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 32 (layers 0-31); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (AMX on every layer)
  - distinct per-layer (amx/avx/fpga) triples: 28,901,376/4,685,768/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep1 decode_like: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/18,882,560/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep1 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/33,587,144/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep2 decode_like: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/18,882,560/0 in layers 0-31
- l8b-tp2-8u-p1024-cpu amxoff rep2 prompt_or_mixed: 32 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 32. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/33,587,144/0 in layers 0-31
- glm-tp2-8u-p2048-cpu amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,904,768/483,840/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 8,523,776/391,168/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp2-8u-p2048-cpu amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 30,752,768/2,818,034/0 in layers 0-51
- glm-tp2-8u-p2048-cpu amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,904,768/483,840/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 8,523,776/391,168/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp2-8u-p2048-cpu amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 30,752,768/2,818,034/0 in layers 0-51
- glm-tp2-8u-p2048-cpu amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 0/8,914,944/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp2-8u-p2048-cpu amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/33,570,802/0 in layers 0-51
- glm-tp2-8u-p2048-cpu amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 0/8,914,944/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp2-8u-p2048-cpu amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/33,570,802/0 in layers 0-51
- glm-tp2-8u-p2048-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/3,162,098/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/33,570,802/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp2-8u-p2048-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/3,162,098/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/33,570,802/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-cpu amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,904,768/483,840/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 8,523,776/391,168/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp4-8u-p2048-cpu amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 30,752,768/2,818,034/0 in layers 0-51
- glm-tp4-8u-p2048-cpu amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 7,904,768/483,840/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 8,523,776/391,168/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp4-8u-p2048-cpu amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (AMX on all 52 layers, FPGA on none)
  - distinct per-layer (amx/avx/fpga) triples: 30,752,768/2,818,034/0 in layers 0-51
- glm-tp4-8u-p2048-cpu amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 0/8,914,944/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp4-8u-p2048-cpu amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/33,570,802/0 in layers 0-51
- glm-tp4-8u-p2048-cpu amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50; 0/8,914,944/0 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51
- glm-tp4-8u-p2048-cpu amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 0 (layers none); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/33,570,802/0 in layers 0-51
- glm-tp4-8u-p2048-fpga amxon rep1 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxon rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxon rep2 decode_like: 52 layers; AMX K tokens > 0 in 39 (layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 7,900,672/487,936/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxon rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 52 (layers 0-51); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. UNEXPECTED: expected AMX on the 39 sliding layers, FPGA on the 13 full layers, none on both; seen AMX on 52, FPGA on 13, both on 13
  - distinct per-layer (amx/avx/fpga) triples: 933,888/2,228,210/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 29,376,512/4,194,290/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxoff rep1 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxoff rep1 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/3,162,098/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/33,570,802/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxoff rep2 decode_like: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/10,240/4,452,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/8,388,608/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50
- glm-tp4-8u-p2048-fpga amxoff rep2 prompt_or_mixed: 52 layers; AMX K tokens > 0 in 0 (layers none); FPGA > 0 in 13 (layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51); AVX > 0 in 52. as expected (no AMX layer)
  - distinct per-layer (amx/avx/fpga) triples: 0/3,162,098/15,204,352 in layers 3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51; 0/33,570,802/0 in layers 0-2, 4-6, 8-10, 12-14, 16-18, 20-22, 24-26, 28-30, 32-34, 36-38, 40-42, 44-46, 48-50

## 6. Performance (every repetition)

Per cell and arm over the 2 repetition(s): decode TPS per user = mean over the 8 users' 'average tok/s' lines of a run, then mean over repetitions, with the min-max over repetitions in brackets. Aggregate decode TPS = the sum over users. Prefill time = the slowest user's 'Parsing the prompt took' of a run. Prefill tokens/s per request = mean of the users' 'at R tokens/s'. Aggregate prefill rate = users x prompt tokens / the slowest user's prefill time. Delta = amxon relative to amxoff; a positive delta on a rate is a gain for the AMX kernel, a positive delta on the prefill time is a loss.

| cell | arm | reps | decode TPS per user (min-max) | aggregate decode TPS | prefill s, slowest user (min-max) | prefill tokens/s per request | aggregate prefill tokens/s | delta decode TPS | delta prefill time | delta aggregate prefill rate |
|---|---|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-cpu | amxon | 2 | 42.14 (42.11-42.17) | 337.1 | 14.703 (14.679-14.727) | 69.7 | 557.2 | +13.4 % | -6.6 % | +7.1 % |
| glm-tp2-8u-p1024-cpu | amxoff | 2 | 37.15 (37.11-37.18) | 297.2 | 15.750 (15.725-15.775) | 65.1 | 520.1 |  |  |  |
| glm-tp2-8u-p1024-fpga | amxon | 2 | 41.89 (41.89-41.90) | 335.2 | 14.836 (14.832-14.841) | 69.1 | 552.2 | +9.0 % | -2.8 % | +2.9 % |
| glm-tp2-8u-p1024-fpga | amxoff | 2 | 38.42 (38.42-38.42) | 307.4 | 15.265 (15.261-15.269) | 67.1 | 536.7 |  |  |  |
| glm-tp4-8u-p1024-cpu | amxon | 2 | 62.54 (62.52-62.55) | 500.3 | 8.448 (8.447-8.449) | 121.3 | 969.7 | +6.1 % | -1.3 % | +1.3 % |
| glm-tp4-8u-p1024-cpu | amxoff | 2 | 58.96 (58.95-58.97) | 471.7 | 8.561 (8.553-8.570) | 119.7 | 956.9 |  |  |  |
| glm-tp4-8u-p1024-fpga | amxon | 2 | 63.08 (62.94-63.21) | 504.6 | 8.313 (8.304-8.322) | 123.3 | 985.5 | +4.4 % | -0.6 % | +0.6 % |
| glm-tp4-8u-p1024-fpga | amxoff | 2 | 60.44 (60.32-60.55) | 483.5 | 8.363 (8.356-8.371) | 122.6 | 979.5 |  |  |  |
| l8b-tp2-8u-p1024-cpu | amxon | 2 | 119.08 (118.93-119.23) | 952.6 | 3.408 (3.407-3.409) | 300.8 | 2,403.6 | +5.2 % | -6.3 % | +6.7 % |
| l8b-tp2-8u-p1024-cpu | amxoff | 2 | 113.20 (113.00-113.41) | 905.6 | 3.638 (3.636-3.640) | 281.8 | 2,252.0 |  |  |  |
| glm-tp2-8u-p2048-cpu | amxon | 2 | 37.78 (37.77-37.78) | 302.2 | 30.945 (30.921-30.970) | 66.2 | 529.4 | +21.2 % | -14.8 % | +17.3 % |
| glm-tp2-8u-p2048-cpu | amxoff | 2 | 31.17 (31.14-31.19) | 249.3 | 36.310 (36.201-36.418) | 56.4 | 451.2 |  |  |  |
| glm-tp2-8u-p2048-fpga | amxon | 2 | 38.15 (38.12-38.18) | 305.2 | 30.910 (30.907-30.913) | 66.3 | 530.1 | +15.2 % | -8.7 % | +9.5 % |
| glm-tp2-8u-p2048-fpga | amxoff | 2 | 33.11 (33.08-33.13) | 264.8 | 33.849 (33.825-33.874) | 60.5 | 484.0 |  |  |  |
| glm-tp4-8u-p2048-cpu | amxon | 2 | 58.71 (58.56-58.87) | 469.7 | 17.346 (17.257-17.435) | 118.1 | 944.6 | +13.7 % | -11.0 % | +12.3 % |
| glm-tp4-8u-p2048-cpu | amxoff | 2 | 51.63 (51.62-51.64) | 413.0 | 19.481 (19.428-19.533) | 105.2 | 841.0 |  |  |  |
| glm-tp4-8u-p2048-fpga | amxon | 2 | 59.74 (59.67-59.82) | 477.9 | 17.065 (17.031-17.099) | 120.1 | 960.1 | +10.2 % | -6.9 % | +7.4 % |
| glm-tp4-8u-p2048-fpga | amxoff | 2 | 54.21 (54.20-54.23) | 433.7 | 18.326 (18.303-18.348) | 111.8 | 894.0 |  |  |  |

The same numbers are in results.json (per cell: arms -> reps, tps_user, tps_user_reps, tps_agg, prefill_s, prefill_s_reps, prefill_rate, prefill_agg; delta -> tps_user, prefill_s, prefill_agg in percent).

## 7. Time

Cycles are converted with tsc_hz of the run.

- T1 ms per forward = forward wall time per forward.
- busy s = T2 summed over all workers and jobs of the class. busy ms per job = T2 per attention job (both software passes and the join, without the upstream K/V wait).
- join wait share = T5 / T2.
- T4 ms per forward = the layer-to-layer periods on attention worker 0, summed per forward (n_layers - 1 periods).

| cell | class | arm | forwards | T1 ms per forward | busy s (all workers) | busy ms per job | join wait share | T4 ms per forward |
|---|---|---|---|---|---|---|---|---|
| glm-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 256 | 23.61 | 18.43 | 0.069 | 14.8 % | 21.65 |
| glm-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 256 | 23.64 | 18.57 | 0.070 | 14.8 % | 21.68 |
| glm-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 256 | 26.83 | 34.88 | 0.131 | 5.4 % | 24.82 |
| glm-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 256 | 26.78 | 34.71 | 0.130 | 5.3 % | 24.76 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8 | 1,830.13 | 43.04 | 5.173 | 42.5 % | 1,776.98 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8 | 1,836.31 | 43.45 | 5.222 | 43.1 % | 1,782.97 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8 | 1,966.85 | 64.20 | 7.717 | 17.5 % | 1,910.82 |
| glm-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8 | 1,960.69 | 63.63 | 7.648 | 16.6 % | 1,904.81 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep1 | 256 | 23.70 | 15.99 | 0.060 | 25.3 % | 21.74 |
| glm-tp2-8u-p1024-fpga | decode_like | amxon rep2 | 256 | 23.70 | 16.05 | 0.060 | 25.7 % | 21.75 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep1 | 256 | 25.86 | 27.06 | 0.102 | 9.5 % | 23.90 |
| glm-tp2-8u-p1024-fpga | decode_like | amxoff rep2 | 256 | 25.85 | 27.07 | 0.102 | 9.5 % | 23.90 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8 | 1,845.68 | 43.10 | 5.180 | 43.8 % | 1,786.84 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8 | 1,844.36 | 42.99 | 5.167 | 43.6 % | 1,785.69 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8 | 1,898.19 | 51.09 | 6.141 | 16.0 % | 1,839.48 |
| glm-tp2-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8 | 1,899.21 | 51.41 | 6.179 | 16.3 % | 1,840.49 |
| glm-tp4-8u-p1024-cpu | decode_like | amxon rep1 | 256 | 15.86 | 29.88 | 0.048 | 31.5 % | 14.61 |
| glm-tp4-8u-p1024-cpu | decode_like | amxon rep2 | 256 | 15.87 | 30.19 | 0.048 | 31.7 % | 14.62 |
| glm-tp4-8u-p1024-cpu | decode_like | amxoff rep1 | 256 | 16.85 | 42.88 | 0.069 | 10.1 % | 15.58 |
| glm-tp4-8u-p1024-cpu | decode_like | amxoff rep2 | 256 | 16.84 | 42.33 | 0.068 | 10.2 % | 15.56 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8 | 1,052.61 | 72.03 | 4.329 | 62.4 % | 1,018.94 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8 | 1,052.13 | 71.91 | 4.322 | 62.3 % | 1,018.44 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8 | 1,065.23 | 75.17 | 4.517 | 28.2 % | 1,031.37 |
| glm-tp4-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8 | 1,067.46 | 75.46 | 4.535 | 28.5 % | 1,033.42 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep1 | 256 | 15.64 | 23.94 | 0.038 | 32.2 % | 14.41 |
| glm-tp4-8u-p1024-fpga | decode_like | amxon rep2 | 256 | 15.71 | 24.28 | 0.039 | 31.1 % | 14.47 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep1 | 256 | 16.33 | 32.85 | 0.053 | 12.3 % | 15.10 |
| glm-tp4-8u-p1024-fpga | decode_like | amxoff rep2 | 256 | 16.40 | 32.96 | 0.053 | 13.4 % | 15.17 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep1 | 8 | 1,032.12 | 61.91 | 3.720 | 56.8 % | 992.90 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxon rep2 | 8 | 1,029.45 | 61.35 | 3.687 | 56.6 % | 990.13 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep1 | 8 | 1,037.83 | 62.90 | 3.780 | 30.5 % | 998.71 |
| glm-tp4-8u-p1024-fpga | prompt_or_mixed | amxoff rep2 | 8 | 1,036.13 | 62.34 | 3.746 | 29.9 % | 997.09 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep1 | 256 | 8.27 | 33.87 | 0.090 | 3.2 % | 7.28 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxon rep2 | 256 | 8.29 | 33.99 | 0.090 | 3.4 % | 7.30 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep1 | 256 | 8.71 | 41.34 | 0.105 | 3.7 % | 7.69 |
| l8b-tp2-8u-p1024-cpu | decode_like | amxoff rep2 | 256 | 8.74 | 41.49 | 0.105 | 3.8 % | 7.73 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep1 | 8 | 423.58 | 19.95 | 0.647 | 10.4 % | 395.99 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxon rep2 | 8 | 423.92 | 19.88 | 0.644 | 10.5 % | 396.37 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep1 | 8 | 452.44 | 36.44 | 1.117 | 7.2 % | 427.14 |
| l8b-tp2-8u-p1024-cpu | prompt_or_mixed | amxoff rep2 | 8 | 452.00 | 36.40 | 1.115 | 7.3 % | 426.69 |
| glm-tp2-8u-p2048-cpu | decode_like | amxon rep1 | 256 | 26.30 | 31.81 | 0.119 | 9.3 % | 24.25 |
| glm-tp2-8u-p2048-cpu | decode_like | amxon rep2 | 256 | 26.28 | 31.78 | 0.119 | 8.9 % | 24.24 |
| glm-tp2-8u-p2048-cpu | decode_like | amxoff rep1 | 256 | 31.93 | 60.83 | 0.228 | 3.7 % | 29.76 |
| glm-tp2-8u-p2048-cpu | decode_like | amxoff rep2 | 256 | 31.88 | 60.70 | 0.228 | 3.9 % | 29.72 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxon rep1 | 16 | 1,932.12 | 121.32 | 7.291 | 43.0 % | 1,878.42 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxon rep2 | 16 | 1,929.20 | 121.10 | 7.278 | 42.7 % | 1,875.52 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxoff rep1 | 16 | 2,258.70 | 223.31 | 13.420 | 10.9 % | 2,198.51 |
| glm-tp2-8u-p2048-cpu | prompt_or_mixed | amxoff rep2 | 16 | 2,272.29 | 226.19 | 13.593 | 12.0 % | 2,211.55 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep1 | 256 | 25.97 | 26.65 | 0.100 | 21.0 % | 23.97 |
| glm-tp2-8u-p2048-fpga | decode_like | amxon rep2 | 256 | 25.93 | 26.59 | 0.100 | 20.8 % | 23.92 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep1 | 256 | 29.92 | 47.01 | 0.177 | 7.6 % | 27.92 |
| glm-tp2-8u-p2048-fpga | decode_like | amxoff rep2 | 256 | 29.97 | 47.27 | 0.178 | 7.8 % | 27.97 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 16 | 1,924.09 | 115.02 | 6.912 | 45.1 % | 1,870.31 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 16 | 1,923.74 | 114.98 | 6.910 | 45.2 % | 1,869.89 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 16 | 2,108.62 | 172.23 | 10.350 | 9.1 % | 2,054.62 |
| glm-tp2-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 16 | 2,105.88 | 171.83 | 10.326 | 8.8 % | 2,051.93 |
| glm-tp4-8u-p2048-cpu | decode_like | amxon rep1 | 256 | 16.79 | 41.86 | 0.067 | 16.3 % | 15.48 |
| glm-tp4-8u-p2048-cpu | decode_like | amxon rep2 | 256 | 16.88 | 41.62 | 0.067 | 16.8 % | 15.57 |
| glm-tp4-8u-p2048-cpu | decode_like | amxoff rep1 | 256 | 19.18 | 69.36 | 0.111 | 8.6 % | 17.82 |
| glm-tp4-8u-p2048-cpu | decode_like | amxoff rep2 | 256 | 19.17 | 69.39 | 0.111 | 8.3 % | 17.82 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxon rep1 | 16 | 1,086.88 | 169.01 | 5.078 | 56.1 % | 1,053.90 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxon rep2 | 16 | 1,075.79 | 165.81 | 4.982 | 55.3 % | 1,043.08 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxoff rep1 | 16 | 1,217.90 | 248.57 | 7.469 | 19.4 % | 1,182.38 |
| glm-tp4-8u-p2048-cpu | prompt_or_mixed | amxoff rep2 | 16 | 1,211.41 | 245.95 | 7.390 | 18.4 % | 1,176.05 |
| glm-tp4-8u-p2048-fpga | decode_like | amxon rep1 | 256 | 16.44 | 32.60 | 0.052 | 22.9 % | 15.15 |
| glm-tp4-8u-p2048-fpga | decode_like | amxon rep2 | 256 | 16.48 | 33.34 | 0.053 | 22.8 % | 15.20 |
| glm-tp4-8u-p2048-fpga | decode_like | amxoff rep1 | 256 | 18.16 | 53.50 | 0.086 | 10.2 % | 16.88 |
| glm-tp4-8u-p2048-fpga | decode_like | amxoff rep2 | 256 | 18.17 | 53.35 | 0.085 | 10.4 % | 16.89 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxon rep1 | 16 | 1,057.08 | 146.46 | 4.401 | 53.7 % | 1,023.09 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxon rep2 | 16 | 1,061.31 | 148.02 | 4.448 | 54.2 % | 1,027.19 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxoff rep1 | 16 | 1,139.06 | 195.55 | 5.876 | 18.9 % | 1,105.11 |
| glm-tp4-8u-p2048-fpga | prompt_or_mixed | amxoff rep2 | 16 | 1,136.81 | 194.67 | 5.850 | 18.6 % | 1,102.75 |

## 8. Situations

### 8.1 Glimmer with FPGA attention (the production default: 13 card layers, 39 software layers)

- glm-tp2-8u-p1024-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 72.1 % of the K tokens (2,766,816 visits). AVX 2.9 %. FPGA 24.9 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 7,028,736 in the software-only layers.
  - amxoff: AVX 75.1 %, FPGA 24.9 %, avx_full_page visits 2,795,832.
  - Busy per job goes from 0.060 ms (amxon) to 0.102 ms (amxoff), 169.2 % of amxon.
- glm-tp2-8u-p1024-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 57.4 % of the K tokens (3,913,728 visits). AVX 20.8 %. FPGA 21.9 %.
  - AVX K tokens split by layer kind: 13,737,802 in the card layers, 76,996,062 in the software-only layers.
  - amxoff: AVX 78.1 %, FPGA 21.9 %, avx_full_page visits 4,900,480.
  - Busy per job goes from 5.180 ms (amxon) to 6.141 ms (amxoff), 118.5 % of amxon.
  - Decode TPS per user 41.89 (amxon) vs 38.42 (amxoff) over 2 rep: +9.0 % for the AMX kernel; prefill time -2.8 %.
- glm-tp4-8u-p1024-fpga (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 72.1 % of the K tokens (2,766,816 visits). AVX 2.9 %. FPGA 24.9 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 7,028,736 in the software-only layers.
  - amxoff: AVX 75.1 %, FPGA 24.9 %, avx_full_page visits 2,795,832.
  - Busy per job goes from 0.038 ms (amxon) to 0.053 ms (amxoff), 137.2 % of amxon.
- glm-tp4-8u-p1024-fpga (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 57.4 % of the K tokens (3,913,728 visits). AVX 20.8 %. FPGA 21.9 %.
  - AVX K tokens split by layer kind: 13,737,802 in the card layers, 76,996,062 in the software-only layers.
  - amxoff: AVX 78.1 %, FPGA 21.9 %, avx_full_page visits 4,900,480.
  - Busy per job goes from 3.720 ms (amxon) to 3.780 ms (amxoff), 101.6 % of amxon.
  - Decode TPS per user 63.08 (amxon) vs 60.44 (amxoff) over 2 rep: +4.4 % for the AMX kernel; prefill time -0.6 %.
- glm-tp2-8u-p2048-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 69.5 % of the K tokens (4,814,472 visits). AVX 4.3 %. FPGA 26.1 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 19,029,504 in the software-only layers.
  - amxoff: AVX 73.9 %, FPGA 26.1 %, avx_full_page visits 4,816,968.
  - Busy per job goes from 0.100 ms (amxon) to 0.177 ms (amxoff), 176.4 % of amxon.
- glm-tp2-8u-p2048-fpga (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 66.3 % of the K tokens (18,091,008 visits). AVX 11.0 %. FPGA 22.6 %.
  - AVX K tokens split by layer kind: 28,966,730 in the card layers, 163,577,310 in the software-only layers.
  - amxoff: AVX 77.4 %, FPGA 22.6 %, avx_full_page visits 19,940,544.
  - Busy per job goes from 6.912 ms (amxon) to 10.350 ms (amxoff), 149.7 % of amxon.
  - Decode TPS per user 38.15 (amxon) vs 33.11 (amxoff) over 2 rep: +15.2 % for the AMX kernel; prefill time -8.7 %.
- glm-tp4-8u-p2048-fpga (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), decode_like, amxon: AMX 69.5 % of the K tokens (4,814,472 visits). AVX 4.3 %. FPGA 26.1 %.
  - AVX K tokens split by layer kind: 133,120 in the card layers, 19,029,504 in the software-only layers.
  - amxoff: AVX 73.9 %, FPGA 26.1 %, avx_full_page visits 4,816,968.
  - Busy per job goes from 0.052 ms (amxon) to 0.086 ms (amxoff), 164.1 % of amxon.
- glm-tp4-8u-p2048-fpga (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card on, 13 of 52 layers; amx_available yes), prompt_or_mixed, amxon: AMX 66.3 % of the K tokens (18,091,008 visits). AVX 11.0 %. FPGA 22.6 %.
  - AVX K tokens split by layer kind: 28,966,730 in the card layers, 163,577,310 in the software-only layers.
  - amxoff: AVX 77.4 %, FPGA 22.6 %, avx_full_page visits 19,940,544.
  - Busy per job goes from 4.401 ms (amxon) to 5.876 ms (amxoff), 133.5 % of amxon.
  - Decode TPS per user 59.74 (amxon) vs 54.21 (amxoff) over 2 rep: +10.2 % for the AMX kernel; prefill time -6.9 %.

### 8.2 Glimmer with CPU attention (all 52 layers in software)

- glm-tp2-8u-p1024-cpu (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), decode_like, amxon: AMX 96.5 % of the K tokens (3,701,152 visits). AVX 3.5 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 3,727,776.
  - Busy per job goes from 0.069 ms (amxon) to 0.131 ms (amxoff), 189.3 % of amxon.
- glm-tp2-8u-p1024-cpu (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 86.0 % of the K tokens (5,870,592 visits). AVX 14.0 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 6,391,424.
  - Busy per job goes from 5.173 ms (amxon) to 7.717 ms (amxoff), 149.2 % of amxon.
  - Decode TPS per user 42.14 (amxon) vs 37.15 (amxoff) over 2 rep: +13.4 % for the AMX kernel; prefill time -6.6 %.
- glm-tp4-8u-p1024-cpu (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), decode_like, amxon: AMX 96.5 % of the K tokens (3,701,152 visits). AVX 3.5 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 3,727,776.
  - Busy per job goes from 0.048 ms (amxon) to 0.069 ms (amxoff), 143.5 % of amxon.
- glm-tp4-8u-p1024-cpu (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 86.0 % of the K tokens (5,870,592 visits). AVX 14.0 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 6,391,424.
  - Busy per job goes from 4.329 ms (amxon) to 4.517 ms (amxoff), 104.4 % of amxon.
  - Decode TPS per user 62.54 (amxon) vs 58.96 (amxoff) over 2 rep: +6.1 % for the AMX kernel; prefill time -1.3 %.
- glm-tp2-8u-p2048-cpu (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), decode_like, amxon: AMX 94.6 % of the K tokens (6,548,360 visits). AVX 5.4 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 6,555,016.
  - Busy per job goes from 0.119 ms (amxon) to 0.228 ms (amxoff), 191.2 % of amxon.
- glm-tp2-8u-p2048-cpu (Glimmer-30B tp2, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 91.6 % of the K tokens (24,986,624 visits). AVX 8.4 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 26,047,424.
  - Busy per job goes from 7.291 ms (amxon) to 13.420 ms (amxoff), 184.1 % of amxon.
  - Decode TPS per user 37.78 (amxon) vs 31.17 (amxoff) over 2 rep: +21.2 % for the AMX kernel; prefill time -14.8 %.
- glm-tp4-8u-p2048-cpu (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), decode_like, amxon: AMX 94.6 % of the K tokens (6,548,360 visits). AVX 5.4 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 6,555,016.
  - Busy per job goes from 0.067 ms (amxon) to 0.111 ms (amxoff), 165.7 % of amxon.
- glm-tp4-8u-p2048-cpu (Glimmer-30B tp4, fitting shape: kv_mul 16, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 91.6 % of the K tokens (24,986,624 visits). AVX 8.4 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 26,047,424.
  - Busy per job goes from 5.078 ms (amxon) to 7.469 ms (amxoff), 147.1 % of amxon.
  - Decode TPS per user 58.71 (amxon) vs 51.63 (amxoff) over 2 rep: +13.7 % for the AMX kernel; prefill time -11.0 %.

### 8.3 llama-3.1-8b regression cell (kv_mul 4, the unchanged kernel path)

- l8b-tp2-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), decode_like, amxon: AMX 96.5 % of the K tokens (9,110,528 visits). AVX 3.5 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 9,176,064.
  - Busy per job goes from 0.090 ms (amxon) to 0.105 ms (amxoff), 116.6 % of amxon.
- l8b-tp2-8u-p1024-cpu (llama-3.1-8b tp2, fitting shape: kv_mul 4, head size 128; card off; amx_available yes), prompt_or_mixed, amxon: AMX 86.0 % of the K tokens (14,450,688 visits). AVX 14.0 %. FPGA 0.0 %.
  - amxoff: AVX 100.0 %, FPGA 0.0 %, avx_full_page visits 15,732,736.
  - Busy per job goes from 0.647 ms (amxon) to 1.117 ms (amxoff), 172.7 % of amxon.
  - Decode TPS per user 119.08 (amxon) vs 113.20 (amxoff) over 2 rep: +5.2 % for the AMX kernel; prefill time -6.3 %.

## 9. Failed or stopped runs

Runs with no complete attempt:

- none

## 10. Files

- results: exec/results/glimmer-20261016/ (rt-results.txt, rt/<run>.log, exit-reports.txt, results.json, tests.txt, preservation.txt, build.txt, leaves/<run>/ = in-flight FUSE leaf snapshots, not used by this report)
- scripts: exec/glimmer-20261016/ (build.sh, tests.sh, chain.sh, campaign.sh, gen_compare.py, launch.sh, README.md)
- binary: runtron.g16 built from branch jhan-amx-kvmul16 5061623a34 with --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON (see build.txt)
