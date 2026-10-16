# pr4trace-20261015: cost of convert_k_blocks (PR #4901), measured 2026-10-15 20:28 to 20:30 UTC on delphi-3bda (our half)

Short version. The forward-end conversion of PR #4901 (convert_pending_k_blocks, span `convert_k_blocks`) runs once
every 16 decode steps on the forward thread, inside the pass, and converts 288 blocks (8 users x 36 layers) each time.
One run takes 1.08 to 1.16 ms at tp2 and 1.17 to 1.20 ms at tp4 (3.7 to 4.2 us per block). That is 9 to 13 % of the
pass it runs in and 0.6 to 0.8 % of decode time averaged over the 16 steps.

Words used here: tron = the inference program under test; runtron = its command-line tool; pass = one scheduler
forward() call (span "forward"; 1024 token jobs = a prefill pass of one user's prompt, 8 = one decode step of 8 users);
block = 16 consecutive tokens of a KV page; Perfetto = the trace recorder built into tron.

Setup: runtron.pr4 (commit ea94e95a4e, TRON_K_VNNI=ON, TRON_AMX_DISPATCH=ON, sha256 e6e87e7cba981077...), CPU attention
(USE_HW_ATTN=0), qwen3-4b tp2 and tp4, 8 users, prompt 1024, -l 64 (61 generated per the log), --trace-gen with
--trace-passes 1-72 and TRON_TRACE_CATEGORIES="-*,+model,+scheduler". Script exec/pr4trace-20261015/trace.sh, reader
exec/pr4trace-20261015/analyze.py (output analyze.out). The run shared the machine with the i4934-abl-cpu campaign
(serialized by the campaign flock; it waited 27 min for the lock). Load at start 74 (tp2) and 37 (tp4): the other
campaign's run had just ended; the decode pass means (12.04 ms tp2, 9.25 ms tp4) match the untraced logs
(12.129 and 9.353 ms/tok).

Per trace: 71 forward passes (8 prefill, 63 decode), 3 convert_k_blocks spans (decode steps 16, 32, 48 = passes 24, 40,
56; the 4th would be step 64, past the 61 generated). Every span is a child of the "forward" span on the same thread
(utid 2, "96/?-work_queue") and ends about 0.4 ms before the pass ends.

| cell | pass | blocks | span us | us/block | % of that decode pass | mean decode pass ms |
|---|---|---|---|---|---|---|
| tp2 | 24 | 288 | 1159.7 | 4.03 | 9.63 | 12.042 |
| tp2 | 40 | 288 | 1112.0 | 3.86 | 9.23 | |
| tp2 | 56 | 288 | 1076.1 | 3.74 | 8.94 | |
| tp4 | 24 | 288 | 1191.5 | 4.14 | 12.87 | 9.254 |
| tp4 | 40 | 288 | 1196.2 | 4.15 | 12.93 | |
| tp4 | 56 | 288 | 1169.9 | 4.06 | 12.64 | |

Amortized over 16 decode steps: tp2 1116 us / 16 = 70 us per step = 0.58 % of a 12.04 ms step; tp4 1186 / 16 = 74 us
= 0.80 % of a 9.25 ms step.

Posted: PR #4901 body v14 (exec/pr4-20261012/pr-body-v14.md), Performance paragraph "Conversion cost", 2026-10-15 20:31 UTC.
