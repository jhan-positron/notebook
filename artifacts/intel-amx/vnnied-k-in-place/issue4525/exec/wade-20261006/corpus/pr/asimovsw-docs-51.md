# positron-ai/asimovsw-docs PR #51: spec v0.1.3: GOLD authority chain + delivery model, Figure 5 redraw, MoE doc-home repairs
author: jeremyconner1975  created: 2026-08-17  state: closed  merged: 2026-09-24  head: e7c2c00abd49c86b1746cf68cd567f668e82a1d7  base: main  url: https://github.com/positron-ai/asimovsw-docs/pull/51
commits: 4
  - spec v0.1.3: repair GOLD links, record the GOLD authority chain, log the XMS/HRA-SBSX gap
  - spec: align GOLD delivery model with gold.md — program group at load, per-pass FwdPassPlan
  - spec: redraw Figure 5 from GOLD_V1, repair MoE doc references, STE pass on new prose
  - spec: address PR #51 review; record the interpreter rewrite and Gold ABI v2
files (1):
  - docs/asimov_sw_architecture_spec.md (+87 -38)

## PR body (as it is now; may have been edited after the review)

Refresh of the Asimov SW Architecture Spec after the 2026-08 branch cleanup. Three commits, one file.

## What's in it
- **Repair the three broken GOLD references** (§3, §9.1, §9.3): they pinned `blob/bgamari-gold-spec/docs/gold.md`, which 404s since that branch moved the file. Now repo-relative links that work on main today.
- **Record the GOLD authority chain** (§3 + §9.1): prose language spec = `docs/gold.md` (here); authoritative AST = [`Asimov.Gold.Ast`](https://github.com/positron-ai/asimov-sw/blob/main/asimov-model/src/Asimov/Gold/Ast.hs) in `asimov-sw`; GOLD_V1 wire format = [`gold-command-encoding.md`](https://github.com/positron-ai/asimov-sw/blob/main/asimov-model/docs/gold-command-encoding.md).
- **Record the GOLD delivery model** (§9.1, §9.1.1, §16): programs upload as a group at model load (one per regime); each pass sends only the `FwdPassPlan` binding environment plus latents. Per `docs/gold.md` ("Program environment (forward pass plan)" / "Model lifecycle"). Per-pass regeneration is no longer the baseline.
- **Redraw Figure 5 + rewrite the §9.2 state description** from the pinned GOLD_V1 catalog and the `asimov-interpreter` code (branch `tzhou-fast-gold-interpreter`, 2026-08-21). Marked as code observations pending Interface-Spec confirmation. Notables: no WaitFsr/TraceEvent/HALT commands; typed Plan bindings instead of a register file; depth-limited native `Call` recursion; safe-mode prevalidation; trusted/prepared precompiled hot loop.
- **Repair the MoE references** (§1, §9.4, §13.4, §16): no standalone MoE design doc exists. The MoE-with-GOLD mechanics will home in the GOLD spec; the §9.1 delivery model forecloses inline per-pass expansion. New §16 Docs row tracks the extraction from PR #24 §7.1.
- **New §16 rows**: XMS / HRA-SBSX documentation gap (derive from current `cmn.sv`, pending Interface-Spec confirmation).
- New prose follows ASD-STE100 (Simplified Technical English).

## Known follow-ups (not blockers)
- **#34** moves `gold.md` → `gold-spec/gold.md`; the NOTE in §9.1 marks the links to repoint when it lands.
- **#45** (observability §14 rewrite) merges cleanly with this in either order (merge-tree verified); whoever lands second adds their revision-history row.
- **§9.2 naming**: the code says "Plan"; the spec says "FwdPassPlan" — settle during review.
- **§9.2 reconcile** with interpreter-doc content waits on the PR #24 extract-and-close decision.

## Wade's reviews (summary verdicts)

- review 5021611550 COMMENTED at 2026-08-25T16:54 commit e83e9e99e4c8da0d691543d5e7a16d3de3c6cede: (no text)
- review 5021644825 APPROVED at 2026-08-25T16:57 commit e83e9e99e4c8da0d691543d5e7a16d3de3c6cede: (no text)

## Wade's inline comments

### inline 3855274893 at 2026-08-25T16:54  docs/asimov_sw_architecture_spec.md:612 (commit e7c2c00abd)
```diff
@@ -576,38 +596,56 @@ The GOLD interpreter is the on-device runtime that executes GOLD. It runs on the
 
 The interpreter's job is to **run GOLD as fast as possible, only waiting on FSR when required**. Once commands are in the CPS / SAL FIFOs, the HW FSMs drive the systolic array at wire rate — but those FIFOs only stay full if the interpreter keeps refilling them. The interpreter is therefore **on the critical path**: slow dispatch starves the HW, and starved HW is a failure mode (see [§5.2 SW Architectural Principles](#52-sw-architectural-principles)). The estimated dispatch rate must comfortably exceed steady-state command consumption.
 
-The interpreter's complete state is small:
+The interpreter's runtime state is small:
+
+- A program counter: the instruction offset in the current program. A program ends at the end of its code span. There
+  is no HALT command and no return command.
+- The per-pass Plan: a typed binding store (progress counts, integers, addresses, SMS pointers, attention contexts).
+  `Assign` and `ReadProgressCounter` write bindings; command operands read them. There is no separate register file.
+- A bounded call structure: `Call` invokes a preloaded program by SMS address, with a depth limit and cycle
+  detection.
+- A typed hardware backend for SAL / CPS submission, DMA, and FSR waits. Command handlers do not compute MMIO
+  addresses; the platform backends own MMIO.
 
-- A program counter within the current GOLD bar
-- A small file of scratch temporaries (~16–32 64-bit registers) for indexed address computation and runtime-read values
-- A small call stack for nested function calls inside the bar
-- MMIO read / write primitives
+The dispatch framework is tag-agnostic, but the command handlers validate their payloads deeply (template fields,
+memory ranges, padding). In safe mode, the interpreter validates the full program set before it writes to hardware.
```
WADE: first mention of 'safe mode'... is there a link/reference pointer to where this is better described (e.g. how it's enabled/disabled/dictated/driven)?
  reply by jeremyconner1975 (2026-09-24): Addressed in e7c2c00. Short answer: it was never a runtime flag — the caller selected the mode per call site by entry point (`execute` = safe with full prevalidation; `execute_trusted`; `prepare_trusted` + `execute_prepared`), documented in asimov-interpreter `src/README.md` ('Execution Model') at commit 0c07152. The caption now says this. Heads-up found while answering: the 2026-08-26 interpreter rewrite collapsed all three modes into one trusted entry point and moved to Gold ABI v2 — the §9.2 
