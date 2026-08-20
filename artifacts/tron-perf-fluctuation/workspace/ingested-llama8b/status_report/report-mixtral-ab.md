# Mixtral-8x7B ingested-vs-hand-authored A/B: decode-TPS fluctuation, tp4 and tp2 on delphi-3bda

Date: 2026-08-15. Owner-approved follow-up to the llama-8b screen (report.md).
Host: delphi-3bda only. Build: stock latest main
`1e1c03c571ba0012f67e5358c3287b1ec4ee12c3`, binary sha256
`4bc21f38d787c1014094596c04bdd4f4e0693ad459b9bcb969a7bb25dc98deb9`
(install-llama8b-stock — the SAME binary as the llama-8b screen, so all five
campaigns from 2026-08-15 are directly comparable). No probes, no perfetto
(CAPTURE=none, KVWAIT=0). Workload per draw: prompt 1024, gen 4096, shared
system prompt 256, 1 user, 1 instance, speculation 0, USE_HW_ATTN=0, greedy
seed 2954953865, --pay-for-determinism.

## Purpose

Before this A/B, the tested-model matrix confounded two variables: every
ROLLS row was ingest-generated and every TIGHT row was hand-authored.
Mixtral-8x7B is the only model with both a hand-authored and an
ingest-generated variant on the same default_weights
(`mistralai/Mixtral-8x7B-Instruct-v0.1`, fp16, per config/models.yaml
@ 1e1c03c57), so it can separate implementation from parallelism degree.

## Conclusion

- **The ingested/hand-authored confound is broken**: hand-authored
  `mixtral-8x7b-instruct-v0.1-tp4` ROLLS on delphi-3bda — CV 2.43%,
  gap 9.03% (campaign 3bda-mixtral-tp4-20260815T152808Z) — the first
  hand-authored model observed to roll.
- The same-weights ingested variant at tp4 also fluctuates but MILDER:
  CV 1.11%, gap 4.38% (campaign 3bda-ingmixtral-tp4-20260815T155824Z).
- Ingested tp2 is extremely tight: CV 0.14%, gap 0.52%
  (campaign 3bda-ingmixtral-tp2-20260815T163100Z), matching the
  hand-authored tp2 precedent (CV 0.179%, ab60d, n=26).
- **For Mixtral, parallelism degree — not ingestion — drives the
  fluctuation**: both implementations are tight at tp2 and fluctuate at tp4.
  Combined with the lowered_freq exclusion of frequency/power (peer report
  2026-08-15-01, intra-pass), the cause space narrows to something
  tp4-specific (4-card execution).
- Secondary observation: the ingested plugin is ~30% slower than
  hand-authored at tp4 (105.5 vs 150.9 tok/s mean).

## Per-config numbers

All campaigns: 20 ok draws of 20 scheduled, harness exit 0, machine
restored, token_sha256 identical across draws within each campaign,
bitfile Release Code 01.05.08.00 / 06-16-2026 on every draw. sd is the
sample standard deviation (n-1); per-token sd is the sample sd of 1e6/TPS.

| config | campaign id | n | mean tok/s | sd | CV | min | max | gap | per-token sd (us) | screen classification |
|---|---|---|---|---|---|---|---|---|---|---|
| hand-authored tp4 | 3bda-mixtral-tp4-20260815T152808Z | 20 | 150.907 | 3.670 | 2.43% | 143.030 | 156.664 | 9.03% | 163.2 | FLUCTUATES |
| ingested tp4 | 3bda-ingmixtral-tp4-20260815T155824Z | 20 | 105.490 | 1.169 | 1.11% | 102.195 | 106.817 | 4.38% | 106.7 | FLUCTUATES |
| ingested tp2 | 3bda-ingmixtral-tp2-20260815T163100Z | 20 | 94.290 | 0.132 | 0.14% | 94.009 | 94.503 | 0.52% | 14.8 | TIGHT |

Per-token time means: hand tp4 6630.4 us, ingested tp4 9480.7 us,
ingested tp2 10605.5 us.

Rule notes:
- Screen rule (llama-8b runbook): FLUCTUATES = CV >= 1.0% or gap >= 3%;
  TIGHT otherwise.
- Matrix rule (pre-registered in ab kits): TIGHT = CV <= 0.8%;
  ROLLS = CV >= 2.5% or range/mean >= 5%. Under it: hand tp4 = ROLLS
  (range 9.03% >= 5%); ingested tp4 falls BETWEEN the bands
  (CV 1.11%, range 4.38%) — reported as-is, not forced into a bucket;
  ingested tp2 = TIGHT.
- n=20 CV estimates carry ~±16% relative error at 1 sigma. Neither tp4
  verdict is borderline under the screen rule; the ingested-tp4
  "between bands" placement under the matrix rule is (range 4.38% vs
  the 5% bound).

## Per-draw decode TPS (tok/s)

Distribution strips (per-config scale, `*`=1 draw, digit=draws per bin):

```
hand-tp4 143.03 |*.*........*.*....*2..**..*2.*..*.2...*.....*| 156.66
ing-tp4  102.19 |*......*......*....*.....2..*..2*2.2*22*.....| 106.82
ing-tp2   94.01 |2........*..*..*.**...*.32*2..2.*..*......*..|  94.50
```

hand-authored tp4, draw order (3bda-mixtral-tp4-20260815T152808Z):
143.03 154.19 150.73 148.72 153.34 154.55 151.42 144.65 156.66 146.63
147.86 148.24 153.55 149.82 152.41 150.01 153.00 155.60 149.37 154.36
(smoke, not counted: 150.468)

ingested tp4, draw order (3bda-ingmixtral-tp4-20260815T155824Z):
106.29 105.10 106.15 106.46 105.38 105.96 103.29 102.19 105.50 106.16
105.24 106.09 106.26 105.33 104.37 104.40 106.00 106.73 106.82 106.09
(smoke, not counted: 106.756)

ingested tp2, draw order (3bda-ingmixtral-tp2-20260815T163100Z):
94.30 94.35 94.50 94.35 94.25 94.17 94.29 94.36 94.46 94.19
94.41 94.33 94.36 94.01 94.24 94.38 94.01 94.37 94.32 94.14
(smoke, not counted: 94.337)

token_sha256 per campaign: hand tp4
`865824c57a84d973a02ae27cf55097f2f658db00de9d6c8659a986a5caa08924`,
ingested tp4
`fd612763d69561e299b7ec92c8532df195ccf0bbc89be852d4755b7769ba3902`,
ingested tp2
`bfc59d4f73f79cdf92f04dacffdde264832a629f420e657c6ec3abd15869fa1a`.
(Shas differ BETWEEN campaigns — expected: different plugin / parallelism;
the determinism gate is within-campaign identity only.)

## Context rows (same host or precedent, never merged)

- Hand-authored `mixtral-8x7b-instruct-v0.1-tp2`: TIGHT, CV 0.179%
  (ab60d, n=26, fp16 178 GB) — the pre-existing matrix row this A/B
  extends.
- llama-8b same-day same-binary screens on 3bda: tp4 FLUCTUATES
  (CV 1.44%, gap 5.80%), tp2 TIGHT (CV 0.67%, gap 2.45%) — see report.md.
- Counter-example on record: hand-authored llama-70b tp4 TIGHT (ab60b
  n=26; also PDJN on delphi-3af6) — tp4 alone does not roll every model;
  the effect is model-dependent even among hand-authored ones.
- Frequency/power EXCLUDED as cause (peer lowered_freq analysis,
  2026-08-15: zero 0x64F throttle reasons, busy clocks flat 3737-3770 MHz,
  slow draws burn more power at higher clocks). Report:
  ../../intra-pass/status_report/2026-08-15-01-lowered_freq.html.
- Converging evidence from the wcls-bypass experiment (peer session
  trace-sync-points-7a, 2026-08-15, recorded in intra-pass/CONTEXT.md
  section 5c): under the wcls bypass, cross-draw TPS correlation moved onto
  the [open->F1] transfer phase (r = -0.81) and the intra-pass span
  (r = -0.86) — both are 4-card coordination paths, consistent with the
  tp4-specificity found here.
- Host DRAM bandwidth EXCLUDED as cause (peer dram-ceiling campaign
  3bda-drambw-tp4-20260816T195258Z, 2026-08-16): measured achievable
  ceiling ~220 GB/s reads per socket (membw saturation ground truth);
  decode uses 11.5-14.4% of ceiling at the mean, 28-30% at the busiest
  second of any draw; correlations inverted (corr(TPS, bandwidth) = +0.57,
  corr(TPS, peak util) = +0.74 — bandwidth follows throughput). Report:
  ../../intra-pass/status_report/2026-08-16-01-dram-ceiling.html.
  (Platform note from that campaign: raw IMC cas_count counters
  under-scale by exactly x2.01 on 3bda — DDR5 sub-channel.)
- Exclusion ledger as of 2026-08-16 (peer's summary): wcls pipeline,
  CPU frequency/power, ingestion (this A/B), host DRAM bandwidth.

## Data

Archived in ../data/: results-mixtral-tp4-20260815T152808Z.csv,
results-ingmixtral-tp4-20260815T155824Z.csv,
results-ingmixtral-tp2-20260815T163100Z.csv (+ identity.env each).
Campaign roots under /scratch/jhan/perf-fluctuation/deep-dive/.
