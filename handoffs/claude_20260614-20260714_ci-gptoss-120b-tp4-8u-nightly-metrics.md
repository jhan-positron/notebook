# CI nightly metrics: ingested-gpt-oss-120b-tp4 @8u per machine (2026-06-14 to 2026-07-14)

> Collected by Claude (Claude Code) on 2026-07-14 from Slack #ci-cd-notifications
> (channel C06S8PNDBQA), Talos nightly-report messages. Not a session handoff —
> this is a data-collection note; it intentionally has no `Claude session:`
> header, so `SCOPE: auto` handoff runs ignore it.

## What this is

Per-machine nightly CI results for the `ingested-gpt-oss-120b-tp4 @8u per
machine` TPS test over the last 30 days: decode throughput, prefill
throughput, TTFT, and the machine (DUT) each run executed on. Decode goal is
52.0 TPS throughout; slowest-user goal 40.0 TPS; TTFT measured @1k prompt.

Notes on the source format:
- `prefill` is the report's own client-side approximation (prompt_length /
  TTFT), quoted verbatim (values like `1k` mean ~1000 tok/s).
- Reports before 2026-06-17 used an older format without prefill/TTFT (shown
  as em-dash).
- Rig `GENOA96_RINZLER` runs on DUT andoria-b1a3; rig
  `GRANITE_RAPIDS_72_RINZLER` ran on delphi-17cf, and additionally on
  delphi-3bda from 2026-07-09 (its first night back in CI rotation after the
  July FPGA/flat-freq work; that first run scored 0.00 and passed from
  2026-07-10 on). DUT labels only appear in headers from 2026-06-30; rows
  before that show "(not labeled)" — the rig->DUT mapping in that window is
  not stated in the messages.
- No nightly reports were posted on 2026-06-28, 06-29, and 07-13; GRANITE
  had no report on 06-25, 06-27, and 07-02; GENOA's 06-26 run failed to
  provision (DUT kernel marked TSC unstable). delphi-3bda's 2026-07-08
  nightly ran but included no gpt-oss @8u result.
- Duplicate human reposts of the same (rig, DUT, date) report were deduped.

## Data

| Date | Machine (DUT) | Rig | Status | Decode TPS (goal 52.0) | % of goal | Slowest user TPS | Prefill ≈tok/s | TTFT ms (@1k prompt) |
|---|---|---|---|---|---|---|---|---|
| 2026-06-14 | (not labeled) | GENOA96_RINZLER | PASS | 115.11 | 221% | 111.63 | — | — |
| 2026-06-14 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 93.71 | 180% | 90.63 | — | — |
| 2026-06-15 | (not labeled) | GENOA96_RINZLER | PASS | 112.80 | 216% | 107.78 | — | — |
| 2026-06-15 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 94.07 | 180% | 89.02 | — | — |
| 2026-06-16 | (not labeled) | GENOA96_RINZLER | PASS | 112.60 | 216% | 104.03 | — | — |
| 2026-06-16 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 92.33 | 177% | 84.75 | — | — |
| 2026-06-17 | (not labeled) | GENOA96_RINZLER | PASS | 112.79 | 216% | 110.48 | 1k | 1008 |
| 2026-06-17 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 95.97 | 184% | 90.56 | 799 | 1281 |
| 2026-06-18 | (not labeled) | GENOA96_RINZLER | PASS | 111.50 | 214% | 80.25 | 1k | 1024 |
| 2026-06-18 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 95.03 | 182% | 75.46 | 799 | 1281 |
| 2026-06-19 | (not labeled) | GENOA96_RINZLER | PASS | 114.20 | 219% | 110.23 | 1k | 1020 |
| 2026-06-19 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 96.39 | 185% | 91.01 | 801 | 1278 |
| 2026-06-20 | (not labeled) | GENOA96_RINZLER | PASS | 112.78 | 216% | 106.14 | 973 | 1052 |
| 2026-06-20 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 96.73 | 186% | 94.48 | 802 | 1277 |
| 2026-06-21 | (not labeled) | GENOA96_RINZLER | PASS | 113.25 | 217% | 106.44 | 977 | 1048 |
| 2026-06-21 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 95.60 | 183% | 92.63 | 797 | 1285 |
| 2026-06-22 | (not labeled) | GENOA96_RINZLER | PASS | 112.50 | 216% | 107.64 | 1k | 1023 |
| 2026-06-22 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 94.06 | 180% | 89.73 | 794 | 1290 |
| 2026-06-23 | (not labeled) | GENOA96_RINZLER | PASS | 113.07 | 217% | 106.51 | 1k | 1015 |
| 2026-06-23 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 96.25 | 185% | 92.16 | 798 | 1283 |
| 2026-06-24 | (not labeled) | GENOA96_RINZLER | PASS | 113.99 | 219% | 111.70 | 1k | 994 |
| 2026-06-24 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 96.14 | 184% | 91.18 | 803 | 1275 |
| 2026-06-25 | (not labeled) | GENOA96_RINZLER | PASS | 113.15 | 217% | 111.11 | 1k | 1001 |
| 2026-06-26 | (not labeled) | GENOA96_RINZLER | FAIL/NO-RESULT | — | — | — | — | — |
| 2026-06-26 | (not labeled) | GRANITE_RAPIDS_72_RINZLER | PASS | 93.66 | 180% | 89.76 | 792 | 1293 |
| 2026-06-27 | (not labeled) | GENOA96_RINZLER | PASS | 113.40 | 218% | 111.34 | 1k | 1019 |
| 2026-06-30 | andoria-b1a3 | GENOA96_RINZLER | PASS | 113.10 | 217% | 110.00 | 969 | 1057 |
| 2026-06-30 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 94.58 | 181% | 91.25 | 789 | 1298 |
| 2026-07-01 | andoria-b1a3 | GENOA96_RINZLER | PASS | 112.50 | 216% | 97.76 | 953 | 1075 |
| 2026-07-01 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | WARN | 0.00 | 0% | 0.00 | n/a | n/a |
| 2026-07-02 | andoria-b1a3 | GENOA96_RINZLER | PASS | 112.35 | 216% | 106.02 | 912 | 1123 |
| 2026-07-03 | andoria-b1a3 | GENOA96_RINZLER | PASS | 114.76 | 220% | 101.37 | 939 | 1091 |
| 2026-07-03 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 98.59 | 189% | 95.32 | 803 | 1275 |
| 2026-07-04 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.26 | 221% | 112.32 | 900 | 1138 |
| 2026-07-04 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 99.03 | 190% | 96.06 | 804 | 1274 |
| 2026-07-05 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.48 | 222% | 109.94 | 974 | 1051 |
| 2026-07-05 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 98.58 | 189% | 96.03 | 809 | 1266 |
| 2026-07-06 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.06 | 221% | 110.91 | 926 | 1106 |
| 2026-07-06 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 98.09 | 188% | 94.04 | 801 | 1279 |
| 2026-07-07 | andoria-b1a3 | GENOA96_RINZLER | PASS | 114.90 | 220% | 109.77 | 962 | 1065 |
| 2026-07-07 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 98.02 | 188% | 95.40 | 803 | 1276 |
| 2026-07-08 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.49 | 222% | 106.49 | 1k | 994 |
| 2026-07-08 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 97.52 | 187% | 93.42 | 801 | 1279 |
| 2026-07-09 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.63 | 222% | 113.00 | 1k | 1008 |
| 2026-07-09 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | WARN/NO-RESULT | — | — | — | — | — |
| 2026-07-09 | delphi-3bda | GRANITE_RAPIDS_72_RINZLER | WARN | 0.00 | 0% | 0.00 | — | — |
| 2026-07-10 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.44 | 221% | 112.63 | 993 | 1031 |
| 2026-07-10 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 93.39 | 179% | 87.85 | 797 | 1285 |
| 2026-07-10 | delphi-3bda | GRANITE_RAPIDS_72_RINZLER | PASS | 93.28 | 179% | 88.99 | 799 | 1282 |
| 2026-07-11 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.52 | 222% | 112.43 | 1k | 1000 |
| 2026-07-11 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 88.24 | 169% | 84.08 | 788 | 1300 |
| 2026-07-11 | delphi-3bda | GRANITE_RAPIDS_72_RINZLER | PASS | 94.18 | 181% | 87.66 | 783 | 1307 |
| 2026-07-12 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.57 | 222% | 110.32 | 959 | 1068 |
| 2026-07-12 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 89.56 | 172% | 85.28 | 772 | 1326 |
| 2026-07-14 | andoria-b1a3 | GENOA96_RINZLER | PASS | 115.86 | 222% | 113.88 | 1k | 990 |
| 2026-07-14 | delphi-17cf | GRANITE_RAPIDS_72_RINZLER | PASS | 96.05 | 184% | 92.39 | 788 | 1299 |
| 2026-07-14 | delphi-3bda | GRANITE_RAPIDS_72_RINZLER | PASS | 95.70 | 184% | 93.07 | 874 | 1171 |

## Provenance

- Source: Slack #ci-cd-notifications (C06S8PNDBQA), messages 2026-06-14
  through 2026-07-14 (91 channel messages scanned, 60 nightly reports, 57
  gpt-oss @8u data rows after dedupe).
- Poster: `talos` bot (plus occasional human reposts, deduped).
- Extraction: regex parse of the Nightly Report TPS section line
  `ingested-gpt-oss-120b-tp4 @8u per machine: ...` with the machine taken
  from the report header (`━━━ <rig> DUT: <host> ━━━`).
