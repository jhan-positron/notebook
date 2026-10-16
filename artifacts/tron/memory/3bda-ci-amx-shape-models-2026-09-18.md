---
name: 3bda-ci-amx-shape-models-2026-09-18
description: Which delphi-3bda nightly-CI models have the AMX 128x4 attention shape; the apt tron package had AMX compiled out until 2026-09-18 and compiled in from 2026.09.23 (deb preset sets TRON_AMX_DISPATCH ON via PR 4505)
metadata:
  type: project
---

Nightly CI on delphi-3bda (systems_test, PLATFORM_TYPE granite_rapids_72_rinzler) runs 12 perf configs over 9 base models (scripts/perf.py `configs`). Of those, 3 base models / 4 runs have head size 128 and kv_mul 4, the only shape tron's AMX kernel (`amx_attn_h128g4`) serves: llama-3.1-8b-instruct-good-tp2, mixtral-8x7b-instruct-v0.1-tp2, ingested-qwen-3-4b-instruct-2507 (tp2 and tp4). Not fitting: llama-3.2-3b (kv_mul 3), llama-3.3-70b (kv_mul 8), qwen-2.5-32b (kv_mul 5), gemma-2-9b (head 256, kv_mul 2), gpt-oss-120b (head 64, kv_mul 8), gemma-4-31b (256/2 and 512/8).

Measured 2026-09-18 on delphi-3bda: installed `tron 2026.09.18-3faba6d0` (includes the AMX merge 3fd5edaa66 of 2026-09-15) has 0 `TRON_AMX_DISABLE` / `amx_attn` strings in /opt/positron/bin/rinzler (control `TRON_NO_RTM` = 2 hits). At that time the deb preset did not set TRON_AMX_DISPATCH (CMake default OFF).

UPDATE 2026-10-05: tron PR 4505 (merged 2026-09-22) added `"TRON_AMX_DISPATCH": "ON"` to the `deb` preset [tron/CMakePresets.json:80]; `make deb` uses that preset [tron/GNUmakefile:510] and publish-deb.yml runs `make deb` on cron and on version tags. First package with kernels: tron 2026.09.23-5cf65b92 (nightly AMX row 28.25 -> 32.49 TPS, +15 %). The CMake option itself is still OFF by default [tron/CMakeLists.txt:48], so only `make deb` (or an explicit -DTRON_AMX_DISPATCH=ON) produces an AMX binary. Run-time kill switch: TRON_AMX_DISABLE=1, read once at first attention dispatch.

**Why:** jhan asked which CI models fit AMX (2026-09-18); the "fits the shape" vs "runs AMX in CI" distinction was the non-obvious part, and the package probe is a measurement not recorded in any repo.

**How to apply:** For CI numbers before 2026-09-23 the binary had AMX compiled out; from 2026-09-23 it is compiled in. Re-probe with `strings /opt/positron/bin/rinzler | grep -c TRON_AMX_DISABLE` after any packaging change. qwen-3-4b's generated plugin also forces hardware (FPGA) attention on by default, so even with AMX on, only its software remainder could use it. Related: [[3bda-rinzler-takeover-harness-2026-09-15]].
