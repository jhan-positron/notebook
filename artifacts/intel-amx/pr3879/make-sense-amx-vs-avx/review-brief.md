# Review brief: two guarded campaigns queued for delphi-3bda after tonight's CI window

Host: delphi-3bda, 2x Xeon 6962P (Granite Rapids), 288 CPUs (HT on -> 4 general PMU counters
per hw thread), 512x1GB hugepages, runs nightly CI (authoritative busy signal = lease file
/run/lock/systems-test-ci.lease; CI prep starts 03:30Z, usually done by 09:30Z). Production
serving (rinzler@0-3) may linger after the nightly; policy: stop it ONLY when journal shows no
non-heartbeat traffic for 10 min AND no remote client connections; never restart it.
Model under test: ingested-qwen-3-4b-instruct-2507-tp2 (36 layers, 32 q-heads/8 KV heads/128).

## Campaign A (queued, self-starts ~09:15Z): run-ctxfill.sh
Purpose: complete the deployable boost-vs-context curve. Denominator rationale: the same-binary
kill switch (TRON_AMX_DISABLE=1) measures 2-5pp slower than a clean build (code-layout effect),
so the headline pairs a CLEAN binary (all AMX compiled out: -DTRON_AMX_DISPATCH=OFF) against the
AMX arena-mirror binary. Existing clean pairs: ctx {2048, 8192} only.
Grid: 1u, ctx {256,512,1024,4096,16384} x {clean, mirror} x 8 reps, arm order alternating per
rep, 256 generated tokens per run, tok/s parsed from runtron's log line.
Known traps already handled elsewhere: NFS attribute cache can serve stale file content to the
build host seconds after a cross-host edit (verify content on build host before building);
sampled decode can stop early at an EOS token (affects run LENGTH, not tok/s line validity).
The mirror binary is reused from a build earlier tonight (sha-checked file copy); only the clean
binary is built by this script (the cmake configure it runs flips the tree's gen/ to the clean
configuration).

## Campaign B (prepared, runs in a later window, needs re-approval of the sysctl lift):
run-perfstat3.sh
Purpose: three-arm counter round (canonical AMX / arena-mirror AMX / kill-switch AVX) at 1u/8K.
Round-2 findings this design extends: EXE.AMX_BUSY 0 on kill switch, ~2.4% busy on AMX arms;
mirror dTLB tax ~80M 4K-walks/12s window vs ~0.2M canonical; busy clocks 3.52-3.55 vs 3.75 GHz.
Round-2 gaps this round must close: NO cache-miss events were captured; IMC bandwidth varied
47-76 GiB/s because EOS early-stops relaunch the workload and move the 12s windows between run
phases (prefill vs decode vs different context depths as the sequence grows 8K->16K).
Groups (12s perf stat windows on the 28 pinned app cores, no multiplexing intended):
G1 instructions,cycles,ref-cycles + uops_retired.slots + EXE.AMX_BUSY(0xb7/0x02);
G2 dTLB load walks 4K/1G/2M4M/active; G3 dTLB totals + store walks; G4 uncore IMC cas read/write
(system-wide); G5 msr aperf/mperf/tsc; G6 MEM_LOAD_RETIRED.L1_MISS(0xd1/0x08)/L2_MISS(0x10)/
L3_MISS(0x20) + LONGEST_LAT_CACHE.MISS(0x2e/0x41); G7 MEM_LOAD_L3_MISS_RETIRED local(0xd3/0x01)/
remote(0x02) DRAM. Encodings from intel/perfmon GNR core JSON (the host kernel's event list
lacks these names). kernel.perf_event_paranoid=4 on the host; the script lifts to 0 under sudo
and restores 4 in every exit path.

## Questions for you
R1. Bugs or hazards in either script (bash correctness: stop_now clock logic vs a campaign that
    starts ~09:30Z and runs into the SAME DAY's schedule; PIPESTATUS use; the smoke/relaunch
    logic in B inherited from round 2; marker/trap interactions; anything that could strand the
    DUT guarded or serving stopped).
R2. Campaign A design: is 8 reps x alternating order sufficient against drift; anything to
    randomize or record that is missing (NUMA/first-touch, run order effects, warmup discard)?
R3. Campaign B: are the event groups within the 4-GP-counter budget with HT on (G2 and G6 have
    exactly 4 each - any hidden fixed-counter or NMI-watchdog conflict that forces multiplexing?);
    are the 0xd1/0xd3/0x2e encodings right for Granite Rapids; is 12s x 1 window per group per
    run statistically defensible or should windows repeat?
R4. The phase problem: windows land at different sequence depths as decode grows 8K->16K.
    Proposals on the table: (a) shorter -l so depth is bounded; (b) poll the runtron log token
    counter and start each window at a fixed token index; (c) ignore-EOS if runtron has such a
    flag (unverified). Which do you endorse for comparable IMC/cache windows across arms?
R5. Anything that makes the clean-vs-mirror headline comparison unfair as designed (compiler
    flag deltas beyond the AMX macros, gen/ regeneration side effects, the reused mirror binary
    being from the same tree state)?
Be terse; number your answers R1-R5; quote script lines when flagging bugs.
