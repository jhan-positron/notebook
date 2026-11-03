# Draft Slack message to Jesse (run 3: cache test with the fix, plus the CME test)

Hi Jesse, thanks for run 2 (membench-jibin-002). The numbers met every criterion except one, and
I have a fix plus a second test ready in the same folder. Could you run both as one job?

**What to run**
- Repo: https://github.com/jhan-positron/asimov, folder `cache-mem-perf`, branch `main`,
  commit `ba834c0` (replaces 8ae533c).
- Build as before (`make CC=<your gcc>`, your flags). Then, as root: `sh run_all.sh`.
  It runs `run_asimov.sh` (the cache and mesh test you ran as run 2) and then `run_cme.sh` (the
  CME test) into one results directory. Please send back the whole directory, as for run 2.

**What changed in the cache test (run_asimov.sh)**
- The 256 KiB per-region OCM latency rows in run 2 still had prefetched lines (1.11 to 1.45 L2
  refills and 0.76 to 0.95 L3 refills per load). The chase now uses sparse chains for the OCM rows:
  one member line per 4 KiB page per chain, so a prefetched neighbour is never a chain member.
  The dense 1.25 MiB all-five row, which was clean in run 2, is kept beside it as the control.
- Every counter row now carries a coverage column, so a multiplexed counter group is flagged
  instead of silently accepted.
- Nothing else in the rows changed.

**The CME test (run_cme.sh, new)**
- The same loads and stores as the cache test, run through the CME (the DSU's C1-SME2 unit) from
  CPU 2 in streaming mode, with CPU 3 offline so the CME is not shared: a register round trip
  control, the latency chase at the same footprints (4 KiB to 32 MiB, fresh and flushed), the OCM
  chases, and read / write / copy bandwidth at the same footprints, plus OCM read and write.
- It needs SME2 in `/proc/cpuinfo` (your run 2 image had it: `sme sme2 smef32f32 ...`), the same
  `/dev/ocm`, the same 256 huge pages, CPUs 2 to 9 online and isolated. It opens three CME PMU
  events through the core PMU (0x3246, 0x327D, 0x327E), the way asimov-bench does. If an event
  is refused the rows still run and say so.
- The SCP firmware must arm the CME PPU in dynamic mode before the first streaming instruction
  (a core issuing SME against an unarmed CME PPU stalls with no rescue path). The arming code
  (asimov_system_enable_cme_dynamic) entered the SCP before 0.34.0, and the scp-v0.48.0 tag
  still has it, so your run 2 image (0.48.0-nopcie.1) and the control run's 0.34.0 are both
  fine. Please tell me if the firmware changes.

**Chip time**
- Between 2.5 and 4.1 s in all (est.). The cache test is run 2's script (1.63 s measured) plus
  four commands and the sparse rows, about 1.6 to 2.8 s; the CME test adds about 0.8 to 1.3 s.
  The spread is the process-launch cost: your run 2 README puts it at 3 to 5 ms per command,
  my tool still assumes 14 ms from run 1. Either way it is under your 5 s allowance; say if it
  is a problem and I will cut rows.
- `sh run_all.sh --dry-run | python3 est_chip_time.py` lists every command with the counts
  behind the 4.1 s figure.

**One extra thing, if easy**
- Any kernel message about SME during the run (`dmesg | grep -i sme`).

Thanks again. Jibin
