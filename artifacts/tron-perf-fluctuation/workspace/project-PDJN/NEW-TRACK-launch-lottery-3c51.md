# PDJN new track — "the lottery is drawn at launch": localize the draw itself
Proposed 2026-08-11 · venue: Bill's delphi-3c51 (2 days) · author: Claude (Fable 5)

## Premise (from the combined record)
Everything measured says the per-launch speed level is FIXED by the time decoding starts:
draws are independent (no draw-to-draw memory), warm/fresh relaunches re-roll identically,
tokens are bit-identical between fast and slow draws, and the carrier is a per-launch
DEVICE ROUND-TRIP LATENCY LEVEL (deep-dive: per-layer K/V-arrival waits, uniform across
layers/cards). Both prior tracks study steady-state decode. Nobody has studied the LAUNCH.

## Distinctness from the other tracks
- Not geometry/CV screening (suspended PDJN track): no model/card matrices.
- Not steady-state attribution (deep-dive track): no perf/vtune on running decode.
- Studies the INITIALIZATION WINDOW: when, during engine bring-up, does the machine's
  state acquire the launch's speed level, and which init step sets it.

## Three legs
1. INIT-TIMELINE ORACLE — run the memory-latency bystander (dramprobe, ~1 ms-resolution
   timeline mode to be added) ACROSS engine startup. If the machine-visible state (loaded
   latency level) shifts at a specific moment of init, that timestamp identifies the
   init phase that draws the ticket. Correlate probe timeline with the engine log
   timeline (device reset, ring setup, DMA map, weight load, worker spawn, first forward).
2. TRON-FREE MINIMAL REPRODUCER ("launch-probe") — a small standalone program on the
   driver layer: open devices → DMA arena → submit small work-requests in a loop →
   measure round-trip latency distribution; relaunch hundreds of times. If the per-launch
   level reproduces without tron, the search space collapses to device bring-up / DMA-ring
   / PCIe state, with ~500 launches/hour of statistics (vs ~30 draws/hour today). This is
   the never-executed S2-L3 rung of the old ledger's sim ladder.
3. INIT-STEP BISECTION — with 1+2, toggle/reorder init steps (reset vs no-reset, ring
   sizes, mapping order, worker spawn order, card subset) to isolate the step whose
   outcome sets the level; then read that step's code/registers for the actual mechanism.

## Why 3c51 works for this
Same hardware as 3bda (8 cards, same PCI layout 10/13/38/3b+90/93/b9/bc, vendor 8200:0011,
Xeon 6962P/288t, 1G hugepages), NO nightly/CI duties, no production serving — free rein
for hundreds of launches without window constraints. First step tomorrow: confirm the
phenomenon exists on 3c51 (one qwen3-4b-tp4 screen, ~30 min, using deep-dive's exact
recipe for comparability) before investing in the program.

## Day-0 prep state (2026-08-11, no FPGA interaction per owner instruction)
DONE: connectivity verified (jhan@delphi-3c51); hardware inventoried (snapshot at
/scratch/jhan/pdjn-3c51/snapshots/prep-20260811T1636Z); /scratch + /home are the SAME NFS
filer as 3bda → all pdjn tools/scripts/binaries already visible; workspace
/scratch/jhan/pdjn-3c51/ created; dramprobe built from shared f3kit source and sanity-run
(idle latency ~181 ns — vs 3bda's 127 ns floor; first machine-difference note, park it).
Machine profile: kernel 6.8.0-136, tron pkg 2026.07.20-distributed-dice (older than
3bda's), platformd active but nothing serving, dice inactive, no actions-runner units,
hugepages 512 (480 free), Bill has 7 (idle-looking) sessions.

## Blockers — status 2026-08-11 evening
1. ~~Passwordless sudo~~ RESOLVED (verified; numactl+msr-tools installed, perf works,
   privileged snapshot taken: prep-priv-20260811T1723Z).
2. Exclusive use CONFIRMED by owner; awaiting the go-signal time before any card use.
3. Still nice-to-have from Bill: 3c51 fluctuation history; machine quirks.
Machine-difference ledger vs 3bda (watch these if behavior differs): BIOS 92011600/04-09
vs 92011500/03-27 · tron pkg 2026.07.20-distributed-dice vs 2026.08.09 · idle DRAM
latency 181 vs 127 ns (dramprobe, single measurement each).

## Tomorrow's plan (with cards, pending blockers)
09:00Z confirm phenomenon (qwen3-4b-tp4 screen, deep-dive recipe) →
if present: leg 1 (probe-across-init timeline, ~20 launches) → leg 2 skeleton
(launch-probe program against 1 card) → evening: first bisection candidates.
If absent on 3c51: THAT is itself a major result — diff the two machines' configs
(tron pkg version first: 07-20 vs 08-09) and hunt the difference.
