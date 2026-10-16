---
name: amd-amx-fallback-test
description: 2026-09-11 AMD (andoria-06) test that the AMX-enabled runtron takes the AVX path; the amxprobe LD_PRELOAD shim method (strace breaks runtron's FUSE mount) and the Intel control
metadata:
  type: project
---

Result (2026-09-11, head 47f6f2dceb): on andoria-06 (AMD EPYC 9654, no amx cpuinfo flags) the
runtron built with -DTRON_AMX_DISPATCH=ON (gen-amd/, 32 tdpbf16ps instructions, 10
amx_attn_h128g4 symbols) ran ingested-qwen-3-4b-instruct-2507-tp2 with USE_HW_ATTN=0 and
TRON_AMX_DISABLE unset and never issued arch_prctl(ARCH_REQ_XCOMP_PERM); tokens identical to the
TRON_AMX_DISABLE=1 arm. Intel control on delphi-3bda (Friday binary gen/runtron): the same run
DID issue arch_prctl(0x1023, 18) = 0 with AMX enabled and did not with the kill switch. Logs:
exec/logs/amd-amx-20260911/ (andoria-06-*.log/.probe/.tokens, 3bda-*), script
exec/amd-amx-20260911/run-andoria06.sh, shim source exec/amd-amx-20260911/amxprobe.c.

Method facts that cost time:
- strace (even -f -b execve) breaks runtron: the setuid fusermount3 helper loses privileges under
  ptrace -> "fusermount3: mount failed: Operation not permitted" -> runtron exits 1 before load.
  Use the LD_PRELOAD shim (interposes libc syscall(); runtron links syscall dynamically) with
  AMXPROBE_FILE=<path>; it logs "loaded in pid" and any arch_prctl(0x1023) call.
- Put the FUSE stats mount on local disk: --fuse-mount /var/tmp/jhan/<name> (default is under the
  NFS worktree stats/instance-N; worked too, but keep local).
- Token identity ON vs OFF is NOT proof: on Intel the 29-token qwen run was also identical.
- andoria-06 second half = SYSTEM_CONFIG "--instance 1,2" = devices 81/a1/c1/e1:00.0, NUMA 1,
  slices 4-7 of 8. tron adopts/reuses an existing unlocked slice file of another user
  (tzhou's slice-4-of-8 was truncated 16 GiB -> 4 GiB and kept tzhou ownership). runtron keeps
  slice files at exit; remove ours after fuser check, leave others'.
- Build recipe on andoria-06 (nix develop, 32 jobs): cmake --preset cross-avx512 -B gen-amd
  -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= ; target runtron; 9 min
  wall incl. the Haskell ingest build. jhan is in the sudo group there (unused).

**Why:** the probe is the only observable of available(); no log/counter exists.
**How to apply:** reuse the shim for any "did AMX engage" question on any host; pair every AMD
negative with an Intel positive control. See [[runtron-determinism-recipe]], [[amx-ci-coverage-facts]].
