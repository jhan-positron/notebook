"""The fixed ids of the page: section keys, subsection ids, figure ids, table ids.

IDS.md in this folder is the readable form of this file.  gen_c1nano_perf.py prints a
note for a subsection id that a section module uses and this list does not have, and
for one that this list has and the built section does not.
"""

# section key -> (suggested title, [(h3 id, title)], [figure ids], [table ids])
SECTIONS = [
    ('setup', 'What was measured', [
        ('setup-chip', 'The chip under test'),
        ('setup-mesh', 'The mesh'),
        ('setup-boots', 'The boots'),
        ('setup-latency-test', 'The latency test'),
        ('setup-bandwidth-test', 'The bandwidth test'),
        ('setup-counters', 'Counters, clock, integrity'),
    ], ['fig-S1', 'fig-S2', 'fig-S3', 'fig-S4'], ['tab-TS1', 'tab-TS2', 'tab-TS3', 'tab-TS4']),
    ('glance', 'Results at a glance', [
        ('glance-numbers', 'Numbers to quote'),
        ('glance-repeat', 'Repeatability'),
    ], ['fig-G1', 'fig-G2'], ['tab-TG1', 'tab-TG2']),
    ('latency', 'Latency by footprint', [
        ('lat-footprint', 'By footprint, CPU 2'),
        ('lat-levels', 'Which level serves each footprint'),
        ('lat-l3', 'What an L3-served load costs'),
        ('lat-dram', 'The DRAM-model row'),
        ('lat-clusters', 'The other clusters'),
        ('lat-order', 'Address order and the prefetchers'),
    ], ['fig-L1', 'fig-L2', 'fig-L3', 'fig-L4', 'fig-L5', 'fig-L6'],
        ['tab-TL1', 'tab-TL2', 'tab-TL3', 'tab-TL4', 'tab-TL5']),
    ('bandwidth', 'One-core bandwidth', [
        ('bw-1core', 'One core by footprint'),
        ('bw-l1forms', 'Inside the L1: two forms'),
        ('bw-variants', 'The read stream and the prefetchers'),
    ], ['fig-B1', 'fig-B2', 'fig-B3'], ['tab-TB1', 'tab-TB2', 'tab-TB3', 'tab-TB4', 'tab-TB5']),
    ('multicore', 'Multi-core bandwidth', [
        ('mc-clusters', 'One core per cluster, all eight'),
        ('mc-writers', 'Writer placement'),
    ], ['fig-M1', 'fig-M2'], ['tab-TM1', 'tab-TM2']),
    ('ocm', 'OCM latency and bandwidth', [
        ('ocm-quote', 'The OCM row to quote'),
        ('ocm-page', 'One line per page: not an OCM latency'),
        ('ocm-region', 'Per region and per mesh step'),
        ('ocm-pagemap', 'Page mapping'),
        ('ocm-bw', 'OCM bandwidth'),
    ], ['fig-O1', 'fig-O2', 'fig-O3', 'fig-O4', 'fig-O5'],
        ['tab-TO1', 'tab-TO2', 'tab-TO3', 'tab-TO4', 'tab-TO5', 'tab-TO6']),
    ('mesh', 'Mesh counters', [
        ('mesh-own', 'Each command reached its own node'),
    ], ['fig-N1'], ['tab-TN1']),
    ('open', 'Open items', [
        ('open-l3', 'The read stream and the L3 state'),
        ('open-items', 'Other open items'),
        ('open-notmeasured', 'Not measured'),
    ], ['fig-P1', 'fig-P2'], ['tab-TP1', 'tab-TP2', 'tab-TP3', 'tab-TP4']),
]
# The Short version carries the headline figure.
SHORT_FIGS = ['fig-H1']
# The shell adds these two h2 ids after the sections.
TAIL = ['words', 'references']

H3 = {key: [i for i, _ in subs] for key, _, subs, _, _ in SECTIONS}
FIGS = {key: figs for key, _, _, figs, _ in SECTIONS}
TABLES = {key: tabs for key, _, _, _, tabs in SECTIONS}
