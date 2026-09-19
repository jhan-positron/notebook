# Part 1: does the speed-select policy on delphi-3bda match Bill's resource map?

Facts read live on delphi-3bda on 2026-09-17 06:50 to 07:20 UTC, and from tron origin/main.

## Short version

The shipped speed-select policy already puts every tron app core of the current map in the fast class. It was
derived from Bill's 2026-06-28 layout; Bill's last change (2026-07-02) only renamed the die-A cores to their HT
siblings, which share the same clock. The one change from the July project that is still not deployed is the
front-end un-clamp (rinzler cores 1-2 and 73-74).

## Evidence

| item | value | source |
|---|---|---|
| deployed policy | FAST_CORE_RANGES='7-14 24-71 79-86 96-143', HT siblings added by the apply script | /etc/default/intel-speed-select-state; /usr/local/sbin/intel-speed-select-state add_thread_siblings |
| service state | intel-speed-select-state.service active (exited), applied 2026-09-15 23:54 UTC, 224 cpus in CLOS0 and 64 in CLOS3 | systemctl status; core-power get-assoc over cpus 0-287 |
| map generations | 05-20 (pre-Bill): tron_cores 27-36,37-46,51-60,61-70 / 75-84,85-94,99-108,109-118 (40 per socket); 06-28: 7-8,24-29,48-53 ... 85-86,114-119,138-143 (56 per socket); 07-02 (current): 151-152,24-29,48-53 ... 229-230,114-119,138-143 | git show 508b451ec4 / e6a69889f3 / c2d3b10f15 -- config/resource-map.yaml |
| coverage of current map | tron app cores 24-71, 96-143 -> CLOS0 (direct); 151-158, 223-230 -> CLOS0 (siblings of 7-14 and 79-86) | live get-assoc: cpus 24 27 36 47 48 53 60 71 96 101 143 151 152 158 223 224 230 all clos:0 |
| newer map changes | none for granite_rapids_6962p after 2026-07-02 on any tron branch; only Rhys's 2026-07-24 change to granite_rapids_6960p | git log --all --since=2026-07-03 -- config/resource-map.yaml |
| deployed map = main | /opt/positron/config/resource-map.yaml (tron deb 2026.09.17-31b80a18) granite_rapids_6962p section identical to origin/main | diff by eye of both sections, 2026-09-17 |
| front-end cores | rinzler_cores 1,2,73,74 and siblings 145,146,217,218 -> CLOS3 (2.7 GHz cap); rinzler main pids pinned there (taskset 73,74,217,218 and 1,2,145,146) | live get-assoc; taskset -pc on the rinzler pids |
| dev and platform cores | dev_cores 3-6, 75-78 and platform_cores 0, 72 (+ siblings) -> CLOS3 | live get-assoc cpus 0 3 72 75 144 216 |
| live frequency shape | during the CI soak (rinzler@0 on our half): tron app cores of slices 4-5 at 3934 MHz mean, 96% busy; dev cores 75-76 at 2700 MHz, 99.8% busy | turbostat 2 x 2-s samples, 2026-09-17 07:15 UTC |

## Reading

- The user's memory that the policy predates Bill's final map is right on the date, but the 07-02 change is clock-neutral for speed-select: cpu 7 and cpu 151 are the two hyper-threads of one physical core and must be in the same class (the apply script enforces this). So the fast set needs no update for coverage.
- The pre-Bill map (05-20) is NOT what the policy was derived from: its 40 app cores per socket (27-46, 51-70) do not match the 56-core fast ranges. The policy matches the 06-28 layout exactly.
- What IS missing: the July 2026 ship candidate "front-end un-clamp" (handoff claude_20260702-20260729, section SHIP CANDIDATE): FAST_CORE_RANGES '7-14 24-71 79-86 96-143' -> '1-2 7-14 24-71 73-74 79-86 96-143'. Measured then in the serving path on gpt-oss-120b tp4: decode +1.12% +/- 0.21 at 8 users and +2.44% +/- 1.05 at 24 users, positive in 5 of 5 draws, +6 to 8 W package power. The front-end threads (HTTP/SSE delivery and orchestration) run only in rinzler, so a runtron test cannot see this change; today's campaign covers the dev cores (75-78) instead through the tunedplus arm.
- The Ansible role that renders /etc/default/intel-speed-select-state (Hannah's) was not found through the GitHub API in positron-infrastructure, pos-deploy or external-infrastructure (tree listing and code search returned nothing). Insufficient data: ask Hannah for the role's repository before changing FAST_CORE_RANGES; do not hand-edit the file on the host (Ansible overwrites it).
