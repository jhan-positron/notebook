Agreed, 52 ns is too good to be true for DRAM, and the data now shows why: it is not DRAM timing at all.

What the 52 ns is made of. A load that misses every cache makes two trips. The first is core to home node and
back, which the 2 MiB test measures on its own because that footprint fits in the SLC: 24 ns. The second is
home node to memory and back: 52.7 minus 24, about 29 ns. A random read on LPDDR5X costs about 50 ns inside
the chip alone (precharge, activate, column access), before the controller and wires. The CRB measures 148 ns
for a DDR5 random read, with a mesh part near 29 ns, so its memory leg is about 120 ns. A 29 ns memory leg is
shorter than one row cycle.

The test that proves it is a model. Boot B of the current run has the hardware prefetchers off. There, an
8 MiB dependent chain in address order reads 52.76 ns per load and the same chain in random order reads
52.74 ns. Real DRAM would serve the address-order chain much faster, since every row opens once and the
rest are row hits. This memory gives the same delay regardless of address order, so it has no row
behaviour: it is a fixed-delay transaction-level model (the emulator image is hemi_rtws_tlm, and asimov-bench
calls its memory "host-model DRAM"). I am asking Jesse what delay the model is configured with.

What I do with it. The DRAM latency and the DRAM bandwidth rows on the Asimov pages are labelled as the
emulator's memory model, not silicon, and I will not compare them with the CRB's DRAM rows. Everything up
to the SLC (L1, L2, the mesh, OCM at 21 to 28 ns, SLC hits at 24 ns) is the emulated chip itself and stands.
