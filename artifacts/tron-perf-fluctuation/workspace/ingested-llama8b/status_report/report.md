# Decode-TPS fluctuation screen: ingested-llama-3.1-8b, tp2 and tp4 on delphi-3bda

Date: 2026-08-15. Executor: Claude session, per RUNBOOK-llama8b-tps-screen.md.
Host: delphi-3bda only. Build: stock latest main
`1e1c03c571ba0012f67e5358c3287b1ec4ee12c3`, binary sha256
`4bc21f38d787c1014094596c04bdd4f4e0693ad459b9bcb969a7bb25dc98deb9`
(install-llama8b-stock). No probes, no perfetto, no instrumentation
(CAPTURE=none, KVWAIT=0).

## Conclusion (one sentence per config)

- **tp4 FLUCTUATES**: ingested-llama-3.1-8b-tp4 decode TPS rolls draw-to-draw
  on delphi-3bda at this build — CV 1.44% (>= 1.0%) and gap 5.80% (>= 3%)
  (campaign 3bda-llama8b-tp4-20260815T113956Z).
- **tp2 TIGHT**: ingested-llama-3.1-8b-tp2 decode TPS is tight on delphi-3bda
  at this build — CV 0.67% (< 1.0%) and gap 2.45% (< 3%)
  (campaign 3bda-llama8b-tp2-20260815T120428Z).

This reproduces the qwen-3-4b pattern (tp2 tight, tp4 rolls): the fluctuation
follows the parallelism degree, not the model. Cause-hunting is out of scope
here (see ../intra-pass/CONTEXT.md).

## Per-config numbers

Both campaigns: 20 ok draws of 20 scheduled, harness exit 0, machine
restored. sd is the sample standard deviation (n-1). Per-token sd is the
sample sd of 1e6/TPS in microseconds.

| config | campaign id | n | mean tok/s | sd | CV | min | max | gap | per-token sd (us) | classification |
|---|---|---|---|---|---|---|---|---|---|---|
| tp4 (SLICE_OF=2, 4 cards) | 3bda-llama8b-tp4-20260815T113956Z | 20 | 205.129 | 2.953 | 1.44% | 200.978 | 212.866 | 5.80% | 69.6 | FLUCTUATES |
| tp2 (SLICE_OF=4, 2 cards) | 3bda-llama8b-tp2-20260815T120428Z | 20 | 162.506 | 1.095 | 0.67% | 160.517 | 164.503 | 2.45% | 41.4 | TIGHT |

Per-token time means: tp4 4875.9 us/token, tp2 6153.9 us/token.

Precision caveat: at n=20 a CV estimate has ~±16% relative error at 1 sigma.
That does not change either verdict here: tp4's CV 1.44% is >= 1.0% by ~3
sigma of that estimate error, and tp2's CV 0.67% stays < 1.0% even at +2
sigma (0.67% + 2×0.11% = 0.89%). tp2's gap 2.45% is the closest number to
its threshold (3%); the CV criterion is comfortably met, and the rule is
CV-first with gap as companion guard.

## Per-draw decode TPS (tok/s)

Distribution strips (per-config scale, `*`=1 draw, digit=that many draws in
the bin):

```
tp4 200.98 |***.2..*..***.*.*..2**.**.*.*................*| 212.87
tp2 160.52 |*....*....****.2.*.*.**.......2*.**.*....*...*| 164.50
```

Read: tp4's body spans ~201-208.5 with one outlier draw at 212.87
(draw_13); even excluding that outlier the body gap is ~3.7% — tp4
fluctuates without the outlier. tp2's 20 draws all fit inside a 4.0 tok/s
band.

tp4, draw order (campaign 3bda-llama8b-tp4-20260815T113956Z):
201.568 207.181 206.088 202.973 206.527 208.518 205.385 202.225 206.078
202.133 206.437 203.674 212.866 204.853 204.042 207.363 201.307 204.282
208.106 200.978 (smoke, not counted: 208.385)

tp2, draw order (campaign 3bda-llama8b-tp2-20260815T120428Z):
160.985 163.738 163.200 161.908 160.517 163.583 162.276 161.568 161.927
162.550 163.207 163.477 163.286 164.503 161.448 162.379 161.600 164.200
161.698 162.061 (smoke, not counted: 162.981)

## Determinism and gates

- token_sha256 identical across all 20 draws within each campaign (the
  within-campaign identity gate; no external reference sha exists for this
  model): tp4 `3831fb161958c9c213a5185622fa504abddd55172c14807c8b136702d95349ae`,
  tp2 `6ee9697e3a56075661a381b240e981e7541669c6cbbc0a54455c995de4700055`.
  Greedy, fixed seed 2954953865, --pay-for-determinism, --threshold_p 0.
- Bitfile identical across both campaigns and all draws: Release Code
  01.05.08.00, Release Date 06-16-2026 (journal.log of both campaigns).
- Workload per draw: prompt 1024, gen 4096, shared system prompt 256,
  1 user, 1 instance, speculation 0, USE_HW_ATTN=0 (sw-attention banner
  gate passed every draw).
- Device-set gate passed on both configs (tp4: first 4 BDFs; tp2 with
  SLICE_OF=4: first 2 BDFs) — the runbook's tp2 EXPECTED_DEVS concern did
  not trip.

## Context (different host or model — never merged into the classification)

- qwen-3-4b tp4 fluctuates: CV 1.3-3.3% across campaigns/hosts/builds;
  2026-08-14 control on 3c51 CV 1.32%; wadefix-on on 3bda CV 1.32%
  (deep-dive + wadefix campaigns). llama-8b tp4 CV 1.44% sits inside that
  band.
- qwen tp1 and tp2 screens were tight (deep-dive report 2026-08-11-02);
  llama-8b tp2 CV 0.67% matches qwen tp2's tight behavior.
- Counter-example on record: llama-70b tp4 was TIGHT on delphi-3af6 (PDJN)
  — host and model still matter; this report's claims are delphi-3bda only.

## Execution notes

- Campaign A first attempt (3bda-llama8b-tp4-20260815T113251Z) failed at
  smoke ('no bitfile lines') due to a collision with a concurrent campaign
  from another session (lowfreq-20260815T113207Z, pfgate family) launched
  35 s earlier on the same host: both preflights passed inside the ~60 s
  traffic-gate window and their cleanups killed each other. Both restored
  cleanly; the attempt is not counted. Sequencing was agreed with that
  session (this screen ran first); the counted tp4 campaign is attempt 2.
- The build's gated-HF blocker (HTTP 401 on meta-llama/Llama-3.1-8B-Instruct)
  was resolved by staging config.json + tokenizer files from 3bda's
  /opt/positron/weights store to the same path on alpha; the --meta-device
  torch export reads only config.json, so the trace was regenerated by stock
  code with no HF access. Fresh metadata.json parameter shapes are identical
  to the pre-existing pr3244 export (291 parameters).
- Raw data archived in this folder: data/results-tp4-20260815T113956Z.csv,
  data/results-tp2-20260815T120428Z.csv (+ identity.env for each).
  Campaign roots on /scratch/jhan/perf-fluctuation/deep-dive/.

## Glossary

- **draw**: one full benchmark run (fresh runtron launch, 1024-token prompt,
  4096 generated tokens); the campaign repeats 20 draws plus one uncounted
  smoke draw.
- **decode TPS / generate_tok_s**: generated tokens per second during the
  decode (generation) phase, as reported by the harness's metrics.json.
- **CV**: coefficient of variation = sd / mean, in percent.
- **gap**: (max - min) / mean over the campaign's draws, in percent.
- **tp2 / tp4**: tensor-parallelism degree (2 or 4 FPGA cards);
  SLICE_OF = 8 / cards.
- **rolls**: shorthand for "fluctuates draw-to-draw beyond the threshold".
