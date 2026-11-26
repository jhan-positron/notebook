---
name: lint-tla-lean-tron-page-2026-11-22
description: "Page and example files that explain \"correction -> lint rule\", TLA+ model checking and Lean proofs on TRON code (capture_controller, chunk_evenly); lists what was machine-checked and what was not"
metadata:
  node_type: memory
  type: reference
  originSessionId: 9e4b2a33-7940-4569-b4c2-5871971b6be0
  modified: 2026-11-23T00:15:38.549Z
---

Page: `~/workspace/random/from-claude/lint-tla-lean-on-tron.html`. Example files and saved outputs: `~/workspace/random/from-claude/lint-tla-lean-on-tron/`. Written 2026-11-22 from tron `origin/main` 7eddde7895, for jhan's questions about Lauren Tan's talk "All Code Is Slop (Except Mine)" (AI Engineer CODE 2026).

- Lint: `lint-example/lint-source-rules.py` (rule table + baseline; 6 old `#if 0` blocks on that commit), `lint-env-vars-documented.py` (65 getenv names, 0 missing from jhan's README.env-vars.md draft), a PostToolUse hook script, `wiring.diff` for lefthook.yml / flake.nix / GNUmakefile, and `lesson-to-lint/SKILL.md`. Nothing is installed or applied.
- Model check: `capture_slot_check.py` models `capture_controller` (src/pos/trace_capture.cpp): 32 states, all rules pass, 3 seeded bugs caught. `CaptureSlot.tla` is the same model but was NOT run through TLC.
- Proof: `ChunkCount.lean` (two `omega` theorems on the chunk count, model.hpp:246) was NOT checked by Lean. A range test to n = 1,000,000 passed.
- Hypothesis, not confirmed on TRON: `chunk_evenly` returns a chunk over 128 token jobs when `max_minibatches` >= 2 (first input: groups 1 + 249, max_minibatches 2 -> chunks 121 and 129); the assert at model.hpp:359 would then abort. Found by running the real function text in `chunk_evenly_harness/`. Default (-1) and 1 showed no failure.

**How to apply:** for follow-ups, reuse these files. Before repeating the TLA+ or Lean claims as verified, run TLC and Lean: on 2026-11-22 the auto-mode classifier denied a background `curl` download of a JRE, tla2tools.jar and Lean 4.36.0 into the scratchpad, so ask jhan first. Related: [[tron-precommit-hook-agentsrv]], [[tron-multiuser-attention-page-2026-10-19]].
