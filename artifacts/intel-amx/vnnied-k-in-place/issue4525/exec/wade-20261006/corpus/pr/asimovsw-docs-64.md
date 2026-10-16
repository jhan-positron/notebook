# positron-ai/asimovsw-docs PR #64: spec v0.1.4: Silver/Gold split, Figure 5 on Gold ABI v2, PR #118 counter-model note
author: jeremyconner1975  created: 2026-09-24  state: open  merged: None  head: 3b1f9ae87bb91e0a763cfaa2190d12b5442d8692  base: main  url: https://github.com/positron-ai/asimovsw-docs/pull/64
commits: 2
  - spec v0.1.4: add the Silver/Gold split, redraw Figure 5 to ABI v2, add the PR #118 counter note
  - spec: address PR #64 review — hemisphere/loop caveats, 'erased' gloss, doc-retirement plan
files (1):
  - docs/asimov_sw_architecture_spec.md (+97 -44)

## PR body (as it is now; may have been edited after the review)

Brings the Asimov SW Architecture Spec current with the Silver/Gold work in `asimov-sw`. Every in-review citation carries its PR number and is labeled as pending merge + Interface-Spec confirmation; nothing unmerged is stated as settled.

## What's in it
- **§9 + §2 glossary: the Silver / Gold split** (per asimov-sw [#152](https://github.com/positron-ai/asimov-sw/pull/152), in review): Silver = the command language of the abstract machine, authored/verified in Lean, no loops/branches, one-hemisphere scope; Gold = the instruction language the C1-Nano decodes; certified resolution + lowering translates 1:1. Explicit statement that production placement is unchanged (Phoenix generates, C1 executes) and that [#169](https://github.com/positron-ai/asimov-sw/pull/169)'s Silver interpreter is a host-side *verification* model, not an execution venue.
- **§9.1 authority chain updated**: executing authority today = Gold ABI v2 (`asimov-interpreter` main, pinned to asimov-sw `8808746`, v1 rejected); successor normative docs = `silver-language.md` + `gold-abi.md` with Lean modules as canonical syntax (`Cmd` = Silver, `Insn` = Gold). The Haskell model / GOLD_V1 encoding doc are no longer the stated authority.
- **§9.1 delivery vocabulary**: environment image (per-pass, no `.program` entries), `fwd_pass_plan` demoted to a private runtime materialization, out-of-band program publication (THUNK→PROGRAM magic handshake), future CBOR compiler-artifact bundle — with the **dangling `compiler-artifact-cbor.md` reference flagged**.
- **Figure 5 + §9.2 redrawn to ABI v2** (closes the v0.1.3 §16 row): 28 instructions (5 fused SPA + 23 direct), one trusted mode with admission-then-abort, erased binding classes with slot 0 unbound, depth-8 calls with legal cycles (no cycle detection), `FAIL` as the only execution fault, `runtime/moe` layer beside the interpreter.
- **§13.2 counter-model NOTE** (asimov-sw [#118](https://github.com/positron-ai/asimov-sw/pull/118), changes-requested): 19-bit internal / 16- and 32-bit published windows, N−1 predecessor thresholds with strict wrap-aware compare, CPS/SAL divergence at 2^18, C2C tx/rx asymmetry, per-counter visibility limits. Flags §13.2's current numbers as superseded-pending-merge; wholesale rewrite waits for #118.
- **§16 rows updated**: encoding shape decided (16-bit tag + statically-known variable payload); family-rename follow-up gated on the Silver stack (#113 gates; #117 approved); new row for the unfinished compiler-artifact/loader path.

## Sequencing notes
- The §9.1 command-family list keeps v0.1 names with a rename NOTE — the rewrite to the Silver `Cmd` inventory waits for #117–#125 to merge.
- No overlap with #45/#58 (§14/observability) — this PR doesn't touch §14.

## Wade's reviews (summary verdicts)

- review 5306324349 COMMENTED at 2026-09-24T15:10 commit c57b74863bdea9be8872eeeb6f002648a6cb942f: (no text)
- review 5306413738 COMMENTED at 2026-09-24T15:17 commit c57b74863bdea9be8872eeeb6f002648a6cb942f: (no text)
- review 5306442328 COMMENTED at 2026-09-24T15:20 commit c57b74863bdea9be8872eeeb6f002648a6cb942f: (no text)
- review 5344169503 APPROVED at 2026-09-28T20:22 commit 3b1f9ae87bb91e0a763cfaa2190d12b5442d8692: (no text)

## Wade's conversation comments

### issue-comment 5818393161 at 2026-09-24T16:50
> Referencing moving targets (i.e. in-progress PRs) in a specification document feels bad.

I sort of had the same gut reaction, but until things settle more I think we're basically treating *this* document as a moving target too ;p? As long as someone keeps on top of the updates/correlations, I can sorta see why he's doing this.


## Wade's inline comments

### inline 4095187050 at 2026-09-24T15:10  docs/asimov_sw_architecture_spec.md:486 (commit c57b74863b)
```diff
@@ -477,16 +480,32 @@ After the final unembedding matmul, the logit vectors — one per batched token
 
 GOLD is the bytecode language Phoenix uses to drive Asimov. It has two halves: the **language** itself — the opcode set, encoding, and semantics — and the **interpreter** that executes it on the C1-Nano ARMs.
 
+**The Silver / Gold split (in review).** The successor specification (`asimov-sw` [PR #152](https://github.com/positron-ai/asimov-sw/pull/152), unmerged) splits this contract into two languages plus a translation step.
+**Silver** is the command language. A Silver command specifies one operation of the Silver abstract machine: submit a
+hardware command, control execution, update the environment, wait for progress, start a DMA transfer, or change
+configuration. Silver has no loop or branch command. It models one hemisphere (C2C egress excepted). Silver programs
```
WADE: is this meant to say "C2C egress accepted"? Or perhaps "C2C egress is the exception"? I would imagine both are true.
  reply by jeremyconner1975 (2026-09-28): Fixed in 3b1f9ae — both readings were intended. The text now uses the source doc's own phrasing: Silver models one hemisphere; C2C egress is the exception because its port mask can select links from both hemispheres. (Posted by Claude on Jeremy's behalf.)

### inline 4095262504 at 2026-09-24T15:17  docs/asimov_sw_architecture_spec.md:510 (commit 3b1f9ae87b)
```diff
[... hunk truncated]
+**Silver** is the command language. A Silver command specifies one operation of the Silver abstract machine: submit a
+hardware command, control execution, update the environment, wait for progress, start a DMA transfer, or change
+configuration. Silver has no loop or branch command. It models one hemisphere (C2C egress excepted). Silver programs
+are authored and verified in Lean. **Gold** is the instruction language: the byte stream the C1-Nano control
+processor decodes and executes. A certified resolution and lowering step translates a Silver workload to a Gold
+workload; the command-to-instruction mapping is 1:1. The successor spec's vocabulary rule: `Cmd.foo` names Silver,
+`Insn.foo` names Gold, and hardware command words are shared representations, not a third language. Production
+placement does not change: Phoenix generates, the C1-Nano executes. A separate design note (`asimov-sw` PR #169)
+proposes a host-side Lean *verification* interpreter for Silver — a validation model checked against RTL, not an
+execution venue.
+
 The design principle that runs through both halves: **complexity lives above the API line.** The Phoenix-side GOLD generator inside Alchemist knows the model, the hardware state, every command field, every memory's contents, every counter value. The on-device interpreter knows none of those things — it reads GOLD pieces, pokes MMIO addresses, and waits on FSR values when told to.
 
 ### 9.1 The GOLD Language
 
-GOLD is built on the opcode set in [`docs/gold.md`](gold.md). That document is the prose specification. The
-authoritative definition of the language is the `Cmd` GADT in
-[`Asimov.Gold.Ast`](https://github.com/positron-ai/asimov-sw/blob/main/asimov-model/src/Asimov/Gold/Ast.hs) (repo
-`asimov-sw`). The document
+GOLD is built on the opcode set in [`docs/gold.md`](gold.md). That document is the prose specification. The executing
+authority today is Gold ABI v2: the `asimov-interpreter` repo implements it and pins its wire authority to
+`asimov-sw` commit `8808746`; v1 images are rejected. The in-review successor authority (`asimov-sw` PR #152) is
+[`asimov-lean/docs/silver-language.md`](https://github.com/positron-ai/asimov-sw/blob/bgamari/gold-spec-2/asimov-lean/docs/silver-language.md)
+plus
+[`asimov-lean/docs/gold-abi.md`](https://github.com/positron-ai/asimov-sw/blob/bgamari/gold-spec-2/asimov-lean/docs/gold-abi.md),
+with the Lean modules as canonical syntax: `Cmd` in `Asimov.Silver.Ast` (Silver) and `Insn` in
+`Asimov.SilverGold.Program` (Gold). The older Haskell model (`Asimov.Gold.Ast`) and
 [`gold-command-encoding.md`](https://github.com/positron-ai/asimov-sw/blob/main/asimov-model/docs/gold-command-encoding.md)
-in the same repo specifies the GOLD_V1 wire format.
+remain on `asimov-sw` main but are no longer the stated authority.
```
WADE: what is our retirement plan for these older docs? It's confusing (esp. for newer folks) to come across multiple specs in multiple locations, and then add to that the in-flight / uncommitted docs in branches of this repo (https://github.com/positron-ai/asimovsw-docs/blob/bgamari-gold-spec/docs/gold-spec/gold.md, and https://github.com/positron-ai/asimovsw-docs/blob/add-gold-doc/docs/GOLD.md) which early adopters were told to reference as well, but apparently are not intended to actually drop anywhere?
  reply by jeremyconner1975 (2026-09-28): Great question — 3b1f9ae adds a §16 Docs row with the retirement plan: when asimov-sw #152 merges, docs/gold.md becomes a tombstone pointer (the docs/decisions.md pattern), PR #34 closes and its branch is deleted, and the PR #24 extraction row executes and that branch is deleted too. The two branch drafts you linked are exactly the targets. Until then, §3's references table is the single index for what's authoritative. (Posted by Claude on Jeremy's behalf.)

### inline 4095287201 at 2026-09-24T15:20  docs/asimov_sw_architecture_spec.md:640 (commit c57b74863b)
```diff
@@ -601,47 +637,47 @@ The interpreter's runtime state is small:
 
 - A program counter: the instruction offset in the current program. A program ends at the end of its code span. There
   is no HALT command and no return command.
-- The per-pass Plan: a typed binding store (progress counts, integers, addresses, SMS pointers, attention contexts).
-  `Assign` and `ReadProgressCounter` write bindings; command operands read them. There is no separate register file.
-- A bounded call structure: `Call` invokes a preloaded program by SMS address, with a depth limit and cycle
-  detection.
+- The per-pass plan: four erased runtime binding classes (64-bit scalars, 64-bit addresses, 32-bit progress counts,
```
WADE: 'erased'?
  reply by jeremyconner1975 (2026-09-28): Fixed in 3b1f9ae — spelled out now: the exact semantic types are erased to four storage classes at this level; exact-type evidence belongs to the producer / admission layer (gold-abi.md's vocabulary). (Posted by Claude on Jeremy's behalf.)
