# PR4' gate failure diagnosis (2026-10-21)

Short version: the option-on build of PR4' at f7c2ccf6b7 failed one assertion of t_llama_unit (page splits match emulation). Eight instrumented builds on 3bda and a 63-agent code analysis agree: PR4' has no numeric defect. The VNNI slot presents fill_random's raw rows at permuted tokens, so the option-on build scores a different random K instance than the row-major build, and the bf16 truncation of the softmax weights in the PV product lands one element beyond the test's absolute bound of 0.01. Fix 38ad10f25c: the bound is 5e-2 under the option, the bound the case's split comparison already uses.

Probe logs (exec/results/benstack-20261021/probe-*.log):
- bp4v: the gate binary, section alone: fails at query 6 of the 2-page call, s* and m* within 1e-5, v*[6][255] 0.269 vs 0.253.
- bp4d (PR4' + DIAG): storage unchanged by the attention run, 131-196 of 256 v* elements per query beyond 2e-3, ratio obs/exp 0.997 mean.
- bp4e (PR 4959 head + DIAG): passes with the same deviation level (131-205 elements, max 0.019).
- bp4f / bp4g (later pages all row-major / all converted): identical results to the 41-row setup, to the last digit.
- bp4h / bp4i (data hash): K hash differs between the heads (e7e1751d… vs e89c1ad9…), V hash equal, m* bit-identical, s* differs 0.25 %.
- bp4j (PR4' option off): identical to the PR 4959 option-on run (the base's re-store gave its VNNI build the row-major instance).
- bp4k (hash before recording): equal to the hash after recording, so the in-place conversion changes no K value.

Workflow: wf_208a07c8-9ac (pr4-diagnosis-workflow.json, pr4-diagnosis-synthesis.md), 19 hypotheses, 3 survivors, all test-only fixes.
