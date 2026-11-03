# 01: What "prefetching" means here

Short version: a CME doesn't wait for a DMA engine to bring its data closer. It loads the data from
memory into its own caches ahead of use. Almost all of that is done by the CME's **hardware
prefetcher**, which spots the access stream. The **`RPRFM`** instruction in the kernel adds a software
hint. In our runs, CMEs prefetching straight from SMS (DRAM) were as fast as or faster than the
alternative, where DMA first copies the data into OCM (on-chip memory) and the CMEs read it there.

## The data path

One hemisphere has 5 DSU clusters. Each cluster has 2 C1 cores and one CME (the Arm C1-SME2 unit),
which both cores share. CPUs 2d and 2d + 1 share the CME of DSU d, so the benches use CPUs 0, 2, 4,
6 and 8 to drive the five CMEs.

```
CME (L1D 64 KB, hardware prefetcher)
  -> DSU L3 (shared by the cluster's 2 cores and its CME)
    -> CMN-S3 mesh
      -> HN-S home node (5 per hemisphere): SLC slice + snoop filter; 4 of its 16 SLC ways locked as OCM
        -> SMS DRAM (behind every HN-S; addresses hashed over all five)
        or OCM (256 KiB window per HN-S, no memory behind it)
```

| Level | Size, per our setup | Dependent-load latency from the CME (#3969) |
|---|---|---|
| CME L1D | 64 KB, 4-way, 64 B lines (C1-SME2 TRM, "L1 data memory system") | 21.6 ns |
| DSU L3 | 256 KiB (the bench's notes give L1 + L3 = 320 KiB) | 26.6 ns |
| OCM (one HN-S's locked SLC ways) | 256 KiB per HN-S at `0xE000_0000 + n × 1 MiB`, n = 0-4; 1.25 MiB in all | 34.8 ns idle; 46.1 ns with 3 other CMEs streaming the same window |
| SLC | 5 MiB over the 5 HN-S (16 ways × 64 KiB each) | not measured alone |
| SMS DRAM | Linux RAM, hashed over all 5 HN-S | about 300-390 CME cycles per read under load (02) |

- SCP firmware locks the OCM ways at boot (scp-v0.40.0, profile `cold-boot-ocm-w4`). OCM window n
  belongs to HN-S n, the home node nearest DSU n.
- A CME read is a cacheable CHI read. The HN-S for the address serves it from its SLC, or from SMS on
  a miss. CME requests are QoS 14 out of reset (POCQ class 1); the DMA engines are QoS 0 (class 3).

## Software prefetch vs the hardware prefetcher

| | Software prefetch | Hardware prefetcher |
|---|---|---|
| What issues it | An instruction in the kernel | The CME's load/store unit, from the access pattern (VA, part of the PC and opcode); 128 training streams |
| Instructions | Only `RPRFM` (range prefetch) runs in streaming mode, at most 1024 B per instruction. `PRFM` and `PRFB/H/W/D` are NOPs in streaming SVE mode (C1-SME2 TRM §6.3) | none |
| Where lines land | the CME L1 | the CME L1 and the DSU L3 (TRM §6.3, "Hardware data prefetcher") |
| What we measured | Bench (#4045): `RPRFM` 1 KiB ahead saved 7-10 % per GDN block from SMS or OCM and about 7 % on a plain stream; nothing on SPM (uncached). Stress app (#4323): L1 refills due to software prefetch (`0x32B1`) were 0; on/off/further ahead gave the same rate | Accuracy 0.98-0.99, coverage 0.97-0.98, timeliness 0.81-0.87 (#4422, #4423). It fetches about 1.02 lines per line used, and about 18 % of first uses hit a line whose prefetch is still in flight |

The two `RPRFM` results don't agree, and we haven't settled why. The bench rows ran one user per
call with the state cleaned from the caches after each call. The stress app streams continuously
over many slots.

Prefetcher metrics follow the Arm C1-SME2 telemetry spec (109821, §5.15):

| Metric | Formula (CME PMU events) |
|---|---|
| Accuracy | (`0x3274` + `0x32AD`) / `0x32B2` |
| Coverage | (`0x3274` + `0x32AD`) / (`0x3274` + `0x32AD` + `0x3280` + `0x3281`) |
| Timeliness | `0x3274` / (`0x3274` + `0x32AD`) |

`0x3274` = demand first hit on a hardware-prefetched line; `0x32AD` = first hit in the line-fill
buffer (prefetch still in flight); `0x32B2` = L1 refills by the hardware prefetcher; `0x3280`/`0x3281`
= L1 refills on read/write.

A C1 core (not the CME) can also prefetch for the CME with `PRFM PLDL3KEEP` into the shared DSU L3.
We tried that as a "helper core". It placed lines in the L3 but made the CME slower (#4180, see 02).

## Controls

**`IMP_CMECFG_EL1`** (`S3_0_C15_C11_4`, C1-SME2 TRM appendix A.1.5):

| Field | Bits | Reset | Meaning |
|---|---|---|---|
| `PF_DISABLE` | [28] | 0 | 1 turns the hardware prefetcher off |
| `SW_PF_ADV` | [33:32] | `0b10` | Prefetcher advance budget, set as the memory latency it assumes: `00` 90, `01` 150, `10` 200, `11` 250 cycles |

- EL0 can't access it. EL1 and EL2 accesses trap unless EL3 firmware sets `ACTLR_EL3.CMEEN` (and
  `ACTLR_EL2.CMEEN` when EL2 is enabled). The stock asimov-tfa BL31 we ran didn't set `CMEEN`, so
  using this register needs a small firmware change. We haven't checked current main.
- We haven't run with either field changed. Inference, untested: SMS-fed CME reads stayed outstanding
  for 296-392 CME cycles (#4480), above the 200-cycle default budget, so `SW_PF_ADV = 0b11` is a
  natural experiment.
- The same register holds the CME arbitration fields (fair-share between the two cores), which
  matter when both cores of a cluster use the CME.

**DSU `IMP_CLUSTERECTLR_EL1`** (DSU TRM A.1.5): `DCC` [45:44] (reset `0b11`) controls whether clean
evictions carry data to the CMN. Setting `0b00` (dataless `Evict`) made the CMEs slower (#4187, see 02).

**HN-S `cmn_hns_cfg_ctl` bit 47 `rd_migrate_on_sfmiss`** (CMN-S3 TRM 8.3.9.7, reset 1). It changes
how a read is served from the SLC on a snoop-filter miss. It mattered for OCM-fed runs (02). SCP sets
it per node at boot.

## SMS-fed vs OCM-fed

| | SMS-fed | OCM-fed |
|---|---|---|
| How | Each CME prefetches its state straight from SMS through the hashed HN-S | DMA engines (4 SPM-DMA plus one DMA-357) fill a ring of slots in each CME's OCM window; the CME prefetches from OCM |
| Write path | Results go back to SMS (Normal non-cacheable, out of place) | the same |
| Best measured (GDN example, five CMEs) | 175.6 K tok/s (#4480) | 175.1 K tok/s, only with bit 47 set per node (#4478) |
| Why OCM-fed struggles | n/a | Each OCM HN-S takes the DMA fill writes, the CME reads and a fifth of all result writes. DMA writes into OCM must be cacheable (OCM has no memory behind it), and the HN-S retries many of them |

That's why Jacob's Slack reply says the CMEs prefetch from SMS: DMA into OCM was the slow part
(56.3 GB/s for 4 SPM-DMA engines with nothing else running, #4032), while five CMEs streaming from
SMS together reach about 96 GB/s (#4065).
