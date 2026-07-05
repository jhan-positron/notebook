# delphi-flat-freq artifacts

Preserved copies of workspace tools that are hard to recreate. The live
(canonical) copies are on mutable NFS storage — these repo copies exist to
survive accidental workspace deletion. Update the repo copy whenever the
canonical one changes.

## flat_freq_utils.sh (v2, 2026-07-03)

- Canonical location:
  delphi-3bda:/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
  (NFS-shared; same path on delphi-3af6)
- What it is: SST-CP/SST-TF frequency-shape utilities for the delphi Xeon
  6962P hosts. `flat_freq_apply` (no args) = all 288 CPUs -> CLOS0, TF on
  (universal flat, 4100-class for <=20 busy cores/domain);
  `flat_freq_apply <cpulist>` = select mode, listed cores + HT siblings ->
  CLOS0 (4100-class), rest -> CLOS3 <= 2700; `flat_freq_revert` = boot
  default; `flat_freq_status` = read-only state. Auto-detects the
  NOPASSWD isst binary per host (3bda: /opt copy, 3af6: workspace build).
- Verified: universal flat + select mode measured on both 3bda and 3af6
  (2026-07-02/03 experiment series); used for the 24h flat sweep, the
  TRON-80 run (3af6), and the TRON-88 baseline round (3bda).
- Related handoffs: handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md
  (created v2), handoffs/claude_20260702-20260704_debug-3bda-flat-freq-run-ci-tests.md
  (benchmark usage). Central results doc:
  delphi-3bda:/scratch/jhan/flat_freq_tests/README.md
- NOTE: frequency state applied by this tool does NOT survive a reboot.
