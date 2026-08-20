# PDJN handoff — plan suspended by owner 2026-08-11 ~03:00 UTC
Author: Claude (Fable 5). Read this first on resume; detail lives in status_report/01–13.

## State of the investigation (one paragraph)
The decode-TPS per-launch fluctuation is explained by a two-ingredient model, both
demonstrated on delphi-3bda in one night (2026-08-10/11), software attention verified per
draw, replicated for the headline arm: (A) **tensor spreading beyond the model's TP
group** — a tp2 model given 4 cards has its tensors spread across both card pairs and
fluctuates (llama-8b: CV 0.28→6.92%, replication 4.80%); at exact card fit every
non-gpt-oss model meets the ≤1% target (mixtral 0.14%, llama-8b 0.28–0.48%, qwen2.5 0.69%);
(B) a **gpt-oss-specific ingredient** present even at exact fit (gpt-oss-20b-tp2 on 2
cards: CV 5.42% vs mixtral 0.139% at identical geometry). UPDATE 2026-08-11: the deep-dive
session resolved the open tension — qwen3-4b at tp1/tp2 (1/2 cards) is TIGHT (0.56%/0.44%)
and at NATIVE tp4 (4 cards) ROLLS (1.29-1.87%, u1 + pay-for-determinism, bit-identical
token streams). So "tensor spreading" is NOT required; 4-card geometry itself triggers it
for this dense model, and spreading is an amplifier. Deep-dive's perf attribution puts 46%
of the slow-draw excess in per-layer K/V-arrival waits inside the forward pass, uniform
across layers/cards → per-launch DEVICE ROUND-TRIP LATENCY LEVEL. Full matrix: status
report 13 (incl. addendum 4). llama-70b-tp4-on-3bda remains the untested cell.

## What was excluded along the way (do not re-chase)
Kernel 124→136 (one-shot boot test) · BIOS config (dmidecode diff over cold cycle) · FPGA
bitfile (constant 01.05.08.00/06-16-2026, per-draw check now automated) · cold-power state ·
host DMA-heap placement (addrmap campaign + Mantel test) · IOMMU/IOTLB (VT-d PMU, perfect
hit rates) · logits-buffer multiplicity (chunk1 A/B) · multi-user batching (u1 arm) ·
wcls/fill_logits_buffer consume path as carrier (trace mining) · adaptive worker split
(pay-for-determinism A/B — pins numerics, not perf) · thermal/pre-state (July record).
RETRACTED en route: report 05's "machine/boot-state epoch" claim (was a workload-shape
confound — ab59 ran u8/g1024/slice-4; see report 12).

## Key facts a resumer must know
1. -u N / gen-length / --slice-of are HARNESS parameters; TP is a build-time model
   variant (-m …-tpN). --slice-of N grants 8/N cards; extra cards trigger tensor spreading.
2. USE_HW_ATTN=0 env is REQUIRED for software attention on trunk (some models default
   hw-attention ON, banner "model default"); all pdjn harnesses set + capture it.
3. CI window: nightly fires ~04:00 UTC, ends ~11:30 UTC on a good night, LATER on bad
   nights (Rhys Jordan). The serving trio coming up ≠ nightly done — it starts the SOAK
   (we crashed it once, report 10). Harnesses now traffic-gate (gate_count.sh) before
   touching serving. No lock file exists yet.
4. Bit-identical tokens require -u 1 + --pay-for-determinism (verified 3/3 hashes).
   Ben's forward-pass seq marker + Mike's "data ready" instant are in the instrumented
   binary; ~61 marker traces exist (txlat + p4dab campaigns).
5. The machine is on kernel 6.8.0-124 (one-shot); the NEXT reboot auto-returns to
   6.8.0-136. The shape results hold on both kernels.
6. qwen3-30b-a3b crashes at launch on trunk 12804a81 (NaN logit at token 0, tp2+tp4) —
   unfixed as of origin/main 48056bf12; it is the many-expert MoE test vehicle.

## Where everything lives
- Status reports: /home/jhan/workspace/perf-fluctuation/project-PDJN/status_report/ (01–13;
  12–13 carry the current model; 10 is the soak incident; 05 is retracted by 12).
- Campaign data (DUT): /scratch/jhan/pdjn/<campaign>/ (journal.log, results.csv, per-draw
  runtron-command.txt / runtron-environment.txt / bitfile.txt / arm.txt). Shape arms:
  shape{B=ab59shape,C,C2,D,E,F,G}-*. Earlier: chunkab/u1/addrmap/txlat/p4dab/tokid/bare*/
  oldkernel*/preboot*/postboot*.
- Harnesses (DUT): /scratch/jhan/pdjn/tools-*/perfetto-5cat-campaign-v4.sh; tools-shape is
  parameterized via SHAPE_USERS/SHAPE_GEN/SHAPE_SLICE/SHAPE_NDEV env. All variants:
  traffic gate v3 (gate_count.sh), bitfile check, USE_HW_ATTN=0, env capture.
- Instrumented binary: /scratch/jhan/pdjn/install-txlat (sha 60ccb786…): TRON_TXLAT_FILE
  dispatch aggregates, seq marker, data-ready instant, TRON_DMA_MAP_FILE alloc logger.
  Built from worktree /scratch/jhan/pdjn-wt @ 12804a812 (models.local.yaml overlay:
  only gpt-oss 20b/120b + mixtral plugins — add models before using it for others).
  Build: PATH=/nix/var/nix/profiles/default/bin:$PATH nix develop -c
  "cmake --preset native && ninja -C gen runtron" (in the worktree).
- Snapshots: /scratch/jhan/pdjn/preboot-snapshot-20260810T1236Z + postboot-…1723Z (diffed:
  config identical over cold cycle). Owner's BIOS dump: /home/jhan/workspace/delphi-3bda/BIOS.
- Trace-mining outputs: /scratch/jhan/pdjn/mine1..6/ (mine6 = per-step seq-aligned CSVs).
- Project memory (auto-loaded next session): ~/.claude/projects/-home-jhan-workspace-
  perf-fluctuation-project-PDJN/memory/ — pdjn-project-state.md marks the suspension.

## Why suspended (owner, 2026-08-11) + my assessment
Owner's reasoning: allocating more cards than a model's built-in TP is not a valid
production use case, so the spread track has little product value. Assessment: AGREED on
product relevance — the spread configuration is synthetic. One partial dissent for the
record: the spread arm was DIAGNOSTIC, not a proposed use case — it is the largest-effect,
cheapest on/off switch for the underlying mechanism (per-launch device round-trip latency
level), and identical-per-launch-mechanism evidence now comes from three directions (spread
tp2, native tp4, gpt-oss exact-fit). If mechanism work ever stalls on valid-use-case
configs, the spread switch remains the best amplifier for instrumented experiments.

## HYPOTHETICAL resume plan (thought exercise only — owner directed no further testing on
## this track; superseded by the new direction)
1. Close the matrix's last cell: llama-3.3-70b-tp4 on 3bda (native tp4; tight would
   implicate a per-model/step-length threshold, rolling would make 4-card geometry
   sufficient for ANY model on this host).
2. Instrumented drill at native-tp4 (valid use case) rather than the spread shape:
   txlat + seq/data-ready markers on qwen3-4b-tp4 (plugin already in the instrumented
   worktree overlay's buildable set? gpt-oss-20b-tp4 works today) — decompose the
   per-launch round-trip-latency level: slot waits vs launch writes vs devlat percentiles
   fast-vs-slow launches; correlate with deep-dive's KV-wait attribution.
3. Per-launch device-init forensics at tp4: diff what init does with 4 cards vs 2
   (DMA queue/ring sizing, act_slot counts, per-card worker pinning) and log candidate
   init-time values per draw to find the per-launch discriminator.
4. gpt-oss ingredient: expert-dispatch dose response (top-k sweep if configurable;
   qwen3-30b after NaN fix as the 128-expert/top-8 point).
5. Matrix replication per ab53 + the min=max helpers A/B (predicted null).

## Suspended queue as it stood (for reference)
1. llama-3.3-70b-tp4 at 4 cards on 3bda (still untested on this host).
2. ~~qwen3-4b tp2/tp1~~ — DONE by deep-dive session (tight/tight; see addendum 4).
3. Instrumented drill on spread path.
4. Matrix replication hours-apart.
5. qwen3-30b NaN crash fix → many-expert MoE arm.
6. Optional: TRON_MIN/MAX_MAIN_HELPERS=N A/B (predicted: no CV change; report 13 addendum 3).

## Resume checklist
- Check date/CI window (02:30–11:30 UTC keep-off) and traffic-gate before any campaign.
- Verify which kernel is running (uname -r) — don't assume.
- Verify bitfile version vs 01.05.08.00/06-16-2026 (nightly may have updated it since).
- Re-read owner guidance memories: u4-vs-u1 policy, status-report run-identity rules.
