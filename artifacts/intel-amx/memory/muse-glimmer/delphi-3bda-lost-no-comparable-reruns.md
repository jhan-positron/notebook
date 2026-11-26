---
name: delphi-3bda-lost-no-comparable-reruns
description: "jhan lost delphi-3bda for own runs (said 2026-11-19); PR 5022 benchmarks from it cannot be rerun comparably, so the provenance gap is closed by object compare on delphi-3b35"
metadata:
  node_type: memory
  type: project
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-20T01:42:02.560Z
---

jhan, 2026-11-19: "We lost delphi-3bda, cannot do apple-2-apple comparison now." delphi-3bda still runs the nightly systems test (nightly report of 2026-11-19, platformd 0.11.3), but it is not available for jhan's own runs since about 2026-11-12. All test and benchmark records of PR 5022 came from it. The record files survive on shared storage under `~/workspace/intel-AMX/exec/results/` (glimmer-20261016, glimext-20261018, glimci-20261017).

Decision for PR 5022 (point D6, 2026-11-19): "do what we can without hw testing". No benchmark rerun. The gap between the measured commit 5061623a34 and later commits is closed by an object compare of `src/tron/kernels/amx_attn.cpp`, which needs a compiler and no AMX. Scripts and the first result: `~/workspace/intel-AMX/exec/objcmp5022-20261119/` and `exec/results/objcmp5022-20261119/`. delphi-3b35 has the same compiler build as the measured binaries (Ubuntu clang 19.1.7, build string ++20250114103320+cd708029e0b2).

**Why:** throughput numbers from delphi-3b35 cannot stand next to delphi-3bda numbers (TSX off, no Speed Select setup, deep idle states on, shared machine). The measured differences are in the memory `delphi-3b35-default-server` of the parent project folder `-home-jhan-workspace-intel-AMX`.

**How to apply:** Do not plan any run on delphi-3bda. Do not offer a benchmark rerun as evidence for a PR whose numbers came from delphi-3bda. Offer the object compare, and state plainly what it does not cover. jhan confirmed on 2026-11-19 (evening) that the pass or fail unit-test runs at the final head of PR 5022 move to delphi-3b35, after John Pruitt's reboot of that machine that night, and without disturbing Brian Hamon's and John Pruitt's work on the other half of the FPGA cards. Related: [[changes-need-system-tests]].
