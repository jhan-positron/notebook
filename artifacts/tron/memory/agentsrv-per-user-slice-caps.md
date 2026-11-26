---
name: agentsrv-per-user-slice-caps
description: "agentsrv caps each user at 8 CPUs / 64 GiB RAM / 8 GiB swap / 8192 tasks (systemd user slice, since 2026-10-14); the claude-dev container sits under that cap; \"slow apps in the container\" on 2026-11-20 was CPU-quota throttling from a wide parallel batch; read-only diagnosis recipe"
metadata:
  node_type: memory
  type: project
  originSessionId: ecb9b33c-b02e-4fa0-9901-0de54ce24323
  modified: 2026-11-21T04:56:58.456Z
---

agentsrv applies per-user caps through the systemd user slice since 2026-10-14
13:09 (Ansible-managed drop-in
`/etc/systemd/system/user-.slice.d/20-runaway-guard.conf`): CPUQuota=800%
(8 of 32 CPUs), MemoryMax=64G, MemorySwapMax=8G, TasksMax=8192, and
systemd-oomd kills a whole cgroup under the slice when the slice's memory
pressure stays above 50% for 20 s. The drop-in's own comment says the caps are
meant to push large jobs to LSF.

The claude-dev container has no limits of its own. Its cgroup is a leaf at
`/sys/fs/cgroup/user.slice/user-644434775.slice/user@644434775.service/user.slice/<container id>`,
so the caps cover the container plus all host-side sessions of jhan together.
`nproc` inside the container still reports 32, so thread pools and `-j$(nproc)`
oversubscribe by 4x.

Incident 2026-11-20 18:22-18:41 PST: jhan reported very slow applications in
the container and suspected the container. Container state, disk, NFS
(0.2 ms per GETATTR), pasta and host load were all healthy. Cause: a Claude
session in `intel-AMX/GDN` launched `xargs -P 10` over 29 Python check scripts
that use `Pool(28)`, `Pool(8)` and `Pool(5)`. The scripts ran 5.7x to 16.8x
slower than when run alone that morning. CPU pressure showed only in jhan's
slice (every other user's slice was at or below 0.24%).

Read-only diagnosis recipe (host side, no podman exec needed):
- `cat /sys/fs/cgroup/user.slice/user-644434775.slice/cpu.stat` gives
  nr_throttled and throttled_usec; `cpu.pressure` and `memory.pressure` give the
  stall share. The same files of other `user-*.slice` directories are
  world-readable; comparing them separates "my cap" from "host is busy".
- Host load average and `free` do not show this problem.
- Container files are readable from the host through
  `/proc/<container PID 1>/root/...` (PID from
  `podman inspect -f '{{.State.Pid}}' claude-dev`), including `/tmp/claude-0`
  session scratchpads, which are on the container overlay and not on NFS.
- `oomctl` works without sudo and lists each slice's pressure against the limit.
- `dmesg` and the system journal are not readable by jhan.

Near-limit readings on 2026-11-20 (all caused by shells left open in the
container after the ssh window closed: 155 live exec sessions, 185 registered):
- inotify instances 117 of 128 per user; each open container shell holds one
  through its conmon process (measured: +1 during a test exec).
- kernel keys 176 of 200 (173 session keyrings); an exec session itself adds no
  key (measured), the ssh login that started it does.
- slice swap 7.0 of 8 GiB; 5.4 GiB of it held by 105 idle perfetto
  `trace_processor_shell -D` daemons in the container (started 2026-09-14 to
  2026-11-20, 31 of them on 2026-11-20). Nothing was killed.

**Why:** the symptom looks like a broken container, and the host looks idle,
but the limit is the per-user cap. Agents size their jobs from `nproc` = 32.

Update 2026-11-20 evening: [[agent-cpu-guard]] now pins every agent shell
command on agentsrv to CPUs 26-31, so `nproc` prints 6 there. The short bursts
that this note could not attribute came from 54 idle tmux clients (detached the
same evening).

**How to apply:** on agentsrv keep the total of CPU-bound workers at 6 or
fewer (the guard enforces the CPU count; size pools from `nproc`). numpy's
OpenBLAS follows the pin by itself (32 threads unpinned, 6 pinned, measured). When jhan reports slowness there, read the slice's
`cpu.stat` and pressure files first. jhan's instruction on 2026-11-20 was "do
not kill container or impact my running applications inside" (my reading: keep
any future diagnosis of claude-dev read-only and host-side as well).
Related: [[claude-box-keepalive-pkill-hazard]],
[[ssh-agent-per-login-keyring-quota]], [[herdr-agentsrv-topology-2026-10-03]],
[[agentsrv-container-single-uid-namespace]].
