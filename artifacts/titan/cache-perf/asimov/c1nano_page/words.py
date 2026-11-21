"""The one glossary of the page ("Words used here", second to last on the page).

Each section module calls S.term(name) (a definition given there is ignored when
the term is in WORDS).  install(S, D) gives the page object one definition per
term, so the page shows the same wording whichever section names the term first.
Only terms that a section registers are listed, plus the terms of ALWAYS.

- WORDS: (name, definition) in the form shown on the page.  A definition is one
  or more full sentences.  The wording follows section 8 of the critic sheet.
- ALIAS: a section name (lower case) that means one or more terms of WORDS.
- ALWAYS: terms that the page text uses and no section needs to register.

No definition holds a measured number, so install() does not read the data layer.
"""

WORDS = [
    ('aggregate rate', 'The bytes of all threads of a rep divided by the elapsed time of the slowest thread, in '
                       'GB/s.'),
    ('address order', 'A chain kind: each line of the buffer holds the address of the next line, so the loads go '
                      'through the buffer in ascending order.'),
    ('background control', 'The 4 KiB chain on 4 KiB pages that runs per CPU under the mesh counters. It is a '
                           'separate measurement.'),
    ('bandwidth test', 'The program that times whole passes of a fixed loop of 32-byte loads or stores over a '
                       'buffer.'),
    ('best row', 'The smallest rep for latency and the largest rep for bandwidth.'),
    ('boot', 'One power-on of the emulated chip with one firmware set, which ran one script once.'),
    ('boot B', 'A boot with the prefetchers off. The L3 of CPUs 2 to 9 holds no data.'),
    ('boot C', 'A boot with the prefetchers on. The L3 holds no data, and the OCM is mapped with 64 KiB '
               'translations.'),
    ('boot D', 'A boot with the conditions of boot B and with the OCM mapped with 64 KiB translations.'),
    ('boot E', 'A boot with the firmware state of boot F1 and another command set.'),
    ('boot F1', 'The main boot of this page. The L3 is on, the prefetchers are on, and the OCM is mapped in 4 KiB '
                'entries.'),
    ('boot R3', 'A boot that ran the command set of boot F1 on an older benchmark build, with the L3 holding no '
                'data.'),
    ('bridge', 'The mesh device that connects the mesh to the DRAM model.'),
    ('C1-Nano', 'The Arm core under test. The chip has ten, and the tests use CPUs 2 to 9.'),
    ('chain kind', 'How the latency test walks its chain: walked many times, walked once, every line flushed '
                   'first, or address order.'),
    ('chain load', 'The elapsed time of a walk divided by its loads, in ns per load.'),
    ('checked in two states', 'The status of a counter event that reads zero in a state where its activity is '
                              'absent and a plausible count in a state where its activity is present.'),
    ('clock-read cost', 'The time that a command measures between two clock reads with no load between them. The '
                        'program does not subtract it from a rep.'),
    ('cluster', 'Two cores that share one L2, one L3 and one mesh port.'),
    ('contiguous hint', 'A flag on a page-table entry. It lets the core keep one translation for 16 neighbour '
                        'entries of 4 KiB, which is 64 KiB.'),
    ('control row', 'The row of a group that the other rows of the group are divided by. It is a separate '
                    'measurement.'),
    ('crosspoint', 'One switch of the mesh grid. A cluster port or a home node attaches to one crosspoint.'),
    ('CME', 'The Arm C1-SME2 matrix engine unit of a cluster. A separate page reports its rows.'),
    ('command', 'One run of a test program. It is one line of the file <code>log.txt</code> of a boot.'),
    ('demand read', 'A read that an instruction of the program causes, as opposed to a prefetch.'),
    ('DRAM-backed', 'A buffer, row or command whose memory is in the DRAM model, not in the OCM.'),
    ('DRAM-model row', 'The 8 MiB chain with every line flushed first, on CPU 2. It is the row to quote for the '
                       'DRAM model.'),
    ('DRAM model', "The emulator's memory behind the home nodes. It has zero configured delay and is not silicon "
                   "timing (operator's README)."),
    ('effective cycles per 64 bytes transferred', 'The number 128 divided by the rate in GB/s, at 2.0 cycles per '
                                                  'ns. It is loop throughput, not the time of one load or store.'),
    ('efficiency', 'The scaling divided by the number of cores, in percent.'),
    ('est.', 'An estimate. Its method stands next to it.'),
    ('every line', 'An OCM chain shape: every 64-byte line of a region is a chain member.'),
    ('every line flushed first', 'A chain kind: every line of the chain is removed from the caches before each '
                                 'timed walk, and the chain is walked once.'),
    ('exploratory', 'The status of a counter event that is not checked in a state where it must read zero.'),
    ('fit', 'A straight-line formula whose constants are chosen so that the sum of the squared residuals is '
            'smallest (least squares).'),
    ('flit', 'One unit of data that a crosspoint sends on a mesh link.'),
    ('footprint', 'The bytes of buffer that a row uses per thread.'),
    ('geometric mean', 'The n-th root of the product of n ratios.'),
    ('GB/s', 'The unit of the bandwidth rows: 1e9 bytes transferred per second of elapsed time. It is loop '
             'throughput.'),
    ('hit set', 'Three events that count the L2 hits, the L3 accesses and the L3 hits of demand reads. They are '
                'exploratory.'),
    ('home node', 'A mesh device that holds one slice of the SLC and one OCM region.'),
    ('kernel', 'One of the loops of the bandwidth test: read, write or copy. It is an assembly routine.'),
    ('L1 prefetch refills', 'The L1 refills that a prefetcher asked for (event 0x81BC).'),
    ('L2 prefetch refills', 'The L2 refills by the prefetchers that fill the L2 (event 0x81BD).'),
    ('L2 refills by the L1 prefetcher', 'The L2 refills that requests of the L1 prefetcher cause (event 0x0111).'),
    ('L2 refills not accounted for', 'The L2 refills minus the two prefetch refill counts minus the L3 read '
                                     'refills. It is a difference of counters, not a count of demand reads.'),
    ('L3 on', "The state in which the L3 of a cluster stores lines, as the firmware sets it (operator's README)."),
    ('L3 read refill', 'An L3 fill from outside the cluster caused by a read (event 0xA2).'),
    ('latency test', 'The program that walks a chain of pointers, one pointer per 64-byte line. The address of '
                     'each load is the data of the load before it.'),
    ('line', 'A block of 64 bytes. It is the unit that a cache stores and fetches.'),
    ('looped form', 'The bandwidth test with one kernel call per pass.'),
    ('mesh', 'The 6 x 6 grid of crosspoints that joins the clusters, the home nodes and the memory.'),
    ('OCM', 'On-chip memory: five regions of 256 KiB that live in the home nodes.'),
    ('OCM row', 'The OCM chain over every line of all five regions. It is the row to quote for the OCM.'),
    ('one line per 4 KiB page', 'An OCM chain shape: one 64-byte line of each 4 KiB page is a chain member, so a '
                                'region gives 64 loads.'),
    ("operator's README", 'The file <code>README.md</code> that the emulator operator wrote into each results '
                          'folder.'),
    ('own node', 'The home node of the region that a one-region command uses.'),
    ('pass', 'One walk over the chain or over the buffer.'),
    ('perf_cov', 'The share of the timed interval during which the counters ran.'),
    ('plain read', 'The read loop of the bandwidth test alone, with no prefetch hint.'),
    ('prefetcher', "The hardware data prefetchers of the core. \"Prefetchers off\" means that the firmware set "
                   "the disable bit (operator's README)."),
    ('read stream', 'The loads of the read loop of the bandwidth test. They go through the buffer in address '
                    'order.'),
    ('refill', 'A line brought into a cache level. The counts include prefetch fills.'),
    ('rep', 'One timed measurement. It is one data row of a CSV file and can hold many passes.'),
    ('requests received', 'The count of requests that one home node received while a command ran (mesh event '
                          '<code>hns_pocq_reqs_recvd_all</code>).'),
    ('requests sent on to memory', "The home nodes' count of requests passed to the memory controller. The event "
                                   "is exploratory."),
    ('rms', 'Root mean square: the square root of the mean of the squared residuals of a fit.'),
    ('residual', 'The measured value of a row minus the value that a fit gives for the same row.'),
    ('single-call form', 'The bandwidth test with all passes of a rep in one kernel call.'),
    ('SLC', "The system-level cache. All clusters share it, and the five home nodes hold it."),
    ('scaling', 'The aggregate rate divided by the one-core rate of the same kernel and footprint.'),
    ('SOG', 'The Arm C1-Nano Core Software Optimization Guide, document 109590_0001_04. It gives the documented '
            'instruction throughput.'),
    ('software prefetch N lines ahead', 'The read loop with one prefetch hint per line, N lines ahead of the '
                                        'loads.'),
    ('spread', 'The largest rep minus the smallest rep, divided by the best row, in percent.'),
    ('step', 'One move between neighbour crosspoints on the mesh, along X or along Y.'),
    ('the L3 holds no data', 'The state in which the L3 of a cluster only tracks which core has a line '
                             "(snoop-filter-only mode), as the firmware sets it (operator's README)."),
    ('TLB', 'The cache of address translations. "64 KiB translations" means that one entry covers 64 KiB.'),
    ('void', 'The verdict on a fit whose largest residual is over 2 % of its smallest value. No number of a void '
             'fit is quoted.'),
    ('two streams', 'The read loop over the two halves of the buffer at once.'),
    ('way', 'One of the equal parts of a cache. A given line can be stored in one place of each way.'),
    ('walked many times', 'A chain kind: one chain is walked again and again inside a rep, until the load count of '
                          'the command is reached.'),
    ('walked once', 'A chain kind: untimed walks of a first chain touch the lines, and each timed rep then walks '
                    'another chain over the same lines one time.'),
]

# A section name (lower case) that means one or more terms of WORDS.
ALIAS = {
    'prefetchers': ['prefetcher'], 'prefetchers off': ['prefetcher'], 'prefetchers on': ['prefetcher'],
    'l3 holds no data': ['the l3 holds no data'], 'the l3 holds no data': ['the l3 holds no data'],
    'l3 on / the l3 holds no data': ['l3 on', 'the l3 holds no data'],
    'walked many times / walked once / every line flushed first / address order': [
        'walked many times', 'walked once', 'every line flushed first', 'address order'],
    'every line / one line per 4 kib page': ['every line', 'one line per 4 kib page'],
    'one line per page': ['one line per 4 kib page'],
    'pass, rep': ['pass', 'rep'],
    'looped form / single-call form': ['looped form', 'single-call form'],
    'plain read / software prefetch n lines ahead / two streams': [
        'plain read', 'software prefetch n lines ahead', 'two streams'],
    'software prefetch': ['software prefetch n lines ahead'],
    'l3 read refill (0xa2)': ['l3 read refill'], 'l3 read refills': ['l3 read refill'],
    'l1 prefetch refill': ['l1 prefetch refills'], 'kernels': ['kernel'],
    'refills': ['refill'], 'ways': ['way'], 'lines': ['line'], 'demand reads': ['demand read'],
    'bridges': ['bridge'], 'read streams': ['read stream'], 'stream': ['read stream'], 'rep spread': ['spread'], 'steps': ['step'], 'home nodes': ['home node'],
    'unaccounted l2 refills': ['l2 refills not accounted for'],
    'effective cycles per 64 bytes': ['effective cycles per 64 bytes transferred'],
    'readme': ["operator's readme"], 'dram': ['dram model'],
    'boot f1 (l3 on, prefetchers on)': ['boot f1'],
}

# Terms that the page text uses in every section.  They are listed without a section call.
ALWAYS = ['boot', 'boot F1', 'boot E', 'boot B', 'boot C', 'boot D', 'boot R3', 'C1-Nano', 'cluster', 'prefetcher',
          'L3 on', 'the L3 holds no data', 'DRAM model', 'footprint', 'pass', 'rep', 'best row', 'spread', 'est.',
          "operator's README", 'chain load', 'GB/s', 'DRAM-model row', 'OCM row', 'crosspoint', 'flit', 'line', 'demand read', 'DRAM-backed',
          'L2 prefetch refills', 'read stream', 'fit', 'void', 'control row']


def install(S, D=None):
    """Give the page object the glossary.  Call before any section.  D is not used."""
    S.words = {name.lower(): (name, d) for name, d in WORDS}
    S.word_alias = dict(ALIAS)
    for name in ALWAYS:
        S.term(name)
