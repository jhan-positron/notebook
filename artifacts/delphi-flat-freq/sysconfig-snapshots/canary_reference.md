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
