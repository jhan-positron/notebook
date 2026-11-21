# Closer edits, round 1: leftovers of findings 3, 4 and 6.  Each old text must occur exactly once.
import io, sys
P = '/home/jhan/workspace/titan/cache-perf/asimov/cme_page/'
EDITS = {}

def E(f, old, new):
    EDITS.setdefault(f, []).append((old, new))

# ---------------------------------------------------------------- sec_latency.py, 4.6
E('sec_latency.py',
  "        'On %s that row counts %s outer, %s inner and %s prefetch refills per load. So every load is served '\n"
  "        'from outside the cluster.' % (n2, c4(f2f['outer']), c4(f2f['inner']), c4(f2f['hwprf'])),\n",
  "        'On %s that row counts %s outer, %s inner and %s prefetch refills per load. These counts are totals '\n"
  "        'of a rep. They do not say which load caused which refill.' % (\n"
  "            n2, c4(f2f['outer']), c4(f2f['inner']), c4(f2f['hwprf'])),\n")
E('sec_latency.py',
  "    ]))\n"
  "    out.append(S.callout(\n"
  "        'The %s is a memory model of the emulator. Its %s ns is not the timing of a silicon memory.' % (\n",
  "    ]))\n"
  "    out.append(S.hyp(\n"
  "        'On %s each load of the row with every line flushed first causes one read refill. The line of that '\n"
  "        'refill comes from outside the cluster.' % n2,\n"
  "        'A record of the refilled addresses of that row. The hypothesis predicts each line of the chain one '\n"
  "        'time in the record, each as an outer refill.'))\n"
  "    out.append(S.callout(\n"
  "        'The %s is a memory model of the emulator. Its %s ns is not the timing of a silicon memory.' % (\n")
# ---------------------------------------------------------------- sec_latency.py, 4.3
E('sec_latency.py',
  "    out.append(S.h3('lat-serve', 'What serves each footprint: refill counters per load'))\n",
  "    out.append(S.h3('lat-serve', 'Refill counters per load at each footprint'))\n")
E('sec_latency.py',
  "        '%s: the rows count %s inner refills per load and at most %s outer refills per load. So the CME L1 '\n"
  "        'serves these loads. The CME L1 holds %s (operator\\'s README) %s.' % (\n",
  "        '%s: the rows count %s inner refills per load and at most %s outer refills per load. '\n"
  "        'The CME L1 holds %s (operator\\'s README) %s. So these footprints fit in it.' % (\n")
E('sec_latency.py',
  "        'outer. So a cache inside the cluster serves these loads.' % (\n",
  "        'outer. So the inner counter counts most refills of these rows.' % (\n")
E('sec_latency.py',
  "        '%s and %s: the outer refills are %s and %s per load. The inner refills are %s and %s per load. So '\n"
  "        'both sources serve these two rows.' % (\n",
  "        '%s and %s: the outer refills are %s and %s per load. The inner refills are %s and %s per load. So '\n"
  "        'these two rows count refills of both sources.' % (\n")
E('sec_latency.py',
  "        '%s: the rows count %s outer refills per load. So most of these loads leave the cluster. The chain '\n"
  "        'load stays within %s ns over the group.' % (\n",
  "        '%s: the rows count %s outer refills per load. So the outer counter counts most refills of these '\n"
  "        'rows. The chain load stays within %s ns over the group.' % (\n")
E('sec_latency.py',
  "        '%s and %s: the outer refills are %s and %s per load.' % (\n"
  "            gF[0]['label'], gF[-1]['label'], c4(gF[0]['outer']), c4(gF[-1]['outer'])),\n"
  "    ]))\n",
  "        '%s and %s: the outer refills are %s and %s per load.' % (\n"
  "            gF[0]['label'], gF[-1]['label'], c4(gF[0]['outer']), c4(gF[-1]['outer'])),\n"
  "        'Every count of this list is a total of a rep. A total does not say which load caused which refill.',\n"
  "    ]))\n")
# ---------------------------------------------------------------- sec_glance.py, 3.1
E('sec_glance.py',
  "        f'outer refills per load, not {_n(g2[\"ocm\"][\"outer_lo\"], 4)}. The other loads of those rows are inner refills.',\n",
  "        f'outer refills per load, not {_n(g2[\"ocm\"][\"outer_lo\"], 4)}. The same rows count '\n"
  "        f'{_n(g2[\"outside-1m\"][\"inner_lo\"], 4)} and {_n(g2[\"outside-3m\"][\"inner_lo\"], 4)} inner refills per load. '\n"
  "        f'These counts are totals of a rep.',\n")
# ---------------------------------------------------------------- sec_open.py, 9.5
E('sec_open.py',
  "          f'{V.size_label(r_out)} read row of boot F1, which does not fit in the CME L1. So it is consistent '\n"
  "          f'with lines that stay in the CME L1 from one call to the next. No bandwidth row has a refill counter '\n"
  "          f'to confirm it.'] if looped_ok else []) +\n",
  "          f'{V.size_label(r_out)} read row of boot F1, which does not fit in the CME L1. No bandwidth row has '\n"
  "          f'a refill counter.'] if looped_ok else []) +\n")
E('sec_open.py',
  "               'set to zero, one and two.')],\n"
  "        ['A rep that counts its first walk and its later walks apart, to show at which time the refills occur.',\n",
  "               'set to zero, one and two.')] +\n"
  "        ([S.hyp(f'In the looped bandwidth rows from {L1S} the lines of the buffer stay in the CME L1 from one '\n"
  "                f'call to the next.',\n"
  "                'The CME refill counters on the looped bandwidth rows. The hypothesis predicts a count near '\n"
  "                'zero refills per line in a call that follows another call.')] if looped_ok else []),\n"
  "        ['A rep that counts its first walk and its later walks apart, to show at which time the refills occur.',\n")
# ---------------------------------------------------------------- sec_setup.py, 2.6 Table 6 and 2.7
E('sec_setup.py',
  "'cycles of the CME clock, over the whole '\n         'counting window', 'all'],\n",
  "'cycles of the CME clock: one total per '\n         'counting window', 'all'],\n")
E('sec_setup.py',
  "        'In the order of the code the counting window starts before the bracket and ends after it. So it counts '\n"
  "        'cycles that the bracket time does not hold %s. '\n"
  "        'No row measures how many.' % r_win,\n"
  "        'For time on those rows the page uses the ns columns, not the cycle columns. %s covers the CME cycle '\n"
  "        'counter on the <code>cme-call</code> rows.' % S.xref('callcost-cmecall', cap=True),\n",
  "        'In the order of the code the counting window starts before the bracket and ends after it. So it counts '\n"
  "        'cycles that the bracket time does not hold %s. '\n"
  "        '%s gives the core cycle count as time minus the bracket time. The rows hold no time stamp that places '\n"
  "        'that difference before or after the bracket.' % (r_win, S.xref('callcost-gap', cap=True)),\n"
  "        'For time on those rows the page uses the ns columns, not the cycle columns. %s also covers the CME '\n"
  "        'cycle counter on the <code>cme-call</code> rows.' % S.xref('callcost-gap', cap=True),\n")
# ---------------------------------------------------------------- sec_callcost.py, Figure 34 and 7.7
E('sec_callcost.py',
  "        dict(name='CME: loads inside the span', blocks=[\n"
  "            dict(start=0, end=fixed4, label=f'does not grow with the bytes: {n1(fixed4)} ns est.', kind='work',\n"
  "                 color=GREY),\n"
  "            (fixed4, S4, f'loop: {nvec} vector loads {n1(data4)} ns est.', 'work'),\n"
  "            (S4, B4, 'outside the span', 'wait')]),\n",
  "        dict(name=SPLIT_LANE, blocks=[\n"
  "            dict(start=0, end=fixed4, label=f'does not grow with the bytes: {n1(fixed4)} ns est.', kind='work',\n"
  "                 color=GREY,\n"
  "                 tip=f'{SPLIT_LANE}: does not grow with the bytes: {n1(fixed4)} ns est.\\n{SPLIT_TIP}'),\n"
  "            dict(start=fixed4, end=S4, label=f'loop: {nvec} vector loads {n1(data4)} ns est.', kind='work',\n"
  "                 tip=f'{SPLIT_LANE}: loop: {nvec} vector loads {n1(data4)} ns est.\\n{SPLIT_TIP}'),\n"
  "            (S4, B4, 'outside the span', 'wait')]),\n")
E('sec_callcost.py',
  "    GREY_LAB = 'span time that does not grow with the bytes (est.)'\n",
  "    GREY_LAB = 'span time that does not grow with the bytes (est.)'\n"
  "    # the two parts of the span are totals of a fit: they have a length and no measured place\n"
  "    SPLIT_LANE = 'span, split by the fit (est.)'\n"
  "    SPLIT_TIP = 'a length, not a position: the place inside the span is schematic'\n")
E('sec_callcost.py',
  "        f'calls is a median of {n1(b2b[F1][\"median\"] * 64)} ns. '\n"
  "        f'So the CME cycle counter also counts outside the spans of calls that follow each other.',\n",
  "        f'calls is a median of {n1(b2b[F1][\"median\"] * 64)} ns. '\n"
  "        f'The conversion uses {V.num(cpn, 3)} cycles per ns, the ratio that the long rows measure '\n"
  "        f'({S.xref(\"setup-clock\")}). At that ratio the CME cycle counter also counts outside the spans of '\n"
  "        f'calls that follow each other.',\n")
# ---------------------------------------------------------------- words.py: a term that no sentence uses
E('words.py',
  "    ('demand load', 'A load of the program that misses the cache and waits for its line. '\n"
  "                    'A prefetch is not a demand load.'),\n", "")
E('words.py', "'command', 'CSV', 'demand load', 'lone call',", "'command', 'CSV', 'lone call',")

bad = 0
for f, eds in EDITS.items():
    s = io.open(P + f, encoding='utf-8').read()
    for old, new in eds:
        n = s.count(old)
        if n != 1:
            bad += 1
            print('MISS', f, n, repr(old[:90]))
            continue
        s = s.replace(old, new)
    if '--apply' in sys.argv and not bad:
        io.open(P + f, 'w', encoding='utf-8').write(s)
print('bad', bad, 'applied' if ('--apply' in sys.argv and not bad) else 'dry run')
