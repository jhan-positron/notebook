---
name: 3bda-nightly-rinzler-cleanup
description: "2026-09-15: System CI never stops its rinzler@N units (Rhys); shared takeover recipe now in lib-guard.sh rinzler_takeover_if_idle; our-half campaign.sh hook is a pending patch (classifier blocked the edit); nightly now ends ~13:20 UTC (06:20 PDT)"
metadata:
  type: project
---

Facts verified 2026-09-15 (delphi-3bda sudo journal + exec/logs):

- System CI (positron-ai/systems_test nightly) never stops rinzler@0..3 when it
  finishes, pass or fail. Rhys confirmed this in the DM D0B4RRDAREX on
  2026-09-15: once the lease file is released the machine is ours and we may
  stop rinzler.
- What stopped them on 09-08/11/13/14 was OUR whole-machine campaign
  (exec/vnnik-20260914/campaign.sh "standing policy (round 1 recipe)": 10 min
  of zero journal requests + no remote connections, then
  `sudo systemctl stop rinzler@0..3` and rm /dev/hugepages/slice-*-of-8),
  3 s to 12 min after the lease cleared.
- The our-half chain (exec/vnnik4-20260915 -> exec/vnnik2-20260915/campaign.sh)
  only logged "waiting: rinzler@N unit active" and never stopped them. On 09-15
  this left rinzler@0/@1 up for 2 h 25 min until jhan stopped them by hand.
- FIX 2026-09-15 (jhan approved "go ahead"): the recipe now lives in
  exec/lib-guard.sh as rinzler_takeover_if_idle (one attempt per call, fail
  closed; backup lib-guard.sh.bak-20260915). A 5-lens adversarial review the
  same day led to these additions on top of the round-1 recipe: lease grace
  600 s (ci_lease_busy takes an optional grace argument; heartbeat gaps of
  261-322 s were seen 2026-08-21), blackout_active check, takeover hold
  01:40-04:30 UTC (production units start 02:45, the nightly took the lease
  03:37:53-03:41:56 on 09-08..15), unit age >= 10 min via systemctl
  ActiveEnterTimestamp, 6 h latch per process (no fight with whoever restarts
  the units), journalctl stderr kept out of the journal text, an empty 10-min
  window accepted only when the last journal line is an idle SYSTEM_STATS
  (idle units log stats at growing intervals 300/450/675/1013 s), ss filter
  covering 3000-3020 + 13000-13020, and a re-check that no unit is active before
  positron slice files are removed. Unit tests: exec/lib-guard-tests/
  test-takeover.sh (45 stubbed cases, all pass), shellcheck clean. Open gaps
  the review named and I left: exec/vnnik-trace-20260914/trace.sh only waits
  (gives up after 60 min); exec/vnnik4-20260915/chain.sh step 2 has no rinzler
  check. The
  wait_clear hook for exec/vnnik2-20260915/campaign.sh could NOT be applied by
  Claude (permission classifier: "interfere with workloads"). jhan applied it
  by hand 2026-09-16 04:0x UTC with `patch -p1 <
  exec/vnnik2-20260915/takeover-hook-20260915.patch` (pre-patch backup
  campaign.sh.bak-20260915). vnnik4 verify.sh and models.sh inherit it. Hook test:
  exec/lib-guard-tests/test-wait-clear.sh (passes on the patched copy, fails
  on the unpatched file). exec/vnnik-20260914/campaign.sh keeps its own inline
  copy (finished campaign, left as a record); new whole-machine forks should
  call the shared function instead.
- Nightly now runs ~1 h 45 min longer (gemma-4-31b added 2026-09-14/15):
  expect the lease to clear ~13:20 UTC (06:20 PDT). Guard keys on the lease,
  not the clock, so nothing to change in lib-guard.sh.
- 09-15 run 34925789174 failed on the soak power threshold (2505 W > 2500 W).

**Why:** jhan's 09-15 message to Rhys assumed the CI failure path skipped a
teardown; that was wrong and cost Rhys an investigation.

**How to apply:** never attribute leftover rinzlers to CI; check the sudo
journal (`journalctl _COMM=sudo | grep "systemctl stop rinzler"`) and our logs
first. See [[delphi-3bda-hardware]] and [[3bda-shared-with-bill]].
