# Machine access, privileges, and environment preconditions

delphi-3af6 is a SHARED machine. Default to read-only commands; never disrupt
other users. Anything that changes global system state or requires a reboot
(e.g. BIOS SNC mode) must be proposed for review, not executed (see planning.md).

## SNC mode — detect at runtime, do not assume
`cat /sys/devices/system/node/online`:
  - 0-5 => SNC/3: 6 NUMA nodes, 3 dies/socket; per-die memory (4 channels/die) and
    per-die L3 quota (~144 MiB); the mirror-die cross-socket L3 rule applies.
  - 0-1 => SNC-OFF: 2 NUMA nodes, 1 per socket = whole socket; 12 channels and the
    full ~432 MiB L3 interleaved; NO per-die nodes and NO mirror-die rule.
Changing the mode is a BIOS setting + reboot, performed by the USER between passes.
The agent runs whichever mode is live and tags its results; it must not change SNC
mode or stall on it.

## Sudo: a narrow NOPASSWD allowlist is installed at /etc/sudoers.d/jhan-snc3
You may run exactly these as root without a password (verify with `sudo -nl`):
```
/usr/bin/tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
/usr/bin/tee /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages
/usr/sbin/dmidecode
/usr/bin/dmesg
/usr/bin/mount  -t resctrl resctrl /sys/fs/resctrl
/usr/bin/umount /sys/fs/resctrl
/usr/bin/mkdir  /sys/fs/resctrl/cat_test
/usr/bin/rmdir  /sys/fs/resctrl/cat_test
/usr/bin/tee    /sys/fs/resctrl/cat_test/schemata
/usr/bin/tee    /sys/fs/resctrl/cat_test/tasks
/usr/sbin/sysctl kernel.perf_event_paranoid=*
/usr/bin/perf
```
If a needed grant is missing, ask the user to add it (`sudo visudo -f
/etc/sudoers.d/jhan-snc3`) rather than working around it.

## perf (required by execute.md's gap-investigation step)
`perf` is installed but `kernel.perf_event_paranoid` defaults to 4 (blocks
unprivileged PMU). Before perf work: `sudo -n /usr/sbin/sysctl
kernel.perf_event_paranoid=0`. Core PMU events then work unprivileged; uncore
IMC/CHA/UPI need root (`sudo perf`). Symbolic event names like
`mem_load_retired.l2_hit` are NOT mapped for this CPU (model 173); use generic
names (`L1-dcache-load-misses`, `l2_rqsts.all_demand_data_rd`, `LLC-loads`,
`LLC-load-misses`, `cache-misses`). Setting resets on reboot.

## resctrl (CAT test)
`sudo -n /usr/bin/mount -t resctrl resctrl /sys/fs/resctrl`. Then
`/sys/fs/resctrl/info/L3/`: num_closids 15, cbm_mask ffff (16-way),
shareable_bits c000; 2 L3 CAT domains (per-socket, not per-die). The CAT test
creates/removes a CLOS group `cat_test`.

## Hugepages and per-node memory (IMPORTANT for buffer sizing)
- 2M pool starts at 0; sweep scripts reserve ~2048 via `sudo tee`, restore on exit.
- 1G pool pre-reserved (~1128, 188/node). Per-node FREE 1G pages: node 0 & 1
  ~48 free; nodes 2-5 ~188 free.
- node 0 has ~3 GB conventional free (the 1G pool consumed it), so LARGE
  per-thread buffers cannot be hosted on mem-node 0. Big-buffer tests should
  target a free node (2-5) and the page size that fits the requested sizes (4K
  for sub-GiB exact sizes; 1G only for >=1 GiB multiples). State the substitution.
- Per-node free memory is mode- and time-dependent; PROBE it at runtime (the
  scripts do). Under SNC-OFF only nodes 0 & 1 exist; the per-die figures above
  (nodes 2-5) apply to SNC/3 only.

## Build
gcc + libnuma-dev; bw_* need AVX-512 (`-mavx512f`). `cd claude-workspace/code &&
make` builds into ../bin. Self-contained; no pre-work rebuild needed.

## Plotting (for the report Figures section)
matplotlib is used to render the figures. Install once with `pip install --user
matplotlib` -- its deps (numpy/pillow/etc.) are pure-Python wrt cffi, so it does
NOT pull cffi 2.x and will NOT disturb the bw-* Positron tooling that pins
cffi==1.14.6. Use a non-interactive backend (`matplotlib.use("Agg")`).

## Known tooling limit
`bw_multi` SIGBUSes at large per-thread WS (>~256 MiB with 2M pages). Size around
it (1G/4K pages or smaller per-thread WS), or fix the binary (open Todo).
