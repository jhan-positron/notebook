# G1 store-cost campaign, 2026-09-08: summary

Summarize the G1 store-cost campaign (exec/results/g1-20260908) into summary.md and summary.json.

Words: TTFT = time to first token (ms, mean over the harness's 10 rounds x N users); TPS = decode tokens per
second per user; arm = which binary/switch served the run (off / canon / canon2 / mirror / g1mirror / sonly /
inplace, see g1-campaign.sh). Deltas are relative to the canonical arm at the same user count. The paired
column matches ROUNDS: round k uses the same set of prompts in every arm (systems_test testlib/tps.py seeds by
k*users+i and prunes each prompt to exactly prompt_length tokens); inside a round the harness appends the
per-request samples in completion order, so single positions are not the same prompt and the per-round mean
is what is paired. "prefill tok/s" is 1024 divided by the same TTFT, not a second measurement; the runtron
section's "Parsing the prompt took" values are the independent prefill numbers. Round-1 (2026-09-04) values
at 8 users are printed for reference, including its one A/A pair (off vs off rep2, +0.2% TTFT).
Interpretation: inplace vs canon = the end-to-end single-K proxy against canonical (the G1 kill comparison):
the inplace arm stores K once, in VNNI layout, inside the page's own hugepage K plane, and the AMX kernel
qk_mirror_128x4 reads that plane; the canon arm stores K contiguously and qk_canonical_128x4 reads it. This is
the comparison the gate needs, because production single-K would also use the mirror reader; but the delta
mixes the store cost with the reader difference (2026-09-01 single-attention measurement: mirror 2.66 us vs
canonical 2.89 us per attention unit at prompt 8192, so the mirror reader is about 8% faster per unit), and an
inplace result inside the spread can hide a store cost of that size. Every arm except off / canon / canon2
reads K through qk_mirror_128x4 (rinzler.mirror and rinzler.g1 are K-mirror builds). sonly vs inplace = arena
placement with the same store pattern and the same reader; mirror vs sonly = the extra canonical store plus
re-read (upper bound); g1mirror vs mirror = probe-binary fidelity (same code path, different build);
canon2 vs canon = ONE in-campaign A/A difference of means, an indication of the spread, not a spread estimate.
Probe arms have wrong numerics; their TPS column is timing only.

## ingested-qwen-3-4b-instruct-2507-tp4

| users | arm | TTFT ms | dTTFT vs canon | paired rounds vs canon | TPS | dTPS vs canon | sd | prefill tok/s (= 1024 / TTFT) | status | mode line |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | canon | 324 | +0.0% |  | 189.31 | +0.0% | 1.32 | 3160 | done |  |
| 1 | inplace | 350 | +8.0% | +26 ms median over 10 rounds, 10/10 rounds slower | 189.91 | +0.3% | 1.22 | 2926 | done | tore mode: inplace (2) |
| 1 | sonly | 378 | +16.7% | +54 ms median over 10 rounds, 10/10 rounds slower | 190.30 | +0.5% | 1.50 | 2709 | done |  store mode: sonly (1) |
| 1 | mirror | 381 | +17.6% | +58 ms median over 10 rounds, 10/10 rounds slower | 189.65 | +0.2% | 2.71 | 2688 | done |  |
| 2 | canon | 517 | +0.0% |  | 159.26 | +0.0% | 1.41 | 1981 | done |  |
| 2 | inplace | 561 | +8.5% | +46 ms median over 10 rounds, 10/10 rounds slower | 157.84 | -0.9% | 2.25 | 1825 | done | tore mode: inplace (2) |
| 2 | sonly | 612 | +18.4% | +95 ms median over 10 rounds, 10/10 rounds slower | 159.90 | +0.4% | 2.24 | 1673 | done |  store mode: sonly (1) |
| 2 | mirror | 612 | +18.4% | +96 ms median over 10 rounds, 10/10 rounds slower | 163.23 | +2.5% | 1.73 | 1673 | done |  |
| 4 | canon | 875 | +0.0% |  | 121.80 | +0.0% | 1.46 | 1170 | done |  |
| 4 | inplace | 980 | +12.0% | +106 ms median over 10 rounds, 10/10 rounds slower | 126.77 | +4.1% | 1.62 | 1045 | done | tore mode: inplace (2) |
| 4 | sonly | 1072 | +22.5% | +198 ms median over 10 rounds, 10/10 rounds slower | 127.12 | +4.4% | 0.82 | 955 | done |  store mode: sonly (1) |
| 4 | mirror | 1080 | +23.4% | +202 ms median over 10 rounds, 10/10 rounds slower | 121.02 | -0.6% | 2.07 | 948 | done |  |
| 8 | canon | 1630 | +0.0% |  | 78.50 | +0.0% | 1.20 | 628 | done |  |
| 8 | canon2 | 1633 | +0.2% | +7 ms median over 10 rounds, 6/10 rounds slower | 80.73 | +2.8% | 0.86 | 627 | done |  |
| 8 | inplace | 1820 | +11.7% | +189 ms median over 10 rounds, 10/10 rounds slower | 77.82 | -0.9% | 1.79 | 563 | done | tore mode: inplace (2) |
| 8 | sonly | 2010 | +23.3% | +370 ms median over 10 rounds, 10/10 rounds slower | 80.46 | +2.5% | 0.70 | 509 | done |  store mode: sonly (1) |
| 8 | mirror | 2022 | +24.0% | +386 ms median over 10 rounds, 10/10 rounds slower | 80.85 | +3.0% | 1.01 | 506 | done |  |
| 8 | g1mirror | 2034 | +24.8% | +404 ms median over 10 rounds, 10/10 rounds slower | 80.06 | +2.0% | 1.36 | 503 | done |  store mode: unset (0) |
| 8 | off | 1778 | +9.1% | +145 ms median over 10 rounds, 10/10 rounds slower | 77.84 | -0.8% | 0.71 | 576 | done |  |

Round 1 reference at 8 users (2026-09-04, same binaries, same placement): off 1777 ms, canon 1618 ms, mirror 2009 ms (mirror vs canon +24.2%). Round-1 A/A (off vs off rep2): +0.2%.

## llama-3.1-8b-instruct-good-tp2

| users | arm | TTFT ms | dTTFT vs canon | paired rounds vs canon | TPS | dTPS vs canon | sd | prefill tok/s (= 1024 / TTFT) | status | mode line |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | canon | 455 | +0.0% |  | 191.55 | +0.0% | 0.54 | 2251 | done |  |
| 1 | inplace | | | | | | | | failed | |
| 1 | sonly | | | | | | | | failed | |
| 1 | mirror | 503 | +10.5% | +48 ms median over 10 rounds, 10/10 rounds slower | 192.90 | +0.7% | 0.89 | 2036 | done |  |
| 2 | canon | 792 | +0.0% |  | 144.00 | +0.0% | 0.12 | 1293 | done |  |
| 2 | inplace | | | | | | | | failed | |
| 2 | sonly | | | | | | | | failed | |
| 2 | mirror | 904 | +14.1% | +105 ms median over 10 rounds, 10/10 rounds slower | 143.58 | -0.3% | 0.11 | 1133 | done |  |
| 4 | canon | 1421 | +0.0% |  | 129.81 | +0.0% | 0.16 | 721 | done |  |
| 4 | inplace | | | | | | | | failed | |
| 4 | sonly | | | | | | | | failed | |
| 4 | mirror | 1648 | +16.0% | +219 ms median over 10 rounds, 10/10 rounds slower | 129.35 | -0.4% | 0.26 | 621 | done |  |
| 8 | canon | 2685 | +0.0% |  | 86.64 | +0.0% | 0.78 | 381 | done |  |
| 8 | canon2 | 2690 | +0.2% | +0 ms median over 10 rounds, 5/10 rounds slower | 85.72 | -1.1% | 0.75 | 381 | done |  |
| 8 | inplace | | | | | | | | failed | |
| 8 | sonly | | | | | | | | failed | |
| 8 | mirror | 3160 | +17.7% | +468 ms median over 10 rounds, 10/10 rounds slower | 90.38 | +4.3% | 0.64 | 324 | done |  |
| 8 | off | 2784 | +3.7% | +101 ms median over 10 rounds, 10/10 rounds slower | 75.00 | -13.4% | 0.25 | 368 | done |  |

Round 1 reference at 8 users (2026-09-04, same binaries, same placement): off 2784 ms, canon 2683 ms, mirror 3148 ms (mirror vs canon +17.3%).

## runtron: qwen-3-4b tp2, 8 users, prompt 8192, 256 generated (August placement)

| arm | completed runs / attempts | prefill s per request (mean) | decode tok/s lines (mean) |
|---|---|---|---|
| g1canon | 2 / 2 | 62.34 (16 requests) | 16.922 (16 lines) |
| g1kill | 2 / 3 | 128.86 (16 requests) | 14.224 (16 lines) |
| g1mirror | 2 / 2 | 63.31 (16 requests) | 18.585 (16 lines) |
| sonly | 2 / 2 | 63.27 (16 requests) | 18.614 (16 lines) |
| inplace | 2 / 3 | 63.01 (16 requests) | 18.669 (16 lines) |

```
# G1 runtron point: qwen-3-4b tp2, 8 users, prompt 8192, 256 generated, --dont-stop, USE_HW_ATTN=0, August placement (cards 10/13, socket 0), 2026-09-08T12:43:26Z
# arms (all head 60d66d9c04): g1canon = runtron.g1canon (TRON_AMX_K_MIRROR=OFF, canonical AMX); g1kill = runtron.g1 with TRON_AMX_DISABLE=1 (AVX baseline, arena build); g1mirror = runtron.g1 (mirror arm); sonly / inplace = runtron.g1 with TRON_DD_G1
c8126c08e05bb0bf106b09957c10682ca1b31e90a723d10e44c0946814321a06  /var/tmp/jhan/tron-g1canon/gen/runtron.g1canon
1c5c5dd71c92a33bb5ac32a088f7cab99f673659f5a36458022a2b5d08b953eb  /var/tmp/jhan/tron-g1/gen/runtron.g1
### arm=g1canon rep=1 bin=/var/tmp/jhan/tron-g1canon/gen/runtron.g1canon env=none 2026-09-08T12:43:30Z
[12:43:30.919051473|thread 3246093|cpu 283] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:43:30.919087436|thread 3246093|cpu 283] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1canon/gen/../config/resource-map.yaml).
[12:43:30.919155810|thread 3246093|cpu 283] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:44:58.244102807|thread 3268570|cpu 283] [info ] [Request 1] Parsing the prompt took 62.382072768 s at 131.31977884842314 tokens/s
[12:44:58.244102673|thread 3268574|cpu 283] [info ] [Request 5] Parsing the prompt took 62.381834078 s at 131.3202813139001 tokens/s
[12:44:58.244102785|thread 3268572|cpu 283] [info ] [Request 3] Parsing the prompt took 62.381858718 s at 131.32022944414504 tokens/s
[12:44:58.244104452|thread 3268577|cpu 283] [info ] [Request 8] Parsing the prompt took 62.381802325 s at 131.32034815731816 tokens/s
[12:44:58.244102908|thread 3268571|cpu 283] [info ] [Request 2] Parsing the prompt took 62.381868869 s at 131.32020807524935 tokens/s
[12:44:58.244104806|thread 3268573|cpu 283] [info ] [Request 4] Parsing the prompt took 62.38184935 s at 131.32024916475163 tokens/s
[12:44:58.244102678|thread 3268575|cpu 283] [info ] [Request 6] Parsing the prompt took 62.381822861 s at 131.3203049268618 tokens/s
[12:44:58.244102719|thread 3268576|cpu 283] [info ] [Request 7] Parsing the prompt took 62.381812244 s at 131.32032727676844 tokens/s
[12:45:13.274889494|thread 3268571|cpu 283] [info ] [Request 2] Generating 253 response tokens with 8193 context took 14.969204 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.274889616|thread 3268570|cpu 283] [info ] [Request 1] Generating 253 response tokens with 8193 context took 14.969209 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.274889576|thread 3268572|cpu 283] [info ] [Request 3] Generating 253 response tokens with 8193 context took 14.969203 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.274891223|thread 3268574|cpu 283] [info ] [Request 5] Generating 253 response tokens with 8193 context took 14.969203 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.274980425|thread 3268574|cpu 283] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381834 s TTFT and 77.412621 s TTLT
[12:45:13.274891959|thread 3268575|cpu 283] [info ] [Request 6] Generating 253 response tokens with 8193 context took 14.969201 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.274894301|thread 3268576|cpu 283] [info ] [Request 7] Generating 253 response tokens with 8193 context took 14.969201 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.275011456|thread 3268576|cpu 283] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381812 s TTFT and 77.412602 s TTLT
[12:45:13.274898250|thread 3268577|cpu 283] [info ] [Request 8] Generating 253 response tokens with 8193 context took 14.969205 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.275030465|thread 3268577|cpu 283] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381802 s TTFT and 77.412593 s TTLT
[12:45:13.274942950|thread 3268571|cpu 283] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381869 s TTFT and 77.412651 s TTLT
[12:45:13.274958022|thread 3268570|cpu 283] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 62.382073 s TTFT and 77.412855 s TTLT
[12:45:13.274968630|thread 3268572|cpu 283] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381859 s TTFT and 77.412640 s TTLT
[12:45:13.274889597|thread 3268573|cpu 283] [info ] [Request 4] Generating 253 response tokens with 8193 context took 14.969201 s at 16.901 average tok/s, or 59.167 ms/tok
[12:45:13.275083450|thread 3268573|cpu 283] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381849 s TTFT and 77.412631 s TTLT
[12:45:13.274997920|thread 3268575|cpu 283] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 62.381823 s TTFT and 77.412611 s TTLT
[12:45:13.339705183|thread 3246093|cpu 283] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=g1kill rep=1 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_AMX_DISABLE=1 2026-09-08T12:45:14Z
[12:45:15.345206761|thread 3321041|cpu 203] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:45:15.345262673|thread 3321041|cpu 203] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[12:45:15.345370635|thread 3321041|cpu 203] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:47:49.916435516|thread 3336158|cpu 203] [info ] [Request 8] Parsing the prompt took 128.405121016 s at 63.79807857491315 tokens/s
[12:47:49.916435547|thread 3336153|cpu 203] [info ] [Request 3] Parsing the prompt took 128.405181347 s at 63.798048599472615 tokens/s
[12:47:49.916435431|thread 3336157|cpu 203] [info ] [Request 7] Parsing the prompt took 128.405137819 s at 63.79807022634445 tokens/s
[12:47:49.916435491|thread 3336155|cpu 203] [info ] [Request 5] Parsing the prompt took 128.405157594 s at 63.79806040114068 tokens/s
[12:47:49.916435505|thread 3336151|cpu 203] [info ] [Request 1] Parsing the prompt took 128.405446844 s at 63.797916687696855 tokens/s
[12:47:49.916437645|thread 3336152|cpu 203] [info ] [Request 2] Parsing the prompt took 128.405201193 s at 63.79803873899919 tokens/s
[12:47:49.916435428|thread 3336154|cpu 203] [info ] [Request 4] Parsing the prompt took 128.405168603 s at 63.798054931323115 tokens/s
[12:47:49.916435450|thread 3336156|cpu 203] [info ] [Request 6] Parsing the prompt took 128.405146817 s at 63.79806575569004 tokens/s
[12:48:07.766908246|thread 3336154|cpu 203] [info ] [Request 4] Generating 253 response tokens with 8193 context took 17.779075 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.766909052|thread 3336156|cpu 203] [info ] [Request 6] Generating 253 response tokens with 8193 context took 17.779077 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.766908290|thread 3336153|cpu 203] [info ] [Request 3] Generating 253 response tokens with 8193 context took 17.779077 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.766981507|thread 3336153|cpu 203] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405181 s TTFT and 146.255654 s TTLT
[12:48:07.766908356|thread 3336152|cpu 203] [info ] [Request 2] Generating 253 response tokens with 8193 context took 17.779077 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.767006372|thread 3336152|cpu 203] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405201 s TTFT and 146.255663 s TTLT
[12:48:07.766908279|thread 3336151|cpu 203] [info ] [Request 1] Generating 253 response tokens with 8193 context took 17.779076 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.767018486|thread 3336151|cpu 203] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405447 s TTFT and 146.255914 s TTLT
[12:48:07.766908384|thread 3336155|cpu 203] [info ] [Request 5] Generating 253 response tokens with 8193 context took 17.779076 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.767042986|thread 3336155|cpu 203] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405158 s TTFT and 146.255633 s TTLT
[12:48:07.766913302|thread 3336158|cpu 203] [info ] [Request 8] Generating 253 response tokens with 8193 context took 17.779076 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.767062074|thread 3336158|cpu 203] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405121 s TTFT and 146.255603 s TTLT
[12:48:07.766970306|thread 3336156|cpu 203] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405147 s TTFT and 146.255624 s TTLT
[12:48:07.766910732|thread 3336157|cpu 203] [info ] [Request 7] Generating 253 response tokens with 8193 context took 17.779076 s at 14.230 average tok/s, or 70.273 ms/tok
[12:48:07.767099396|thread 3336157|cpu 203] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405138 s TTFT and 146.255613 s TTLT
[12:48:07.766953248|thread 3336154|cpu 203] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 128.405169 s TTFT and 146.255643 s TTLT
[12:48:07.843111958|thread 3321041|cpu 203] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=g1mirror rep=1 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=none 2026-09-08T12:48:09Z
[12:48:09.822031877|thread 3434812|cpu 201] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:48:09.822079937|thread 3434812|cpu 201] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[12:48:09.822153937|thread 3434812|cpu 201] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
DD G1 store mode: unset (0)
[12:49:39.249978588|thread 3448686|cpu 201] [info ] [Request 5] Parsing the prompt took 63.258960478 s at 129.49944068159306 tokens/s
[12:49:39.249978711|thread 3448683|cpu 201] [info ] [Request 2] Parsing the prompt took 63.258996373 s at 129.4993671998325 tokens/s
[12:49:39.249978732|thread 3448682|cpu 201] [info ] [Request 1] Parsing the prompt took 63.259240481 s at 129.4988674810359 tokens/s
[12:49:39.249978725|thread 3448687|cpu 201] [info ] [Request 6] Parsing the prompt took 63.258948704 s at 129.4994647845294 tokens/s
[12:49:39.249978725|thread 3448689|cpu 201] [info ] [Request 8] Parsing the prompt took 63.258924335 s at 129.49951467112626 tokens/s
[12:49:39.249978684|thread 3448685|cpu 201] [info ] [Request 4] Parsing the prompt took 63.258970871 s at 129.4994194057539 tokens/s
[12:49:39.249978737|thread 3448688|cpu 201] [info ] [Request 7] Parsing the prompt took 63.258937227 s at 129.49948827947608 tokens/s
[12:49:39.249978706|thread 3448684|cpu 201] [info ] [Request 3] Parsing the prompt took 63.258985257 s at 129.49938995572973 tokens/s
[12:49:52.916310198|thread 3448685|cpu 201] [info ] [Request 4] Generating 253 response tokens with 8193 context took 13.611034 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916349984|thread 3448685|cpu 201] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258971 s TTFT and 76.925302 s TTLT
[12:49:52.916310102|thread 3448684|cpu 201] [info ] [Request 3] Generating 253 response tokens with 8193 context took 13.611031 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916374130|thread 3448684|cpu 201] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258985 s TTFT and 76.925313 s TTLT
[12:49:52.916310854|thread 3448687|cpu 201] [info ] [Request 6] Generating 253 response tokens with 8193 context took 13.611034 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916390296|thread 3448687|cpu 201] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258949 s TTFT and 76.925284 s TTLT
[12:49:52.916310232|thread 3448686|cpu 201] [info ] [Request 5] Generating 253 response tokens with 8193 context took 13.611035 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916403228|thread 3448686|cpu 201] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258960 s TTFT and 76.925294 s TTLT
[12:49:52.916310246|thread 3448682|cpu 201] [info ] [Request 1] Generating 253 response tokens with 8193 context took 13.611034 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916424221|thread 3448682|cpu 201] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 63.259240 s TTFT and 76.925569 s TTLT
[12:49:52.916312968|thread 3448688|cpu 201] [info ] [Request 7] Generating 253 response tokens with 8193 context took 13.611034 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916440519|thread 3448688|cpu 201] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258937 s TTFT and 76.925274 s TTLT
[12:49:52.916317352|thread 3448689|cpu 201] [info ] [Request 8] Generating 253 response tokens with 8193 context took 13.611035 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916460887|thread 3448689|cpu 201] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258924 s TTFT and 76.925265 s TTLT
[12:49:52.916310230|thread 3448683|cpu 201] [info ] [Request 2] Generating 253 response tokens with 8193 context took 13.611033 s at 18.588 average tok/s, or 53.799 ms/tok
[12:49:52.916483967|thread 3448683|cpu 201] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 63.258996 s TTFT and 76.925322 s TTLT
[12:49:53.175409037|thread 3434812|cpu 201] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=sonly rep=1 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_DD_G1=sonly 2026-09-08T12:49:54Z
[12:49:55.253209158|thread 3504853|cpu 204] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:49:55.253260618|thread 3504853|cpu 204] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[12:49:55.253366694|thread 3504853|cpu 204] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
DD G1 store mode: sonly (1)
[12:51:24.780068980|thread 3516125|cpu 204] [info ] [Request 4] Parsing the prompt took 63.382438971 s at 129.2471563574284 tokens/s
[12:51:24.780068855|thread 3516123|cpu 204] [info ] [Request 2] Parsing the prompt took 63.382459273 s at 129.24711495834418 tokens/s
[12:51:24.780068994|thread 3516127|cpu 204] [info ] [Request 6] Parsing the prompt took 63.382412356 s at 129.24721062978784 tokens/s
[12:51:24.780069002|thread 3516122|cpu 204] [info ] [Request 1] Parsing the prompt took 63.382995424 s at 129.24602166874075 tokens/s
[12:51:24.780068955|thread 3516128|cpu 204] [info ] [Request 7] Parsing the prompt took 63.382399254 s at 129.24723734693603 tokens/s
[12:51:24.780068972|thread 3516126|cpu 204] [info ] [Request 5] Parsing the prompt took 63.382424385 s at 129.2471861006741 tokens/s
[12:51:24.780068982|thread 3516124|cpu 204] [info ] [Request 3] Parsing the prompt took 63.382447249 s at 129.24713947723512 tokens/s
[12:51:24.780074876|thread 3516129|cpu 204] [info ] [Request 8] Parsing the prompt took 63.382396739 s at 129.2472424754389 tokens/s
[12:51:38.428069611|thread 3516129|cpu 204] [info ] [Request 8] Generating 253 response tokens with 8193 context took 13.592545 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428068949|thread 3516127|cpu 204] [info ] [Request 6] Generating 253 response tokens with 8193 context took 13.592548 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428068814|thread 3516125|cpu 204] [info ] [Request 4] Generating 253 response tokens with 8193 context took 13.592548 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428136986|thread 3516125|cpu 204] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382439 s TTFT and 77.030434 s TTLT
[12:51:38.428068740|thread 3516124|cpu 204] [info ] [Request 3] Generating 253 response tokens with 8193 context took 13.592548 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428068896|thread 3516128|cpu 204] [info ] [Request 7] Generating 253 response tokens with 8193 context took 13.592547 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428069012|thread 3516123|cpu 204] [info ] [Request 2] Generating 253 response tokens with 8193 context took 13.592551 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428068764|thread 3516126|cpu 204] [info ] [Request 5] Generating 253 response tokens with 8193 context took 13.592548 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428191523|thread 3516126|cpu 204] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382424 s TTFT and 77.030423 s TTLT
[12:51:38.428105435|thread 3516129|cpu 204] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382397 s TTFT and 77.030391 s TTLT
[12:51:38.428123732|thread 3516127|cpu 204] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382412 s TTFT and 77.030412 s TTLT
[12:51:38.428068806|thread 3516122|cpu 204] [info ] [Request 1] Generating 253 response tokens with 8193 context took 13.592551 s at 18.613 average tok/s, or 53.725 ms/tok
[12:51:38.428241288|thread 3516122|cpu 204] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382995 s TTFT and 77.030992 s TTLT
[12:51:38.428152595|thread 3516124|cpu 204] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382447 s TTFT and 77.030444 s TTLT
[12:51:38.428165408|thread 3516128|cpu 204] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382399 s TTFT and 77.030401 s TTLT
[12:51:38.428179316|thread 3516123|cpu 204] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 63.382459 s TTFT and 77.030455 s TTLT
[12:51:38.682047405|thread 3504853|cpu 204] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=inplace rep=1 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_DD_G1=inplace 2026-09-08T12:51:40Z
[12:51:40.753799210|thread 3572547|cpu 166] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:51:40.753851662|thread 3572547|cpu 166] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[12:51:40.753958061|thread 3572547|cpu 166] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
DD G1 store mode: inplace (2)
[12:53:08.770146896|thread 3592632|cpu 166] [info ] [Request 4] Parsing the prompt took 63.005307866 s at 130.02079154065535 tokens/s
[12:53:08.770146881|thread 3592636|cpu 166] [info ] [Request 7] Parsing the prompt took 63.005276025 s at 130.0208572493116 tokens/s
[12:53:08.770146948|thread 3592629|cpu 166] [info ] [Request 1] Parsing the prompt took 63.005581699 s at 130.02022644812786 tokens/s
[12:53:08.770146938|thread 3592635|cpu 166] [info ] [Request 6] Parsing the prompt took 63.005286148 s at 130.0208363589829 tokens/s
[12:53:08.770146866|thread 3592637|cpu 166] [info ] [Request 8] Parsing the prompt took 63.00526067 s at 130.0208889366698 tokens/s
[12:53:08.770146904|thread 3592631|cpu 166] [info ] [Request 3] Parsing the prompt took 63.005321438 s at 130.02076353282774 tokens/s
[12:53:08.770146750|thread 3592630|cpu 166] [info ] [Request 2] Parsing the prompt took 63.005333499 s at 130.02073864318203 tokens/s
[12:53:08.770146890|thread 3592633|cpu 166] [info ] [Request 5] Parsing the prompt took 63.005296883 s at 130.02081420570775 tokens/s
[12:53:22.380694590|thread 3592629|cpu 166] [info ] [Request 1] Generating 253 response tokens with 8193 context took 13.555449 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380735799|thread 3592629|cpu 166] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005582 s TTFT and 76.616124 s TTLT
[12:53:22.380694499|thread 3592630|cpu 166] [info ] [Request 2] Generating 253 response tokens with 8193 context took 13.555449 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380694639|thread 3592631|cpu 166] [info ] [Request 3] Generating 253 response tokens with 8193 context took 13.555446 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380694609|thread 3592632|cpu 166] [info ] [Request 4] Generating 253 response tokens with 8193 context took 13.555447 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380789474|thread 3592632|cpu 166] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005308 s TTFT and 76.615855 s TTLT
[12:53:22.380696362|thread 3592636|cpu 166] [info ] [Request 7] Generating 253 response tokens with 8193 context took 13.555448 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380805878|thread 3592636|cpu 166] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005276 s TTFT and 76.615825 s TTLT
[12:53:22.380701187|thread 3592637|cpu 166] [info ] [Request 8] Generating 253 response tokens with 8193 context took 13.555450 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380831727|thread 3592637|cpu 166] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005261 s TTFT and 76.615815 s TTLT
[12:53:22.380764491|thread 3592630|cpu 166] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005333 s TTFT and 76.615880 s TTLT
[12:53:22.380776161|thread 3592631|cpu 166] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005321 s TTFT and 76.615866 s TTLT
[12:53:22.380694624|thread 3592635|cpu 166] [info ] [Request 6] Generating 253 response tokens with 8193 context took 13.555446 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380880411|thread 3592635|cpu 166] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005286 s TTFT and 76.615834 s TTLT
[12:53:22.380695716|thread 3592633|cpu 166] [info ] [Request 5] Generating 253 response tokens with 8193 context took 13.555449 s at 18.664 average tok/s, or 53.579 ms/tok
[12:53:22.380899777|thread 3592633|cpu 166] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 63.005297 s TTFT and 76.615847 s TTLT
[12:53:22.440226812|thread 3572547|cpu 166] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=g1canon rep=2 bin=/var/tmp/jhan/tron-g1canon/gen/runtron.g1canon env=none 2026-09-08T12:53:23Z
[12:53:24.432604550|thread 3639847|cpu 224] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:53:24.432634805|thread 3639847|cpu 224] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1canon/gen/../config/resource-map.yaml).
[12:53:24.432703314|thread 3639847|cpu 224] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:54:51.697310339|thread 3662308|cpu 224] [info ] [Request 7] Parsing the prompt took 62.295963083 s at 131.50129791051455 tokens/s
[12:54:51.697310478|thread 3662302|cpu 224] [info ] [Request 1] Parsing the prompt took 62.296224101 s at 131.50074692678683 tokens/s
[12:54:51.697310335|thread 3662307|cpu 224] [info ] [Request 6] Parsing the prompt took 62.295974521 s at 131.5012737659072 tokens/s
[12:54:51.697310626|thread 3662303|cpu 224] [info ] [Request 2] Parsing the prompt took 62.296025441 s at 131.50116627839395 tokens/s
[12:54:51.697310207|thread 3662305|cpu 224] [info ] [Request 4] Parsing the prompt took 62.29599828 s at 131.50122361278582 tokens/s
[12:54:51.697313511|thread 3662304|cpu 224] [info ] [Request 3] Parsing the prompt took 62.296015686 s at 131.5011868703028 tokens/s
[12:54:51.697310374|thread 3662306|cpu 224] [info ] [Request 5] Parsing the prompt took 62.29598584 s at 131.50124987250703 tokens/s
[12:54:51.697325148|thread 3662309|cpu 224] [info ] [Request 8] Parsing the prompt took 62.295966257 s at 131.5012912104801 tokens/s
[12:55:06.691218733|thread 3662304|cpu 224] [info ] [Request 3] Generating 253 response tokens with 8193 context took 14.933132 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691218639|thread 3662303|cpu 224] [info ] [Request 2] Generating 253 response tokens with 8193 context took 14.933130 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691279373|thread 3662303|cpu 224] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 62.296025 s TTFT and 77.289928 s TTLT
[12:55:06.691218755|thread 3662302|cpu 224] [info ] [Request 1] Generating 253 response tokens with 8193 context took 14.933134 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691219408|thread 3662306|cpu 224] [info ] [Request 5] Generating 253 response tokens with 8193 context took 14.933130 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691222261|thread 3662307|cpu 224] [info ] [Request 6] Generating 253 response tokens with 8193 context took 14.933132 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691326489|thread 3662307|cpu 224] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 62.295975 s TTFT and 77.289886 s TTLT
[12:55:06.691223080|thread 3662308|cpu 224] [info ] [Request 7] Generating 253 response tokens with 8193 context took 14.933132 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691341295|thread 3662308|cpu 224] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 62.295963 s TTFT and 77.289877 s TTLT
[12:55:06.691225450|thread 3662309|cpu 224] [info ] [Request 8] Generating 253 response tokens with 8193 context took 14.933131 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691359622|thread 3662309|cpu 224] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 62.295966 s TTFT and 77.289864 s TTLT
[12:55:06.691259671|thread 3662304|cpu 224] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 62.296016 s TTFT and 77.289918 s TTLT
[12:55:06.691299454|thread 3662302|cpu 224] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 62.296224 s TTFT and 77.290130 s TTLT
[12:55:06.691313342|thread 3662306|cpu 224] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 62.295986 s TTFT and 77.289895 s TTLT
[12:55:06.691223604|thread 3662305|cpu 224] [info ] [Request 4] Generating 253 response tokens with 8193 context took 14.933138 s at 16.942 average tok/s, or 59.024 ms/tok
[12:55:06.691415226|thread 3662305|cpu 224] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 62.295998 s TTFT and 77.289911 s TTLT
[12:55:06.756014386|thread 3639847|cpu 224] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=g1kill rep=2 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_AMX_DISABLE=1 2026-09-08T12:55:08Z
RUN-STOPPED rc=143 2026-09-08T12:56:58Z WATCH-STOP monitor: 2026-09-08T12:56:51Z Bill work process: 3771199 python3; (full output: /home/jhan/workspace/intel-AMX/exec/results/g1-20260908/runtron-g1kill-rep2-t0.log)
### arm=g1kill rep=2 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_AMX_DISABLE=1 2026-09-08T12:58:59Z
[12:59:00.414276902|thread 3864755|cpu 185] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[12:59:00.414313546|thread 3864755|cpu 185] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[12:59:00.414396518|thread 3864755|cpu 185] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[13:01:35.870818167|thread 3876037|cpu 185] [info ] [Request 1] Parsing the prompt took 129.316044227 s at 63.34867455131748 tokens/s
[13:01:35.870818018|thread 3876038|cpu 185] [info ] [Request 2] Parsing the prompt took 129.31580435 s at 63.348792061238875 tokens/s
[13:01:35.870818093|thread 3876043|cpu 185] [info ] [Request 7] Parsing the prompt took 129.315745987 s at 63.34882065192226 tokens/s
[13:01:35.870818101|thread 3876042|cpu 185] [info ] [Request 6] Parsing the prompt took 129.315757546 s at 63.34881498943356 tokens/s
[13:01:35.870818277|thread 3876039|cpu 185] [info ] [Request 3] Parsing the prompt took 129.315792452 s at 63.348797889791705 tokens/s
[13:01:35.870818218|thread 3876044|cpu 185] [info ] [Request 8] Parsing the prompt took 129.315732512 s at 63.348827253016665 tokens/s
[13:01:35.870821165|thread 3876040|cpu 185] [info ] [Request 4] Parsing the prompt took 129.315787342 s at 63.348800393061914 tokens/s
[13:01:35.870818259|thread 3876041|cpu 185] [info ] [Request 5] Parsing the prompt took 129.315772027 s at 63.348807895525546 tokens/s
[13:01:53.737426196|thread 3876038|cpu 185] [info ] [Request 2] Generating 253 response tokens with 8193 context took 17.794936 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737426250|thread 3876037|cpu 185] [info ] [Request 1] Generating 253 response tokens with 8193 context took 17.794936 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737426261|thread 3876042|cpu 185] [info ] [Request 6] Generating 253 response tokens with 8193 context took 17.794934 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737426095|thread 3876040|cpu 185] [info ] [Request 4] Generating 253 response tokens with 8193 context took 17.794931 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737519978|thread 3876040|cpu 185] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315787 s TTFT and 147.182385 s TTLT
[13:01:53.737426269|thread 3876043|cpu 185] [info ] [Request 7] Generating 253 response tokens with 8193 context took 17.794933 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737536485|thread 3876043|cpu 185] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315746 s TTFT and 147.182354 s TTLT
[13:01:53.737432089|thread 3876044|cpu 185] [info ] [Request 8] Generating 253 response tokens with 8193 context took 17.794933 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737564328|thread 3876044|cpu 185] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315733 s TTFT and 147.182344 s TTLT
[13:01:53.737480098|thread 3876038|cpu 185] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315804 s TTFT and 147.182407 s TTLT
[13:01:53.737494179|thread 3876037|cpu 185] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 129.316044 s TTFT and 147.182646 s TTLT
[13:01:53.737507601|thread 3876042|cpu 185] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315758 s TTFT and 147.182364 s TTLT
[13:01:53.737426265|thread 3876041|cpu 185] [info ] [Request 5] Generating 253 response tokens with 8193 context took 17.794933 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737616081|thread 3876041|cpu 185] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315772 s TTFT and 147.182375 s TTLT
[13:01:53.737426278|thread 3876039|cpu 185] [info ] [Request 3] Generating 253 response tokens with 8193 context took 17.794935 s at 14.218 average tok/s, or 70.336 ms/tok
[13:01:53.737633307|thread 3876039|cpu 185] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 129.315792 s TTFT and 147.182395 s TTLT
[13:01:53.813843017|thread 3864755|cpu 185] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=g1mirror rep=2 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=none 2026-09-08T13:01:55Z
[13:01:55.807847623|thread 3975304|cpu 193] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[13:01:55.807905684|thread 3975304|cpu 193] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[13:01:55.808038390|thread 3975304|cpu 193] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
DD G1 store mode: unset (0)
[13:03:25.342931618|thread 3988479|cpu 193] [info ] [Request 7] Parsing the prompt took 63.358859415 s at 129.2952568218198 tokens/s
[13:03:25.342931626|thread 3988476|cpu 193] [info ] [Request 4] Parsing the prompt took 63.358906364 s at 129.29516101393168 tokens/s
[13:03:25.342931495|thread 3988475|cpu 193] [info ] [Request 3] Parsing the prompt took 63.358918514 s at 129.29513621969207 tokens/s
[13:03:25.342931599|thread 3988473|cpu 193] [info ] [Request 1] Parsing the prompt took 63.359186782 s at 129.29458877346738 tokens/s
[13:03:25.342931639|thread 3988478|cpu 193] [info ] [Request 6] Parsing the prompt took 63.35887028 s at 129.29523464981833 tokens/s
[13:03:25.342931689|thread 3988474|cpu 193] [info ] [Request 2] Parsing the prompt took 63.358930403 s at 129.29511195807868 tokens/s
[13:03:25.342931575|thread 3988477|cpu 193] [info ] [Request 5] Parsing the prompt took 63.358882143 s at 129.29521044122566 tokens/s
[13:03:25.342936513|thread 3988480|cpu 193] [info ] [Request 8] Parsing the prompt took 63.358854539 s at 129.2952667721839 tokens/s
[13:03:39.014079212|thread 3988473|cpu 193] [info ] [Request 1] Generating 253 response tokens with 8193 context took 13.614998 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014079341|thread 3988478|cpu 193] [info ] [Request 6] Generating 253 response tokens with 8193 context took 13.614996 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014138212|thread 3988478|cpu 193] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358870 s TTFT and 77.030019 s TTLT
[13:03:39.014079351|thread 3988476|cpu 193] [info ] [Request 4] Generating 253 response tokens with 8193 context took 13.614998 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014157925|thread 3988476|cpu 193] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358906 s TTFT and 77.030054 s TTLT
[13:03:39.014079335|thread 3988475|cpu 193] [info ] [Request 3] Generating 253 response tokens with 8193 context took 13.614999 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014175446|thread 3988475|cpu 193] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358919 s TTFT and 77.030065 s TTLT
[13:03:39.014081037|thread 3988479|cpu 193] [info ] [Request 7] Generating 253 response tokens with 8193 context took 13.614998 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014187764|thread 3988479|cpu 193] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358859 s TTFT and 77.030012 s TTLT
[13:03:39.014079314|thread 3988474|cpu 193] [info ] [Request 2] Generating 253 response tokens with 8193 context took 13.614998 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014203639|thread 3988474|cpu 193] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358930 s TTFT and 77.030074 s TTLT
[13:03:39.014085112|thread 3988480|cpu 193] [info ] [Request 8] Generating 253 response tokens with 8193 context took 13.614990 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014227613|thread 3988480|cpu 193] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358855 s TTFT and 77.030001 s TTLT
[13:03:39.014120214|thread 3988473|cpu 193] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 63.359187 s TTFT and 77.030327 s TTLT
[13:03:39.014080186|thread 3988477|cpu 193] [info ] [Request 5] Generating 253 response tokens with 8193 context took 13.615001 s at 18.582 average tok/s, or 53.814 ms/tok
[13:03:39.014261089|thread 3988477|cpu 193] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 63.358882 s TTFT and 77.030034 s TTLT
[13:03:39.262911510|thread 3975304|cpu 193] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=sonly rep=2 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_DD_G1=sonly 2026-09-08T13:03:40Z
[13:03:41.371545929|thread 4044751|cpu 187] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[13:03:41.371587246|thread 4044751|cpu 187] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[13:03:41.371717331|thread 4044751|cpu 187] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
DD G1 store mode: sonly (1)
[13:05:10.692070151|thread 4056045|cpu 187] [info ] [Request 8] Parsing the prompt took 63.164118541 s at 129.69388616865683 tokens/s
[13:05:10.692070147|thread 4056041|cpu 187] [info ] [Request 4] Parsing the prompt took 63.164164921 s at 129.69379093740588 tokens/s
[13:05:10.692070121|thread 4056043|cpu 187] [info ] [Request 6] Parsing the prompt took 63.164142473 s at 129.69383702947815 tokens/s
[13:05:10.692070142|thread 4056039|cpu 187] [info ] [Request 2] Parsing the prompt took 63.164194924 s at 129.69372933283995 tokens/s
[13:05:10.692070004|thread 4056044|cpu 187] [info ] [Request 7] Parsing the prompt took 63.164132075 s at 129.69385837951452 tokens/s
[13:05:10.692070108|thread 4056038|cpu 187] [info ] [Request 1] Parsing the prompt took 63.164451797 s at 129.69320190298998 tokens/s
[13:05:10.692070134|thread 4056042|cpu 187] [info ] [Request 5] Parsing the prompt took 63.164153688 s at 129.69381400191745 tokens/s
[13:05:10.692070132|thread 4056040|cpu 187] [info ] [Request 3] Parsing the prompt took 63.164177535 s at 129.69376503732227 tokens/s
[13:05:24.339024136|thread 4056043|cpu 187] [info ] [Request 6] Generating 253 response tokens with 8193 context took 13.591264 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339024098|thread 4056041|cpu 187] [info ] [Request 4] Generating 253 response tokens with 8193 context took 13.591266 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339024120|thread 4056038|cpu 187] [info ] [Request 1] Generating 253 response tokens with 8193 context took 13.591266 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339099005|thread 4056038|cpu 187] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164452 s TTFT and 76.811401 s TTLT
[13:05:24.339025034|thread 4056044|cpu 187] [info ] [Request 7] Generating 253 response tokens with 8193 context took 13.591265 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339115144|thread 4056044|cpu 187] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164132 s TTFT and 76.811089 s TTLT
[13:05:24.339024146|thread 4056042|cpu 187] [info ] [Request 5] Generating 253 response tokens with 8193 context took 13.591264 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339133816|thread 4056042|cpu 187] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164154 s TTFT and 76.811108 s TTLT
[13:05:24.339028567|thread 4056045|cpu 187] [info ] [Request 8] Generating 253 response tokens with 8193 context took 13.591262 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339154790|thread 4056045|cpu 187] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164119 s TTFT and 76.811078 s TTLT
[13:05:24.339067713|thread 4056043|cpu 187] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164142 s TTFT and 76.811098 s TTLT
[13:05:24.339088822|thread 4056041|cpu 187] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164165 s TTFT and 76.811118 s TTLT
[13:05:24.339024715|thread 4056040|cpu 187] [info ] [Request 3] Generating 253 response tokens with 8193 context took 13.591266 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339206614|thread 4056040|cpu 187] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164178 s TTFT and 76.811130 s TTLT
[13:05:24.339024010|thread 4056039|cpu 187] [info ] [Request 2] Generating 253 response tokens with 8193 context took 13.591266 s at 18.615 average tok/s, or 53.720 ms/tok
[13:05:24.339227383|thread 4056039|cpu 187] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 63.164195 s TTFT and 76.811142 s TTLT
[13:05:24.593164679|thread 4044751|cpu 187] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
### arm=inplace rep=2 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_DD_G1=inplace 2026-09-08T13:05:25Z
RUN-STOPPED rc=143 2026-09-08T13:06:56Z WATCH-STOP monitor: 2026-09-08T13:06:55Z Bill work process: 4161612 python3; (full output: /home/jhan/workspace/intel-AMX/exec/results/g1-20260908/runtron-inplace-rep2-t0.log)
### arm=inplace rep=2 bin=/var/tmp/jhan/tron-g1/gen/runtron.g1 env=TRON_DD_G1=inplace 2026-09-08T13:08:57Z
[13:08:58.300026846|thread 55587|cpu 200] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
[13:08:58.300060783|thread 55587|cpu 200] [info ] Configured instance 0,4 using resource map (/var/tmp/jhan/tron-g1/gen/../config/resource-map.yaml).
[13:08:58.300147537|thread 55587|cpu 200] [info ] App CPU list: 151-152,24-29,48-53,153-154,30-35,54-59
DD G1 store mode: inplace (2)
[13:10:27.460442523|thread 66849|cpu 200] [info ] [Request 1] Parsing the prompt took 63.009492838 s at 130.0121558042368 tokens/s
[13:10:27.460442493|thread 66852|cpu 200] [info ] [Request 4] Parsing the prompt took 63.00918926 s at 130.0127822022384 tokens/s
[13:10:27.460442370|thread 66855|cpu 200] [info ] [Request 7] Parsing the prompt took 63.009150493 s at 130.0128621938823 tokens/s
[13:10:27.460442521|thread 66856|cpu 200] [info ] [Request 8] Parsing the prompt took 63.009135386 s at 130.0128933656211 tokens/s
[13:10:27.460442471|thread 66853|cpu 200] [info ] [Request 5] Parsing the prompt took 63.009177818 s at 130.0128058115967 tokens/s
[13:10:27.460442507|thread 66850|cpu 200] [info ] [Request 2] Parsing the prompt took 63.009218575 s at 130.01272171387185 tokens/s
[13:10:27.460442486|thread 66854|cpu 200] [info ] [Request 6] Parsing the prompt took 63.009163785 s at 130.01283476722148 tokens/s
[13:10:27.460442504|thread 66851|cpu 200] [info ] [Request 3] Parsing the prompt took 63.009204843 s at 130.01275004837788 tokens/s
[13:10:41.062343859|thread 66852|cpu 200] [info ] [Request 4] Generating 253 response tokens with 8193 context took 13.547292 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062343880|thread 66849|cpu 200] [info ] [Request 1] Generating 253 response tokens with 8193 context took 13.547294 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062343766|thread 66853|cpu 200] [info ] [Request 5] Generating 253 response tokens with 8193 context took 13.547291 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062343884|thread 66851|cpu 200] [info ] [Request 3] Generating 253 response tokens with 8193 context took 13.547292 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062435887|thread 66851|cpu 200] [info ] [Request 3] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009205 s TTFT and 76.611104 s TTLT
[13:10:41.062345504|thread 66854|cpu 200] [info ] [Request 6] Generating 253 response tokens with 8193 context took 13.547296 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062343889|thread 66850|cpu 200] [info ] [Request 2] Generating 253 response tokens with 8193 context took 13.547290 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062472401|thread 66850|cpu 200] [info ] [Request 2] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009219 s TTFT and 76.611115 s TTLT
[13:10:41.062347232|thread 66855|cpu 200] [info ] [Request 7] Generating 253 response tokens with 8193 context took 13.547294 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062496679|thread 66855|cpu 200] [info ] [Request 7] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009150 s TTFT and 76.611057 s TTLT
[13:10:41.062347860|thread 66856|cpu 200] [info ] [Request 8] Generating 253 response tokens with 8193 context took 13.547293 s at 18.675 average tok/s, or 53.547 ms/tok
[13:10:41.062390280|thread 66852|cpu 200] [info ] [Request 4] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009189 s TTFT and 76.611088 s TTLT
[13:10:41.062405866|thread 66849|cpu 200] [info ] [Request 1] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009493 s TTFT and 76.611386 s TTLT
[13:10:41.062420890|thread 66853|cpu 200] [info ] [Request 5] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009178 s TTFT and 76.611076 s TTLT
[13:10:41.062458489|thread 66854|cpu 200] [info ] [Request 6] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009164 s TTFT and 76.611070 s TTLT
[13:10:41.062515236|thread 66856|cpu 200] [info ] [Request 8] Request with 8192 tokens in and 256 out (sequence limit) saw 63.009135 s TTFT and 76.611042 s TTLT
[13:10:41.121832590|thread 55587|cpu 200] [info ] KV cache footprint: 0.00 GB DMA + 0.00 GB K mirror in 0 books
```

## canonical-arm soak

arm canon, models llama-3.1-8b-instruct-good-tp2, ingested-qwen-3-4b-instruct-2507-tp2, planned 60 min, 25 users, started 2026-09-08T14:05:08Z, status stopped. Memory-growth lines: see soak__canon60/soak.log (grep 'Memory Growth' and 'used memory').

Probe build: g1_ok=1
