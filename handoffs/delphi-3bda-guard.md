# Guard: using delphi-3bda (nightly CI, and sharing with Bill)

> Written by Claude Code (Linux CLI, machine claude-box) on 2026-09-06.
> Facts were read from the live machine, the tron source, and jhan's shell
> files on 2026-09-06 20:40-20:47 UTC; file:line references point at those
> sources. Companion to `handoffs/check-CI.md`, which covers the nightly CI
> in detail.

## Short version

Two rules. (1) Do not run heavy work while the nightly CI holds the machine;
`handoffs/check-CI.md` says how to tell. (2) Bill uses the first four FPGA
cards; jhan uses the second four. Every tron program jhan starts must select
the second half, which `SYSTEM_CONFIG="--instance 1,2"` does by default.
Nothing else needs checking.

## Words used here

- DUT: device under test; here always delphi-3bda (Intel Xeon 6962P, two CPU
  sockets, 8 FPGA cards).
- tron: the inference program under test; runtron: its command-line tool;
  rinzler: the production server (systemd units rinzler@0..3).
- TP (tensor parallelism): running one model across N cards. "First half" and
  "second half" mean the first four and the last four cards.
- slice: tron's unit of machine resources, one per card (cores, one card,
  64 GiB of hugepages). Slices 0-3 are socket 0, slices 4-7 are socket 1
  [/opt/positron/config/resource-map.yaml, entry granite_rapids_6962p].
- `--instance x,y`: runtron option meaning "instance x of y". y instances
  split the 8 slices evenly; instance x takes slices x*(8/y) to
  (x+1)*(8/y)-1 [tron src/system/system.cpp `get_slices`; src/runtron.cpp:77].
- SYSTEM_CONFIG: environment variable tron reads for `--instance` when the
  command line has none. A command-line `--instance` wins over it
  [system.cpp `early_parse_instance`].
- lease: `/run/lock/systems-test-ci.lease`, the nightly CI's "I hold the DUT"
  file.

## Rule 1: stay out of the CI window

The nightly CI takes all 8 cards, so the half split does not apply while it
runs. Before any launch:

```bash
cat /run/lock/systems-test-ci.lease 2>/dev/null || echo "no lease"
for i in 0 1 2 3; do echo "rinzler@$i $(systemctl is-active rinzler@$i)"; done
```

- Lease present with `state: busy` and not expired: CI holds the machine.
  Do only light work. Details and the GitHub-side check are in
  `handoffs/check-CI.md`.
- Any rinzler@N active: production serving is up on all 8 cards (the 02:45 UTC
  prep step starts 4 engines at TP 2) [/opt/positron/config.d/50-user-overrides.yaml].
  Do not launch.
- Long runs must finish before about 02:30 UTC.

Campaign scripts already do this through `campaign_guard_acquire` in
`~/workspace/intel-AMX/exec/lib-guard.sh`.

## Rule 2: use only the second half

```
socket 0 (slices 0-3)            socket 1 (slices 4-7)
 card 10:00.0  --.                card 90:00.0  --.
 card 13:00.0    |  BILL          card 93:00.0    |  JHAN
 card 38:00.0    |                card b9:00.0    |  --instance 1,2
 card 3b:00.0  --'                card bc:00.0  --'
```

Sources: `lspci -D -d 8200:0011` (8 cards), `/sys/bus/pci/devices/0000:<card>/numa_node`
(0 for the first four, 1 for the last four), resource map `devices:` array.

`--instance 1,2` selects slices 4-7: cards 90:00.0, 93:00.0, b9:00.0,
bc:00.0, the socket-1 tron cores, hugepage files `/dev/hugepages/slice-4-of-8`
to `slice-7-of-8`, and NUMA node 1 memory [system.cpp `configure_instance`].

How the environment sets it:

- `~/jibin.bashrc.positron.dev:16` exports `SYSTEM_CONFIG="--instance 1,2"`
  for every machine, then sources `~/$(hostname)-setup.sh`.
- `~/delphi-3bda-setup.sh` exports the same value for this machine (typo
  `SYSTEM_CONFIF` fixed by jhan on 2026-09-06). Unset it only for
  whole-machine measurements when Bill is not using the machine.
- Check in a login shell on delphi-3bda:
  `bash -lc 'echo $SYSTEM_CONFIG'` should print `--instance 1,2`.

If a script passes its own `--instance` or `--devices`, they must stay inside
the second half:

| want | write |
|------|-------|
| 4 cards (TP 4) | `--instance 1,2` |
| 2 cards, first pair of our half | `--instance 2,4 --devices 90:00.0,93:00.0` |
| 2 cards, second pair of our half | `--instance 3,4 --devices b9:00.0,bc:00.0` |
| 1 card | `--instance 4,8` to `--instance 7,8` |

Never write `--instance 0,2`, `0,4`, `1,4`, or `0..3,8`, and never list cards
10, 13, 38, 3b in `--devices`.

## Two things to fix before the next campaign (found 2026-09-06)

1. **30 campaign scripts pin Bill's cards.** In `~/workspace/intel-AMX/exec/`,
   30 scripts pass `--instance 0,4 --devices 10:00.0,13:00.0` (slices 0-1),
   and a command-line `--instance` overrides SYSTEM_CONFIG. Change them to
   `--instance 2,4 --devices 90:00.0,93:00.0` before reuse. List them with:

   ```bash
   grep -l -- '--devices 10:00.0,13:00.0' ~/workspace/intel-AMX/exec/*.sh
   ```

   Scripts without an explicit `--instance` inherit SYSTEM_CONFIG and are
   already correct.
2. **The guard library still blocks on Bill.** `campaign_guard_acquire` refuses
   to launch while any other login user's processes are busy
   [lib-guard.sh:47-147, `other_user_active`]. Under the half split Bill's
   work on socket 0 is not a reason to wait. One-line fix, in
   `~/delphi-3bda-setup.sh`:

   ```bash
   export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
   ```

## Note

`HugePages_Free: 0` in `/proc/meminfo` is normal on this machine: all 512
1-GiB pages live in the eight `/dev/hugepages/slice-N-of-8` files, and tron
reuses the file for each slice it owns [tron src/system/huge.cpp:78-108].
jhan is in group `positron`, which owns those files.

## Sources

- delphi-3bda: `lspci -D -d 8200:0011`, `/sys/bus/pci/devices/0000:*/numa_node`,
  `/opt/positron/config/resource-map.yaml`,
  `/opt/positron/config.d/50-user-overrides.yaml`, `/proc/meminfo`,
  `/dev/hugepages`, `id`.
- tron source (`~/workspace/tron`): `src/runtron.cpp:77`,
  `src/system/system.cpp` (`get_slices`, `early_parse_instance`,
  `configure_instance`), `src/system/huge.cpp:78-135`.
- `~/jibin.bashrc.positron.dev:15-23`, `~/delphi-3bda-setup.sh`.
- `~/workspace/intel-AMX/exec/lib-guard.sh`; `grep -l` over `exec/*.sh`.
- `handoffs/check-CI.md` (2026-09-05).
