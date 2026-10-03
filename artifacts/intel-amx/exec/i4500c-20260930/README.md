# i4500c-20260930: perf record of the Save K gap, after the i4500b chain

Short version. The 2026-09-30 decode traces (exec/results/i4500b-20260930/traces) show the main thread's Save K span
of the policy build (452b2052c9) at about twice the canonical build's per pass (105 vs 58 us at tp2 with 2 users, 171
vs 111 at tp4 with 4 users) although both write the same 4 cache lines per (token, KV head). A store rewrite (0bb74c2ab0,
dropped) was refuted by review: the production K buffer is bf16, so the old path was one memcpy already. This chain
waits for the i4500b chain's end marker and then records perf profiles of both runtron binaries in decode (perf.sh) so
the gap can be attributed by symbol. Words: see exec/i4500b-20260930/README.md.
