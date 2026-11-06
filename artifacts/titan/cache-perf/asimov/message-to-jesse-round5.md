# Draft to Jesse (round five: run 6, boots F1 and F2)

Run 6 is on main at 0c190a1 (cache-mem-perf, pushed today). It improves test overheadabout the
SMSTART/SMSTOP cost per CME call: every CME kernel now reads the counter inside the streaming span,
so each --cme row prints its in-span time next to the bracket time, and the bandwidth test gets a
single-call form (all passes of a rep in one assembly call, --asm-passes) with two controls
(--no-fold read, --dsb-st write). Nothing outside the --cme rows changed; the core phases print the
same rows as before.

Two asks, both on 0c190a1, in this order:

1. `make cme_test && ./cme_test` once on an SME2 machine before the script. It checks the new
   kernels (single-call forms, the DSB ST write, the no-fold read, the span stamps and their
   running sum). Please put its exit status and its last line in the README. I built it on the
   CRB and on an x86 host, but no Arm run of the new kernels has happened yet.

2. Two boots, each with its own --out directory and the README naming the boot:
   - **F1, L3 on, prefetchers on**: boot E's firmware (SCP 0.48.0-nopcie-l3.1, TF-A 0.35.0),
     `sh run_all.sh`. Chip time about 4.0 s est. (run 3's 2.918 s plus the new phase F2's 1.0 s);
     this also gives the core phases their L3-on rows, which boot E did not run. If chip time is
     short, `sh run_cme.sh` alone: about 2.4 s est.
   - **F2, L3 on, prefetchers off**: boot E's SCP with boot B's TF-A (0.35.0-pfoff.1),
     `sh run_cme.sh`, about 2.4 s est. Same readbacks in the README as boot B
     (IMP_CPUECTLR_EL1 bit 48, IMP_CMECFG_EL1 bit 28, IMP_CLUSTERPWRSTAT_EL1 0x70).

Still open from my boot E message: what delay is the memory model behind the home node configured
with? Boot B's address-order 8 MiB chain (52.762 ns) equals the random one (52.739 ns), so the
memory leg looks like a fixed delay of about 29 ns after the 24 ns home-node step; a configured
value would let me say so with a source.

No hurry on the queue; nothing here launches or changes the platform on my side.
