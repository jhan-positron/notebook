# 04: Emulation resources

**Your question:** "Is there another emulator, or is that the one we all use?"
**Answer:** it's one shared pool of boards, not one emulator per person. Jesse's run and yours both
draw from the same GA13 Palladium boards. Several runs can share a host at once as long as there are
free boards and licences, and each parallel run comes from its own asimov clone. Spokane has a
second, smaller Palladium.

The process authority is the `palladium-emulation` skill
(`/scratch/jgeldbach/env-setup-general/skills/palladium-emulation/SKILL.md`), with setup in
`/scratch/jgeldbach/env-setup-general/04-emulation.md`. This page is a summary, current as of 2026-11-02.

## GA13 (Cadence cloud Palladium Z3)

| Item | Value |
|---|---|
| Executor hosts | `ga13pd01`, `ga13pd02`, 18 boards each; reached through `ga13ut01` |
| Launch from | the executor host itself (the ssh hop to the other host drops the licence setting) |
| Queue | a shared SQLite FIFO inside `emu/common/scripts/run.sh`; read-only for you |
| Release images | `/projects/positronem/asimov/<release>`; use `--run-only` against a published release |
| Your work area | `/projects/positronem/work/<you>/` (the filer was 99 % full on 2026-11-02: clean up your own trees) |

**Image sizes (boards per run):**

| Image (`--test` flavour) | Boards | What's in it | Used for |
|---|---|---|---|
| `hemi_notws_tlm` | 3 | one hemisphere, SPM/TWS/SLS stubbed | stress-app CME/DMA runs (#4292-#4480) |
| `hemi_rtws_tlm` | 4 | one hemisphere, `rtws` build (not the full TWS) | the cme-perf bench (#3845-#4187) |
| `hemi_tlm` (full) | 9 | one hemisphere, full TWS | DPA stress on a full hemisphere |
| `fc_*` (e.g. `fc_nopcie_tlm`) | 18 | full chip, both hemispheres | full-chip DPA (#4293); takes a whole host |

Check the image's `MANIFEST` defines before relying on a block. Some hemi flavours tie off paths, and
an access there hangs.

**Licences.** Each run needs one `Xcelium_Single_Core` seat, and hemi images also take Cadence AVIP
features. Set
`LM_LICENSE_FILE=5280@10.1.162.54:5280@10.1.162.55:5280@10.1.162.56:5280@192.168.1.226` in the run
environment, AWS triad first (about 125 seats on each triad server; `ga13ut01` has 6). A run
started from tmux or ssh doesn't source the site profile, so set it yourself. If xmsim sits queued
on `ga13ut01`, see the skill.

**One run per clone.** Two runs from one asimov clone collide (shared build lock and xrun working
directory). For a second parallel run, use a second clone and a different `EMU_VDEBUG_PORT` (outside
8192-82xx).

**Etiquette.**
- Daytime: at most one run of yours per GA13 host. Larger or extra runs at night, finished by morning.
- `--run-only` against a published release. Never `--build` without the emulation owners' agreement
  (about 44 GB and hours per image).
- `--job-description`: plain words, the subject, the one thing varied, and what's measured (about 200
  characters).
- Stop only your own run, with SIGTERM, never `-9`.
- Launching, rebuilding, deleting on the filer and releasing a quarantined request all need your
  explicit yes. Your agent must ask.

**How runs fit together (example).** A 4-board `hemi_rtws_tlm` bench run and a 9-board `hemi_tlm` run
fit together on one 18-board host, from two clones. Two 3-board `hemi_notws_tlm` runs ran in parallel
on `ga13pd01` (#4478 and #4479). A full-chip `fc_*` run takes all 18 boards of a host.

## Spokane (local Palladium)

| Item | Value |
|---|---|
| Driver host | `palladium-94a4`, 4 boards |
| Launch from | any lab host with an asimov checkout and `/tools` (agentsrv, alpha) |
| Site switch | `MODULESHOME` must be **unset**, or the scripts quietly target the cloud |
| Queue DB | `/ice/infra/asimov-emu/queue.sqlite3` (read-only) |
| Release images | `/scratch/asimov/<release>` |

Runs that need more than 4 boards are GA13 only. For runs that fit in 4 (a `hemi_rtws_tlm` cme-perf
run), check both sites and use whichever can start now.

## Who to ask

- GA13 chamber account: Slack #positron-cadence-emulation.
- Release images: Alexey, Slack #emulation.
- The skill: Dan McDermott. This package and our runs: Jacob.
