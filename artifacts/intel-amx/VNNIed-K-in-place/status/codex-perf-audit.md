# Performance audit of Claude's VNNI K delivery

## Short version

All 24 numerical result rows and all 30 percentage-comparison rows agree with an independent calculation from 60 full run logs. The four-device results include slower first-token times at both prompt length 1024 tokens and prompt length 2048 tokens. Several report sentences hide those costs or assign a cause that the measurements do not isolate. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

## Words used here

- tron is the inference program under test. runtron is its command-line tool.
- AMX and AVX-512 are CPU (processor) instruction sets. VNNI is the pair-interleaved memory layout used for cached attention keys, called K.
- tp2 and tp4 mean the model is split across two and four devices, respectively.
- base is the row-major K binary with AMX enabled. vnni is the new VNNI K binary with AMX enabled. off and vnnioff are the corresponding binaries with AMX disabled.
- TPS means decode tokens per second per user. TTFT means time to first token, measured here from request submission to the prompt-completion callback.
- sd means sample standard deviation across repetitions. It describes their spread. It is not a confidence interval.
- JSON is the structured text format used for the numeric audit. SHA-256 is the file fingerprint used to detect byte differences.
- A cell is one combination of device count, prompt length and arm. A paired comparison matches base and vnni by repetition number.

## What was verified

- The audit read every full accepted `rt/*.log` file. It did not calculate metrics from the shortened `rt-results.txt` file. That file supplied run metadata only. The independent parser is reproducible with `python3 status/codex-perf-audit.py`. [[audit parser](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.py)]
- There are 60 accepted logs and 60 attempt logs. Every accepted log is byte-identical to its first attempt. There are no retries, failed attempts or excluded attempts in this campaign. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]
- All 480 requests have one prompt timing, one decode timing and one completion record. Every completion states 256 output tokens and termination at the sequence limit. Every decode timing covers 253 generated steps. No request stopped early. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]
- All 24 cell means and sample standard deviations match the shared summary within an absolute comparison tolerance of 0.000000000001 in the corresponding unit. All 24 report result rows and all 30 percentage-comparison rows match at displayed precision. The shared summary files were not modified. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

## Main comparison: vnni against base

TPS is in tokens/s/user. TTFT is in seconds. Positive TTFT changes mean slower first-token delivery. Percentages are calculated from means before display rounding. The JSON file preserves the full numeric calculation and each source log. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

| Devices | Prompt tokens | Repetitions | Base TPS | VNNI TPS | TPS change | Base TTFT s | VNNI TTFT s | TTFT change ms | TTFT change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1024 | 3 | 79.587625 | 84.443458 | +6.101242% | 3.150942793 | 3.221446371 | +70.503578 | +2.237539% |
| 2 | 2048 | 3 | 52.760333 | 56.530375 | +7.145599% | 7.271866880 | 7.271102571 | -0.764309 | -0.010510% |
| 2 | 8192 | 3 | 17.294667 | 19.089667 | +10.378922% | 53.284308736 | 52.343531777 | -940.776959 | -1.765580% |
| 4 | 1024 | 2 | 106.412062 | 105.468500 | -0.886706% | 2.186942301 | 2.357777786 | +170.835485 | +7.811614% |
| 4 | 2048 | 2 | 78.046125 | 81.004000 | +3.789906% | 4.705931945 | 4.935378058 | +229.446112 | +4.875679% |
| 4 | 8192 | 2 | 30.991375 | 33.060063 | +6.675043% | 30.515534102 | 30.180382311 | -335.151791 | -1.098299% |

## Report findings

1. **The four-device report hides a second first-token regression.** It calls the short-prompt result “the one TTFT cost.” It then says the kernel gain covers the cost at longer prompts. The independently recomputed four-device result at prompt length 2048 tokens is 4.705931946 s to 4.935378058 s, a 229.446112 ms increase or 4.875679%. Both repetitions are slower: 4.898112% and 4.853262%. The 4.875679% cost is larger than the 2% threshold discussed elsewhere in the report. That threshold is stated for the short prompt. The comparison table itself is correct. [[frozen report](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:311); [generator inserts the same claim for both device counts](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_report.py:377); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

2. **The software-path interpretation contradicts its short-prompt four-device data.** For vnnioff against off, the report lists a 1.6% decode-rate reduction and a 3.1% first-token-time increase at prompt length 1024 tokens. The next sentence still says the reader is faster and the store cost does not show. That statement must be restricted to the configurations whose numbers support it. Even there, this comparison measures store plus reader changes together. [[frozen report](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:313); [unconditional report template](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_report.py:380)]

3. **The four-device comparison with the prior campaign uses two-device reference numbers.** The report repeats +13.2% TPS and -20.0% TTFT as the prior four-device result. The prior summary lists those values for two devices. Its four-device rows list +6.8% TPS and -10.5% TTFT. The current four-device AMX baseline comparison is +10.3% TPS and -11.0% TTFT. The claim that the TPS results agree cannot be justified by the copied two-device percentages. [[frozen report](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:315); [prior campaign summary](/home/jhan/workspace/intel-AMX/exec/results/p0perf-20260913/summary.md:5); [report template](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_report.py:383)]

4. **The added first-token time is measured, but its cause is not isolated.** The report calls it “the store cost” and says the difference is real because it exceeds the standard deviations. The measured cost repeats in every relevant pair. The experiment still changes the storage layout, storage writes and attention readers together. It always runs base before vnni. Insufficient data: separate storage-write timing or a controlled store-only comparison is needed to assign that cost specifically to storage writes. Randomized or reversed arm orders would test the effect of run order. [[frozen report](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:303); [arm loop](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:380); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

5. **The small two-device middle-prompt TTFT change is unresolved.** The average change at prompt length 2048 tokens is -0.010510%, or -0.764309 ms. The three matched differences are -33.865323 ms, +41.441103 ms and -9.868708 ms. These data do not establish a consistent reduction in first-token time. Report the result as effectively unchanged within the observed variation. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

6. **Two claims about the mechanism exceed this performance evidence.** The report says attention dominates the long-prompt decode step and that a larger attention share causes the growth in speedup. The campaign contains end-to-end request timings, not timings for individual operations. Insufficient data: an attention-time breakdown from the same configurations would test those explanations. [[frozen report](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:302); [frozen report](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:317)]

## Metric definitions and scope

- The TPS calculation first averages the eight printed per-user decode rates. It then averages run means across repetitions. The raw rates have three decimal places in tokens/s. The extra digits in derived means do not add measurement precision. This is neither first-token-inclusive throughput nor whole-request throughput. [[decode timing implementation](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/h/runtron/stream_generate.hpp:236); [summary calculation](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/summarize.py:86)]
- The timed generation count removes the token produced during prompt processing and removes padding associated with starting the decode timer. The full completion lines distinguish 253 timed steps from 256 output tokens. They also state the termination reason. [[decode timing implementation](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/h/runtron/stream_generate.hpp:238); [completion record](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/h/runtron/stream_generate.hpp:260); [example full run](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/rt/tp2__p1024__base__rep1.log:124)]
- The TTFT calculation takes the maximum of eight enqueue-to-prompt-completion durations in each run. It then averages those maxima across repetitions. The eight durations are close but not identical. The largest within-run range is 275.632000 microseconds. This maximum is not a percentile. [[request start timestamp](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/h/runtron/stream_generate.hpp:728); [prompt-completion timestamp](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/h/runtron/stream_generate.hpp:754); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]
- Process startup, device initialization and model loading occur before this TTFT timer. It is a request-level timing after model setup. It is not a cold process launch time or production service-interface latency. [[example initialization and model setup](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/rt/tp2__p1024__base__rep1.log:94); [request timer begins at submission](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/h/runtron/stream_generate.hpp:728)]

## Experiment controls and limits

- All 15 repetition groups use the order off → base → vnni → vnnioff. The three two-device repetitions run before the two four-device repetitions. These are matched repetitions, not randomized pairs. A systematic change with time could affect a contrast. That is a hypothesis, not a measured explanation. A reversed or randomized sequence would test it. [[arm definition](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:61); [nested run loops](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:380); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]
- The full logs contain 60 different automatically selected random seeds. The performance command does not fix a seed or use a forced token sequence. All requests nevertheless reach the same output length. Insufficient data: matched token records or a fixed-workload rerun would establish whether generated content affects these comparisons. [[example random seed](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/rt/tp2__p1024__base__rep1.log:1); [performance command](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:282); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]
- Every run header records zero Bill processes. This is a sample taken before a run. It does not establish that the entire host remained idle throughout that run. The watcher checks the CI (automated test system) lease and production serving. Insufficient data: time-aligned host-load and frequency measurements would quantify remaining host effects. [[run headers](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/rt-results.txt:8); [watcher](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:133); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]
- There are three repetitions per two-device cell and two repetitions per four-device cell. Treat the displayed standard deviations as descriptive. The evidence supports the measured directions listed here within this campaign. It does not establish a population-wide confidence level or a production service guarantee. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

## Binary and placement evidence

The per-run version lines match the header commit for all 60 runs. Both binary hashes are recorded at build time and at the start of the campaign. Those two records agree. The audit did not access the remote binaries to rehash them after the campaign. [[build record](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/build.txt:1); [campaign binary hashes](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/rt-results.txt:6); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

| Arm | Recorded commit | Recorded binary SHA-256 |
|---|---|---|
| off / base | 544ca05c7a954f892f0e23ccb465f74ad46bea5e | 09c4b6b2129dd722a737f57cd0f7c81f9741e619bb4b639f29f48eb01d08eb68 |
| vnni / vnnioff | 5e45ae55ae3277f025bd69a29e93741e2690e3e3 | 467bd63f0e37a6c3f693a6fa0f76a05818c50747f1e41fd35faf0e70921a6829 |

Every full run log confirms `USE_HW_ATTN=0`, meaning attention runs on the CPU. Each device-count group has exactly one observed application-core list, instance, driver-core list and device set. All runs use memory node 1 and the same recorded model path. The bitfile (device configuration image) release is 03.05.08.00 in every run. This checks recorded configuration equality. It does not prove identical instantaneous CPU frequencies or hardware state. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

| Device count | Instance | Device addresses | Driver cores | Application cores |
|---|---|---|---|---|
| 2 devices | 2,4 | 90:00.0, 93:00.0 | 75,76 | 223-224,96-101,120-125,225-226,102-107,126-131 |
| 4 devices | 1,2 | 90:00.0,93:00.0,b9:00.0,bc:00.0 | 75,76,77,78 | 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 |

## Acceptance and retry checks

The acceptance code requires a zero return code and at least one decode-rate line. Resume detection requires only one decode-rate line in the accepted log. The shared summary also accepts a run with any decode rates and an otherwise unmarked status. It does not require all eight request completions or all eight prompt timings. Its early-stop test checks unequal timed token counts or missing rate lines. It would miss eight requests that all stopped at the same shorter length. These are harness weaknesses. They did not change this campaign's accepted dataset because the independent parser verified every request completion. [[resume check](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:274); [acceptance check](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:295); [summary selection](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/summarize.py:80); [early-stop check](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/summarize.py:90); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

The campaign retries watcher stops, with a limit of three stopped attempts for a cell. Other failures are recorded and do not produce an accepted log. None occurred in the supplied performance dataset. [[stop and failure handling](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:290); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

## Unit-test record and skips

The four recorded test programs report 189467 passed assertions across 39 test cases. The full outputs contain no AMX-unavailable messages, explicit test skips or compiled-out placeholder test names. They show the AMX VNNI identity case running and passing. The compiler-disabled test variants therefore did not stand in for the requested cases in these four recorded runs. [[AMX numeric cases](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/tests-t_amx_numerics.out:19); [independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

| Test program | Passed assertions | Passed cases |
|---|---:|---:|
| t_amx_dispatch_dtype | 1559 | 1 |
| t_amx_numerics | 4621 | 5 |
| t_k_vnni_layout | 63208 | 4 |
| t_llama_unit | 120079 | 29 |

The logs also state that empty-checkpoint fixtures skip weight loading. That is not a skipped test case. The assertion failures printed during the checkpoint-scale case are expected negative tests. Their source requires the abort signal for missing or inconsistent scale metadata. [[empty-checkpoint fixture](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/tests-t_amx_dispatch_dtype.out:22); [negative-test source](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K/t/t_llama_unit.cpp:917)]

This record covers the four selected programs under the recorded AMX and VNNI enabled build. It does not demonstrate that the full repository suite ran. It does not establish hardware-attention staging correctness or performance. The campaign uses a fake-device unit-test environment and CPU attention for measurements. The report itself lists the hardware-attention adapter as unmeasured. [[selected test command](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh:218); [build flags](/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/build.txt:2); [report open items](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/Monday-morning-report.txt:745)]

## Paired repetition record

Each percentage compares vnni with base within the same repetition. Source paths and exact request-line references are retained in the JSON audit. Positive TTFT changes mean slower first-token delivery. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

| Devices | Prompt tokens | Repetition | Base TPS | VNNI TPS | TPS change | Base TTFT s | VNNI TTFT s | TTFT change ms | TTFT change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1024 | 1 | 80.078875 | 84.538000 | +5.568416% | 3.151299233 | 3.213235478 | +61.936245 | +1.965419% |
| 2 | 1024 | 2 | 79.367000 | 84.224000 | +6.119672% | 3.143156188 | 3.225381946 | +82.225758 | +2.616025% |
| 2 | 1024 | 3 | 79.317000 | 84.568375 | +6.620743% | 3.158372959 | 3.225721689 | +67.348730 | +2.132387% |
| 2 | 2048 | 1 | 52.816000 | 56.495125 | +6.965929% | 7.300618036 | 7.266752713 | -33.865323 | -0.463869% |
| 2 | 2048 | 2 | 52.772000 | 56.550000 | +7.159100% | 7.246197580 | 7.287638683 | +41.441103 | +0.571901% |
| 2 | 2048 | 3 | 52.693000 | 56.546000 | +7.312167% | 7.268785024 | 7.258916316 | -9.868708 | -0.135768% |
| 2 | 8192 | 1 | 17.290000 | 19.085000 | +10.381724% | 53.353152999 | 52.456448925 | -896.704074 | -1.680696% |
| 2 | 8192 | 2 | 17.287000 | 19.097000 | +10.470296% | 53.197177730 | 52.399987780 | -797.189950 | -1.498557% |
| 2 | 8192 | 3 | 17.307000 | 19.087000 | +10.284856% | 53.302595479 | 52.174158625 | -1128.436854 | -2.117039% |
| 4 | 1024 | 1 | 107.753000 | 106.217875 | -1.424670% | 2.190539361 | 2.357554266 | +167.014905 | +7.624374% |
| 4 | 1024 | 2 | 105.071125 | 104.719125 | -0.335011% | 2.183345240 | 2.358001306 | +174.656066 | +7.999471% |
| 4 | 2048 | 1 | 77.001625 | 80.213875 | +4.171665% | 4.704091883 | 4.934503594 | +230.411711 | +4.898112% |
| 4 | 2048 | 2 | 79.090625 | 81.794125 | +3.418231% | 4.707772008 | 4.936252522 | +228.480514 | +4.853262% |
| 4 | 8192 | 1 | 30.947250 | 33.492000 | +8.222863% | 30.460455975 | 30.178579070 | -281.876905 | -0.925386% |
| 4 | 8192 | 2 | 31.035500 | 32.628125 | +5.131623% | 30.570612229 | 30.182185551 | -388.426678 | -1.270588% |

## All accepted cell summaries

TPS is in tokens/s/user. TTFT and its standard deviation are in seconds. The means and standard deviations below are calculated directly from the full logs. [[independent full-log audit](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json)]

| Devices | Prompt tokens | Arm | Repetitions | Mean TPS | TPS sd | Mean TTFT s | TTFT sd s |
|---|---:|---|---:|---:|---:|---:|---:|
| 2 | 1024 | off | 3 | 70.279000 | 0.051215 | 3.937796675 | 0.007010015 |
| 2 | 1024 | base | 3 | 79.587625 | 0.426169 | 3.150942793 | 0.007614645 |
| 2 | 1024 | vnni | 3 | 84.443458 | 0.190662 | 3.221446371 | 0.007112871 |
| 2 | 1024 | vnnioff | 3 | 73.927333 | 0.070117 | 3.935471832 | 0.004846880 |
| 2 | 2048 | off | 3 | 45.621667 | 0.066726 | 11.077456357 | 0.003989882 |
| 2 | 2048 | base | 3 | 52.760333 | 0.062324 | 7.271866880 | 0.027340810 |
| 2 | 2048 | vnni | 3 | 56.530375 | 0.030593 | 7.271102571 | 0.014847038 |
| 2 | 2048 | vnnioff | 3 | 47.309000 | 0.128651 | 10.926047866 | 0.017161962 |
| 2 | 8192 | off | 3 | 14.754000 | 0.017521 | 121.679358168 | 0.065592866 |
| 2 | 8192 | base | 3 | 17.294667 | 0.010786 | 53.284308736 | 0.079579362 |
| 2 | 8192 | vnni | 3 | 19.089667 | 0.006429 | 52.343531777 | 0.149373403 |
| 2 | 8192 | vnnioff | 3 | 15.372333 | 0.027209 | 118.812332689 | 0.175728069 |
| 4 | 1024 | off | 2 | 96.452562 | 2.413444 | 2.456799310 | 0.026956740 |
| 4 | 1024 | base | 2 | 106.412062 | 1.896372 | 2.186942301 | 0.005087012 |
| 4 | 1024 | vnni | 2 | 105.468500 | 1.059776 | 2.357777786 | 0.000316105 |
| 4 | 1024 | vnnioff | 2 | 94.910188 | 2.128480 | 2.532836277 | 0.010796550 |
| 4 | 2048 | off | 2 | 71.896938 | 2.356168 | 6.505401145 | 0.000727087 |
| 4 | 2048 | base | 2 | 78.046125 | 1.477146 | 4.705931945 | 0.002602241 |
| 4 | 2048 | vnni | 2 | 81.004000 | 1.117405 | 4.935378058 | 0.001236679 |
| 4 | 2048 | vnnioff | 2 | 77.015500 | 0.035355 | 6.483424525 | 0.008695258 |
| 4 | 8192 | off | 2 | 26.493875 | 0.150083 | 64.651225635 | 0.069702627 |
| 4 | 8192 | base | 2 | 30.991375 | 0.062402 | 30.515534102 | 0.077892234 |
| 4 | 8192 | vnni | 2 | 33.060063 | 0.610852 | 30.180382311 | 0.002550167 |
| 4 | 8192 | vnnioff | 2 | 27.654500 | 0.406586 | 63.169885433 | 0.072230946 |
