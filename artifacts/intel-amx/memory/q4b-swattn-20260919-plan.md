---
name: q4b-swattn-20260919-plan
description: "2026-09-19 plan CI-test/status/qwen3-4b-Saturday-plan.md: qwen3-4b tp2 AMX gain with USE_HW_ATTN=0 on both arms (nightly deb vs canon deb), prompt 1024-8192 at 2 users per engine, CI harness, whole 3bda; key verified facts (nightly prompt is 1024 not 1536; config.env mechanism) and the corrections made to jhan's order"
metadata:
  type: project
---

Plan written 2026-09-19 18:5x UTC for another agent to execute; report target status/Saturday-qwen3-4b.html; scripts to be
copied from exec/l8b-levers-20260919/ to exec/q4b-swattn-20260919/. Same two debs as the llama campaign (base = saved
nightly 2026.09.18-3faba6d0 in /var/tmp/jhan/canon-ci-20260918/nightly.deb, canon = target.deb there).

Verified facts (2026-09-19):
- Nightly qwen3-4b tp2 perf config = 8 users, prompt_length 1024, generate_length 1536, 4 tp2 engines -> 2 users per engine
  (systems_test scripts/perf.py:139-150 at fc27f07 = upstream main). jhan's "1.5k same as CI" is the GENERATION length;
  the plan keeps a 1536 cell and adds the 1024 reference cell (9 cells: 1024 1536 2048 3000 4096 5120 6144 7168 8192).
- USE_HW_ATTN=0 for platformd-started engines: write it to /opt/positron/user/config.env (rinzler@.service reads it as
  EnvironmentFile=- LAST, so it wins over instance-N.env), then restart the engines; clear it (0 bytes) before the restore
  brings production up. Verify per engine with sudo tr '\0' '\n' </proc/PID/environ.
- hw_attn_config.hpp: USE_HW_ATTN unset = FPGA attention for ingested models only; =0 disables for all.
- Ingested qwen3-4b weight dirs (positron-ai/Qwen--Qwen3-4B-Instruct-2507-ingest-best-gptq and -v1): tokenizer truncation
  null, 36 layers, 8 KV heads x 128 -> 144 KiB KV per token, max_position_embeddings 262144. No truncation trap.
- Harness prompt counting uses llama header strings and drops the first token; qwen has no BOS, so the server-counted
  prompt tokens differ from prompt_length by a model-specific overhead (same in the nightly; measure it).
- Expected: p0perf-20260913 CI layout tp2 2u/engine USE_HW_ATTN=0: 140.61 -> 152.46 TPS (+8.4 %) at prompt 1024;
  nightly FPGA level 186 TPS. Pre-registered band at 1024: +5.4..+11.4 %. Data F runtron: +19.0 % (2048), +17.5 % (8192).
- Duration est. 4.1 h (llama 2u cells 124/137/155/188 s at 1024/2048/3000/4096 -> line 103 s + 0.021 s/token).
- Peer issue-4500 block m6 finished 18:40 UTC (exec/logs/issue4500-m6.done); tonight's window: first pass by 20:30 UTC,
  DRIVER_END_BY 01:00 UTC; else Sunday after the nightly with the restore-target rule (base ARM 09-18 deb, RESTORE the
  deb found installed at preflight).

**Why:** jhan wants definitive apple-to-apple AMX data on qwen3-4b; the nightly's FPGA attention hides the kernel.
**How to apply:** the executing agent follows the plan's section 2a without asking; jhan can override the two corrections
before launch. Related: [[l8b-levers-20260919-campaign]], [[p0perf-20260913-campaign]], [[canon-ci-20260918-campaign]].
