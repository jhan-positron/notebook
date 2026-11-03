import sys
p='perf-measurement-tech.html'
d=open(p).read()
R=[]
def rep(old,new): R.append((old,new))
rep('One thread on CPU 3, best of 3 repetitions,','One thread on CPU 0 (the first entry of <code>--cpus 0-119</code>), best of 3 repetitions,')
rep('--cpus 0-118:2 · one thread per port: 134 GB/s for two threads','--cpus 0,2 · one thread per port: 127 GB/s for two threads (0,64 across meshes: 134 GB/s)')
rep('a stride-2 list puts them on two ports for 134 GB/s','a stride-2 list puts them on two ports for 127 GB/s (134 GB/s when the second thread is on the other mesh)')
rep('<text x="215" y="76" text-anchor="middle">1.05 refills per line</text>','<text x="215" y="76" text-anchor="middle">0.83 of lines leave the core</text>')
rep('Per-line rates are from the home-node counters of <code>run_sudo.sh</code> part 3 after the short/long subtraction (section 3.6).</figcaption>',
    'Per-line rates are from the home-node counters of <code>run_sudo.sh</code> part 3 after the short/long subtraction (section 3.6). L2 refills were not counted on this stream; the L2 figure is the slice access rate (19 % of lines hit L2).</figcaption>')
rep("Reads never cross a CCG: a proxy on the core's own mesh serves lines homed on the other mesh.",
    "A read that hits the mesh cache does not cross a CCG: a proxy on the core's own mesh serves lines homed on the other mesh (0.000 other-mesh accesses at 1 thread × 8 MiB). A read that misses to DRAM homed on the other mesh does cross (0.027 other-mesh accesses per line at 14 threads × 8 MiB; 0.50 remote memory requests per line for 32 readers on each mesh).")
rep('The timed passes then hit (0 L1 refills at 32 KiB; 0.000 slice misses at 8 MiB, 1 thread).',
    'The timed passes then hit (0.000 slice misses at 8 MiB, 1 thread, in the bandwidth tool; the latency tool shows 0 L1 refills up to 64 KiB, and no counter run was taken on the bandwidth loop at 32 KiB).')
rep('<p class="pit"><b>Pitfall:</b> a contiguous list for 40 threads works 20 pairs, and the mesh-cache read total is 1.6 to 1.7 × lower than one thread per pair. The slices get the blame for a port limit.</p>',
    '<p class="pit"><b>Pitfall:</b> a contiguous list for 40 threads works 20 pairs. Measured at 2 threads: two partners on one pair read 78 GB/s, two threads on separate ports 127 to 134 GB/s, so a shared port costs 1.6 to 1.7 × (results/followup-20261030T194205Z/pair.csv). At 40 threads × 3 MiB the contiguous list (CPUs 0 to 39, mesh 0 only) read 733 GB/s against 1,349 GB/s one per pair (CPUs 0 to 78 even, both meshes); that 1.8 × gap mixes the port limit with the mesh split (results/slc-20261030T194835Z/slc.csv). A port limit is then misread as a slice limit.</p>')
rep('256 MiB at 16+ threads keeps the total under a tenth of RAM and the first touch short: 120 × 1 GiB would take minutes to touch.',
    '256 MiB at 16+ threads keeps the resident total at 60 GiB at 120 threads (two buffers per thread, since <code>all</code> includes copy: under a fifth of the 320 GiB) and the first touch short: 120 × 2 × 1 GiB would take minutes (est.) to touch.')
rep('a 512-line re-check must agree 98 %','a 256-line re-check must agree 98 %')
rep('<td class="l">L2-to-L1 fill, about 30 B/cycle (measured, not documented)</td>','<td class="l">85.2 GB/s = about 30 B/cycle at 2.8 GHz; limiting hop not identified (hypothesis: L2-to-L1 fill width)</td>')
rep('85.2 ≈ 30 B/cycle: L2 fill path','85.2 ≈ 30 B/cycle: hop not identified (L2 fill path is a hypothesis)')
rep('<li><b>Label what is not proven.</b> The pair port as a CAL, the CCG as the write-collapse bottleneck, and the two-vector-pipe reading of the C loop are hypotheses in the source; the document says so where it uses them.</li>',
    '<li><b>Label what is not proven.</b> When a number rests on a reading that no counter confirmed, say so next to the number and name the test that would settle it.</li>')
rep('(the counter check of part 5 was run for 8 MiB and 1 GiB only).</li>',
    '(the counter check of part 5 was run for 8 MiB and 1 GiB only); whether the pair port is a CAL (Component Aggregation Layer, Arm\'s block that puts two devices on one XP port; the source\'s reading, not tested on CRB); whether two vector pipes explain the compiled read loop\'s 1.5 loads per cycle (the 3-loads-per-2-adds test was not run).</li>')
rep('The three request-count names (write, read, hbt) share id 0x5 with different filters',
    'The three request-count names, <code>hns_pocq_reqs_recvd_write</code>, <code>_read</code> and <code>_hbt</code> (hbt: home-bound traffic, the read filter that counts only requests at the true home node and excludes the local-proxy share), share id 0x5 with different filters')
rep('<div><b>THP</b>: transparent huge pages, 2 MiB pages the kernel gives without a request.</div>',
    '<div><b>THP</b>: transparent huge pages, 2 MiB pages the kernel gives without a request.</div>\n<div><b>TLB</b>: translation lookaside buffer, the core\'s cache of virtual-to-physical page translations; a miss costs a page-table walk.</div>')
rep('<div><b>XP</b>: a crosspoint, one router of the mesh; its "ports" attach devices such as cores and home nodes.</div>',
    '<div><b>XP</b>: a crosspoint, one router of the mesh; its "ports" attach devices such as cores and home nodes.</div>\n<div><b>Flit</b>: a flow-control unit, the fixed-size piece of a mesh packet that one link moves per cycle; the <code>mxp_*_txflit_valid</code> events count them and <code>mxp_*_txflit_stall</code> counts cycles a flit waited.</div>')
rep('next to the compiled C loops (<code>read</code>, <code>write</code>, <code>copy</code>).</div>\n</div>',
    'next to the compiled C loops (<code>read</code>, <code>write</code>, <code>copy</code>).</div>\n<div><b>x86 terms in the Elsewhere notes</b>: AVX-512 and zmm (Intel\'s 512-bit vector instructions and their registers); SysV ABI (the x86-64 Linux calling convention); SMT (two hardware threads on one core); IMC (the memory controller on the chip); UPI (Intel\'s socket-to-socket link); uncore and CHA (the blocks outside the cores, and the caching/home agent that owns one L3 slice); APIC id (a logical CPU\'s hardware id).</div>\n</div>')
rep('<li>With 4 KiB pages a 1 GiB buffer is 262,144 pages and the TLB walks become part of the measurement. With 2 MiB pages it is 512 pages.</li>',
    '<li>With 4 KiB pages a 1 GiB buffer is 262,144 pages. The page-table walks that refill the TLB then become part of the measurement. With 2 MiB pages it is 512 pages.</li>')
rep('<p class="pit"><b>Pitfall:</b> a zero-fill loop at -O3 becomes <code>memset</code>, which on arm64 glibc uses <code>DC ZVA</code> for large buffers: whole lines are zeroed without the store pipes, and the number is not the application\'s store path.</p>',
    '<p class="pit"><b>Pitfall:</b> a zero-fill loop at -O3 becomes <code>memset</code>. On arm64 glibc, <code>memset</code> of a large buffer uses <code>DC ZVA</code> (the Arm "data cache zero by address" instruction, which zeroes a whole cache line without going through the store pipes). The number is then not the application\'s store path.</p>')
rep('<p class="pit"><b>Pitfall:</b> a global sink, or per-thread results packed into adjacent 8-byte slots, false-shares; the many-thread L1 number then falls and the drop looks like a mesh limit.</p>',
    '<p class="pit"><b>Pitfall:</b> a global sink, or per-thread results packed into adjacent 8-byte slots, causes false sharing (several cores write different words of one 64 B line, so the line moves between their caches on every write). The many-thread L1 number then falls, and the drop looks like a mesh limit.</p>')
rep('On a machine with several memory nodes, this is also what places the pages.',
    'On a NUMA host (non-uniform memory access: each group of cores has its own nearer memory, and a page lives in the memory of the core that first writes it), this is also what places the pages. CRB has one NUMA node, so this does not apply here.')
rep("the pages on the main thread's node.","the pages on the main thread's NUMA node.")
rep('<h4>A loads-only loop: eight ldp of 16 B registers per 256 B</h4>','<h4>A loads-only loop: eight ldp (load pair) of 16 B registers per 256 B</h4>')
rep('The body is 8 × <code>ldp</code>, <code>add</code>, <code>cmp</code>, <code>b.lo</code>: 11 instructions per 256 B.',
    'The body is 8 × <code>ldp</code> (load pair: one instruction fills two 16 B registers, 32 B, from one address), <code>add</code>, <code>cmp</code>, <code>b.lo</code>: 11 instructions per 256 B.')
rep('8 × <code>stp q0, q0</code>, add, cmp, b.lo.','8 × <code>stp q0, q0</code> (store pair: one instruction writes two 16 B registers, 32 B, to one address; here the same register twice), add, cmp, b.lo.')
rep('<h4>The compiled read loop: 16 accumulators, and why it still loses</h4>','<h4>The compiled read loop: 16 accumulators, and why it is still slower</h4>')
rep('<li><code>k_read</code> sums into 16 independent accumulators, which gcc folds into 8 vector chains on 128-bit NEON. That hides the 2-cycle add latency, so the loop is not latency-bound.</li>',
    '<li><code>k_read</code> sums into 16 independent accumulators, which gcc folds into 8 vector chains on NEON (Arm\'s 128-bit vector instruction set). Eight chains hide the 2-cycle add latency. The loop is therefore not limited by add latency.</li>')
rep('<li>It is still issue-bound: one vector add per load.','<li>It is still issue-bound (limited by how many instructions the core can start per cycle): one vector add per load.')
rep('the asm loop is the pipe ceiling.','the asm loop is the pipe upper bound.')
rep('The benchmark pins this down with three levers: the footprint per thread (which cache level the stream lands in), the instruction mix (a loads-only or stores-only loop next to a compiled loop), and the thread placement (which port, mesh, or chip link the streams share).',
    'The benchmark isolates that hop with three measurement variables, changed one at a time: the footprint per thread (hence the cache level), the instruction mix (loads-only, stores-only, or compiled loop), and the thread placement (a shared port, one mesh, or the chip link).')
rep('the lever that picks the cache level.','the measurement variable that picks the cache level.')
rep('Placement is the lever that separates a port bound from a mesh bound','Placement is the measurement variable that separates a port bound from a mesh bound')
rep('The counters later showed 0.30 slice misses per line at 14 threads, because one core reaches only 64 MiB of the slices.',
    'The counters later showed 0.30 slice misses per line at 14 threads. The reason is that one core reaches only 64 MiB of the slices.')
rep('<p class="pit"><b>Pitfall:</b> a <code>malloc</code> buffer is page aligned at best, so its first and last partial 2 MiB are 4 KiB pages; on a THP "madvise" host the whole buffer is.</p>',
    '<p class="pit"><b>Pitfall:</b> a <code>malloc</code> buffer is page aligned at best. On CRB (THP "always") its first and last partial 2 MiB are therefore 4 KiB pages. On a THP "madvise" host the whole buffer is 4 KiB pages.</p>')
rep('The value is not byte-repeating, so gcc cannot turn <code>k_write</code> into <code>memset</code>, and each pass writes different data.',
    'The value is not byte-repeating. gcc therefore cannot turn <code>k_write</code> into <code>memset</code>. The pass counter also makes each pass write different data.')
rep('''<li>The script re-executes itself under <code>taskset -c 0-119</code> once, so every child inherits the mask and the reserved CPUs 120 to 127 are never touched.</li>
<li><code>guard()</code> launches each measurement with <code>setsid</code> so perf and the benchmark form one process group, polls the shared-host marker every 5 s, and on its appearance kills the group (TERM, 1 s, KILL) and exits 3. The kills are guarded against <code>set -e</code>.</li>
<li>Results go to a UTC-stamped directory, stdout and stderr are teed into <code>log.txt</code>, the binaries are rebuilt first, and an exit trap gives the results back to the invoking user.</li>''',
'''<li>The script re-executes itself once under <code>taskset -c 0-119</code>. Every child inherits that mask. The reserved CPUs 120 to 127 are never touched.</li>
<li><code>guard()</code> launches each measurement with <code>setsid</code>, so perf and the benchmark form one process group. It polls the shared-host marker every 5 s. If the marker appears, it kills the group (TERM, then KILL after 1 s) and exits 3. The kills are guarded against <code>set -e</code>.</li>
<li>Results go to a UTC-stamped directory. stdout and stderr are copied into <code>log.txt</code>. The binaries are rebuilt first. An exit trap gives the result files back to the invoking user.</li>
<li><code>PARTS</code> picks which numbered parts run: the default <code>1234</code> skips part 5, so <code>sudo PARTS=5 ./run_sudo.sh</code> runs the six-minute write-path part alone and <code>PARTS=12</code> runs the two homelat parts only.</li>''')
rep('<p class="ref">run_sudo.sh:23-58</p>','<p class="ref">run_sudo.sh:20, 23-58</p>')
rep('''exec > >(tee -a "$OUT/log.txt") 2>&amp;1</pre>''','''exec > >(tee -a "$OUT/log.txt") 2>&amp;1
...
PARTS=${PARTS:-1234}
part() { [[ $PARTS == *$1* ]]; }</pre>''')
rep('Every kernel walks its buffer start to end, so the prefetcher helps and the number is the throughput of the hop that saturates.',
    'Every kernel walks its buffer start to end. The prefetcher therefore helps. The number is the throughput of the hop that saturates.')
rep('one perf run over a 1 GiB-per-thread case counts the first-touch writes and the warm-up with the loop, so a "misses per line" figure for a read stream contains the write stream\'s misses.',
    'one perf run over a 1 GiB-per-thread case counts the first-touch writes and the warm-up together with the loop. A "misses per line" figure for a read stream therefore contains the write stream\'s misses.')
rep('up to 8 MiB, so without the asm loop L1 and L2 would look equally fast.','up to 8 MiB. So without the asm loop L1 and L2 would look equally fast.')
rep('into a separate <code>b</code>, so a load stream and a store stream both hit the level under test.','into a separate <code>b</code>. So a load stream and a store stream both hit the level under test.')
rep('one inline-asm block, so the compiler cannot add arithmetic, reorder or drop anything.','one inline-asm block. So the compiler cannot add arithmetic, reorder or drop anything.')
rep('<code>noinline</code>, so each pass is one real call','<code>noinline</code>. So each pass is one real call')
rep('<code>volatile</code> word, so the loads cannot be dead-code-eliminated.','<code>volatile</code> word. So the loads cannot be dead-code-eliminated.')
rep('test after the add, so a size that is not a multiple of 256 would run one iteration past the end.','test after the add. So a size that is not a multiple of 256 would run one iteration past the end.')
rep('and goes to memory, so a "mesh write" footprint measures the DRAM write path.','and goes to memory. So a "mesh write" footprint measures the DRAM write path.')
rep('(a fresh permutation per run), so the prefetcher is defeated and one load is in flight.','(a fresh permutation per run). So the prefetcher is defeated and one load is in flight.')
rep('(default 500 ms), so a 32 KiB run and a 1 GiB run both get','(default 500 ms). So a 32 KiB run and a 1 GiB run both get')
rep("longest per-thread elapsed time, so bytes moved after the slowest thread's window are never credited.","longest per-thread elapsed time. So bytes moved after the slowest thread's window are never credited.")
rep('both with <code>--reps 1</code> so one window holds exactly one warm-up and one timed loop.','both with <code>--reps 1</code>. So one window holds exactly one warm-up and one timed loop.')
rep('and appends <code>dtc_cycles</code>, so flits per cycle can be formed.','and appends <code>dtc_cycles</code>. So flits per cycle can be formed.')
rep("into the log, which ties the result to this kernel's driver.","into the log. That ties the result to this kernel's driver.")
rep('<td>3.75 ns (10.5)</td>','<td>3.75 ns (10.5 cycles)</td>')
rep('<td>148 ns (415)</td>','<td>148 ns (415 cycles)</td>')
rep('the analysis rejects anything under 99.9.','the analysis rejects any counter that ran under 99.9 % of its interval.')
rep('A clock read costs tens of ns; a 32 KiB pass is about 0.25 µs.','A clock read costs tens of ns (est.). A 32 KiB pass takes about 0.25 µs (32 KiB at the measured 132.7 GB/s L1 read rate).')
rep('tells a core bound from a memory bound','separates a core bound from a memory bound')
rep('2+3 alone cannot tell a port limit from a per-core limit','2+3 alone cannot separate a port limit from a per-core limit')
rep('a slice-distance effect cannot be told from a per-core effect','a slice-distance effect cannot be separated from a per-core effect')
rep('<h2 id="summary">4. Summary: what to internalize</h2>','<h2 id="summary">4. Summary: what to remember</h2>')
rep('which shows whether the load was fair (32 threads on one mesh at 25 to 30 GB/s each) or bimodal.',
    'which shows whether every thread got a similar share (32 threads on one mesh at 25 to 30 GB/s each) or the threads split into a fast group and a slow group (for example 25 GB/s on one mesh and 60 GB/s on the other).')
rep('Naming them as clobbers makes gcc save d8 to d15 once per call, outside the loop.',
    'Naming them in the clobber list (the third colon-separated list in the asm block, which tells gcc which registers the block overwrites) makes gcc save d8 to d15 once per call, outside the loop.')
rep('<li>Half the level leaves room for stack, code and the second buffer of copy, so the stream does not spill. Four times the level above keeps the level above from serving a large share of hits.</li>',
    '<li>Half the level leaves room for stack and code, so a read or write stream does not spill. For copy the two buffers together equal the level exactly (2 × 32 KiB = 64 KiB, 2 × 1 MiB = 2 MiB), so a few sets also hold stack or static data. README puts that effect under about 1 %. Four times the level above keeps the level above from serving a large share of hits.</li>')
rep('''<li>256 MiB at 16+ threads keeps the resident total at 60 GiB at 120 threads (two buffers per thread, since <code>all</code> includes copy: under a fifth of the 320 GiB) and the first touch short: 120 × 2 × 1 GiB would take minutes (est.) to touch.</li>
</ul>
<p class="pit"><b>Pitfall:</b> a footprint equal to the level (64 KiB for L1) shares sets with stack and static data, and the figure drifts toward the next level.</p>
<p class="gen"><b>Elsewhere:</b> read <code>/sys/devices/system/cpu/cpu0/cache/index*/size</code> and <code>shared_cpu_list</code>, then apply the same ratios.</p>
<p class="ref">bench/README.md:61-67, run_crb.sh:83-89</p>''',
'''<li>256 MiB at 16+ threads keeps the resident total at 60 GiB at 120 threads (two buffers per thread, since <code>all</code> includes copy: under a fifth of the 320 GiB) and the first touch short: 120 × 2 × 1 GiB would take minutes (est.) to touch.</li>
<li>Sum over threads: the mesh-cache lists stop at 14 for read and write (14 × 8 MiB = 112 MiB) and at 7 for copy, which holds two buffers per thread (7 × 2 × 8 MiB = 112 MiB). That cap was sized against the 128 MiB Linux reports. One core reaches 64 MiB, and the counters showed 0.30 slice misses per line at 14 threads. The whole-chip mesh number was then taken with 40 threads × 3 MiB.</li>
</ul>
<p class="pit"><b>Pitfall:</b> a footprint equal to the level (64 KiB for L1) shares sets with stack and static data, and the figure drifts toward the next level. 32 threads × 8 MiB is 256 MiB, twice the cache; the result is a DRAM number labelled as a cache number.</p>
<p class="gen"><b>Elsewhere:</b> read <code>/sys/devices/system/cpu/cpu0/cache/index*/size</code> and <code>shared_cpu_list</code>, then apply the same ratios. Keep threads × footprint under about three quarters of the shared capacity that one core can reach, then confirm with the last-level miss counter.</p>
<p class="ref">bench/README.md:61-67, 83-85, run_crb.sh:83-89, brief (home-node counter table)</p>''')
rep('''<h4>Cap the thread count so the sum of footprints fits the shared level</h4>
<ul>
<li>For the mesh-cache regime the thread lists stop at 14 for read and write (14 × 8 MiB = 112 MiB) and at 7 for copy, which holds two buffers per thread (7 × 2 × 8 MiB = 112 MiB).</li>
<li>The cap was derived from the 128 MiB that Linux reports. The counters later showed 0.30 slice misses per line at 14 threads. The reason is that one core reaches only 64 MiB of the slices. The whole-chip mesh number was then taken with 40 threads × 3 MiB instead.</li>
</ul>
<p class="pit"><b>Pitfall:</b> 32 threads × 8 MiB is 256 MiB, twice the cache; the result is a DRAM number labelled as a cache number.</p>
<p class="gen"><b>Elsewhere:</b> keep threads × footprint under about three quarters of the shared capacity that one core can reach, then confirm with the last-level miss counter.</p>
<p class="ref">run_crb.sh:83-85, brief (home-node counter table)</p>
</div>
<div>
<pre># L3: 8 MiB per thread (4x the 2 MiB L2); 14 x 8 MiB = 112 MiB and
# copy 7 x 2 x 8 MiB = 112 MiB both stay under the 128 MiB L3.
L3_BYTES=8M; L3_RW_THREADS="1 2 4 8 12 14"; L3_COPY_THREADS="1 2 4 7"</pre>''',
'''<h4>Verify the sum with a thread ladder under the counters</h4>
<ul>
<li>Part 3 keeps the footprint at 8 MiB and steps the thread count (1, 4, 14), then adds 1 GiB per thread as the all-miss control. Every case runs under the same home-node event sets.</li>
<li>Result: asmread 8 MiB gives 0.000 slice misses per line at 1 and 4 threads and 0.30 at 14 threads. asmwrite 1 GiB at 14 threads gives 1.00 misses per line. This ladder is what found the 64 MiB reachable capacity.</li>
</ul>
<p class="pit"><b>Pitfall:</b> a thread sweep without counters shows the aggregate flattening and cannot say whether the slices or the misses caused it.</p>
<p class="gen"><b>Elsewhere:</b> same ladder with the last-level-cache miss event of the socket; keep the footprint fixed and step only the thread count.</p>
<p class="ref">run_sudo.sh:89, 97-102, brief (home-node counter table); 4-thread row from results/sudo-20261102T054936Z/writebw.csv via subtract.py</p>
</div>
<div>
<pre>for cfg in "asmwrite 8M 1" "asmwrite 8M 4" "asmwrite 8M 14" "asmwrite 1G 1" "asmwrite 1G 14" "asmread 8M 1" "asmread 8M 4" "asmread 8M 14" "asmread 1G 14"; do
    set -- $cfg; k=$1; bytes=$2; t=$3
    for set in $SETS; do
        counted "$OUT/writebw.csv" "$k-$bytes-$t" "$set" --threads $t --cpus 0-119 --bytes $bytes --kernel $k
    done
done</pre>''')
rep('<li><b>Misses by footprint.</b> 1 GiB per thread is 8 × the mesh cache, so every line misses every level (0.99 last-level misses per load at 1 GiB in the latency tool).</li>',
    '<li><b>Misses by footprint.</b> 1 GiB per thread is 8 × the mesh cache, so every line misses every level: 0.99 last-level misses per load at 1 GiB in the latency tool, and 1.00 slice misses per line for the asmwrite 1 GiB stream at 14 threads (part 3), up from 0.75 at 8 MiB.</li>')
rep('''<pre>- Arm cores may detect a long run of full-line stores with no loads (the
  write kernel) and switch to write-streaming mode, which bypasses L1/L2
  allocation. If write at 32K on 1 thread is far below read at 32K, check
  with `perf stat -e l1d_cache_refill,l2d_cache_refill -- ./bandwidth
  --threads 1 --cpus 3 --bytes 32K --kernel write`: refills near bytes/64 per
  pass mean streaming mode is active and the L1/L2 write numbers are
  L3-bound.
''','''<pre># README.md: the write-streaming check
perf stat -e l1d_cache_refill,l2d_cache_refill -- ./bandwidth --threads 1 --cpus 3 --bytes 32K --kernel write
# refills near bytes/64 per pass: streaming mode is active, the L1/L2 write rows are L3-bound
''')
rep('<li>The barrier counts <code>main</code> as a party. Per repetition each worker runs one untimed pass, waits, times its loop, stores bytes and elapsed, and waits again. <code>main</code> waits twice: the first wait releases the workers, the second returns when every result is stored.</li>',
    '<li>threads + 1 parties: <code>main</code>\'s first wait releases the workers, and its second returns when every result is stored. The worker\'s sequence is the code at right.</li>')
rep('<text x="120" y="98" text-anchor="middle">L1/L2 refill, write-back, bus</text>','<text x="120" y="98" text-anchor="middle">L1/L2 refill, write-back, bus, stalls, cycles</text>')
rep('''SET5[core1]=$(core l1d_cache l1d_cache_refill l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_wb);               OPT5[core1]="-C 2"</pre>
</div>
</div>

<div class="tech">
<div>
<h4>Check every event name''','''SET5[core1]=$(core l1d_cache l1d_cache_refill l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_wb);               OPT5[core1]="-C 2"
SET5[core2]=$(core event=0x41 event=0x43 event=0x51 event=0x53 event=0x61 event=0x67);                            OPT5[core2]="-C 2"
SET5[core3]=$(core bus_access mem_access stall_backend_mem bus_cycles cycles instructions);                        OPT5[core3]="-C 2"</pre>
</div>
</div>

<div class="tech">
<div>
<h4>Check every event name''')
rep('<p class="ref">run_sudo.sh:135, 148, 158-161</p>','<p class="ref">run_sudo.sh:135, 148, 158-164</p>')
rep('and home-node queue occupancy on both meshes.</li>',
    'and home-node queue occupancy on both meshes. The three core sets are the L1/L2 cache, refill and write-back counts, the write-only raw events, and bus_access, mem_access, stall_backend_mem, bus_cycles, cycles and instructions, so bus traffic and backend memory stalls can be formed per cycle [run_sudo.sh:162-164].</li>')
rep('it stops gcc from rewriting the write and copy loops as <code>memset</code> and <code>memcpy</code> calls.</li>',
    'it stops gcc from rewriting the write and copy loops as <code>memset</code> and <code>memcpy</code> calls. It also uses <code>-march=native</code> rather than <code>-mcpu=native</code>: gcc 14 on CRB resolves <code>-mcpu=native</code> to nothing.</li>')
rep('''# Makefile
# -fno-tree-loop-distribute-patterns keeps gcc''','''# Makefile
# -mcpu is avoided on purpose: gcc 14 on CRB resolves -mcpu=native to nothing.
# -fno-tree-loop-distribute-patterns keeps gcc''')
rep('''<li>An idle control (<code>sleep 2</code> under the same event set) is recorded first for every set.</li>
</ul>''','''<li>An idle control (<code>sleep 2</code> under the same event set) is recorded first for every set.</li>
<li>Same recipe for the latency tool in <code>run_crb.sh</code>: short = 2 timed cycles (<code>--min-ms 0 --min-cycles 2</code>), long = at least 1 s and 6 cycles (<code>--min-ms 1000 --min-cycles 6</code>), and <code>summarize.py</code> divides the count difference by the load difference. The 0.99 misses per load at 1 GiB in 3.3 come from that difference.</li>
</ul>''')
rep('<p class="ref">run_sudo.sh:75-87, 93-96; subtract.py</p>','<p class="ref">run_sudo.sh:75-87, 93-96; subtract.py; run_crb.sh:119-134; summarize.py:118-133</p>')
rep('<text x="460" y="232" fill="#4d5660">0.38 accesses','<text x="10" y="232" fill="#4d5660">0.38 accesses')
rep('<text x="20" y="276" fill="#4d5660" font-size="11">2 threads, 8 MiB each, read. Not a limit for DRAM streams: 2 threads at 1 GiB get 53 GB/s paired or not.</text>',
    '<text x="20" y="276" fill="#4d5660" font-size="11">2 threads, 8 MiB each, read.</text>\n<text x="20" y="292" fill="#4d5660" font-size="11">Not a limit for DRAM streams: 2 threads at 1 GiB get 53 GB/s paired or not.</text>')
rep('''<text x="520" y="262" fill="#4d5660" font-size="11">256 MiB per thread. Hypothesis, not confirmed: write traffic crossing the CCG links in both directions.</text>
<text x="520" y="278" fill="#4d5660" font-size="11">Home-node retry and throttle counts fall in the collapsed case; CCG and memory-controller counters not yet read.</text>''',
'''<text x="520" y="262" fill="#4d5660" font-size="11">256 MiB per thread. Hypothesis, not confirmed: write traffic crossing the</text>
<text x="520" y="278" fill="#4d5660" font-size="11">CCG links in both directions. Home-node retry and throttle counts fall in the</text>
<text x="520" y="294" fill="#4d5660" font-size="11">collapsed case; CCG and memory-controller counters not yet read.</text>''')
rep('<svg viewBox="0 0 760 430"','<svg viewBox="-20 0 780 430"')
rep('''<text x="700" y="59" fill="#4d5660">exclusive: the hit removes the line from the slice;</text>
<text x="700" y="76" fill="#4d5660">the later L2 eviction writes the clean line back</text>
<text x="700" y="100" fill="#4d5660">0.000 accesses on the other mesh · 0.000 memory requests</text>''',
'''<text x="10" y="104" fill="#4d5660" font-size="11">exclusive: the hit removes the line from the slice; the later L2 eviction writes the clean line back</text>
<text x="10" y="120" fill="#4d5660" font-size="11">0.000 accesses on the other mesh · 0.000 memory requests</text>''')
rep('<text x="440" y="52" fill="#4d5660">× 2.0:','<text x="345" y="52" fill="#4d5660">× 2.0:')
rep('<rect x="310" y="40" width="110" height="46" rx="4"/><rect x="460" y="40" width="200" height="46" rx="4"/>\n</g>',
    '<rect x="310" y="40" width="110" height="46" rx="4"/><rect x="460" y="40" width="230" height="46" rx="4"/>\n</g>')
rep('<text x="560" y="59" text-anchor="middle">HN-S slice hit (own mesh or proxy)</text><text x="560" y="76" text-anchor="middle">0.83 accesses, 0.83 fills, 0.000 misses per line</text>',
    '<text x="575" y="59" text-anchor="middle">HN-S slice hit (own mesh or proxy)</text><text x="575" y="76" text-anchor="middle" font-size="11">0.83 accesses, 0.83 fills, 0 misses per line</text>')
rep('<text x="214" y="90" text-anchor="middle">L2 miss,</text>\n<text x="214" y="118" text-anchor="middle">write-back</text>','<text x="214" y="176" text-anchor="middle">L2 miss, write-back</text>')
rep('<text x="560" y="126" text-anchor="middle" fill="#ffffff" font-size="11">timed whole passes until ≥ min-ms (default 500 ms)</text>',
    '<text x="560" y="104" text-anchor="middle" fill="#2a78d6" font-size="11">timed whole passes until ≥ min-ms (default 500 ms)</text>')
rep('arm_cmn_0/hns_*, arm_cmn_1/hns_*  -a</text>','arm_cmn_{0,1}/hns_*  -a</text>')
fail=0
for old,new in R:
    n=d.count(old)
    if n!=1: fail+=1; print('COUNT',n,':',old[:90].replace('\n','|'))
    else: d=d.replace(old,new)
print('replacements',len(R),'failed',fail)
if not fail: open(p,'w').write(d); print('written')
else: sys.exit(1)
