# Sequential reads of a large buffer run faster with the DSU L3 on: the picture and how to prove it

2026-11-09. Jibin Han, with Claude. Sources: asimov-c1nano-perf.html section 2.3, follow-up-run-plan.md section 14, codex review rounds 17 to 27.

**Short version.** With the L3 of CPU 2's cluster in full mode, one core's sequential read of a 32 MiB buffer runs 2.7 times faster than with the L3 in snoop-filter-only mode, although the buffer is 128 times the L3 and every line still comes from memory once per pass. Jibin's picture: the core's prefetchers run ahead into the L3 many lines at a time, so the core rarely waits; with the L3 off they can run ahead only into L1 and L2, and the core catches up and waits. The open question is how to show that this, and not a change in how the cluster handles the same prefetch requests, is what caused the gain.

## Words used here

- **DSU**: the DynamIQ Shared Unit, the cluster of two cores (CPUs 2 and 3 for CPU 2) with their shared L2 (128 KiB) and L3 (256 KiB). L1 data is 32 KiB per core.
- **L3 full mode / snoop-filter-only mode**: with the L3 RAM on, the L3 holds data. In snoop-filter-only mode the L3 RAM holds no data and the DSU keeps only the snoop filter (its record of which lines the cores hold); every L2 miss goes to the mesh. Run 3 ran CPUs 2 to 9 in snoop-filter-only mode; boots E and F1 ran them in full mode (register IMP_CLUSTERPWRSTAT_EL1 read 0x70).
- **Sequential read**: bandwidth.c's read kernel, eight 32-byte load pairs per 256 bytes in address order, independent loads, which the hardware prefetcher follows.
- **Random read chain**: latency.c's chase, one load per 64-byte line in a random cycle, each address taken from the previous load, so one load is in flight at a time.
- **Prefetcher**: one of the core's hardware data prefetchers. The C1-Nano has several, and each chooses the cache its linefills go to, L1, L2 or L3 [C1-Nano TRM 107753, Hardware data prefetcher]. The DSU TRM describes no prefetcher of the DSU's own.
- **In flight**: a read issued and not yet returned.
- **est.**: an estimate, not a measurement.

## 1. What was measured

| Row, CPU 2, best rep | L3 off | L3 on | Ratio |
|---|---|---|---|
| sequential read 32 MiB, GB/s (run 3 / F1) | 9.2 | 24.6 | 2.68 |
| sequential read 2 MiB, GB/s (run 3 / F1) | 9.3 | 25.0 | 2.69 |
| sequential read 32 MiB, GB/s (boot C / boot E, one build) | 9.2 | 24.5 | 2.67 |
| write 32 MiB, GB/s (run 3 / F1) | 32.0 | 32.0 | 1.00 |
| random read chain 32 MiB, ns per load (run 3 / F1) | 52.2 | 52.2 | 1.00 |
| random read chain 2 MiB, ns per load (run 3 / F1) | 24.1 | 23.7 | 1.02 |

Counters on the 32 MiB sequential read, per 64-byte line, boots C and E (run 3's and F1's bandwidth rows carry no core counters):

| Event | L3 off (boot C) | L3 on (boot E) |
|---|---|---|
| L1 refills | 1.00 | 1.00 |
| L1 refills requested by a hardware prefetcher | 1.00 | 1.00 |
| L2 refills | 1.00 | 1.00 |
| L3 read refills from outside the cluster (0xA2) | 0.0004 | 0.0000 |

Mesh counters: F1's counted 2 MiB read put 0.975 times run 3's requests on the five home nodes, over the whole command [cmn-counts.csv of 011 and 004].

What these say:
- Every line of the stream is filled into L2 and L1 once per pass on both boots, and the prefetcher requested every one of those fills. The core's own loads hit L1 on both boots.
- The number of requests reaching the home nodes is about the same on both boots. The L3 did not save traffic from memory: a 32 MiB buffer is 128 times the L3, so a line is gone before the next pass reaches it.
- One DRAM load costs 52.2 ns on both boots (the chain). The stream spends 7.0 ns per line with the L3 off and 2.6 ns with it on. Divided into the chain's latency, that is about 7.5 lines in flight est. against about 20 est. These two numbers are derived from the rates, not counted.
- 0xA2 reads about zero on both boots, although every line came from outside on boot C. So 0xA2 did not count this stream's fills on boot C. Whether that is because it skips prefetch fills in general is an interpretation, not a measurement.

The L3-sized chains (192 to 384 KiB) are a different case: they got 1.8 to 2.1 times faster because the L3 holds the whole chain, and 0xA2 fell from 0.5 to 0.9 per load to about 0. That is a measurement, and it is not the question of this note.

## 2. Jibin's picture

The question is why a stream whose lines all come from memory runs 2.7 times faster when the L3 holds data.

- The prefetchers choose where each linefill lands. With the L3 RAM on, they can aim linefills at the L3.
- With the L3 on, the prefetch stream runs ahead of the core into the L3, many lines at a time. The core's loads then hit L1, L2 or L3 and rarely wait.
- With the L3 off, the stream can run ahead only into L1 and L2, fewer lines at a time. The core catches up with the prefetcher and waits on fills that have not landed.
- Every line still comes from the SLC or DRAM once per pass on both boots. What the L3 mode changes is when each memory read is issued and how many are outstanding together, not how many there are.

This picture accounts for every measurement above: the same fills per line, about the same requests at the home nodes, the unchanged random chains (one load in flight, nothing to run ahead), the unchanged writes (posted stores already overlap), and the 2.7 times faster streams at footprints the L3 cannot hold. Nothing on disk contradicts it. Codex (round 23) called it the working explanation.

