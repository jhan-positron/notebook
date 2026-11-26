# Rules for agents working under ~/dev (Asimov)

Install this as `~/dev/AGENTS.md` wherever your agent runs (your laptop, and
your home on the shared servers if agents run there too). For Claude Code, also
`ln -s AGENTS.md ~/dev/CLAUDE.md`. Codex and GitHub Copilot CLI read
`AGENTS.md` directly. Every agent and subagent follows it, and it overrides
repo-level docs where they conflict.

"The user" below means the engineer running the agent. Source: Jacob
Geldbach's `~/dev` rules as of 2026-11-02, generalized for any user.

## ⚠️ RULE #1: section 1.2 of the Asimov Arch Spec decides which document wins

**Read this before you open, cite, or act on any document.** PRs built from
the wrong document get thrown away.

The **Asimov Architecture Spec** and the documents linked in its **section
1.2, "Links to Related Asimov Content"**, are the true, most up-to-date Asimov
documents. **They take precedence over every other document.** Other documents
can still be used. They only lose when they conflict with a section 1.2 doc, or
when they are a stale copy of one.

### The section 1.2 list (copied 2026-10-06)

The **live Google Doc is the true version.** The local snapshot is a
2026-10-06 export under `/home/jgeldbach/dev/docs/asimov/` (readable by
everyone on the shared servers) and may be stale.

| Document | Live (the true version) | Local snapshot under `/home/jgeldbach/dev/docs/asimov/` |
|---|---|---|
| Asimov Architecture Spec | https://docs.google.com/document/d/173ihNJW6B-BSV5m1v4pxQd6IZq42MC7_YOlDmTkTU7Q | `Asimov_Arch_Spec.docx` |
| Asimov Interface Spec | https://docs.google.com/document/d/15RZfIG3BqMtV8X-jhO1CDf4qoJGwxTYHVUp8wdB9nCw | `Asimov_Interface_Spec.docx` |
| Asimov Power, Timing, Clock & Reset Spec | https://docs.google.com/document/d/1LaT_9sDoiIJ29x6jAWUHYLpELNPGIlehz4i6DkPR3vw | `PTCR/AsimovPowerTimingClockAndResetSpecificationSilver.docx` |
| Asimov Drawings (Asimov-Arch tab) | https://lucid.app/lucidchart/20fdcbdb-2e19-4b4e-a3d2-d3e189b64a65/edit | none (Lucidchart only) |
| CPS: Command Processing Subsystem | https://docs.google.com/document/d/1jF94xS4DphyhIlv9VB2vNgEUFCZzcJFnmV4Mc0urN7Y | `CPS/Command Processing Subsystem Micro‑Architecture Specification.docx` |
| TWS: TransWarp Subsystem | https://docs.google.com/document/d/1H4Squ4RuLJmVJim4vqgv75FmJBSVA0Jo4WF2BOy00mM | `TransWarp/TWS Microarchitecture.docx` |
| XMS: External Memory Subsystem | https://docs.google.com/document/d/10tp-vufzxLopq9CKg6SnaSkIWLd5Xm5I8OdTpMm9TcY | `XMS/External Memory Subsystem Microarch.docx` |
| SLS: Streaming Logic Subsystem | https://drive.google.com/file/d/1zAOeu_O6xXx1GGxyiHdZDGcH-WkIJoJz | `SLS/streaming_logic_subsystem_uarchitecture.docx` |
| SPM: Scratch Pad Memory | https://docs.google.com/document/d/195P6Qy00LKtRAV8opFuzimRsDPFiXBJqefABWBXn7JM | `SPM (Scratch Pad Memory Manager)/SPM Subsystem Micro‑Architecture Specification.docx` |
| CMN: Arm Coherent Mesh Network | https://docs.google.com/document/d/1QErHoAreoEQ7S9J9Tk8mtatuulwolT4dRHA9j5d5gzI | `CMN/CMN_uArch_Spec.docx` |
| C2C: Chip-to-Chip Subsystem | https://docs.google.com/document/d/1Xv5vaSmzH1m-9XAlPXAOrgvMAN4ACnFkFT_9gEmeduE | `C2C/C2C_uArch_Spec.docx` |
| PCIe Wrapper Microarchitecture Spec | https://docs.google.com/document/d/1DtVr8dqgk4IquMNBssPXCoMQxW3A0MXjv6oC_Cqs4ME | none (stored outside the Asimov folder) |
| PLL control uArch (car_top) | https://docs.google.com/document/d/1taZ4llrEl_iHwlRiPAryFnor9B81g9kHMK9s9zMncWc | `PTCR/PLL control uArch.docx` |
| Asimov Corners Specification | https://docs.google.com/document/d/17lTDCeBh9Fj5A8vQdgRWe4XUojYay0xuVHa7p2hPNCM | `Corners/Asimov Corners Specification.docx` |

The **live section 1.2 is the master list.** If it differs from this table, the
live section 1.2 wins. Docs it adds count, and docs it drops stop counting.

### Precedence

1. **The section 1.2 docs (live Google Doc).** These win over everything else.
2. **The local snapshot of a section 1.2 doc.** Use it only if you can't read
   the live doc, and say so.
3. **Any other document:** other Drive docs, repo docs and READMEs,
   `asimovsw-docs`, Arm's manuals, coworkers' working docs, Notion, issues. Use
   it where section 1.2 is silent and it doesn't conflict.

### Disregard: other versions of a section 1.2 doc

If a document has the same name or covers the same subject as a section 1.2 doc
but **isn't the exact linked document**, ignore it entirely. It's another
version of that doc and is stale. Examples under the snapshot:
- `Copy of Asimov_Arch_Spec.docx`
- `archive/Asimov_Arch_Spec-Archive-March-2026.docx`
- `PTCR/Asimov Power, Timing, Clock & Reset Specification - CADENCE - BRONZE.pdf`
- `PTCR/Retired/…Bronze.docx`
- `Corners/Asimov Corner Specification - DRAFT ONLY.docx`
- `XMS/Old Docs/`
- `TransWarp/Retired/`

Before you use any document that isn't in the table, check that it isn't one of
these versions.

### How to apply it

1. **Check the section 1.2 docs first.** If they cover the topic, they're the source.
2. **If section 1.2 is silent, other docs are fine.** Name the document you
   used, and note in your summary or PR that section 1.2 doesn't cover it.
3. **On a conflict, the section 1.2 doc wins.**
4. **Verify against the RTL in `~/dev/asimov`.** If the RTL and a doc disagree,
   report the mismatch with both sides. Don't silently pick one, and don't open
   a PR that bakes a guess in. Read the RTL at the commit the build or model
   uses (`git -C ~/dev/asimov show <sha>:<path>`), not `main`.
5. **Prefer the live Google Doc to the snapshot.** If you used the snapshot, say
   the work is based on the 2026-10-06 snapshot, and never treat it as newer
   than the live doc.
6. **If nothing covers what you need, or two section 1.2 docs conflict, stop
   and ask the user.**
7. **Cite the document and section in every PR description** for each change.

## RULE: build only in /scratch/$USER/agent-builds

**Never run a build inside `~/dev`.** `~/dev` holds source checkouts only.
Every build, compile, test image, venv or other artifact-producing command runs
in a git worktree under `/scratch/$USER/agent-builds/` on the shared servers.
This applies even if a repo's own README or Makefile tells you to build in
place.

Why:
- `/home` and `/scratch` are separate shared NFS filers. `/scratch` is meant for
  scratch work and is visible from agentsrv, alpha, sw-dev-01, the LSF workers
  and the Spokane Palladium driver host. `/tmp` is local to each host.
- Build trees (Buildroot `output/`, kernel objects, `.venv`s) are tens of GB.
  In `~/dev` they fill the home filer and dirty the trees people edit.
- Several agents building in place in one checkout overwrite each other's
  in-tree state (for example `buildroot/.config`).

How:
```bash
REPO=asimov-os                       # repo directory name in ~/dev
TASK=my-task                         # short unique name for this build
BUILD=/scratch/$USER/agent-builds/$REPO-$TASK
mkdir -p /scratch/$USER/agent-builds
git -C ~/dev/$REPO worktree add "$BUILD" HEAD   # or a branch name
cd "$BUILD"
git submodule update --init --recursive        # if the repo uses submodules
```
- For uncommitted changes from `~/dev`: commit them to a branch and add the
  worktree from it, or `rsync -a --exclude .git ~/dev/$REPO/ "$BUILD"/`.
- Point shared caches there too. For asimov-os (Buildroot), share one download
  cache: `make BR2_DL_DIR=/scratch/$USER/agent-builds/buildroot-dl -j"$(nproc)"`
  (on an LSF host, not agentsrv; see the lab rules). Venvs and tool caches
  (`UV_CACHE_DIR=/scratch/$USER/agent-builds/uv-cache`) also go here.
- **asimov-os** builds Buildroot in-tree; many targets hardcode
  `buildroot/output/` and `buildroot/.config`. Don't redirect it with `O=`; use a worktree.
- When done: `git -C ~/dev/$REPO worktree remove --force "$BUILD"`.

**Never run `git worktree prune`.** `~/dev` on the servers is on NFS and seen
by many hosts, and some worktrees live in a host-local `/tmp`. Prune deletes
the registration of every worktree it can't see from the current host, which
breaks other hosts' and agents' live worktrees. Remove only your own worktree
with `git worktree remove`, on the host that created it.

Allowed in `~/dev`: reading and editing source, `git` operations, linters and
formatters that write no build output, quick read-only commands. If unsure
whether a command writes build output, run it in a scratch worktree.

## RULE: clean up after yourself

When a task is finished, remove what you put in `/scratch/$USER/agent-builds`
or `/tmp`: worktrees, build trees, downloaded FVP and toolchain packages (an
FVP is about 85-180 MB), Buildroot output, `.venv`s, `uv`/pip caches and large
logs.
- Clean up on **every host you used**. `/tmp` is local to each machine
  (agentsrv, sw-dev-01, alpha, LSF workers). LSF job scripts delete their work
  dir on exit: `trap 'rm -rf "$WORK"' EXIT`.
- `/tmp` is shared and often nearly full. Check `df -h /tmp` before a large
  build, and don't start one that would fill it.
- Keep only what the user still needs (for example a worktree for a PR still
  being iterated on), and say what you kept, where, and how big it is.
- Before removing anything, prove it's yours (you created it, under
  `/scratch/$USER/...`). Never delete other users' files.
- Emulation filers (GA13 `/projects/positronem`) have their own, stricter rule:
  see `04-emulation.md` and the palladium-emulation skill.

## RULE: lab etiquette (infra; see lab-guidance.md)

- **Heavy jobs go through LSF** (`bsub`), never on the shared hosts. Heavy
  means more than a few cores, several GB of RAM, or more than a few minutes:
  FVP builds, full FVP suites, sims, synthesis, regressions, Buildroot builds.
  Every licensed tool (`vcs`, `xrun`) goes through LSF. If unsure, use LSF.
- Never run a recursive `find` or `grep` at `/`, `/opt`, or an NFS root
  (`/home`, `/scratch`, `/tools`, `/ice`, `/emu`). Search a subdirectory.
- Keep local work light; unbounded parallel agents have OOM'd agentsrv before.
- For infra questions (hosts, queues, storage, access, a killed or pending
  job), read https://lab-docs.porgy-gecko.ts.net/llms.txt before guessing.

## RULE: no outward action without the user

Don't push, open or merge PRs, comment, review, tag, post to Slack, or launch
emulation runs without the user's explicit go-ahead for that action. Approval
in one context doesn't carry to the next.
- Re-pins of dependencies get their own PRs.
- Stacked PRs start with "Stacked on #N".
- A stack behind `main`: merge `origin/main` into the bottom branch and carry
  it up with merges. Don't rebase and force-push pushed branches.
- Never handle passwords, passphrases or tokens. If a key isn't loaded, ask the
  user to load it.

## RULE: how GitHub writing reads

Everything posted to GitHub under your name (PR descriptions, issues, reviews,
comments, commit messages) uses the voice and table habit of
**positron-ai/asimov-address-map#17**'s description. Read that PR before you
write your first one.

- **PR descriptions and issues are thorough.** PR shape: an opening of 1-2
  sentences (what and who needs it), then `## Why` (what prompted it, linked;
  the gap), `## What changes` (one bullet per file or area, **bold path**),
  `## Open points` (found but deliberately not changed, and who decides),
  `## Follow-ups` if any, `## Tests` (tests by name, exact command, counts, base
  SHA, merge state; emulation run ID or FVP tag), and `## Section 1.2 documents`
  (Rule #1 step 7). Scale it to the change: a one-line fix needs the opening,
  Why and Tests.
- **Issues:** opening, `## Why`, `## Scope`, `## Acceptance` (checklist of
  observable results), `## Decisions` (lettered, with options), `## Related`.
- **Reviews and comments are short** (a review is about 300 words). Lead with
  the answer ("Valid.", "Done:", "Not an issue."). One comment per finding,
  most serious first: `path:line`, at most 3 sentences, plus the fix. Evidence
  by exact anchor (`path:line` at a commit, an emulation run ID, an FVP tag).
  Close threads explicitly ("Resolving.").
- **Tables** wherever data has rows and columns (register maps, per-case
  results, before/after, finding → verdict). Few columns, short cells, units in
  the header, identifiers in backticks.
- **Voice:** plain declarative sentences, exact names in backticks, short SHAs
  (8-9 characters), numbers with units. Say what is and isn't in scope. No hype
  or filler ("This PR aims to…", "comprehensive", "robust"). No AI attribution,
  no local paths, no internal tooling names.
- Match each repo's existing comment and code style.

## Where context lives

Repos are siblings under `~/dev` (see `01-dev-directory-and-repos.md`). Many
vendor each other as submodules under `depends/`, which are often
uninitialized; for reading, use the sibling checkout.

| Path | What it is |
|---|---|
| `~/dev/asimov/` | Chip RTL (SystemVerilog), private (Positron-AI-TSMC): `design/`, `verif/`, `syn/`, `constraints/`, `registers/`, `ip/`, `emu/`. Start with `ONBOARDING.md` and `ASIMOV_CHEAT_SHEET.md`; agent notes in `agentic/` |
| `~/dev/asim/` | Asimov simulator/model (Python). Has its own `CLAUDE.md` |
| `~/dev/terminus/` | Asimov FVP (Arm Fast Models / LISA+), firmware and host-driver helpers. Has its own `CLAUDE.md` |
| `~/dev/asimov-address-map/` | Address-map data the firmware builds use (`manifest.yaml`, `silicon.lock.json`). Section 1.2 wins on any conflict |
| `~/dev/asimov-scp-firmware/` | M7 SCP firmware (BL1/BL2); upstream fork in `scp-firmware/`. BL2 runs from a 196,352 B ITCM window: report BL2 size on every change |
| `~/dev/asimov-tfa/` | Trusted Firmware-A platform port; upstream fork in `trusted-firmware-a/` |
| `~/dev/asimov-os/` | Buildroot OS image; pins the firmware and FVP releases. See `DEVELOPMENT.md`, `SETUP.md` |
| `~/dev/asimov-bench/` | Bring-up measurement tools for the Asimov CMN |
| `/home/jgeldbach/dev/docs/asimov/` | Snapshot of the Asimov Drive folder (2026-10-06). Rule #1 table files take precedence |
| `/home/jgeldbach/dev/docs/asimovsw-docs/` | Software architecture docs (clone of positron-ai/asimovsw-docs). Below section 1.2 |
| `/home/jgeldbach/dev/docs/ARM/` | Arm TRMs and user guides (`ARM_IP/`, …). **Also holds contracts, POs, invoices and royalty/finance docs: confidential, open only when the task needs them** |
| `/home/jgeldbach/dev/docs/ARM/ARM_IP/asimov_b0_cmn_scope.md` | B0 / secure boot: Mike Bly's B0 CMN scope doc (security, RSE-100). A working doc, below section 1.2 |
| `/scratch/jgeldbach/env-setup-general/` | This setup package (FVP/LSF, emulation, scripts) |

Reading binary docs: `pdftotext -layout file.pdf -`; for `.docx`,
`unzip -p file.docx word/document.xml | sed 's/<[^>]*>//g'`. Use `grep -ril`
on extracted text. `docs/` is not a build input, so never build there.

## More

- Running a team of agents (OpenRig + herdr): the `asimov-sw-rig-team` skill,
  positron-ai/llm-toolbox `skills/asimov-sw-rig-team/` (merged in llm-toolbox#33,
  https://github.com/positron-ai/llm-toolbox/pull/33). Set up this environment
  first; the skill builds on it.
- Emulation: load the `palladium-emulation` skill before any emulation action
  (`04-emulation.md`).
