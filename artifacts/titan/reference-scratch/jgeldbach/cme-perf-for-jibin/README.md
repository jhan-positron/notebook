# CME performance on Asimov: a starter package

> **For your agent (read first):**
> 1. Read this README, then the files below in order.
> 2. Install the agent rules from `/scratch/jgeldbach/env-setup-general/AGENTS.md` as `~/dev/AGENTS.md`
>    (see that folder's `README.md` for the full setup).
> 3. For any emulation run, load and follow the `palladium-emulation` skill:
>    `/scratch/jgeldbach/env-setup-general/skills/palladium-emulation/SKILL.md`
>    (install steps in `/scratch/jgeldbach/env-setup-general/04-emulation.md`).
>    Every launch needs Jibin's explicit yes.
> 4. Start CME work from asimov-bench `presilicon-perf/cme-perf/` (PR stack #107 → #108 → #109,
>    branch `feature/cme-perf-pr3`), described in `03-code-and-how-to-run.md`.

For Jibin Han, from Jacob Geldbach, 2026-11-02. You're starting C1-Nano CME performance testing.
This folder collects what we've built and measured so far, and answers your Slack questions.

## Your questions, short answers

| Question | Answer | More |
|---|---|---|
| Resources: tests, docs, specs | The CME bench `asimov-bench presilicon-perf/cme-perf` (PRs #107-#109, drafts) and the DPA stress app (`dpa/stress`). Arm TRMs for the C1-SME2 (CME), the DSU and CMN-S3 are on the shared `/home` | 03, 05 |
| What does "prefetching" mean here? | The CME loads data into its own caches ahead of use. A hardware prefetcher does almost all of it; the `RPRFM` instruction adds a software hint. Feeding the CMEs from SMS this way beat having DMA stage data in OCM first | 01 |
| Did you test on the Asimov emulator? | Yes. Every result here is from Cadence Palladium Z3 at GA13 (Cadence cloud), on RTL release `a10181848` | 02, 04 |
| One emulator for everyone, or another one? | One shared pool. GA13 has two executor hosts, `ga13pd01` and `ga13pd02`, with 18 boards each. Each run takes 3 to 18 boards, depending on the image. Several runs share a host while boards and licences last. Spokane also has a 4-board Palladium. You don't need your own emulator, just your own asimov clone per parallel run | 04 |

## Files

| # | File | What's in it |
|---|---|---|
| 1 | [01-what-prefetching-means.md](01-what-prefetching-means.md) | The CME data path (CME → DSU L3 → CMN mesh → HN-S → SMS or OCM), hardware prefetcher vs `RPRFM`, the control register, and SMS-fed vs OCM-fed |
| 2 | [02-results-so-far.md](02-results-so-far.md) | Measured CME numbers with GA13 run IDs: load latency, stream bandwidth, prefetch, five CMEs at once, one GDN decode example, and things that didn't help |
| 3 | [03-code-and-how-to-run.md](03-code-and-how-to-run.md) | The cme-perf bench (modes, row sets, Palladium boot, checker), the stress app, and how a run is built, launched and checked |
| 4 | [04-emulation-resources.md](04-emulation-resources.md) | GA13 hosts and boards, image sizes, licences, sharing rules, Spokane |
| 5 | [05-docs-and-specs.md](05-docs-and-specs.md) | Which Asimov docs govern (section 1.2), and where the Arm TRMs are, with the sections that matter |

## Where things live

| What | Path (readable from agentsrv, alpha and sw-dev-01) |
|---|---|
| This package | `/scratch/jgeldbach/cme-perf-for-jibin/` |
| Environment setup for agents | `/scratch/jgeldbach/env-setup-general/` |
| Raw Palladium run logs and reports | `/scratch/jgeldbach/asimov-dpa-stress/palladium/<package>/results/` (folder per run, listed in 02) |
| Earlier GDN-on-CME write-up with raw logs | `/scratch/jgeldbach/gdn-cme-results-2026-10-23/` |
| Arm manuals | `/home/jgeldbach/dev/docs/ARM/ARM_IP/` (see 05) |

Numbers in 02 were rechecked against the raw UART logs on 2026-11-02, except where 02 says otherwise.

## Who to ask

| Topic | Person |
|---|---|
| Anything in this package, the cme-perf bench, the runs | Jacob Geldbach |
| The emulation skill | Dan McDermott |
| Emulation release images (Slack #emulation) | Alexey |
| GA13 chamber account (Slack #positron-cadence-emulation) | ask in the channel |
| GDN kernels and the CME stage design | Bill |
