"""The one glossary of the page ("Words used here").

Each section module calls S.term(name, definition) with its own wording.
install(S, D) gives the page object one definition per term, so the page shows
the same wording whichever section names the term first.  Only terms that a
section registers are listed, plus the terms of ALWAYS.

- WORDS: (name, definition) in the form shown on the page.  A definition is one
  or more full sentences without the term as subject.
- ALIAS: a section name that means a term of WORDS (or several, or none).
- ALWAYS: terms that the page text uses and no section registers.
"""

WORDS = [
    ('ADD, CMP, SUBS, B.LO, B.NE', 'The add, compare and branch instructions of the core that step a loop and '
                                   'close it.'),
    ('address order', 'A chain kind: each line of the buffer holds the address of the next line. '
                      'Boot F1 and boot F2 have no row of this kind.'),
    ('Asimov', 'The chip under test. One half of it (a hemisphere) runs on a hardware emulator '
               '(operator\'s README).'),
    ('B/cycle', 'Bytes per cycle: the rate in GB/s divided by %(cpn)s cycles per ns. The measured ratio of the '
                'core cycle counter to the timer is %(cpn_lo)s to %(cpn_hi)s cycles per ns.'),
    ('best rep', 'The rep whose value the best row repeats. The span time and the counters of a best row come '
                 'from the first such rep.'),
    ('best row', 'The row that the test program itself prints with the label <code>best</code>: the lowest ns '
                 'per load of a latency footprint, or the highest bracket rate of a bandwidth command.'),
    ('boot', 'One start of the emulated chip with one firmware build. All rows of a boot share its firmware '
             'settings.'),
    ('boot F1', 'The boot with the cluster L3 on and the hardware prefetchers on (operator\'s README). '
                'It has core rows and CME rows. The page writes "boot F1 (prefetchers on)".'),
    ('boot F2', 'The boot with the cluster L3 on and the hardware prefetchers off (operator\'s README). '
                'It has CME rows only. The page writes "boot F2 (prefetchers off)".'),
    ('bracket rate', 'The bytes moved in a rep divided by its bracket time, in GB/s '
                     '(CSV column <code>aggregate_GBps</code>).'),
    ('bracket time', 'The time between two clock reads in the C program, one before the kernel call or calls '
                     'and one after.'),
    ('chain kind', 'How the latency test walks its chain: walked many times, walked once, every line flushed '
                   'first, or address order.'),
    ('chain load', 'One load of the latency test. It loads 8 bytes through the CME, and the loaded value is the '
                   'address of the next load. The instruction LASTB returns that value to the core. Its time is '
                   'given in ns per load.'),
    ('chain shape', 'Which lines of a buffer belong to the chain: every line, or one line per 4 KiB page.'),
    ('chip time', 'Time on the clock of the emulated chip. Every time on this page is chip time.'),
    ('cluster', 'Two cores that share an L2 cache, an L3 cache, one CME and one port to the mesh. '
                'Arm calls it a DSU (DynamIQ Shared Unit).'),
    ('cluster L3', 'The level 3 cache that the two cores of a cluster and their CME share.'),
    ('cluster port', 'The mesh device through which one cluster sends its requests.'),
    ('CME', 'The Arm C1-SME2 matrix engine unit. Each cluster has one, and the two cores of the cluster share it.'),
    ('CME L1', 'The level 1 data cache of the CME. Its size is 64 KiB (operator\'s README).'),
    ('call-cost rows', 'The rows of the file <code>cme-bandwidth-call-cost.csv</code>. Each one times short kernel '
                       'calls of the looped form, one call per pass.'),
    ('cme-call row', 'A latency row that times 64 kernel calls in one bracket, each call directly after the one '
                     'before it. Each call runs one step of the round-trip baseline.'),
    ('command', 'One run of a test program. It is one line of the file <code>log.txt</code> of a boot.'),
    ('command lifetime', 'The time from the start to the end of a command. The mesh counters run during that '
                         'time.'),
    ('condition number', 'The ratio of the largest to the smallest singular value of the matrix of a fit. '
                         'A large value means that the fit cannot separate its coefficients.'),
    ('control row', 'A row that is run to check one thing about other rows. Its result is known before the run, '
                    'or it differs from the row beside it in one item. An example is an L3 hit count of 0 on a '
                    'boot whose L3 holds no data.'),
    ('correlation coefficient', 'The Pearson correlation: a value from -1 to +1 that says how closely two columns '
                                'follow one straight line. +1 means an exact rising line and -1 an exact '
                                'falling line.'),
    ('core', 'One Arm C1-Nano processor. Linux numbers the ten cores CPU 0 to CPU 9. The core rows run the '
             'tests with the loads and stores of the core itself, on boot F1 only.'),
    ('counting window', 'The interval between the counter start and the counter stop of one latency row. '
                        'In the code the counter start comes before the first clock read of the bracket, and '
                        'the counter stop comes after the second clock read.'),
    ('crosspoint', 'One junction of the mesh, named by its position (x,y).'),
    ('CSV', 'Comma-separated values: the text format of the result files. One line is one row.'),
    ('demand-only', 'Said of a row that counts 0 prefetch refills per load in every pass.'),
    ('DRAM model', 'The memory behind the mesh on this emulator. It is an emulator memory model, not silicon '
                   'DRAM timing.'),
    ('DSB ST', 'A barrier instruction that waits until the stores before it are complete.'),
    ('DSB SY', 'A barrier instruction that waits until all memory accesses before it are complete.'),
    ('DSU 1', 'The cluster of CPUs 2 and 3. Its CME runs every CME row of this page, called from CPU 2.'),
    ('DUP', 'An instruction that copies a register of the core into a vector.'),
    ('effective cycles per 64 bytes transferred', '64 divided by the rate in B/cycle: the cycles of a whole '
                                                  'loop divided by the number of 64-byte units that the loop '
                                                  'transfers. It is a loop throughput. It is not the time '
                                                  'that one load or one store takes to complete.'),
    ('effective rate', 'A loop throughput: what a whole rep transfers, divided by the time of the rep. It is '
                       'not the time that one load or one store takes to complete.'),
    ('EOR', 'The instruction for the XOR operation.'),
    ('est.', 'Marks an estimate: a value derived with an assumption, not read from a row.'),
    ('every line flushed first', 'A chain kind. It is "walked once" with one more step: the core removes every '
                                 'line of the buffer from the caches before each timed rep.'),
    ('excess', 'The requests received by the home node of the region minus the level subtracted.'),
    ('fold', 'The XOR of all loaded 8-byte words into one value. The read kernels return it to the core.'),
    ('footprint', 'The size of the buffer that a test walks. A copy uses two buffers of that size.'),
    ('free intercept', 'A constant term of a fit whose value the fit chooses.'),
    ('GB/s', 'Gigabytes per second, with 1 GB = 1,000,000,000 bytes. 1 GB/s equals 1 byte per ns.'),
    ('hit share', 'The L3 hit count divided by the sum of the L3 hit count and the L3 miss count of one row.'),
    ('home node', 'A mesh device that owns a range of addresses. Each of the five home nodes holds one part '
                  'of the SLC and one OCM region.'),
    ('idle control', 'A mesh count taken while a small command runs that sends almost no requests to the home '
                     'nodes. It gives the background count.'),
    ('in flight', 'A line request is in flight between the moment the CME sends it and the moment the line '
                  'arrives.'),
    ('inner refill', 'A CME L1 refill whose line came from inside the cluster (event 0x327D): from the cluster '
                     'L3 or from a snoop of a core\'s cache (operator\'s README). It counts loads and prefetches '
                     'alike.'),
    ('intercept', 'The time that a fitted straight line gives at 0 bytes per pass.'),
    ('ISB', 'An instruction that makes the core finish the instructions in flight before the next one starts.'),
    ('kernel', 'One test loop written in assembly in the file <code>cme_kern.S</code>. On this page the word '
               'never means the Linux kernel.'),
    ('KiB, MiB', '1,024 bytes and 1,024 KiB.'),
    ('L3 events', 'Three CME events: 0x328E (L3 hit), 0x328F (L3 miss) and 0x3290 (L3 refill). They are '
                  'exploratory: no control row validates them.'),
    ('L3 hit count', 'Event 0x328E (<code>CME_L3D_CACHE_HIT</code>) per chain load. Exploratory.'),
    ('L3 miss count', 'Event 0x328F (<code>CME_L3D_CACHE_MISS</code>) per chain load. Exploratory.'),
    ('L3 refill count', 'Event 0x3290 (<code>CME_L3D_CACHE_REFILL</code>) per chain load. Exploratory.'),
    ('L3-event rows', 'The rows of the latency test that count the three L3 events of the CME.'),
    ('LASTB', 'An instruction that copies the last active element of a vector to a register of the core.'),
    ('latency test', 'The loop of chain loads over a chain of 64-byte lines in random order. Its result is the '
                     'time per chain load in ns.'),
    ('LD1D, LD1B', 'Vector load instructions. LD1D loads 8-byte elements, LD1B loads bytes.'),
    ('LDP, STP', 'The core instructions that load or store a pair of registers.'),
    ('least-squares fit', 'The coefficients that make the sum of the squared residuals smallest.'),
    ('level subtracted', 'The background count that is taken off the count of a home node. In a command on one '
                         'region it is the mean count of the four home nodes that do not hold the region.'),
    ('LLVM model', 'The scheduling description of the C1-Nano in the LLVM compiler source.'),
    ('load pipe, store pipe', 'Execution units of the CME in the LLVM model. The load pipe runs the vector loads '
                              'one after the other. The store pipe does the same for the vector stores.'),
    ('lone call', 'A kernel call that stands alone in its bracket: the bracket holds this one call.'),
    ('looped form', 'The bandwidth test with one kernel call per pass.'),
    ('mesh', 'The on-chip network (Arm CMN) that joins the clusters, the home nodes and the bridges to memory. '
             'It is a grid of 6 x 6 crosspoints.'),
    ('mesh counters', 'Counters of the mesh. They count the requests that each home node receives during one '
                      'whole command.'),
    ('mesh step', 'A move from one crosspoint to the next one. The step count between two crosspoints is the '
                  'difference in x plus the difference in y.'),
    ('miss minus refill', 'The L3 miss count minus the L3 refill count of one row.'),
    ('OCM', 'On-chip memory: cache ways of the home nodes that the firmware locks and maps as memory. '
            'Five regions of 256 KiB, one in each home node.'),
    ('outer refill', 'A CME L1 refill whose line came from outside the cluster, through the mesh (event 0x327E). '
                     'It counts loads and prefetches alike.'),
    ('outside-span time', 'Bracket time minus span time. It holds the C call and return, the register save and '
                          'restore, SMSTART, SMSTOP and the bookkeeping of the second stamp.'),
    ('pass', 'One walk over the whole buffer or the whole chain.'),
    ('plain rows', 'The rows of the latency test at the same footprints with the refill counters and no L3 event.'),
    ('plan rule', 'The fit rule of the run plan for a straight line of time per pass against bytes per pass. '
                  'A largest residual over 2 % of the smallest pass time makes the intercept void. The page '
                  'then quotes neither the intercept nor the rate of that fit.'),
    ('PMU', 'Performance monitoring unit: the event counters of the core.'),
    ('prefetch refill', 'A CME L1 refill that the hardware prefetcher of the CME asked for, not a load of the '
                        'program (event 0x32B2).'),
    ('prefetcher', 'Hardware that requests lines before the program loads them. The cores and the CME each have '
                   'one. They are on in boot F1 and off in boot F2 (operator\'s README).'),
    ('read refill', 'A CME L1 refill caused by a load of the program that missed (event 0x3280).'),
    ('refill', 'The arrival of one 64-byte line in the CME L1 after a miss or a prefetch.'),
    ('rep', 'One timed measurement. It is one data row of a CSV file and can hold many passes. In the rows that '
            'walk a chain once, one rep is one pass.'),
    ('rep spread', 'The highest value minus the lowest value over the reps (or timed passes) of one row. '
                   'The page gives it in the unit of the value, or in percent of the lowest value, and says which.'),
    ('repeat difference', 'The difference between two measurements of the same row inside one boot, in percent '
                          'of the lower value.'),
    ('requests received', 'The mesh counter event <code>hns_pocq_reqs_recvd_all</code> of one home node: the '
                          'number of requests that the node received while the command ran.'),
    ('residual', 'The measured value of a row minus the value that a fit gives for the same row.'),
    ('rms', 'Root mean square: the square root of the mean of the squared residuals of a fit.'),
    ('round-trip baseline', 'The row <code>cme-roundtrip</code>: the loop of the latency test with a register '
                            'copy (DUP) in place of the load. A value goes from the core to the CME and back, '
                            'and no memory is accessed. It is a separate measurement. A chain load minus this '
                            'value is the measured difference between two kernels, not a memory-access '
                            'time.'),
    ('RTL', 'Register transfer level: the source text of the hardware design.'),
    ('run plan', 'The project file <code>follow-up-run-plan.md</code>. Its section 13 plans the rows that measure '
                 'the cost of a kernel call, and it holds the fit rule.'),
    ('SHA-256 checksum', 'A 256-bit value computed from the bytes of a file. Two files with the same checksum '
                         'have the same content.'),
    ('single-call form', 'The bandwidth test with all passes of a rep inside one kernel call.'),
    ('SLC', 'System level cache: the cache inside the mesh, held by the five home nodes. '
            '3.75 MiB est. after the OCM ways are taken out (operator\'s README).'),
    ('SMSTART, SMSTOP', 'The instructions that enter and leave streaming mode.'),
    ('snoop', 'A request to another cache of the cluster for a line that it holds.'),
    ('span rate', 'The bytes moved in a rep divided by its span time, in GB/s (CSV column <code>span_GBps</code>).'),
    ('span time', 'The time between the two stamps of a kernel call. The first stamp follows SMSTART. '
                  'The second stamp comes before SMSTOP.'),
    ('stamp', 'One read of the timer register inside a kernel. Each kernel call takes two stamps, and the time '
              'between them is the span time.'),
    ('ST1B', 'A vector store instruction.'),
    ('streaming mode', 'The processor state between the instructions SMSTART and SMSTOP. In it, vector loads '
                       'and stores run on the CME.'),
    ('test plan', 'The project file <code>CME-plan.md</code>: the design of the CME load and store test.'),
    ('TF-A', 'Trusted Firmware-A: the firmware stage that sets the prefetcher controls before Linux starts '
             '(operator\'s README).'),
    ('thread barrier', 'The point where the worker thread of the test program waits for the main thread before '
                       'each rep.'),
    ('TLB', 'Translation lookaside buffer: the cache of address translations.'),
    ('vector', 'One CME register of 64 bytes. One vector load or store moves 64 bytes, which is one cache line.'),
    ('walked many times', 'A chain kind: one chain is walked again and again inside a rep, until at least '
                          '%(min_loads)s loads are done.'),
    ('walked once', 'A chain kind: two untimed walks of a first chain touch the lines. Each timed rep then '
                    'walks another chain over the same lines one time.'),
    ('warm-up pass', 'One untimed pass over the buffer before each rep of the bandwidth test.'),
    ('write refill', 'A CME L1 refill caused by a store of the program that missed (event 0x3281).'),
    ('XOR', 'The bitwise exclusive-or operation (instruction EOR).'),
    ('ZA array', 'The matrix register of SME, the Arm Scalable Matrix Extension.'),
]

# A section name (lower case) that means one or more terms of WORDS.
ALIAS = {
    'boot f1 (prefetchers on)': ['boot f1'],
    'boot f2 (prefetchers off)': ['boot f2'],
    'inner refill, outer refill': ['inner refill', 'outer refill'],
    'prefetchers': ['prefetcher'],
    'spread': ['rep spread'],
    'pipe': ['load pipe, store pipe'],
    'pearson correlation': ['correlation coefficient'],
    'demand-only row': ['demand-only'],
    'sog': [], 'trm': [],        # the page writes the two document names in full
}

# Terms that the page text uses and that no section registers.
ALWAYS = ['ADD, CMP, SUBS, B.LO, B.NE', 'address order', 'Asimov', 'best rep', 'boot', 'chain kind', 'chain shape',
          'command', 'CSV', 'lone call', 'run plan', 'stamp', 'test plan', 'thread barrier',
          'warm-up pass']


def install(S, D):
    """Give the page object the glossary.  Call before any section."""
    core = [D.clock[b] for b in ('F1', 'F2')]
    fill = {'cpn': '%.2f' % D.cycles_per_ns,
            'cpn_lo': '%.4f' % min(c['core_lo'] for c in core), 'cpn_hi': '%.4f' % max(c['core_hi'] for c in core),
            'min_loads': '{:,}'.format(D.latblocks('F2', 'cme-latency-dram-small.csv')[0]['header']['loads'])}
    S.words = {name.lower(): (name, d % fill if '%(' in d else d) for name, d in WORDS}
    S.word_alias = dict(ALIAS)
    for name in ALWAYS:
        S.term(name)
