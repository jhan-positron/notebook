**R1. Bugs / hazards**

- **A fails open on observability failure.** `sudo journalctl` or `sudo ss` failure becomes zero traffic/connections because errors are discarded and `|| true` accepts the result. That can authorize stopping live serving. `run-ctxfill.sh` lines 31–38:
  ```bash
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -vE '#EVT# (SYSTEM_STATS|Harvester stats)' \
    | grep -icE 'session|request|prompt|generat|token') || true
  ...
  conns=$(sudo -n ss -Htn state established \
    '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null \
    | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  ```
  Require each privileged command to succeed and validate numeric results; otherwise abort without stopping services.  
  `context_start_text="traffic=$(sudo -n journalctl"`; `context_end_text="| awk '$4 !~ /^127\\.0\\.0\\.1:/' | wc -l) || true"`

- **A performs the destructive serving stop before acquiring the campaign lock.** Lines 51–59:
  ```bash
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || { echo stop-failed >"$MARKER"; exit 1; }
  ...
  if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
  ```
  Acquire first with `campaign_guard_acquire --allow-serving`, then perform the verified stop while holding the lock. This closes the cross-session race.  
  `context_start_text="echo \"rinzlers active, zero journal traffic"`; `context_end_text="if ! campaign_guard_acquire"`

- **A can label a clock/CI-truncated campaign `ok`.** `stop_now` breaks the loops, but line 102 checks only run failures:
  ```bash
  grep -qE "RUN-FAILED" "$OUT" && echo check-output >"$MARKER" || echo ok >"$MARKER"
  ```
  Track `STOPPED_EARLY=1` and emit an incomplete/stopped marker.  
  `context_start_text="stop_now \"$tmo\" && break 3"`; `context_end_text="echo ok >\"$MARKER\""`

- **A `PIPESTATUS` use is correct.** Lines 83–86 capture it immediately after the runtron/grep pipeline. The absence of `pipefail` there is not a defect because both statuses are inspected.

- **The 09:30Z same-day clock calculation is correct.** After 03:30Z, lines 71–73 roll the deadline to tomorrow; it will not mistake today’s already-passed 03:30Z for an imminent stop.

- **Both traps use broad process-name killing.** A line 15 / B line 22:
  ```bash
  pkill -TERM -f "gen/runtron\."
  ```
  This can kill an unrelated user’s matching process. Track the campaign PID/process group and terminate only that. The flock itself cannot remain stranded after shell exit because its FD closes automatically.  
  `context_start_text="trap '[ -e \"$MARKER\" ] || {"`; `context_end_text="echo aborted >\"$MARKER\"; }' EXIT"`

- **B hides command failures through pipelines.** Lines 87 and 91 return `grep` status, not `perf` status:
  ```bash
  perf stat -C $APPCORES -e "$ev" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
  perf stat -a -e "$G4" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
  ```
  Capture `PIPESTATUS[0]` or enable `pipefail`; similarly validate `turbostat`. Also line 101 ignores `run_arm` failure:
  ```bash
  run_arm $arm $rep
  ```
  These can still produce an `ok` marker.  
  `context_start_text="perf stat -C $APPCORES"`; `context_end_text="run_arm $arm $rep"`

- **B continues after the required sysctl lift fails.** Lines 33–35:
  ```bash
  else
    echo "### SUDO-SYSCTL-FAILED - perf windows will fail" >>"$OUT"
  fi
  ```
  Abort immediately. Running known-invalid windows wastes the lease.  
  `context_start_text="if sudo -n sysctl"`; `context_end_text="perf windows will fail"`

- **B’s restore is not verified and failure is forgotten.** Lines 16–19:
  ```bash
  sudo -n sysctl -w kernel.perf_event_paranoid=4 >/dev/null 2>&1
  echo "paranoid restored: $(cat /proc/sys/kernel/perf_event_paranoid)" >>"$OUT"
  PARANOID_SET=0
  ```
  Retry and verify the proc value before clearing the flag; emit a high-priority failure marker if restoration fails.  
  `context_start_text="restore_paranoid() {"`; `context_end_text="PARANOID_SET=0"`

- **B relaunch logic does not protect the active window.** `ensure_decoding` checks only before each 12-second interval. Runtron may exit during `perf stat`, leaving part of that window idle; the next check merely relaunches for the following group. Relaunch also resets sequence depth, invalidating cross-group phase alignment.

**R2. Campaign A design**

- Eight paired repetitions with alternating arm order is adequate as a baseline **if paired confidence intervals show stability**; do not assume sufficiency solely from `n=8`.
- Context order is always ascending, so context, elapsed time, temperature and cache/page-cache state are confounded. Use a pre-generated seeded permutation per repetition, preferably balanced with each context occupying each order position approximately equally.
- Add explicit unmeasured warmups for both binaries before the grid. Otherwise the first clean cell bears cold model/page-cache/frequency effects.
- Record: exact context/arm order and seed, generated-token count/EOS reason, wall time, CPU frequency/temperature, kernel, git commit/diff, binary hashes, and per-node hugepage availability.
- Verify and record `lscpu -e=CPU,NODE,SOCKET,CORE` for app/device cores. `--numa 0` is not enough evidence that first-touch, hugepage allocation, PCIe locality and sibling activity are equivalent.

**R3. Campaign B counters**

- G1 consumes two GP counters; `instructions`, `cycles`, and `ref-cycles` normally use fixed counters. G2, G3 and G6 each require four GP counters. G7 requires two. G4 and G5 use separate uncore/MSR PMUs.
- The NMI watchdog commonly reserves one programmable counter. Therefore four-event G2/G3/G6 are not safely within budget while it is enabled. Either obtain approval to disable/restore the watchdog, or split those groups to at most three events.
- The current comma lists are not strong perf groups. Perf may multiplex silently. Use brace groups and reject any `<not counted>`, `<not supported>`, or `time running != time enabled`; first run a smoke measurement for every group.
- The stated GNR encodings are consistent with Intel GNR perfmon definitions: `D1/08`, `D1/10`, `D1/20`, `2E/41`, and `D3/01`/`D3/02`. Still pin provenance to the exact GNR JSON revision and check each event’s `Counter`/constraint field against the installed CPU stepping.
- One 12-second window is not defensible for the reported phase-sensitive effects. Use at least three synchronized windows per arm/group, preferably across independent launches, and report dispersion. Rotate/balance group order if multiple groups share one launch.

**R4. Phase comparability**

Endorse **(c) plus (b)**, but only with verified semantics:

1. Use deterministic generation with EOS ignored/disabled.
2. Start measurement from an explicit machine-readable token-progress signal at a fixed token index—not a potentially buffered human log line.
3. Measure the same token-index interval or start depth for every arm.

Better operationally: launch a fresh identical workload per group, wait for prefill plus a fixed token index, measure 12 seconds, then terminate it. This removes sequential group/depth confounding. Option (a) alone does not align phases and increases the risk that the process ends inside a window.

**R5. Clean-vs-mirror fairness**

As written, provenance is insufficient. Lines 61–69 reuse one binary while reconfiguring its build directory for the other:
```bash
[ -x $WT/gen/runtron.mirror ] || { echo missing-mirror >"$MARKER"; exit 1; }
...
cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=OFF -DTRON_AMX_K_MIRROR=OFF -DCMAKE_CXX_FLAGS= >/dev/null && cmake --build gen --target runtron -j96
...
sha256sum gen/runtron.clean gen/runtron.mirror
```
`sha256sum` proves identity of files, not equal source/toolchain/options. Reconfiguring `gen/` can also regenerate runtime sidecars or model artifacts subsequently consumed by the reused mirror binary.

For a headline result, build both binaries from the same commit/worktree and Nix closure in separate build directories. Diff normalized CMake caches and record compiler/link commands. Confirm the mirror build differs only in intended AMX/mirror options and that neither binary loads configuration-dependent artifacts from the other build directory.

**Campaign A verdict: NO-GO as written.**

Fixes ranked by urgency:

1. **P0:** Make journal and connection checks fail closed.
2. **P0:** Acquire `campaign_guard_acquire --allow-serving` before inspecting/stopping rinzler.
3. **P0:** Replace broad `pkill` with tracked PID/process-group cleanup.
4. **P1:** Mark clock/CI-truncated output incomplete, never `ok`.
5. **P1:** Build clean and mirror from identical provenance in separate build directories before using the result as a headline comparison.
6. **P1:** Add balanced seeded context order and symmetric warmups.
7. **P2, campaign B:** Abort on sysctl failure, verify restoration, propagate pipeline/run failures, split four-counter groups or disable/restore the watchdog, and redesign phase-synchronized repeated windows.

---

AGENT'S TURN: Evaluate this perspective alongside your analysis to form a comprehensive solution and continue with the user's request and task at hand.