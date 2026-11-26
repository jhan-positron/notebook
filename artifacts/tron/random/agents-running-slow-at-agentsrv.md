# Agents running slow at agentsrv

- Date: 2026-11-20. All times are PST.
- Host: agentsrv, a shared development server with 32 CPUs.
- Subject: the claude-dev container, started by `~/claude-container/claude-box`.
- Author: a Claude Code session, for jhan.

## Short version

The container is healthy. agentsrv limits each user to 8 CPUs, and the container counts against that limit. A batch job from jhan's Claude session exceeded it from 18:22 to 18:41, and the kernel kept pausing jhan's processes.

## Words used here

- **claude-dev**: the podman container in which jhan runs coding agents (Claude Code and Codex sessions) on agentsrv.
- **slice**: the Linux control group (cgroup) that systemd creates per user. All processes of a user on the host live in it, including the container.
- **CPU quota**: the CPU time a slice may use per 100 ms period. Here it is 800 ms, which equals 8 CPUs.
- **throttled period**: a 100 ms period in which the slice used its whole quota. The kernel then pauses every process of the slice until the next period.
- **pressure**: the kernel's "pressure stall information". It reports the share of time in which processes were ready to run and had to wait. "Full" means all of them waited at once.
- **swap allowance**: the cap on how much of a user's memory may sit in swap (memory moved to disk).
- **inotify instance**: a kernel handle that a program opens to watch files for changes.
- **container shell**: one shell opened in the container by `claude-box enter`. podman keeps one helper process on the host per shell.
- **systemd-oomd**: a service that kills processes when a slice stalls on memory for too long.
- **LSF**: the batch job scheduler that the admins provide for large jobs.

## What was reported

At about 18:44 jhan reported that applications inside the container ran very slowly. jhan suspected a fault in the container.

The checks in this report ran between 18:45 and 19:03.

## Health checks

| Check | Reading | Result | Source |
|---|---|---|---|
| Container state | running since 2026-09-12, 0 restarts, never killed for lack of memory | healthy | [Ref2] |
| Container limits | none of its own | healthy | [Ref2] |
| Processes inside | 517, with 0 zombies and 0 blocked on I/O | healthy | [Ref14] |
| Disk | 128 GiB free on the container root, 8.8 TiB free on the NFS home | healthy | [Ref15] |
| NFS speed | 0.20 ms per attribute read, 0.78 ms per write | healthy | [Ref16] |
| Network helper (pasta) | alive, uses 0.2% of one CPU | healthy | [Ref17] |
| Host | 4.6 of 32 CPUs busy on average, 89 GiB of 157 GiB RAM available | healthy | [Ref8] |
| Per-user CPU quota | 8 CPUs, used up in 903,938 periods since 2026-10-14 (2.8% of all periods) | cause | [Ref2] |
| Swap allowance | 7.0 of 8 GiB used | nearly full | [Ref9] |
| inotify instances | 117 of 128 used | nearly full | [Ref10] |
| Kernel keys | 176 of 200 used | nearly full | [Ref12] |

## Where the limit sits

```
agentsrv host: 32 CPUs, 157 GiB RAM
└─ slice of user jhan    <- cap: 8 CPUs, 64 GiB RAM, 8 GiB swap
   ├─ ssh logins on the host (2 claude sessions)
   └─ claude-dev container (no cap of its own)
      ├─ interactive: 5 claude, 5 codex, herdr, tmux
      └─ 18:22 batch: up to 36 worker processes at once
```

The container has no cap of its own. It shares the 8 CPUs with everything else that jhan runs on the host.

## What slowed the applications

- An admin rule caps every user on agentsrv at 8 CPUs, 64 GiB RAM and 8 GiB swap [Ref1]. The rule dates from 2026-10-14.
- The container sits inside jhan's slice and has no limit of its own [Ref2].
- Programs in the container still see 32 CPUs. `nproc` returned 32 there at 18:22:20 [Ref3]. A numpy script there started 32 threads [Ref14].
- At 18:22:23 a Claude session in `intel-AMX/GDN` started the script `run.sh` [Ref3]. It runs 29 Python check scripts, 10 at a time. The last script ended at 18:41:16.
- Four of the scripts start pools of worker processes [Ref4].
  - `vm_checks.py` starts 28 and later 9.
  - `02_split3_exhaustive.py` starts 8.
  - `gdn_block_proto.py` and `proto_rerun.py` start 5 each.
- Two of these scripts alone can keep 36 processes busy at once (28 + 8). The quota covers 8.
- The same scripts ran 5.7 to 16.8 times slower than when they ran alone in the morning [Ref5]. The chart and the table below show the times.
- When the quota runs out, the kernel pauses every process of the slice. That includes Claude Code, Codex, herdr and tmux (two terminal managers), not only the batch.
- At about 18:46 the 5-minute average showed the container fully stalled on CPU for 19.7% of the time [Ref6]. That average falls after an event ends. Back-calculated to 18:41, the stall was about 56% (est., assumes no stall after the batch).
- At 18:51 jhan's slice read 8.0%. Each of the other 32 users read 0.24% or less [Ref7]. So the stall was in jhan's slice alone, and the host was not the cause.
- Since the cap began, the kernel throttled jhan's slice in 903,938 periods [Ref2]. Only one of the 33 users on the host was throttled for longer.

```
Wall time of the same script, alone in the morning
and inside the 18:22 batch. One "#" is 40 s.
A time under 40 s is drawn as one "#".

lead_numerics.py
  alone |#                               20.9 s
  batch |#########                      352.0 s   16.8x slower
lead_numerics_rerun.py
  alone |#                               25.4 s
  batch |########                       332.7 s   13.1x slower
02_split3_exhaustive.py
  alone |###                            116.1 s
  batch |###########################  1,074   s    9.2x slower
vm_checks.py (sum of its 9 scenarios)
  alone |#                               45   s
  batch |######                         256   s    5.7x slower
```

Every script took several times longer in the batch, and the longest one took 18 minutes.

| Script | Alone in the morning | In the 18:22 batch | Slower by |
|---|---|---|---|
| `lead_numerics.py` | 20.9 s | 352.0 s | 16.8x |
| `lead_numerics_rerun.py` | 25.4 s | 332.7 s | 13.1x |
| `02_split3_exhaustive.py` | 116.1 s | 1,074 s | 9.2x |
| `vm_checks.py`, sum of 9 scenarios | 45 s | 256 s | 5.7x |

## After the batch

A sampler read the slice counters every 2 s from 18:52:19 to 19:01:43 [Ref8].

- The slice used 1.04 CPUs on average. The quota allows 8.
- The slice was fully stalled on CPU for 0.68% of the time on average. So processes waited for a CPU less than 1% of the time.
- Memory stall was 0.3% at most.
- 209 of 5,664 periods (3.7%) were still throttled. A period is throttled only when the slice uses 800 ms of CPU within it. So these were short bursts of 8 or more CPUs.
- Which process makes these bursts: Insufficient data. Sampling per thread every 100 ms would show it.

| Minute | Samples | CPUs used (mean) | Throttled periods | Full CPU stall (mean) | Full CPU stall (max) | Host CPUs busy (mean) |
|---|---|---|---|---|---|---|
| 18:52 | 21 | 0.84 | 8 of 427 | 0.72% | 2.1% | 3.7 |
| 18:53 | 29 | 0.80 | 9 of 589 | 0.32% | 1.3% | 4.0 |
| 18:54 | 30 | 0.89 | 20 of 609 | 0.75% | 2.6% | 4.4 |
| 18:55 | 29 | 1.05 | 25 of 590 | 0.45% | 1.9% | 4.1 |
| 18:56 | 30 | 1.50 | 40 of 611 | 1.13% | 3.9% | 5.0 |
| 18:57 | 29 | 1.10 | 37 of 591 | 0.77% | 2.6% | 4.9 |
| 18:58 | 29 | 1.40 | 22 of 597 | 0.86% | 3.4% | 6.4 |
| 18:59 | 29 | 1.05 | 26 of 595 | 0.85% | 10.8% | 5.0 |
| 19:00 | 30 | 0.82 | 12 of 609 | 0.47% | 2.0% | 4.1 |
| 19:01 | 22 | 0.82 | 10 of 446 | 0.38% | 1.3% | 4.0 |

The first and the last row cover part of a minute.

## Follow-up at 20:08

At about 20:03 jhan asked whether the system was back to normal. Codex still looked slow in the container.

The system:

- At 20:08 the slice used 0.68 of 8 CPUs, and 3 of 150 periods were throttled [Ref19]. So the system was normal at that moment.
- The time from 18:51 to 20:08 was not all normal. 6,988 of 46,237 periods (15.1%) were throttled [Ref19].
- One more wide job ran in that time. A workflow agent of the same Claude session ran `r3_split_facts.py` twice between 19:48:32 and 20:02:15 [Ref20].
- That script uses a pool of 8 processes, which equals the whole quota.
- The 5-minute average of full CPU stall still read 9.1% at 20:06:50 [Ref19]. Back-calculated to 20:02, the stall was about 23% (est., assumes no stall after the run).

Codex:

- Codex was not slow. It was waiting for the Claude session.
- The two agents exchange review comments through a shared file [Ref21]. The Claude session is the worker, and Codex is the reviewer.
- Codex posted its round-1 comments at 19:41:05. Since 19:41:10 it has checked the file every 15 s for the round-2 entry of the Claude session.
- The Claude session started a workflow with 5 investigator agents at 19:44:04 to answer the comments [Ref22]. 3 agents finished by 19:59:56, and the last 2 finished at 20:08:11.
- Four of the five agents spent their time in model calls, not in local commands. Agent R1 spent 958.7 s in model calls and 31.1 s in commands [Ref22].
- The fifth agent, R3, spent 708.2 s in commands. Those were the two runs of `r3_split_facts.py`.
- At 20:09:36 the round-2 entry was not in the file yet, and Codex was still waiting.
- When the Claude session will post round 2: Insufficient data. The workflow is one step of that round, and the later steps are not recorded yet.

```
One character is 2 minutes. "#" is work, "." is waiting.

         18:18                                   19:38         20:08
         |                                       |             |
Claude   ########################################.#############>
Codex    ........................................#.............>
                                                 ^
                                 19:41 Codex posts its comments
```

Codex worked for 2 minutes 22 seconds of these 110 minutes, and it waited for the rest.

## Limits that are nearly full

None of these caused the slowness on this day.

Swap allowance:

- 7.0 of 8 GiB is used.
- 105 idle `trace_processor_shell` daemons in the container hold 5.4 GiB of it [Ref9]. They are Perfetto trace viewers that earlier sessions started.
- 111 such daemons run under jhan's account in total. 80 of them were started before 2026-11-20.

inotify instances:

- 117 of 128 are used [Ref10].
- podman's helper processes hold 104 of them. One new container shell adds one.
- 154 container shells are alive, and jhan has 7 login sessions on the host. So at least 147 shells belong to ssh windows that were closed.
- At 128, a program that wants to watch files gets an error [Ref11].

Kernel keys:

- 176 of 200 are used [Ref12].
- 173 of them are session keyrings. The kernel creates one per ssh login.
- At 200, podman could not start a container on the host alpha on 2026-09-02 [Ref18].

systemd-oomd:

- It watches jhan's slice [Ref13]. Its limit is 50% memory stall for 20 s.
- The memory stall of the container read 11.1% (5-minute average) right after the batch [Ref6].
- Past the limit, systemd-oomd kills every process of one cgroup. The whole container is one cgroup.

## What to change

- Run the four pool scripts one after another, and cap each pool at 6 processes. About 6 busy processes in total leaves room for the interactive tools.
- Set `OPENBLAS_NUM_THREADS=1` for numpy scripts that also use worker pools. OpenBLAS is the math library inside numpy, and it starts one thread per CPU that it sees.
- Add a line for agents to the machine section of `~/.claude/CLAUDE.md`. The session ran `nproc` three seconds before it started the batch, and `nproc` returned 32 [Ref3]. An example line follows.

  ```
  agentsrv: per-user cap of 8 CPUs, 64 GiB RAM, 8 GiB swap.
  nproc reports 32. Never run more than 6 CPU-bound processes at once.
  ```

- Send larger jobs to LSF. The admin's rule file says that the caps exist to push large jobs there [Ref1].
- Close the shells that were left open and the old `trace_processor_shell` daemons when convenient. That frees swap allowance, inotify instances and kernel keys.

## What was done and what is missing

- Nothing was killed, restarted or changed on agentsrv. The container needs no restart.
- All checks were read-only and ran from the host side, with two exceptions. Both have exited.
  - The sampler ran for 9 minutes at the lowest priority.
  - One 4-second `sleep` ran in the container to measure what one shell costs.
- The throttle counter was not measured during the batch itself. Monitoring started at 18:45, after the batch ended. A sampler run during the next wide batch would confirm the link directly.
- Cause of the memory stall right after the batch: Insufficient data. Page-fault and reclaim rates, sampled during a repeat of the batch, would resolve it.
- The kernel log and the system journal are not readable without sudo. Kernel messages were not checked.
- The load on the host during the morning runs is not recorded. So the "alone" times are a reference, not a controlled comparison.

## References

- [Ref1] `/etc/systemd/system/user-.slice.d/20-runaway-guard.conf` on agentsrv. It is managed by Ansible and dated 2026-10-14 13:09. It sets `CPUQuota=800%`, `MemoryMax=64G`, `MemorySwapMax=8G` and `TasksMax=8192`.
- [Ref2] `podman inspect claude-dev` (Memory=0, NanoCpus=0, PidsLimit=0, RestartCount=0, OOMKilled=false). Also the files `cpu.max` ("800000 100000"), `memory.max` (64 GiB) and `cpu.stat` under `/sys/fs/cgroup/user.slice/user-644434775.slice`. `cpu.stat` read at 18:51:07: 32,208,641 periods, 903,938 throttled, 90.8 hours of throttled time summed over CPUs.
- [Ref3] Transcript of session `6abaa6d4-a2e5-4e74-bd4c-106db969141b` in `~/.claude/projects/-home-jhan-workspace-intel-AMX-GDN`. It shows the `nproc` call at 18:22:20 and the batch start at 18:22:23. The script is `rerun-checks/run.sh` in that session's scratchpad inside the container.
- [Ref4] `~/workspace/intel-AMX/exec/gdn-20261120/design-checks`: `verify-math/vm_checks.py` lines 244 and 323, `kernel/02_split3_exhaustive.py` line 72, `proto/gdn_block_proto.py` line 1038 and `verify-math/proto_rerun.py` line 1038.
- [Ref5] "Alone" times come from the saved `.out` files in the folder of [Ref4], written between 10:10 and 11:15. Batch times come from the `.rerun.out` and `.rc` files of the 18:22 run.
- [Ref6] `cpu.pressure` and `memory.pressure` of the container's cgroup, 5-minute averages, read at about 18:46.
- [Ref7] `cpu.pressure`, 5-minute average, of all 33 `user-*.slice` cgroups under `/sys/fs/cgroup/user.slice`, read at 18:51:07.
- [Ref8] Sampler output, 278 samples, in `/tmp/claude-0/-home-jhan-workspace-random/ecb9b33c-b02e-4fa0-9901-0de54ce24323/scratchpad/sampler.tsv`. The script is `sampler.py` in the same folder. That folder is temporary and sits in the claude-sw-dev-01 container, so the per-minute table above is the lasting record.
- [Ref9] `VmSwap` from `/proc/<pid>/status`, summed per command name over the container's processes.
- [Ref10] inotify handles counted in `/proc/<pid>/fd` for all of jhan's processes. Readings before, during and after one test shell: 117, 118, 117.
- [Ref11] inotify(7) manual page, error `EMFILE`.
- [Ref12] `/proc/key-users`, line for uid 644434775, and `/proc/keys`.
- [Ref13] `oomctl` output for `user-644434775.slice` (limit 50.00%), and systemd.resource-control(5), setting `ManagedOOMMemoryPressure=kill`.
- [Ref14] `ps` over the processes listed in the container cgroup's `cgroup.procs`, read at about 18:48. It showed 517 processes, 516 sleeping and 1 running. The running one was `python3 fit_variants.py` with 32 threads.
- [Ref15] `stat -f` on the container's root through `/proc/1572206/root`, and `df` on the host.
- [Ref16] `/proc/self/mountstats` on the host for the `/home` mount, two snapshots 20 s apart.
- [Ref17] `ps` for the pasta process (pid 1572201) on the host.
- [Ref18] Claude memory note `ssh-agent-per-login-keyring-quota`, which records the incident on alpha.
- [Ref19] `cpu.stat` and `cpu.pressure` of jhan's slice. `cpu.stat` at 20:08:11 read 32,254,878 periods and 910,926 throttled. The 5-minute average of full stall read 9.11% at 20:06:50 and 6.94% at 20:08:11.
- [Ref20] Transcript of workflow agent `afdb09ec1341a6791` (Bash calls at 19:48:32 and 19:57:05). The script is `round1/R3/r3_split_facts.py` in the session's scratchpad, with `Pool(8)` at line 167. Its `.time` file reads real 7m6.640s, user 29m48.499s, sys 4m54.821s.
- [Ref21] Entry headers of `~/workspace/intel-AMX/GDN/gdn-amx-design.html.review.md`, and the command line of Codex's wait loop (pid 2040782, started 19:41:10).
- [Ref22] Journal and agent transcripts of workflow `gdn-review-round1-findings` (`wf_788692f4-847`) under the `subagents/workflows` folder of session `6abaa6d4`.
