## pr4ci-20261012 summary: base (the deb of main at 72308ec90c, jhan-pr4ci-base) against target (the PR-4 deb, jhan-pr4ci-target)

Runs found: base-pass1 (3 cells, 18.31 min, tron v2026.10.12-72308ec9-jhan-pr4ci-base), target-pass1 (3 cells, 17.92 min, tron v2026.10.12-ea94e95a-jhan-pr4ci-target), base-pass2 (3 cells, 18.62 min, tron v2026.10.12-72308ec9-jhan-pr4ci-base), target-pass2 (3 cells, 17.92 min, tron v2026.10.12-ea94e95a-jhan-pr4ci-target)

Resolution rule: resolved = |paired t| >= 2.26 AND |delta| >= 1 % (TTFT also |delta| >= 1 ms). The paired t pools the paired-by-round differences (target - base, round means) of every complete pass pair (pass1 with pass1, pass2 with pass2; n = 10 rounds per pair). Memory = mean over passes of the sum over engine pids of VmHWM (peak resident set) and VmRSS read right after the benchmark (MiB; 1 GiB hugepages are NOT in these sums, they are in HugetlbPages). n/t = not testable (no complete pass pair).

### Full passes (FPGA attention as shipped; the cells of the configs file given to the driver)

| cell | base TPS mean (sd over passes) | target TPS | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama-3.1-8b-instruct-good-tp2@8u-p1024 | 150.78 (0.08) n=2 | 150.15 (0.33) n=2 | -0.4 % | -1.05 (20) | no | 572 | 586 | +14 ms (+2.5 %) t=+2.08 | no | 21,926 | 21,929 | +3 MiB (+0.0 %) | 759 | 762 | +3 MiB |
| llama-3.1-8b-instruct-good-tp2@32u-p4096 | 32.73 (0.00) n=2 | 34.42 (0.05) n=2 | +5.2 % | +53.81 (20) | YES | 11,670 | 11,653 | -17 ms (-0.1 %) t=-1.37 | no | 21,926 | 21,929 | +3 MiB (+0.0 %) | 999 | 1,013 | +14 MiB |
| ingested-gpt-oss-120b-tp4@8u-p1024 | 123.49 (0.90) n=2 | 123.11 (0.07) n=2 | -0.3 % | -0.59 (20) | no | 969 | 972 | +4 ms (+0.4 %) t=+0.58 | no | 128,492 | 128,489 | -3 MiB (-0.0 %) | 5,491 | 5,493 | +2 MiB |

### Extra cell: qwen3-4b tp2, 8 users, prompt 8192, software attention (USE_HW_ATTN=0)

sw8k cell: not run

Per-provisioning checks (installed binary mapped by every engine, USE_HW_ATTN state): all ok

