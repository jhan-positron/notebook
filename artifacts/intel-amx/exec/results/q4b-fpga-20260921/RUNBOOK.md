# Runbook: q4b-fpga-20260921 (FPGA attention against CPU attention, qwen3-4b tp2, prompt 1024 to 8192)

Written 2026-09-21 22:3x UTC by Claude for whoever watches or finishes this campaign.

## Words used here

- DUT: device under test, delphi-3bda. Client: claude-agentsrv (this container), where campaign.sh and the harness run.
- pass: one driver run over the 9 cells of configs-full.json (prompt 1024 .. 8192, 8 users = 2 per engine, 1536 generated tokens).
- cold cell: one driver run with a single cell (cold-p<len>.json). The harness re-provisions the engines at the start of every
  driver run, so the cell meets an empty prefix cache.
- arms: fpgabase (nightly deb, FPGA attention), fpgacanon (canonical-AMX deb, FPGA attention), canon (canonical-AMX deb, CPU
  attention), base / vnnik / fpgavnnik (optional, not in tonight's list).
- marker: /bill-has-instance-0,2 on the DUT. The campaign removed it at 22:31 UTC (whole machine) and re-creates it at the end.

## Where things are

- scripts: ~/workspace/intel-AMX/exec/q4b-fpga-20260921/ (campaign.sh, dut.sh, st_ci_perf.py, launch.sh, configs-full.json, cold-p*.json)
- log: ~/workspace/intel-AMX/exec/logs/q4b-fpga-20260921.log
- results: ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/<tag>/{driver.log,perf.json,summary.txt}; .status = last status line;
  status-history.log = every status line; outcome.txt and .done / .done-with-failures / .done-aborted at the end
- tonight's knobs: DEADLINE_START 2026-09-22T00:30Z, PASS_DEADLINE 01:20Z, DRIVER_END_BY 02:15Z (ci-runner-stop timer 02:45Z, nightly lease ~03:38Z)
- tonight's list: fpgabase-pass1 fpgacanon-pass1 canon-pass1 fpgacanon-cold-p8192 fpgacanon-cold-p4096 fpgabase-cold-p8192 fpgabase-cold-p4096

## Monitoring

    tail -f ~/workspace/intel-AMX/exec/logs/q4b-fpga-20260921.log
    cat ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/.status
    grep -E "RESULT|CONFIG DONE|STOP" ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/*/driver.log | tail

## Stop early

    kill -TERM <campaign.sh pid>      (launch.sh printed it: 1154400 for the first launch, 1910785 for the 23:37 UTC relaunch; never -9, never pkill st_ci_perf.py alone)

The TERM path stops the driver, clears config.env, reinstalls the deb found at preflight (2026.09.18-3faba6d0), brings production
up, re-creates Bill's marker and releases the flock.

## Recovery if campaign.sh died without its trap

On delphi-3bda:

    kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/.lock.out); flock -n /var/tmp/jhan/3bda-campaign.lock true && echo flock free
    bash ~/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh hwattn-clear          # config.env must print 0 bytes
    cat ~/workspace/intel-AMX/exec/results/q4b-fpga-20260921/base-identity.txt   # line "restore VERSION SHA FILE"
    bash ~/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh ensure-base VERSION SHA FILE
    IDLE_MIN=5 bash ~/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh serving-down && bash ~/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh serving-up
    bash ~/workspace/intel-AMX/exec/bill-share.sh release; stat -c %s /opt/positron/user/config.env   # must print 0

## Second launch (after the 2026-09-22 nightly, lease clears about 13:20 UTC)

Remaining work (jhan, 2026-09-22 00:5x UTC: NO more CPU-attention passes; the CPU-attention data are the 2026-09-20 series plus
tonight's canon-pass1): passes 2 and 3 of fpgabase and fpgacanon, a second cold cell per FPGA arm at 8192 and 4096, and any
FPGA tag tonight did not finish. A tag whose perf.json exists is skipped, so the same list can be given again.

    cd ~/workspace/intel-AMX && NOT_BEFORE=2026-09-22T13:00:00Z DEADLINE_START=2026-09-22T19:30:00Z PASS_DEADLINE=2026-09-23T00:30:00Z \
      DRIVER_END_BY=2026-09-23T02:15:00Z TAKE_MARKER=0 \
      PASS_TAGS="fpgacanon-pass2 fpgabase-pass2 fpgacanon-cold-p8192 fpgacanon-cold-p4096 fpgabase-cold-p8192 fpgabase-cold-p4096 fpgabase-pass3 fpgacanon-pass3 fpgacanon-cold2-p8192 fpgabase-cold2-p8192" \
      bash exec/q4b-fpga-20260921/launch.sh

(PASS_TAGS is the explicit list; tags already holding a perf.json are skipped. campaign.sh accepts <arm>-cold<N>-p<len>
for repeated cold runs of one cell since 2026-09-22 01:0x UTC, atomic file replace while the first launch ran.)

## After the campaign

    python3 ~/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/ingest_fpga.py     # rows from the perf.json files
    python3 ~/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/gen_page.py        # regenerates CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html

Then the render check (cairosvg) and the artifact republish (same file path, https://claude.ai/artifact/T6c2gB9zzJQsCukmC69e51).

## Incident log

- 2026-09-21 23:11 UTC: fpgabase-pass1 done (rc 0, 36 min, 9 cells, even spread 20/20/20/20).
- 23:12 to 23:24 UTC: the switch to fpgacanon failed at serving-down. Cause: an edit of dut.sh made at 22:40 UTC (own-address
  filter for the idle test) used `awk -v own="<regex with backslashes>"`; awk -v re-reads backslashes, the pattern became a
  character class and never matched, so Caddy's four keep-alive connections from 127.0.0.1 to the engines were counted as remote
  users for 12 minutes and the idle test failed. The campaign stopped safely (restore path: nightly deb reinstalled at 23:24).
  Fix 23:27 UTC (atomic file replace, new inode): the peer address is matched with index() on a space-padded list of
  127.0.0.1, ::1 and `hostname -I`. The restore path's own serving-down still ran the broken copy and is expected to end
  with HANDOFF INCOMPLETE (engines left running; marker and flock released). Relaunch with the same PASSES: the existing
  fpgabase-pass1/perf.json is skipped.
- 2026-09-22 01:25 UTC: relaunch (pid 1910785) DONE, no problems: fpgacanon-pass1 (31 min), canon-pass1 (39 min), four cold
  cells (3-4 min each). Restore: nightly deb 3faba6d0, config.env 0 bytes, production up (4 qwen tp2 engines, FPGA attention),
  marker re-created 01:25:05, flock released. Results ingested into exec/prefill-amx-vs-fpga-20260921/fpga-campaign-rows.json.
- 2026-09-22 01:4x UTC: second launch QUEUED (pid 4073541): NOT_BEFORE 13:00Z, then the lease wait, marker take, preflight,
  PASS_TAGS fpgacanon-pass2 fpgabase-pass2 fpgacanon-cold2-p8192 fpgabase-cold2-p8192 fpgabase-pass3 fpgacanon-pass3
  fpgacanon-cold2-p4096 fpgabase-cold2-p4096; DEADLINE_START 19:30Z, PASS_DEADLINE 2026-09-23T00:30Z, DRIVER_END_BY 02:15Z.
  The page v3 (2026-09-22 01:4x UTC) already carries tonight's data; rerun ingest_fpga.py + gen_page.py after this launch.

## Finding 2026-09-22 06:5x UTC (refined 07:3x UTC): HBM exhaustion in the warm long-prompt FPGA cells

The engine journal (hbm-journal-20260921.txt in this directory, pulled with journalctl -u 'rinzler@*' 22:30 to 01:30 UTC)
holds 2,804 warnings "HBM bypass space exhausted; caller degrades to SW attention" / "shard base tok_ix N ... 36 of 36 slots
lose HW attention". exec/prefill-amx-vs-fpga-20260921/hbm_cells.py maps them onto the perf.json cell windows
(hbm-exhaustion-cells.json). Per cell (both FPGA passes): 4096 and 5120 exhausted through the whole cell (first warning in
round 1, last at 98-99 %, about 78 % of the shard placements failed, est.), 6144 exhausted for the first 76-79 % of the cell,
7168 no warning, 8192 clean in rounds 1-6 and exhausted from round 7 (AVX build, 85 warnings) or 8 (AMX build, 36). 509
warnings fall in the 30 s gaps between cells (after 3000, 4096, 5120): they are the pre-cell AMX probe's own 4 requests, and
they show the card was already full when the 3000 cell ended. None in the cold cells, none in the CPU-attention pass, none in
any earlier prompt-1024 FPGA run. Every warning names the largest free block: 0x3000 (12 KiB) on the lower-PCI card of each
engine, 0x5800 (22 KiB) on the other, constant through the window (hypothesis: full space in a steady state).

What it does NOT explain (verification workflow, 4 agents): the AMX build's warm gains under FPGA attention also appear where
nothing fell back: 2048 (-22.5 % TTFT, 0 warnings), 7168 (-30.1 % TTFT, +14.0 % TPS, 0 warnings), 8192 rounds 1-6 (-33 %,
before either arm's first warning). So exhaustion is a measured co-occurrence at 4096-6144, not the measured cause; the
cached-prefix-on-CPU hypothesis stays open (the pre-cell AMX probe reads 16-21 G cycles in every warm window without a
warning against 10.6-13.4 G on fresh engines, but it measures its own traffic). The page's sections 3, 5, 6, 8 and the Short
version say this since v7 (2026-09-22 07:3x UTC). The second launch records allocator free_total/free_max and
sw_fallback_total per device per cell (st_ci_perf.py FUSE_STATS); after it, rerun hbm_cells.py with a new journal pull:

    ssh delphi-3bda "journalctl -u 'rinzler@*' --since '2026-09-22 13:00:00 UTC' --until '2026-09-23 02:30:00 UTC' -o short-iso --no-pager | grep -E 'HBM bypass|lose HW attention|HW attention disabled'" > exec/results/q4b-fpga-20260921/hbm-journal-20260922.txt
    python3 exec/prefill-amx-vs-fpga-20260921/hbm_cells.py    # reads every hbm-journal-*.txt in the results dir

## Follow-up campaign q4b-rt8u-20260922 (runtron, 8 users on one engine, prompt 1024 / 2048 / 4096 / 8192)

Scripts exec/q4b-rt8u-20260922/{campaign.sh,summarize.py}; results exec/results/q4b-rt8u-20260922/; log
exec/logs/q4b-rt8u-20260922.log; status .status; marker .done. Runs ON delphi-3bda (started 2026-09-22 ~07:00 UTC with
START_NOT_BEFORE=2026-09-22T16:30:00Z, DEADLINE_HHMM=130). Arms base (runtron.pre3879, AVX) and canon (runtron.main0916,
canonical AMX), attention cpu and fpga, cells 8 users x 1024/2048/4096/8192 and 2 users x 4096/8192, 3 repetitions,
interleaved inside every repetition. Each run's rt-results.txt record carries an HBM-EXHAUSTION line (counts of the two
warnings in that run's log). It waits for the whole-machine second launch (campaign flock) and takes over idle production
serving; at the end it brings production up again through platformd (dut.sh serving-up). Stop: kill -TERM the campaign.sh
pid on 3bda (finish aborted runs the cleanup).

## 2026-09-22 16:25 UTC: second launch DONE

outcome.txt: "incomplete passes: none; stop reason: none; problems: none". Tags fpgacanon-pass2, fpgabase-pass2,
fpgacanon-cold2-p8192, fpgabase-cold2-p8192, fpgabase-pass3, fpgacanon-pass3, fpgacanon-cold2-p4096, fpgabase-cold2-p4096,
all rc 0, every cell 20/20/20/20 except three cells with one engine unreported (fpgabase-pass2 2048, fpgabase-pass3 7168,
fpgacanon-pass3 1536). Restore ok (nightly deb, config.env 0 bytes, production up, marker re-created 16:25:14). Journal pull
hbm-journal-20260922.txt (13:00 to 16:30 UTC, 5,702 lose-HW-attention lines); hbm_cells.py now covers 51 cells. The per-cell
FUSE counters (hbm_sw_fallback_dev0/1 deltas, hbm_free_total_after per engine) are in each perf.json raw record: free_total
falls to 59,113,472 B (56.4 MiB) on every card in the exhausted 4096/5120 cells (= full space, not fragmentation), recovers to
5-12 GB during 6144, and the fallback deltas agree with the journal counts. Fresh-engine free space is about 30-31 GB per card
(est. from the cold cells: free_total after + the cell's own shards), so weights + fixed allocations take about 3-4 GB (est.).

## 2026-09-22 16:36 UTC incident: platformd 0.11 restarts engines that the guard stops with systemctl

The runtron campaign q4b-rt8u-20260922 (runs ON 3bda) took over idle production at 16:36:07 with lib-guard.sh
rinzler_takeover_if_idle = `systemctl stop rinzler@0..3`. platformd 0.11 supervises the engines and started them again at
16:37:08 ("inference Adding server engine=default-0"), so the campaign's watcher saw rinzler@N active 10 s into the first run
and stopped it (RUN-STOPPED rc=143 WATCH-STOP). The 6-hour "someone started them" latch then kept the campaign waiting; it was
stopped with kill -TERM at 16:39 (clean: flock and marker released, production up). Fix (lib-guard.sh, backup
lib-guard.sh.bak-20260922): new rinzler_stop_serving() takes serving down through POST http://localhost:8080/api/inference/down
when platformd answers (the same call dut.sh serving-down makes) and waits up to 180 s for the units to stop; systemctl stop
stays the fallback without platformd. lib-guard-tests: 45 + 6 pass. The CI-harness campaign (q4b-fpga) was never affected: it
uses dut.sh serving-down (platformd API) itself. Relaunch of q4b-rt8u: the Claude Code classifier denied the launch command
from the agent session ("Modify Shared Resources"); jhan runs it by hand:

    ssh delphi-3bda 'cd ~/workspace/intel-AMX && DEADLINE_HHMM=130 setsid nohup bash exec/q4b-rt8u-20260922/campaign.sh >/dev/null 2>&1 </dev/null & sleep 5; pgrep -f "^bash exec/q4b-rt8u-20260922/campaign.sh"; tail -3 exec/logs/q4b-rt8u-20260922.log'

(the script appends to its own log; the aborted-run marker exec/logs/q4b-rt8u-20260922.done was moved aside at 16:46 UTC;
START_NOT_BEFORE unset = start at once; the stopped rep-1 run is redone because its log has no "average tok/s" line.)

## 2026-09-22 18:12 UTC: runtron campaign q4b-rt8u-20260922 DONE

Launched by jhan by hand at 16:58 UTC (after the classifier denial). Takeover through platformd worked (log line "platformd
answers, taking serving down through POST .../api/inference/down"); 72 runs, rc 0, no HBM-exhaustion warning in any run;
production back up through dut.sh serving-up at 18:12 (4 engines running, marker present, flock free). Results:
exec/results/q4b-rt8u-20260922/summary.{md,json}. Key numbers (mean of 3 repetitions): 8 users x 8192 prefill (batched, runtron)
AVX-CPU 123.1 s, AMX-CPU 53.5 s, FPGA+AVX 29.7 s, FPGA+AMX 29.1 s; decode per user 14.5 / 17.1 / 61.5 / 61.5 TPS. AMX build vs
AVX build under FPGA attention: prefill -0.3 to -2.0 % (8 users), decode within 1.2 %. Page section 7 (v8) carries it.

## 2026-09-22 19:4x UTC: page v9 published (artifact Version 8)

Three passes per FPGA arm, aggregated exhaustion table with counters, section 7 = runtron campaign. 52 verification findings
applied (workflow wf_29fc06f2-9fd). Two lessons for the next round: (1) a degraded shard warns once and stays on CPU attention
while its prefix-cache node lives, so "0 new warnings" in a later cell does not mean "no CPU attention" (h/tron/shard.hpp:8-31,
h/tron/scheduler/full.hpp:2400-2428); only cells before the first exhaustion of a pass are clean. (2) Three FPGA-arm cells had a
mid-cell engine restart (fpgabase pass 2 at 2048, fpgabase pass 3 at 7168, fpgacanon pass 3 at 1536: one engine unreported,
2-3 Caddy health events, counters reset); the two 7168 exhaustion cases are on exactly those engines. Pass 1 is the only pass
without a restart on either arm. Regenerate: ingest_fpga.py, hbm_cells.py, gen_page.py (rt8u_section.py reads
exec/results/q4b-rt8u-20260922/summary.json).
