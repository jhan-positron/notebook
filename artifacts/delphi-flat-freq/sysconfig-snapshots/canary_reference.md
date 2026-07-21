# Canary reference (established 2026-07-19/20, RTM on, arena on, clean env)
# Post-reboot/maintenance ritual: run 1 clamp-all + 1 fast-all p1024 cell,
# compare all four absolutes + ratios; investigate if any drifts >3%.
# gpt-oss-120b tp4, 8 users, p1024/g1024 (runtron) or g1536 (talos serving)
runtron  clamp-all : gen 95.8-96.6  parse 559-561   (ab26v5/ab27, aa8&0bf)
runtron  fast-all  : gen 102.4-103.2 parse 660      (ab26v5/ab27)
serving  clamp-all : gen 89.7       prefill 735     (ab25 native geom)
serving  fast-all  : gen 96.1       prefill 897     (ab25 native geom)
serving  tron112   : gen ~94.5      prefill ~871-877 (ab22); nightly ~92.9/874
power    clamp/fast: ~530-580 W / ~750-800 W pkg (p1024 cells)
# Matching host state: sysconfig_snapshots/delphi-3bda_20260720_045931.txt
uncore GUARDRAIL (2026-07-20): mesh must run 0.8-2.5GHz auto; pinned 1.6GHz costs -6..-7% decode (ab31/ab31b). Check intel_uncore_frequency in the snapshot on any drift.
PREFLIGHT (2026-07-21, every session start + after any reboot): verify
fast/slow partition matches the plan: `sudo /usr/local/sbin/
intel-speed-select-state verify` + check FAST_CORE_RANGES in
/etc/default/intel-speed-select-state (post-unclamp plan: must contain
'1-2' and '73-74'); under load, front-end freq readback max-across-set.
RESTORE RULE: prefer `sudo systemctl restart intel-speed-select-state`
over hardcoded assoc ranges — old kit restore_all lines (REST112
containing 1-2/73-74) would re-clamp the front-end once the un-clamp
ships.
