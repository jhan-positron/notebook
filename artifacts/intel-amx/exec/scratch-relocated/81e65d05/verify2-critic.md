## Corrections (apply)

All numbers below were recomputed with python3 over `exec/results/attnstats-20261002/rt/*__rep1.log` (exit reports), `leaves/*/`, and `exec/logs/attnstats-20261002.log`. Line numbers refer to `attn-stats-compare.md` revision 2.

### N5 + N10 + N12 — Short version (lines 5 and 7)

Verdict: all three imprecise. Recount: the 19 non-timer totals fields, 8 non-timer forwards fields and all per-layer triples are identical between arms in the 3 AoF decode rows. The 6 cycle fields differ (gpt-oss busy_cycles -4.85 %, qwen +0.06 % / +0.41 %). First run 13:59:41Z, last run log ends 14:12:44Z, "repetition 1 done" 14:12:45Z. Flock wait 13:45:40 to 13:59:41 = 14.0 min, takeover wait 13:37:10 to 13:45:40 = 8.5 min, hand-back 14:12:45 to 14:15:02 = 2.3 min.

Original (line 5, third sentence):
> With attention on the FPGA, the AMX kernel scores 0 % of the decode K tokens of gpt-oss-120b and qwen3-4b, and disabling it changes no decode counter; decode TPS then differs by less than 1 % and TTFT by less than 2 % between the arms (one repetition per arm).

Replacement:
> With attention on the FPGA, the AMX kernel scores 0 % of the decode K tokens of gpt-oss-120b and qwen3-4b. Disabling it changes no decode work counter (visits, K tokens, token jobs, forwards, path sets and per-layer K tokens are identical between the arms in the 3 AoF cells). Only the cycle timers differ, by up to 4.8 % of decode busy cycles (gpt-oss). Decode TPS differs by less than 1 % and TTFT by less than 2 % between the arms (one repetition per arm).

Original (line 7):
> Measured 2026-10-02 13:59 to 14:13 UTC on our half of delphi-3bda (the campaign process ran 13:37 to 14:15 UTC; the rest was the wait for the production takeover and the hand-back), tron main dd0f942c75, ...

Replacement:
> Measured 2026-10-02 13:59 to 14:12 UTC (first run start 13:59:41, last run end 14:12:45, 13 min) on our half of delphi-3bda, tron main dd0f942c75, 6 cells x 2 arms = 12 runtron runs, all finished, 0 HBM warnings [exec/results/attnstats-20261002/rt-results.txt]. The campaign process ran 13:37 to 14:15 UTC. The rest was an 8 min wait for production to go idle before the takeover, a 14 min wait on another session's campaign lock, and a 2 min hand-back [exec/logs/attnstats-20261002.log].

### N15 + N17 — Words used here, line 12

Verdict: N15 imprecise (page.count() counts live entries, not "written"; under FPGA attention the visibility test is sw_required; the function ends at line 1721). N17 imprecise (true per key, false per page: the pending page is partly card-held in 239 of 255 qwen decode steps).

Original:
> A page is dense for one query when all 64 tokens are written, all are visible to that query through one range, and the whole page is inside the query's sliding window (is_dense_amx_page, h/tron/models/self_attention.hpp:1710-1720 at main). ... Pages the FPGA card holds are scored by the card, by neither CPU path.

Replacement:
> A page is dense for one query when all 64 entries of the page are live (page.count() == 64), the query sees all of them through one range (under FPGA attention: one range the CPU must score), and the page's first token is inside the query's sliding window, so the whole page is (is_dense_amx_page, h/tron/models/self_attention.hpp:1710-1721 at main). ... Keys the FPGA card holds (up to the last complete GOF) are scored by the card, by neither CPU path. The split is per key, not per page: the 1 to 4 newest keys of the same page go to the AVX loop (next bullet).

### N19 — line 13

Verdict: imprecise (shard undefined at first use; the full region is the K/V arena of the card's HBM).

Original:
> HBM = the card's high-bandwidth memory, where it keeps the K/V it scores; an HBM warning means a shard did not fit.

Replacement:
> HBM = the card's high-bandwidth memory, where it keeps the K/V it scores. A shard = one 1024-token range of K/V placed on one card. An HBM warning ('lose HW attention' or 'HBM bypass space exhausted' in the log) means one shard did not fit in the K/V region of that card's HBM, so its tokens are scored on the CPU.

### N21 + N22 — line 14

Verdict: imprecise. 2.49 = 1,465,344 / 587,520 holds for decode only. In the prompt_or_mixed class of the same runs the pending AVX tail is 43.0 keys per visit (152,174,592 / 3,538,944), because each prompt query scores its own chunk.

Original:
> The CPU scores the rest: the 1 to 4 newest keys past that GOF (inside the pending page; measured 2.49 keys per visit on qwen), queries below the engagement point ...

Replacement:
> The CPU scores the rest. In a decode step that is the 1 to 4 newest keys past that GOF, inside the pending page (measured 2.49 keys per visit in decode on qwen, both prompt lengths, both arms). In a prefill chunk it is each query's own chunk, 1 to 128 keys written in the same forward. In every case it also includes queries below the engagement point ...

### N28 — line 23

Verdict: imprecise (one join covers all of a worker's tokens of the batch; the card returns per-pass partials that the join folds).

Replacement:
> join = the last step of an attention job. Each worker combines the partial results of all workers for its share of the batch's tokens and KV heads and normalizes them. Under FPGA attention, in the layers the card serves, it also folds in the card's per-pass partial results and waits when those or the peer workers' partials are not ready.

### N34 — line 25

Verdict: imprecise. Recount: prompt forwards = prompt/128 in all 12 runs, listener_jobs per prompt forward = 8 = one chunk end per user per forward, token_jobs per prompt forward = 1,024 (qwen) / 1,023.1 (llama, gpt-oss).

Original:
> A prompt chunk = the 128 tokens of one user that one prompt forward processes.

Replacement:
> A prompt chunk = up to 128 consecutive prompt tokens of one user (the TRON_PER_USER_PROMPT_CHUNK_LIMIT default, not set in this campaign; the last chunk of a prompt holds the remainder, here 1 token for llama and gpt-oss). One prompt forward processes one chunk of each of the 8 users: 1,024 token jobs per prompt forward (1,017 in the first forward of llama and gpt-oss, where 7 BOS tokens come from the prefix cache).

### N35 — line 26

Verdict: imprecise (7 reused tokens is less than one page; section 8's hypothesis needs sub-page reuse).

Replacement:
> prefix cache = tron's reuse of K/V entries already computed for an identical leading token sequence (matched token by token, so part of a 64-token page can be reused). BOS = the beginning-of-sequence token some tokenizers add.

### N47 — line 50

Verdict: imprecise. Transcript (2026-10-02T02:40:37Z and 02:50:58Z): gpt-oss FPGA prompt 8192 was dropped as "not needed", not under the AoF rule. gpt-oss CPU prompt 8192 was "yes, drop #8".

Original:
> gpt-oss under CPU attention at both prompt lengths and gpt-oss under FPGA attention at prompt 8192 ("we always use AoF for gptoss"), llama with USE_HW_ATTN=1 at both prompt lengths ("llama is not AoF"), and qwen under CPU attention at prompt 8192 ("not needed").

Replacement:
> gpt-oss under CPU attention at prompt 1024 ("we always use AoF for gptoss, no need to test AoF off") and at prompt 8192 ("yes, drop #8", after the same rule was pointed out), gpt-oss under FPGA attention at prompt 8192 ("not needed"), llama with USE_HW_ATTN=1 at both prompt lengths ("essentially same as #1 because llama is not AoF"), and qwen under CPU attention at prompt 8192 ("not needed").

### N53 — line 76, last sentence

Verdict: imprecise. Busy per job amxoff vs amxon: gpt-oss decode -4.85 %, prefill -0.68 %; qwen p1024 decode +0.06 %, prefill -8.14 % (0 AMX visits in both arms); qwen p8192 decode +0.41 %, prefill +3.60 %. Prefill counters differ in gpt-oss (144 empty visits) and qwen p8192 (7,077,888 visits move from AMX to AVX).

Original:
> The work counters and the attention busy time are the same in both arms, so this report does not count them as effects (section 4 gives the bound).

Replacement:
> In decode the work counters are identical in both arms of every AoF cell. The attention busy time per job is not: it differs by -4.8 % (gpt-oss), +0.1 % and +0.4 % (qwen) although the kernel scored nothing in either arm. This report therefore treats the decode TPS and TTFT differences as single-repetition variation, not as kernel effects (section 4 gives the bound). In prefill the counters differ in two places: 144 more empty visits for gpt-oss in amxoff, and 7,077,888 whole-page visits that move from the kernel to the AVX loop for qwen at prompt 8192 (see below).

### N56 — line 81, end

Verdict: imprecise (qwen's measured mean is 2.49 over 255 positions, gpt-oss 2.50 over 256).

Replacement for "..., the same tail as measured for qwen on 2026-09-25.":
> ..., the same (p mod 4) + 1 tail per step as measured for qwen on 2026-09-25 (qwen's mean is 2.49 because it has 255 decode positions, 1024 to 1278, instead of 256).

### N60 + N61 — line 83

Verdict: N60 wrong (3,670,016 is the per-query count; the exit report's per-layer FPGA value is not multiplied by n_kv_heads; the leaf for layer 1 shows fpga_k_tokens_x_kv_heads 29,360,128). N61 imprecise (56 = 7 users x 8 KV heads x 1 pair).

Original:
> ... and the card scores the earlier chunks (3,670,016 per layer = 8 users x 128 x 128 x 28 chunk pairs). The 56 missing pairs are the 7 BOS tokens served from the prefix cache (see section 8).

Replacement:
> ... and the card scores the earlier chunks (3,670,016 per layer as the per-layer line counts them, once per query = 8 users x 128 queries x 128 keys x 28 earlier-chunk pairs; on the software scale that is 29,360,128 = 8 users x 8 KV heads x 128 x 128 x 28, against the 4,227,016 AVX K tokens of the same layer). The 56 missing pairs are 7 users x 8 KV heads x 1 pair: for users 2 to 8 the BOS token is served from the prefix cache and is never a prompt query, so its own query-key pair is not scored (see section 8).

### N63 — line 84, and N83 — line 92

Verdict: imprecise. Engagement point 127 is the first eligible position (hw_attn_config.hpp:18-19, strict `<` gates). Positions 0 to 126 = 1,009 jobs (gpt-oss) / 1,016 (qwen); the 8 jobs at position 127 are avx-only because no earlier page of that user is on the card yet.

Line 84 replacement for "In prefill, 1,017 jobs used avx only: the first 128-token chunk of each user (8 x 128 - 7 reused BOS tokens), whose queries sit below the engagement point.":
> In prefill, 1,017 jobs used avx only: the first 128-token chunk of each user (8 x 128 - 7 reused BOS tokens). Positions 0 to 126 sit below the engagement point (127), and position 127 has no earlier page of its user on the card yet, so all 128 queries of that chunk run on the CPU only.

Line 92 replacement for "The 1,024 jobs with path set avx only are the first chunk of each user, below the engagement point.":
> The 1,024 jobs with path set avx only are the first 128-token chunk of each user (8 x 128): positions 0 to 126 sit below the engagement point (127), and position 127 has no earlier page on the card to score.

### N71 — line 85, last sentence

Verdict: imprecise (the 13 per layer for amxoff is derived, not measured: 16,362 / 18 - 896, assuming the same even spread; amxon's 901 per even layer is measured in 36 leaf files summing to 16,218).

Replacement:
> The remaining 5 per layer (amxon, measured in the per-layer snapshot) and est. 13 per layer (amxoff: 16,362 / 18 = 909 minus 896, assuming the same spread over the 18 sliding-window layers, because the amxoff prompt per-layer leaves are 0-byte files) differ between the runs by 144 = 8 x 18 in total. Their cause is not measured.

### N78 + N81 — line 91

Verdict: N78 imprecise (cell 4 amxoff has AVX 1,209,139,200 in prefill). N81 wrong for decode: control AMX 658,243,584 vs card 675,357,696; the 17,114,112 difference (2.5 % of decode K tokens) is AVX work in the control (18,579,456) that the card takes under FPGA attention (AVX 1,465,344).

Replacement for the whole bullet:
> The card replaces the kernel's part, and in decode a little more. The qwen CPU control (cell 4, amxon arm) and the qwen AoF cell (cell 3, both arms) have the same prefill totals: AVX 152,174,592 K tokens in each, and the card's 1,056,964,608 K tokens (software scale) equal the control's AMX K tokens [section 3]. (In the control's amxoff arm the kernel's part moves to the AVX loop: AVX 1,209,139,200.) In decode the totals also agree (676,823,040 in both cells), but the card scores more than the kernel did: 675,357,696 against the control's AMX 658,243,584. The extra 17,114,112 K tokens (2.5 % of the decode K tokens) are the partial pending page down to the last complete GOF. The control's AVX loop scored them (18,579,456 K tokens, 32 keys per visit), and under FPGA attention only the 1 to 4 key tail stays on the CPU (1,465,344). So in prefill the card scores exactly the kernel's pages and nothing else moves. In decode the AVX-to-card move is a second change.

### N87 + N90 — line 93

Verdict: N87 imprecise (per-user split and "each 8 pages" are means; counters hold no per-user or per-job breakdown). N90 imprecise (the code reads the boundary from DMA state at plan time, full.hpp:2850/2882, shard.hpp:355-365, so the data rules out timing noise, not timing as the mechanism; and 2026-09-25 had two runs of the cell with the same count).

Replacement for "3,072 token jobs (384 per user = 3 prompt chunks of 128 tokens) each scored 8 whole pages (512 tokens) on the CPU that the card had not yet taken.":
> 3,072 token jobs used the kernel (24 chunk-units of 128 prompt tokens). Averaged over them that is 384 per user (3 chunks, if the lag hit every user equally) and 8 whole pages (512 tokens) per job, layer and KV head above the prefix the card had copied. The counters record totals only, so the per-user split and the per-job page count are means.

Replacement for "The count is identical in both arms and in the 2026-09-25 run of the same cell (the 'state 6' row of counter.html Table 2, prefill copy lag), so the cause is a fixed rule of the copy boundary rather than copy timing; which rule is open.":
> The count is identical in both arms, in both 2026-09-25 runs of the same cell (binary cbf1bb6c0c; the 'state 6' row of counter.html Table 2, prefill copy lag) and in every one of the 36 layers. So the lag is deterministic, not timing noise that varies between runs. The code sets the card boundary from the GOFs landed at the moment the plan is built [h/tron/scheduler/full.hpp:2850, 2882; h/tron/shard.hpp:355-365], so the cause is a fixed ordering between the copy submission and that poll. Which ordering is open.

### N96 — line 98

Verdict: imprecise (the file is h/tron/plugins/llama.hpp, not in models/; the mechanism is the absent `force_hw_attn` member; the llama cells here set USE_HW_ATTN=0 explicitly).

Replacement:
> llama runs CPU attention when USE_HW_ATTN is unset: its hand-written plugin h/tron/plugins/llama.hpp does not define the `force_hw_attn` member that the generated plugins set to true [h/tron/models/model.hpp:742-748; ingest/src/TronCpp.hs:243]. (The llama cells here set USE_HW_ATTN=0 explicitly.) This is the situation where the kernel does the most work.

### N106 — line 102, last sentence

Verdict: imprecise (qwen's decode class has 6,912 pending-pass AMX visits, 442,368 K tokens, already in the section 3 table).

Replacement:
> In prefill, qwen's CPU cell shows the clean case: 0 ready-pass AVX visits and 0 pending-pass AMX visits. (Its decode class keeps 0 ready-pass AVX visits but has 6,912 pending-pass AMX visits = 24 token jobs x 36 layers x 8 KV heads, the full pending pages of section 2.3.)

### N109 + N110 + N113 + N114 + N115 + N116 — line 104

Verdict: N109 imprecise (attn_jobs 377,664 = 64 x (13 x 24 + 243 x 23): the amxon run had 23 attention workers in 243 of 256 decode forwards; the per-worker leaf shows pool worker 3 with 832 = 13 x 64 jobs). N110 imprecise (24 is the class maximum). N113 imprecise (2.9 ms = T1 - T3, not T1 - busy). N114 imprecise (the timers measure part of it: T3 +0.68 ms vs T4 +0.24 ms; llama runs 2.0 attention jobs per worker per layer per forward, qwen 1.0). N115 imprecise (+1.293 ms). N116 imprecise (95 %, not whole).

Replacement for the whole bullet:
> Why the prompt 1024 decode TPS moves only 3 %: the attention workers are busy 5.8 ms of the 8.7 ms decode forward in amxon (busy 34.34 s / 5,901 worker-forwards = 67 %). The amxon run used 23 attention workers in 243 of the 256 decode forwards and 24 in the other 13, read from attn_jobs = 64 jobs per worker per forward; dividing by the maximum of 24 would give 5.6 ms (65 %). Worker 0's attention wall T3 is 5.7 ms. The kill switch (24 workers in 255 of 256 forwards) raises busy time to 6.59 ms per worker per forward, +0.77 ms, but adds only 0.26 ms to the forward (+3 %). About two thirds of the extra attention time is therefore absorbed by the time the workers spend outside attention jobs: 2.85 ms per forward on the busy basis (8.66 - 5.82), or 2.95 ms as worker 0's time outside its attention wall (8.66 - 5.72). Worker 0's timers show where it goes: under the kill switch its attention wall per forward grows 0.68 ms but its layer periods (T4) grow only 0.24 ms, close to the 0.26 ms of T1. Hypothesis for the mechanism (code-supported, not measured directly): llama runs two attention jobs per worker per layer per forward (377,664 / 5,901 / 32 = 2.0), consistent with the two-minibatch split its plugin allows (max_minibatches = -1, h/tron/plugins/llama.hpp:183; chunk_evenly splits a lone chunk in two "to enable FPGA-vs-CPU latency hiding", h/tron/models/model.hpp:246-250), and tron's own comment says a single minibatch cannot hide attention behind main work [model.hpp:2082-2090]. qwen's generated plugin runs one minibatch (max_minibatches = 1, ingest/src/TronCpp.hs:273; 1.0 jobs per worker per layer) and passes the extra time through almost 1:1: T1 +1.45 ms per decode forward for +1.29 ms busy per worker per forward (ratio 1.12). At prompt 8192 the attention time grows 6.6x (busy per worker per forward 5.8 -> 36.7 ms) while the rest of the forward stays near 3 ms, and 6.4 of the 6.7 ms the kill switch adds per worker (95 %) reaches the forward (T1 39.6 -> 46.1 ms) and the time per token (TPS -13.8 %).

### N136 — line 117

Verdict: imprecise. The 2026-09-25 prompt-64 FPGA run (exec/results/attnstats-20260925-fpga/rt/q3-4b-tp2-8u-p64__fpga__headon2__rep1.log, HW attention enabled) has 149,760 decode AMX visits, 9,584,640 of 112,803,840 decode K tokens = 8.5 % through the kernel.

Replacement:
> Under FPGA attention, in the cells measured here (prompt 1024 and 8192, cold prefix cache), no model puts decode keys through the kernel, fitting or not. A fitting model with a short prompt does (qwen3-4b at prompt 64: 8.5 % of its decode K tokens, measured 2026-09-25).

### N139 — line 170, last sentence

Verdict: wrong. The qwen p1024 FPGA prefill row has 0 AMX visits in both arms and busy per job 1.493 -> 1.371 ms (-8.1 %). The qwen p8192 FPGA prefill row is not a neither-arm row (7,077,888 AMX visits in amxon). T1 / TPS / TTFT maxima: 1.64 % / 0.87 % / 1.62 %.

Replacement:
> The rows where the kernel ran in neither arm (gpt-oss, and qwen under FPGA attention except the prompt-8192 prefill row) bound that variation at up to 1.6 % of T1 and TTFT, under 1 % of TPS, up to 5 % of busy per job in decode (gpt-oss, 0.0322 vs 0.0307 ms) and up to 8 % of busy per job in prefill (qwen prompt 1024, 1.493 vs 1.371 ms). Only differences above that are attributed to the kernel.

### N149 — line 296

Verdict: wrong as written. attn_jobs counts one job per attention worker per operation [attn_stats.hpp:503-511]. attn_jobs differs only in the three llama rows whose n_attn_workers_min/max differ (23/24, 14/20, 14/26); p8192 decode (26/26) is equal in both arms. Prefill leaves (complete snapshots, sums 30,848 and 33,408): pool workers 13-26 hold 2,080 jobs each in both arms, the whole 2,560 surplus sits on the optional workers 8-12.

Replacement for "The cause of the extra jobs is not measured.":
> The extra jobs come from the per-forward attention-worker split, not from more attention work: attn_jobs counts one job per attention worker per operation [h/tron/models/attn_stats.hpp:503-511], and the kill-switch runs ran more attention workers per forward. In decode at prompt 1024 the amxoff run used 24 workers in 255 of 256 forwards and the amxon run in 13 (377,664 = 64 x (13 x 24 + 243 x 23); 393,152 = 64 x (255 x 24 + 23)). In prefill the 14 always-attention workers record identical job counts in both arms and the whole difference sits on the optional workers 8 to 12 [leaves/l8b-8u-p1024-cpu__cpu__amx*__rep1/prompt_or_mixed_worker_*]. At prompt 8192 decode both arms used 26 workers in every forward and the counts are equal. The split follows recommend_n_main_helpers(), which balances predicted main and attention thread time [h/tron/models/model.hpp:2068-2103]; the estimator inputs behind each decision are not recorded.

### N152 + N153 — line 298

Verdict: N152 wrong (T4/T1 spans 83.1 % to 96.4 %; 8 of 24 rows fall outside 88-95 %, all prefill rows). N153 imprecise (T1 +6.41 ms, T4 +6.19 ms; llama p1024 prefill T4 +22.0 vs T1 +19.4 ms).

Replacement:
> T4 (worker 0's layer-to-layer periods) is 88 to 95 % of T1 in the 12 decode rows, 93 to 96 % in the CPU-attention prefill rows and 83 to 89 % in the FPGA-attention prefill rows (lowest gpt-oss prefill, 278.6 of 335.1 ms). In the CPU-attention cells the kill switch moves T4 by nearly the same amount as T1: within 0.2 ms in decode (llama prompt 8192: T1 +6.4 ms, T4 +6.2 ms), and within 3 % of the move in prefill except llama prompt 1024 (T4 +22.0 ms against T1 +19.4 ms).

### N155 — line 302

Verdict: imprecise (the exit report has per-layer K tokens only, no per-layer visits).

Replacement for "AMX+AVX visits and K tokens (per class and per layer)":
> AMX+AVX visits (per class), AMX+AVX K tokens (per class and per layer)

### N166 — line 304

Verdict: wrong on "Insufficient data". The existing counters fix the per-visit key counts. Decode prompt 1024: 524,288 ready AVX visits = 65,536 full pages (64 keys) + 458,752 visits with 458,752 K tokens = exactly 1 key each. Prompt 8192: 65,536 full + 917,504 non-full visits at 32.0 keys each (14 per step, head and layer = 2 per branch user summing 64). The off-grid layout predicts ready AMX visits 9,102,336 = 256 x (4,224 + 7 x 4,476) exactly at prompt 1024; at prompt 8192 ready AMX 67,371,008 = 2,048 x 32,896 equals eight on-grid users.

Replacement for "Hypothesis (not verified): the 7 reused BOS tokens put llama's branch pages off the 64-token page grid. Insufficient data; a per-visit key-count histogram would resolve it.":
> The counters already give the per-visit key counts. In decode at prompt 1024, 7 of every 8 ready AVX visits score exactly 1 key (458,752 visits, 458,752 K tokens) and 1 of 8 scores a full page (65,536 visits x 64 keys). Reading (consistent with every counter, not confirmed per user): users 2 to 8 score the shared BOS page, which holds 1 visible key for them, and user 1 scores its own first page, which holds the BOS, is full, but fails the dense-page test because the BOS is its own token range (self_attention.hpp:1718). The branch pages of users 2 to 8 start at position 1, off the 64-token grid, but are dense and go to the kernel: that layout predicts the ready AMX visits exactly (9,102,336 = 256 x (4,224 + 7 x 4,476)). At prompt 8192 one more non-full visit per (step, KV head, layer) appears for each of users 2 to 8 (983,040 visits, 14 non-full at 32 keys mean = 1 + 63), and the ready AMX count 67,371,008 = 2,048 x 32,896 equals eight on-grid users, so the branch pages return to the grid somewhere in the prompt. Where and why is open; a per-user breakdown would confirm the attribution.

### N168 + N169 — line 305

Verdict: N168 imprecise (four runs have empty leaves: gpt-oss amxoff 146 of 187 files, llama p8192 amxon 89 of 123, qwen p8192 FPGA amxoff 103 of 131, and qwen p8192 FPGA amxon 28 of 131 = its 27 prompt worker leaves + summary; the other 8 runs have 0). N169 imprecise (section 2.1 line 85 takes the per-layer split of the 16,218 empty visits from the amxon snapshot; the exit report has no per-layer empty-visit count; section 7 takes four figures from two snapshots).

Replacement for the second and following sentences:
> In four runs the copy overlapped the run's exit, so every file after one point in the copy order is empty: gpt-oss amxoff (146 of 187 files, all prompt layer and worker leaves, 52 of 55 decode worker leaves), llama prompt 8192 amxon (89 of 123, all worker leaves and all prompt layer leaves), qwen prompt 8192 FPGA amxoff (103 of 131, all worker leaves, all prompt layer leaves, decode layers 27 to 35) and qwen prompt 8192 FPGA amxon (28 of 131: the 27 prompt worker leaves and the summary). The other 8 snapshots have no empty files. Every attention counter and timer in the tables of sections 3 to 7 comes from the exit reports. TPS, TTFT, the HBM counts, the 'HW attention' line and the 'context' and 'reused tokens' figures come from the other runtron log lines. Two hand-written passages use the amxon snapshots: the per-layer split of the gpt-oss prefill empty visits in section 2.1 (901 per sliding-window layer, 0 per card layer, from a snapshot copied after the prompt forwards had finished, so its sum equals the exit-report total) and the four per-layer join-wait figures in section 7 (18.2 % and 13.7 % join share, 3.8 us and 24.4 us per job).

### N172 — section 9, lines 311-329 (new defect in revision 2)

Verdict: the sentence about hand-written vs generated parts is almost right, but the delivered file is broken here. `assemble.py` does `prose.replace('GEN_TABLE_1', ...)` on the whole text, so the literal "GEN_TABLE_1" inside section 9's own sentence ("the hand-written prose with GEN_TABLE_1..6 placeholders") was also replaced. Section 9 now holds a second copy of the geometry/TPS table and the six HW-attention bullets, and the "logs:" and "binary:" bullets are cut off from the list. This leak is not in `.prev` (its section 9 has no `final_prose.md` mention; `grep -c GEN_TABLE_1 attn-stats-compare.md.prev` = 0). Two smaller omissions: section 7's four T1/busy/join/T4 definition bullets (lines 260-263) are generated, and the lead-in "Geometry, attention mode and throughput per cell (...)" is a literal in assemble.py.

Fix (two steps):
1. In `exec/attnstats-20261002/assemble.py` replace only whole-line placeholders (e.g. `re.sub(r'^GEN_TABLE_%d$' % n, repl, prose, flags=re.M)`), or reword the section 9 bullet so the literal token does not appear in prose, then re-run assemble.py.
2. Section 9 scripts bullet text:
> - scripts: exec/attnstats-20261002/ (chain.sh, campaign.sh, gen_compare.py, assemble.py, launch.sh, README.md, final_prose.md = the hand-written prose with six table placeholders). This file is final_prose.md with gen_compare.py's output inserted at the placeholders by assemble.py. Hand-written: Short version, most of Words used here (6 of the 25 entries are the generator's wording), the text and cells table of section 1, sections 2, 8 and 9, the closing paragraph of section 4 and the reading notes of section 7. Generated: the tables, the lead-in sentence and HW-attention bullets of section 1, the intro sentences of sections 3 to 7, the four timer-definition bullets of section 7 and the per-layer bullets of section 6.

## Plain-English fixes (apply)

New in revision 2 only (checked against `.prev` with grep):

| Rule | Line | Original phrase | Fix |
|---|---|---|---|
| 8 (semicolon) | 5 | "changes no decode counter; decode TPS then differs" | Split into two sentences (done in the N5 replacement). |
| 8 | 7 | "(... 13:37 to 14:15 UTC; the rest was ...)" | Split (done in the N10/N12 replacement). |
| 1, 8 | 13 | "HBM = ...; an HBM warning means a shard did not fit" | "shard" undefined at first use. Split and define (done in the N19 replacement). |
| 8 | 16 | "Same binary; every page the CPU scores goes to the AVX loop." | "Same binary. Every page the CPU scores goes to the AVX loop." |
| 1 | 39 | "the chain log's count of 86 uses a mnemonic list without tilezero" | "uses a list of instruction names (mnemonics) that omits tilezero". |
| 1 | 50 | "gpt-oss's ingested plugin" | "gpt-oss's generated (ingested) plugin", since line 18 calls them "generated plugins". |
| 8 | 50 | "...defaults to CPU attention; USE_HW_ATTN=0 or =1 overrides either" | Split at the semicolon. |
| 2, 7 | 85 | One bullet with six separate claims (cross-arm difference, timer fields, empty-visit definition, per-layer location, off-by-one model, remainder) | Split into sub-bullets, one claim each. |
| 8 | 93 | "...rather than copy timing; which rule is open" | Split (done in the N90 replacement). |
| 2 | 102 | "...because a page written in this forward has one visible range per token and usually fails the dense-page test (...)" | Split: "A page written in this forward has one visible range per token. It usually fails the dense-page test (...)." |
| 6 | 104 | "on the critical path", "passes the extra time through", "the whole saving shows in TPS" | "critical path" needs one clause: "(the chain of work that sets the forward time)". The other two are replaced in the N109-N116 text ("reaches the forward", "appears in the forward and in the time per token"). |
| 8 | 113 | "...also give the kernel work under FPGA attention; they were measured on 2026-09-25, not here." | "... under FPGA attention. They were measured on 2026-09-25, not here." |
| 8 | 170 | "...up to 5 % of busy per job; only differences above that..." | Split (done in the N139 replacement). |
| 3 | 294 | "3.8 us per job against qwen's 24.4 us" | Write "3.8 microseconds (us)" at first use. |
| 2 | 296 | "Summed over all workers the rise is ... because the llama kill-switch runs recorded 4 to 11 % more attention jobs ..." | Split: "Summed over all workers the rise is 18 to 19 % in decode and 1.9x to 2.8x in prefill. The llama kill-switch runs recorded 4 to 11 % more attention jobs for the same forwards (...)." |
| 6 | 76 | "these differences cannot be resolved" | "these differences are inside the single-repetition variation (section 4)". |

Not new (present in `.prev`, left alone): "in-flight samples" (line 305), "by construction" (line 302), "one visible range per token" (line 102).

## False alarms

- N20 (card scores up to the last complete GOF): holds. Both verifiers' closed-form recomputation reproduces every FPGA and AVX decode total to four decimals (qwen p1024: 1149.5059 keys per query on the card, 2.4941 on the CPU; gpt-oss: 1150.000 / 2.500). The code uses the leading run of complete GOFs (shard.hpp:355-365); the data show no gap, so "last complete GOF" and "end of the leading complete run" coincide in every measured run. Optional parenthesis only: "(the end of the unbroken run of complete GOFs; GOFs can land out of order)".
- N68 (empty visits in sliding-window layers, card progress does not set the count): holds for what the sentence states. It is scoped to "the amxon run", the 36 amxon leaf files give 901 per even layer and 0 per odd layer summing to 16,218 (the exit total), and in a sliding-window layer the visit test uses `visible()`, not the card-coverage mask (self_attention.hpp:505-514, 1504-1505, 1517, 1869, 1920). The per-layer K-token lines are identical in both arms, so the card covered the same keys in both runs. The sentence's own next sentence already says the amxoff per-layer leaves are empty.
- N145 (join wait 1 to 4 % of busy in CPU decode): holds at integer precision. Recomputed shares: 3.30 / 4.19 % (llama p1024), 2.04 / 2.26 % (qwen), 1.81 / 0.89 % (llama p8192). The table prints 0.9 % and 4.2 %. Optional: write "0.9 to 4.2 %" to match the table.
- N175 (serving back at 14:12, idle at 14:15): holds. POST /api/inference/up at 14:12:46Z [log line 101], "idle 2" line at 14:15:02Z [line 102]. The helper prints that line after a fixed 10 s settle, so the first idle poll was about 14:14:50 (est.); at the minute precision the sentence uses, 14:15 is the logged time. No change needed.
- N47's third quote "not needed" for the qwen CPU prompt 8192 cell: correct (transcript "#9 is not needed."). Only the gpt-oss attribution was wrong (fixed above).
- N110 as a standalone claim: 24 is correct as `n_attn_workers_max` of the decode class in both arms. The defect is only in using it as the divisor for a run that mostly ran 23 workers (fixed in the N109 replacement).
- N172, verifier 2's statement that the GEN_TABLE_1 leak "is present in attn-stats-compare.md.prev": not true. The `.prev` section 9 scripts bullet reads "(chain.sh, campaign.sh, gen_compare.py, launch.sh, README.md); this file is gen_compare.py's tables plus the prose of sections 2, 4, 7 and 8" and contains no table. The leak is new in revision 2 and must be fixed as stated above.