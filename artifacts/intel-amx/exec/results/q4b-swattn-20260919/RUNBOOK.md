# q4b-swattn-20260919: how this campaign is run and finished (handoff for whoever picks it up)

Plan: CI-test/status/qwen3-4b-Saturday-plan.md. Scripts: exec/q4b-swattn-20260919/ (copied from exec/l8b-levers-20260919/,
originals in .orig/). Results: this directory. Log: exec/logs/q4b-swattn-20260919.log. Report target:
CI-test/status/Saturday-qwen3-4b.html (written by gen_report.py at the end of the Sunday run; render check and artifact publish are manual).

## Two launches (both detached on the client host, launch.sh)

1. Saturday night 2026-09-19 (check-only): `CHECK_ONLY=1 DEADLINE_START=2026-09-20T00:15:00Z PASS_DEADLINE=2026-09-20T00:30:00Z DRIVER_END_BY=2026-09-20T01:00:00Z bash launch.sh`
   = preflight, save debs, hwattn-off, canon, the check cell 8 users x prompt 8192, restore (hwattn-clear first), production up,
   marker released. Writes configs-used.txt (configs-full.json, or -no8192/-no7168 if the check dropped cells), check-8u-p8192/,
   outcome-check.txt, .done-check.
2. Sunday 2026-09-20 (the six passes): `NOT_BEFORE=2026-09-20T13:00:00Z CHECK=0 TAKE_MARKER=0 DRIVER_TIMEOUT=4800 bash launch.sh`
   (defaults: DEADLINE_START 19:30Z, PASS_DEADLINE 23:45Z, DRIVER_END_BY 2026-09-21T01:00Z). Sleeps until 13:00 UTC (the nightly's expected
   END minus 20 min: an ABSENT lease file reads as free, so NOT_BEFORE must never fall inside the nightly's possible window 03:30-13:20),
   then waits for the CI lease in case the nightly runs late, the peer pgrep, the flock, takes Bill's marker (retries every 30 min while he
   is active, re-checking the lease each time, gives up at DEADLINE_START), re-checks the lease, preflight (the installed package = the NEW
   nightly deb = RESTORE target, saved as restore.deb; base arm stays 2026.09.18-3faba6d0 from nightly.deb), hwattn-off, passes base canon
   base canon base canon, restore (hwattn-clear first), analyze.py, gen_report.py. CHECK=0 is valid only when configs-used.txt exists
   (tonight's run reached its verdict, .done-check or prev-*-done-check present); otherwise the driver runs the check cell itself first.
   At start, campaign.sh renames the previous run's end-state files to prev-<time>-<name> (done-check, outcome-check.txt, preflight.txt, status).

## Known gap (permission classifier refused the fix on 2026-09-19): no dead-man switch for config.env

If the CLIENT host dies (reboot, SIGKILL of campaign.sh) while USE_HW_ATTN=0 is in /opt/positron/user/config.env, nothing on the machine
clears it: production engines started later (ci-runner-stop 02:45 UTC, the nightly) would run software attention. A transient systemd
timer on the DUT that truncates the file at DRIVER_END_BY + 10 min was designed and tested in a dry form, but creating the unit was
refused as "unauthorized persistence". jhan can arm it by hand on delphi-3bda before the Sunday window:
    sudo systemd-run --on-calendar="2026-09-21 01:10:00 UTC" --unit=q4b-deadman /bin/bash -c 'truncate -s 0 /opt/positron/user/config.env'
and disarm it after the run with `sudo systemctl stop q4b-deadman.timer`. Without it: if the campaign log stops mid-run, run the RECOVERY
sequence in campaign.sh's header (hwattn-clear first).

## Check-only run result (2026-09-19 22:15-22:3x UTC)

Check cell 8 users x prompt 8192 on the canonical deb, software attention: driver rc 0 in 8 min; cell wall time 394 s (plan estimate
273 s, so 1.44x); TPS mean 60.18 (sd 0.69, min 58.23); TTFT mean 12.7 s (max 13.9 s); server-counted prompt tokens 7658 to 8158 (mean
7890, band 7392 to 8592; the qwen template counts fewer tokens than the harness's prompt_length, measured offline as -534 to -34);
AMX-busy 38.2 G cycles; FUSE max_prompt_tokens = max_total_tokens = 131072 on all 4 engines; USE_HW_ATTN=0 on all 4 engine pids;
Caddy spread 20/20/20/20; 0 anomalous samples; binary check ok. Verdict: all 9 cells stay (configs-used.txt = configs-full.json).
Pass estimate from it: 1.44 x 28.7 min of cells + 4 min = about 46 min (est.); six passes + switches about 5.2 h (est.); Sunday
DRIVER_TIMEOUT 4800 s (1.7x the estimate).

## Monitoring (from the client host; a Monitor tail -F on the NFS file delivers nothing, use a periodic grep)

    cat exec/results/q4b-swattn-20260919/.status; tail -5 exec/logs/q4b-swattn-20260919.log
    ls exec/results/q4b-swattn-20260919/   # .done-check / .done / .done-with-failures / .done-aborted
    ssh delphi-3bda 'stat -c %s /opt/positron/user/config.env; dpkg-query -W -f="${Version}\n" tron; ls /bill-has-instance-0,2; systemctl list-units "rinzler@*" --no-legend'

## After the Sunday run (.done or .done-with-failures present)

1. `cat outcome.txt summary.txt; tail -30 status-history.log` and read gen_report.log / analyze.log for warnings.
2. If the report is stale or missing: `python3 exec/q4b-swattn-20260919/analyze.py` then `python3 exec/q4b-swattn-20260919/gen_report.py`.
3. Render check: extract each inline SVG from CI-test/status/Saturday-qwen3-4b.html and rasterize with cairosvg, look at the PNGs
   (labels in the arrow corridors, overlapping text). Assert pure ASCII (`LC_ALL=C grep -P '[^\x00-\x7F]'` must print nothing).
4. Publish as a private artifact (Artifact tool, file_path = the html, icon chart); give jhan the link. Do not post to Slack or GitHub
   (plan 2a); jhan decides filing and the optional gen_ci_shapes.py feed.
5. Check the machine end state: config.env 0 bytes, the restore-target deb installed (base-identity.txt line "restore ..."), rinzler@0-3
   active (HANDOFF=up), Bill's marker present, flock free.

## To stop early

`kill -TERM <campaign.sh pid>` (the pid launch.sh printed). Never -9 and never pkill st_ci_perf.py alone. Recovery steps if the script died
without its trap are in the header of campaign.sh (hwattn-clear FIRST, then ensure-base of the restore line, serving-down/up, marker release).
