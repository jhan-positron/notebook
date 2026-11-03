p = "build_plan.py"
s = open(p, encoding="utf-8").read()
n = 0
def rep(old, new):
    global s, n
    c = s.count(old); assert c == 1, (c, old[:80]); s = s.replace(old, new); n += 1
def cut(start, end, new):
    """Replace from the unique start anchor through the unique end anchor (inclusive)."""
    global s, n
    assert s.count(start) == 1, ("start", s.count(start), start[:60]); assert s.count(end) == 1, ("end", s.count(end), end[:60])
    i = s.index(start); j = s.index(end) + len(end); assert j > i
    s = s[:i] + new + s[j:]; n += 1

# ---------------------------------------------------------------- inputs: the two new texts, the two new quotes
rep('REQ = open(os.path.join(HERE, "requests.txt"), encoding="utf-8").read()',
    'REQ = open(os.path.join(HERE, "requests.txt"), encoding="utf-8").read()\n'
    'REPLY = open(os.path.join(HERE, "reply-to-jeremy-2026-10-22.txt"), encoding="utf-8").read().rstrip("\\n")\n'
    'NOTE = open(os.path.join(HERE, "note-to-arm-users-2026-10-22.txt"), encoding="utf-8").read().rstrip("\\n")')
rep('marker = {"original": "=== MESSAGE 1", "deadline": "=== MESSAGE 2", "latest": "=== MESSAGE 3"}[name]',
    'marker = {"original": "=== MESSAGE 1", "deadline": "=== MESSAGE 2", "latest": "=== MESSAGE 3", "reply": "=== MESSAGE 4", "second": "=== MESSAGE 5"}[name]')

# ---------------------------------------------------------------- CSS for the table of contents, and a chip for Jeremy's side
rep('@media print{body{background:#fff}main{max-width:none}}',
    '.contents{background:var(--surf);border:1px solid var(--grid);border-radius:6px;padding:10px 18px 8px;margin:14px 0 4px;font-size:13.5px}\n'
    '.contents h2{border:0;margin:0 0 6px;padding:0;font-size:15px}.contents ol{margin:0;padding-left:22px}.contents ol ol{padding-left:20px;margin:2px 0 4px;color:var(--sec)}\n'
    '.contents li{margin:2px 0}.contents a{text-decoration:none}.contents a:hover{text-decoration:underline}\n'
    '@media print{body{background:#fff}main{max-width:none}}')
rep('CLOSED = chip("done", "✔ closed"); OPENQ = chip("open", "○ open"); PARTQ = chip("open", "◑ partly open"); TODOQ = chip("open", "● to do (Jibin)")',
    'CLOSED = chip("done", "✔ closed"); OPENQ = chip("open", "○ open"); PARTQ = chip("open", "◑ partly open"); TODOQ = chip("open", "● to do (Jibin)")\n'
    'JSIDE = chip("jeremy", "● Jeremy\'s side"); NOTICE = chip("gray", "ℹ notice")')

# ---------------------------------------------------------------- header, TOC placeholder, short version
rep('Written for Jibin on 21 October 2026. Revised three times on 22 October (UTC).',
    'Written for Jibin on 21 October 2026. Revised four times on 22 October (UTC), the last at about 18:30 UTC after Jeremy\'s two replies and Jibin\'s change of plan (away from 22 October to about 29 October).')
rep('The three messages are quoted verbatim in section 1.</p>',
    'The three requests are quoted verbatim in section 1, Jeremy\'s two replies of 22 October in section 4.</p>')
cut('<nav class="toc">', '</nav>', '<!--TOC-->')
cut('<p><strong>Short version.</strong> Jeremy\'s account, toolchain and disk are ready on phoenix-crb,',
    'so the message in section 4, approved by Jibin, is the next step.</p>',
    '<p><strong>Short version.</strong> The host work for Jeremy is complete and he accepted every default on 22 October: cores 126–127 isolated, the performance governor, the timers paused, no nohz_full before 5 November, the latency judge as the path, and the reservation and clock rules.</p>\n'
    '<p>His data settles the 21 October void: 2,132 passes that write a logits row were each about 109 µs late, so the host clock alone cannot make a run count and his 12× faster write (not yet on Phoenix) is the fix (Figure 8).</p>\n'
    '<p>His first counted block is Friday 23 October 13:00–16:00 UTC, Jibin is away from 22 to about 29 October, and today\'s three items are the reply at the end of section 4, the note to the other <code>arm</code> users, and a contact name in both.</p>')

# ---------------------------------------------------------------- glossary
rep('(govtest-2, only if Jeremy offers a run, since Q6 was dropped from the message)."),',
    '(govtest-2, moot since 22 October: Jeremy\'s own counted blocks replace it)."),')
rep('''    ("launcher", "The shell and Python processes that start Jeremy's job (<code>ev3-churn-job.sh</code>, <code>churn.py</code>, the judge). Where they first land decides where their threads stay once cores are isolated."),
]''',
'''    ("launcher", "The shell and Python processes that start Jeremy's job (<code>ev3-churn-job.sh</code>, <code>churn.py</code>, the judge). Where they first land decides where their threads stay once cores are isolated."),
    ("logits row", "One pass's output scores, one per vocabulary entry, which the fake device thread writes into the record for the passes that need it. Jeremy's reply of 22 October: 2,132 of churn-r1's 37,275 passes wrote one, and those were the late passes."),
    ("the twins", "Jeremy's term (22 October) for churn runs that have no fake device thread. Not defined further in his message."),
    ("block (of runs)", "Jeremy's word for one reserved stretch of counted runs, announced at least 2 h ahead, with the RUNNING file present throughout. The first one is Friday 23 October 13:00–16:00 UTC."),
    ("RUNNING file", "<code>/tmp/positron-perf.RUNNING</code>, written by Jeremy's run script at the start of a block (start, end, pid, tag, commit) and removed at the end. His script refuses to start if the file exists or if the run would end after 21:00 UTC. His build script stops a build when the file appears. For everyone else the rule is: while the file exists, stay off the host."),
    ("measure-job, smoke-setup, phxship, phx-isol.py", "Jeremy's scripts seen on the host on 22 October: the measurement job for a block (CPU, memory, disk and compile steps, then the churn run), its two smoke runs on CPUs 0–7, the build of commit <code>fa7f715f</code> on CPUs 0–95, and a sampler that reads no per-CPU file of CPUs 120–127 during a run."),
    ("fio", "A disk benchmark program. Jeremy's block runs it with direct I/O on up to 32 GiB of temporary files under his home."),
    ("host-timing gate", "The later SDK gate that uses tools/perf and is the only user of nohz_full (Jeremy, 22 October). Not part of the 5 November demo."),
]''')

# ---------------------------------------------------------------- section 3 rows
rep('''    ("Nothing else running during timed runs, nightly window", PART, "Host side done 22 Oct 05:30–05:33 UTC: 11 timers disabled, tmpfiles-clean masked, netperf stopped and disabled (sysstat kept, A8). The host is near idle. The reservation rule and the windows (D4) are still Jeremy's to accept.", "yes", "no", "no", "yes: D4 (windows in UTC)"),''',
    '''    ("Nothing else running during timed runs, nightly window", DONE, "Host side done 22 Oct 05:30–05:33 UTC: 11 timers disabled, tmpfiles-clean masked, netperf stopped and disabled (sysstat kept, A8). Jeremy accepted the windows and the reservation rule on 22 Oct (D4 closed). His run script writes the RUNNING file and refuses to start a run that would end after 21:00 UTC (his reply). The other <code>arm</code> users get the rule from Jibin today (A14).", "yes", "no", "no", "answered 22 Oct: accepted"),''')
rep('''    ("One job at a time", PART, "No host mechanism. The perf lane holds a lock. The churn script does not. A marker-file rule is proposed in D4.", "no", "no", "no", "yes: D4 (reservation rule)"),''',
    '''    ("One job at a time", DONE, "No host mechanism, by design. Jeremy's run script creates <code>/tmp/positron-perf.RUNNING</code> and refuses to start while it exists, and his build script stops a build when the file appears (seen on the host 22 Oct, <code>runs/phxship-fa7f715f5f86/build-job.sh</code>).", "no", "no", "no", "answered 22 Oct: accepted"),''')
rep('''    ("Counted runs from Monday 26 Oct", UNK, "The host setup is done (22 October), without nohz_full. Validity is unproven: the first run was voided by the device thread's mean lateness, and the host clock alone does not explain it (measured). A pinned device thread (D5) or a re-run that proves otherwise is needed.", "yes", "yes", "depends on D2", "yes: D2, D5"),''',
    '''    ("Counted runs from Monday 26 Oct", PART, "The host setup is done, and the first counted block comes earlier: Fri 23 Oct 13:00–16:00 UTC (Jeremy's notice, 22 Oct). Whether a churn run counts depends on Jeremy's side: the 21 Oct void came from 2,132 logits-row passes each about 109 µs late (his data), the host clock alone cannot bring the mean under 2.5 µs (Figure 8), and his 12× faster write is not on Phoenix yet.", "yes", "yes", "no", "answered 22 Oct: judge path, device thread to 126, blocks announced 2 h ahead"),''')
rep('''never booted on this board.", "yes", "yes", "yes", "yes: D1, D2"),''',
    '''never booted on this board. Deferred on 22 Oct: Jeremy says only the later tools/perf host-timing gate needs it, not 5 Nov, and he will say before they need it (Q2).", "yes", "yes", "yes", "answered 22 Oct: not needed before 5 Nov"),''')
rep('''nohz_full CPUs get it automatically.", "yes", "yes", "yes", "no (follows D1)"),''',
    '''nohz_full CPUs get it automatically.", "yes", "yes", "yes", "answered 22 Oct: not needed before 5 Nov"),''')
rep('''"yes: D3 (which CPUs, and the job's launch command). 126-127 applied by default at the 22 Oct reboot"),''',
    '''"answered 22 Oct: keep 126-127 (D3 closed), launch line adopted"),''')
rep('''"no", "no", "no", "nice: keep it"),''', '''"no", "no", "no", "answered 22 Oct: used only for pinned package installs, never during a timed run"),''')
rep('''    ("Test 2: sampling unit tests on Arm", UNK, "No test run is recorded. The build job built three targets only, and no ctest or pytest log exists under <code>~/positron</code>.", "no", "no", "no", "nice: Q9"),''',
    '''    ("Test 2: sampling unit tests on Arm", NA, "Jeremy, 22 Oct: they run on GitHub's native Arm runners on every C++ change, not on Phoenix yet, need no isolation, and will run on cores 0–95 later. Not needed for Monday.", "no", "no", "no", "answered 22 Oct"),''')
rep('''    ("Test 3: timed compile", NOTDONE, "The <code>compile-0.8b</code> gate runs on the perf lane, which the SDK README says “does not run it yet”. No compile wall time is recorded.", "no", "no", "depends on D2", "nice: Q9"),''',
    '''    ("Test 3: timed compile", NOTDONE, "Jeremy, 22 Oct: not ready on his side and not needed for Monday. His measurement plan seen on the host the same day runs an import-hf build through a script named <code>timed_compile.py</code>; whether that is this test is not stated.", "no", "no", "no", "answered 22 Oct"),''')

# ---------------------------------------------------------------- section 4: title, intro, decision table
rep('<h2>4. Do we need input from Jeremy to proceed?</h2>', '<h2>4. Jeremy\'s input: the six decisions, his replies of 22 October, and the messages</h2>')
cut('<p><strong>Not to start.</strong> The governor change,', 'Jibin can run it at any idle moment.</p>',
    '<p><strong>All six decisions are closed.</strong> Jeremy answered on 22 October (his replies are quoted below) and took every default. The table keeps the reasoning for the record and adds his answer in the last column. The second table holds the administrator questions, with five new ones from his replies (A12 to A16), three of them for Jibin today.</p>')
rep('<tr><th style="width:4%">#</th><th style="width:24%">Decision</th><th>Why it matters</th><th style="width:26%">Default if no answer</th></tr>',
    '<tr><th style="width:4%">#</th><th style="width:20%">Decision</th><th>Why it matters</th><th style="width:20%">Default if no answer</th><th style="width:24%">Jeremy\'s answer, 22 Oct</th></tr>')
rep('Treat nohz_full as a parallel kernel task (plan step P4).</td></tr>',
    'Treat nohz_full as a parallel kernel task (plan step P4).</td><td>""" + CLOSED + """ Q1: yes. The 250 Hz tick costs at most about 0.05% of a busy core, inside the limits he judges. Friday stood and was met on 22 October.</td></tr>')
rep('Assume the latency judge. Keep the kernel task running in parallel.</td></tr>',
    'Assume the latency judge. Keep the kernel task running in parallel.</td><td>""" + CLOSED + """ Q2: the churn label and the latency judge on the current kernel. tools/perf is for a later host-timing gate, not 5 November, and is the only user of nohz_full; he will say before they need it. The kernel task is deferred (P4).</td></tr>')
rep('One-core variant: isolate 127 only.</td></tr>',
    'One-core variant: isolate 127 only.</td><td>""" + CLOSED + """ Q3: keep 126–127, no reboot: 127 for the pass thread, 126 for the device thread, his other threads on 120–125. His next run uses the double taskset line; the inner set becomes 120–127 once the device thread pins itself (fine, with the outer call kept: A16).</td></tr>')
rep('from one feedback-counter pair read before and after the run, no polling during it.</td></tr>',
    'from one feedback-counter pair read before and after the run, no polling during it.</td><td>""" + CLOSED + """ Q5 and the clock rule accepted: Mon–Fri 13:00–21:00 UTC, 2 h notice, the RUNNING file (start, end, pid, tag, commit), no run that would end after 21:00 UTC. Clock: 2,772 MHz from one CPPC pair before and after, read on 126 and 127, nothing read during; a miss voids the run. Only a few blocks: one next week, one or two before 5 November. His question back: builds and untimed tests on 0–95 outside the window (A15: yes).</td></tr>')
rep('A governor-only run is no longer possible: the reboot came before any re-run.</td></tr>',
    'A governor-only run is no longer possible: the reboot came before any re-run.</td><td>""" + CLOSED + """ Q4: yes, the device thread goes to 126 with 1 µs slack; change in progress, aim before Monday, else 126 stays idle. No churn run with a device thread has been non-void yet. The 21 October lateness came entirely from the 2,132 logits-row passes (105–111 µs late each at 1.6 GHz); the write is 12× faster on main (about 5 µs against a 26.6 µs window on LSF hosts), not yet on Phoenix. Figure 8.</td></tr>')
rep('Validation uses Jibin\'s own probes (hiccup and feedback counters) and Jeremy\'s own first run.</td></tr>',
    'Validation uses Jibin\'s own probes (hiccup and feedback counters) and Jeremy\'s own first run.</td><td>""" + CLOSED + """ Item 1: the alpha sessions and churn-r1 were his side\'s. No re-run by Jibin. His Friday block is the first run on the as-built host.</td></tr>')
rep('<p><strong>Useful but not blocking.</strong> Q8, Q9 and part of Q10 are in the message\'s “Nice to have” paragraph. Q7 is moot (the governor is on all 128 CPUs). Q11 is answered by A10 and by item 6 of the message. Q12 is not asked yet:</p>',
    '<p><strong>The side questions, after 22 October.</strong> Q7 is moot (the governor is on all 128 CPUs). Q8 answered: the clock rule is accepted, and his tool reads the counter pair on 126 and 127. Q9 answered: the sampling tests run on GitHub\'s Arm runners and need no isolation, the timed compile is not ready, and neither is needed for Monday. Q10 answered: nothing needed, they bring clang and ninja and create the directories. Q11 answered: outbound access is used only for pinned package installs, never during a timed run. Q12 was not asked; its second item is answered by his data (the lateness came from the logits-row writes, not from the interrupts). The list stays for the record:</p>')

# ---------------------------------------------------------------- admin table
rep('<p>Jibin answered these on 22 October between 04:30 and 06:35 UTC. The fourth column records the answer, what was done afterwards (up to 05:48 UTC), and whether the question is still open.</p>',
    '<p>Jibin answered A1 to A11 on 22 October between 04:30 and 06:35 UTC. A12 to A16 come from Jeremy\'s two replies later that day. The fourth column records the answer, what was done afterwards, and whether the question is still open.</p>')
rep('Item 1 of the message asks Jeremy to confirm this.</td></tr>',
    'Item 1 of the message asked Jeremy to confirm this, and he did on 22 October: the sessions from alpha and the churn-r1 run were his side\'s.</td></tr>')
rep('If Jeremy picks the latency judge (the default), the rebuilt kernel is wanted but not required before the demo.</td></tr>',
    'Jeremy picked the latency judge on 22 October and said tools/perf, the only user of nohz_full, is for a later gate, so the rebuilt kernel is deferred (P4) and nothing blocks the demo. Arm\'s answer is still pending, and nothing waits on it this week.</td></tr>')
rep('''Items 4 and 5 of the draft below carry the two statements, item 4 in Jibin's own words.</td></tr>
</table>''',
'''Items 4 and 5 of the draft below carry the two statements, item 4 in Jibin's own words.</td></tr>
<tr class="sep"><td>A12</td><td>May Jeremy keep running counted blocks under the same rule while Jibin is away (23 to about 29 Oct), and who is the contact if the host needs attention? (Jeremy's second message, item 2.)</td><td>Jibin alone has the BMC console (A3). The other <code>arm</code> users have root for everything else.</td><td>""" + TODOQ + """ Jibin answers in the reply below. Proposed: yes, same rule. The reply has a marked place for the contact's name and channel, which only Jibin can fill in.</td></tr>
<tr><td>A13</td><td>Were the three interactive positron-perf logins from 192.168.2.136 (21 Oct 05:15 and 23:37, 22 Oct 00:51 UTC) Jibin's? (Jeremy's first reply, item 1.)</td><td>Jeremy wants to know who else enters his account.</td><td>""" + CLOSED + """ Yes. 192.168.2.136 is Jibin's workstation. The host's login record shows each lasted 3 to 5 s. The first came a minute after the account was created from the same address (<code>arm</code> sessions 05:03–05:14 UTC, sudoers file 05:12 UTC). The third was followed within seconds by a 27-minute <code>arm</code> session from the same address that created the <code>jhan</code> account. They were Jibin's own test logins and the agent's read-only checks [verification-2026-10-22/state-1756.txt].</td></tr>
<tr><td>A14</td><td>Tell the other <code>arm</code> users the rule, the Friday block and the away week.</td><td>Jibin promised it in Q5 of the message. Nobody else will do it while Jibin is away.</td><td>""" + TODOQ + """ Today, before Jibin leaves. The note at the end of this section is ready, with the channel and the contact to fill in.</td></tr>
<tr><td>A15</td><td>Builds and untimed tests on cores 0–95 outside the window: OK? (Jeremy, Q5.)</td><td>Those cores are shared with the other engineers' work.</td><td>""" + TODOQ + """ Proposed answer in the reply: yes, at any time, with the note that build times vary when the other engineers are busy.</td></tr>
<tr><td>A16</td><td>Keep CPU 126 in the inner taskset set (120–127) once the device thread pins itself? (Jeremy, launch line.)</td><td>A taskset call whose new set does not contain its current CPU is moved by the kernel to any CPU of the new set, isolated ones included. That is why the outer <code>taskset -c 120-125</code> exists.</td><td>""" + TODOQ + """ Proposed answer in the reply: yes, as long as the outer call stays. With it, the inner call already runs inside its set and nothing moves, and threads created later never land on 126 or 127 by themselves.</td></tr>
</table>''')
rep('<p>Still to do: send the message below, then wait for Arm\'s answer on the kernel source (A6).</p>',
    '<p>Done since: the message below was sent on 22 October and Jeremy replied the same day (quoted after it). Still to do today: the reply and the note at the end of this section.</p>')
rep('''<h3>Message to Jeremy (approved, ready to send)</h3>
<p>Updated 22 October 07:00 UTC with Jibin's answers, the as-built state, and Jibin's edits (items 4, 5 and 7, Q1 and Q5 shortened, Q6 dropped, PDT and EDT next to every UTC time). Jibin accepted A11, so the text is final.</p>''',
'''<h3>Message sent to Jeremy on 22 October (for the record)</h3>
<p>Final text as sent by Jibin on 22 October. Jeremy answered it the same day; his reply follows.</p>''')

# ---------------------------------------------------------------- section 4: the new subsections after the sent message
rep('''~/positron/fetchcontent, artifacts and work/sdk-v2 do not exist yet.</pre></blockquote>
</section>""")''',
'''~/positron/fetchcontent, artifacts and work/sdk-v2 do not exist yet.</pre></blockquote>
<h3>Jeremy's reply, 22 October (quoted)</h3>
<blockquote><pre>""" + html.escape(q('reply')) + """</pre></blockquote>
<h3>Jeremy's second message, 22 October, later the same day (quoted)</h3>
<blockquote><pre>""" + html.escape(q('second')) + """</pre></blockquote>
<h3>What the two replies say, in plain English</h3>
<p>Every line of the two messages, what it means for the host, and what changes. Chips: """ + CLOSED + """ settled, """ + JSIDE + """ Jeremy's side is doing it, """ + TODOQ + """ Jibin's action today, """ + NOTICE + """ information only.</p>
<table><tr><th style="width:4%">#</th><th style="width:28%">Jeremy wrote</th><th style="width:30%">In plain English</th><th>What changes, and where it stands</th></tr>
<tr><td>R1</td><td>The 21 Oct sessions from 192.168.1.200 and the churn-r1 run were ours. The interactive positron-perf logins from 192.168.2.136 were not. Were those you?</td><td>He confirms that the staging from alpha and the first run were his side's work, and asks who made three short logins from Jibin's workstation.</td><td>""" + CLOSED + """ A2 and D6 closed (no re-run by Jibin). A13 answers the logins: Jibin's own tests and the agent's read-only checks, 3 to 5 s each. Item 3 of the reply says so.</td></tr>
<tr><td>R2</td><td>Thanks for keeping outbound access. We only use it to install pinned package versions, and never during a timed run.</td><td>The host keeps its internet access. He downloads packages only between runs.</td><td>""" + CLOSED + """ Q11 closed. Nothing to do.</td></tr>
<tr><td>R3</td><td>Q1: Yes. The 250 Hz tick costs at most about 0.05% of a busy core, well inside the limits we judge.</td><td>A host without nohz_full is acceptable for the counted runs. His estimate matches this plan's: 250 ticks per second at 1 to 2 µs each is 0.025% to 0.05% of a core.</td><td>""" + CLOSED + """ D1 closed. The Friday deadline was met on 22 October.</td></tr>
<tr><td>R4</td><td>Q2: The churn label + latency judge, on the current kernel. tools/perf is for a later host-timing gate, not 5 Nov, and it's the only thing that needs nohz_full. I'll let you know before we need it.</td><td>The numbers that count come from the latency judge, which runs on the kernel as it is. The tool that refuses a host without nohz_full is not part of the demo.</td><td>""" + CLOSED + """ D2 closed. The kernel rebuild (A6, P4) is deferred until he asks; Arm's GitHub access is no longer on any path before 5 November.</td></tr>
<tr><td>R5</td><td>Q3: Keep 126-127, no reboot needed: 127 for the pass thread, 126 for the device thread, the rest of our threads on 120-125.</td><td>The core split as built is what he wants. No second reboot.</td><td>""" + CLOSED + """ D3 closed. Figure 6 shows the split.</td></tr>
<tr><td>R6</td><td>Q4: Yes, we'll pin the device thread to 126 with 1 us timer slack. No churn run with a device thread has been non-void yet (only the twins, which have none).</td><td>He takes the SDK-side change this plan asked for. No churn run that has a fake device thread has ever produced a valid record, on any host.</td><td>""" + JSIDE + """ D5 closed on his side: change in progress, aim before Monday 26 October; if not ready, his runs use the double taskset line and 126 stays idle.</td></tr>
<tr><td>R7</td><td>The 21 Oct run was the closest at 6.25 us mean, and all of it came from the 2,132 passes that write a logits row, each about 105-111 us late at 1.6 GHz; none of the other 35,143 passes was late.</td><td>The cause of the void is now known: a specific piece of work on the device thread (writing the pass's output scores) takes longer than its window on 5.7% of the passes. The other 94.3% were on time.</td><td>""" + CLOSED + """ Hypothesis H3 of section 5.3 is confirmed; H2 and H4 did not contribute to the mean. The arithmetic matches the record (2,132 × 109 µs / 37,275 = 6.25 µs). Figure 8 gives the budget: each of those passes may be at most 43.7 µs late for the mean to stay at 2.5 µs.</td></tr>
<tr><td>R8</td><td>That write is now about 12x faster on main (about 5 us against its 26.6 us window on our LSF hosts), but it isn't on Phoenix yet.</td><td>The fix exists in his main branch and is not yet in the code on this host.</td><td>""" + JSIDE + """ This is what makes a run count. The governor alone would leave each late pass 51 to 109 µs late (est.), still over the budget (Figure 8). Whether the tree built on the host today (commit fa7f715f) carries the fix is not stated.</td></tr>
<tr><td>R9</td><td>Q5: Accepted: counted runs only Mon-Fri 13:00-21:00 UTC, 2 h notice, and the RUNNING file. We only need a few blocks of runs: one next week, then one or two before 5 Nov. I'll post each block's times here at least 2 h before it starts.</td><td>He agrees to the reservation rule, and expects two or three blocks in total before the demo. He announces each one in the channel of this conversation.</td><td>""" + CLOSED + """ D4 closed. The announcements reach Jibin's channel; the other <code>arm</code> users need the rule from Jibin (A14) and, while Jibin is away, a way to see the announcements (the note names the channel).</td></tr>
<tr><td>R10</td><td>Builds and untimed tests stay on cores 0-95 and never overlap a RUNNING file. Are those OK outside the window?</td><td>He asks whether he may build and run untimed tests at any hour, on the first 96 cores, as long as no timed run is in progress.</td><td>""" + TODOQ + """ A15. Proposed answer: yes (item 4 of the reply). Those cores are shared with the other engineers' work.</td></tr>
<tr><td>R11</td><td>Clock rule: Yes, 2772 MHz from one CPPC pair before and after, nothing read during the run. We'll read it on 126 as well as 127. A miss voids the run rather than failing it.</td><td>He accepts the clock pass rule and extends it to the device core. A run whose clock was too low is discarded, not reported as a failure.</td><td>""" + CLOSED + """ Q8 closed. His tool already records the rule (seen in the smoke-run summary on the host: “delivered MHz ≥ 2772 on every measured CPU, one CPPC pair before and after the block”).</td></tr>
<tr><td>R12</td><td>Launch line: our next run uses yours. Once the device thread pins itself, the inner set becomes 120-127 so our tool can give it 126; the outer taskset still starts the shell and Python on 120-125. Tell me if you'd rather keep 126 out of the set.</td><td>He adopts the double taskset line, and asks whether the inner set may include CPU 126 later.</td><td>""" + TODOQ + """ A16. Proposed answer: yes, as long as the outer call stays (item 5 of the reply gives the reason).</td></tr>
<tr><td>R13</td><td>RUNNING file: our run script creates /tmp/positron-perf.RUNNING (start, end, pid, tag, plus our commit), refuses to start if the file exists or if the run would end after 21:00 UTC, and removes it when it exits. If a run is ever killed hard and leaves the file behind, we remove it only after checking its pid is gone.</td><td>His script enforces the rule on his side, including the end of the window.</td><td>""" + CLOSED + """ Seen on the host on 22 October: his build job refuses to start while the file exists and stops a build when it appears; his measurement summary records the file and the block end.</td></tr>
<tr><td>R14</td><td>Before Monday we'll copy in the latest code and rebuild on 0-95, outside any counted run.</td><td>A fresh build of the SDK on the host, on the housekeeping cores.</td><td>""" + CLOSED + """ Done 22 October 16:19 UTC: commit fa7f715f built on CPUs 0–95 at nice 10 with 32 jobs, log ends <code>BUILD-DONE rc=0</code> (section 5.7).</td></tr>
<tr><td>R15</td><td>Sampling tests: they run on GitHub's native Arm runners on every C++ change, but not on Phoenix yet. They don't need isolation, so we'll run them on 0-95 later. The timed compile isn't ready on our side yet. Neither is needed for Monday.</td><td>Test 2 happens elsewhere for now. Test 3 is not ready. Nothing of either is needed for the first runs.</td><td>""" + CLOSED + """ Q9 closed. Section 3 rows updated.</td></tr>
<tr><td>R16</td><td>tools/perf setup: nothing needed. We bring our own clang and ninja and create those directories ourselves.</td><td>The three user-level gaps this plan listed for the perf lane are his side's to fill, when that lane is used.</td><td>""" + CLOSED + """ Q10 closed.</td></tr>
<tr class="sep"><td>R17</td><td>We'll run our first counted block tomorrow, Fri 23 Oct, 13:00-16:00 UTC: CPU, memory and disk measurements on CPUs 0-125 (126-127 untouched; up to 32 GiB of temporary files under our home, deleted at the end), then one churn latency run. /tmp/positron-perf.RUNNING is present for the whole block.</td><td>This is the 2 h notice the rule asks for, one day ahead. It is a notice, not a question and not a host task. For three hours the whole host is his, except the two isolated cores, which his measurements leave alone.</td><td>""" + NOTICE + """ Nothing to do on the host. The disk fits: 1.7 TB free, his own setup log puts the block's peak at about 39 GB. The block is 06:00–09:00 PDT, before most Pacific-time colleagues start. Jibin's part: tell the other users (A14) and acknowledge (item 1 of the reply).</td></tr>
<tr><td>R18</td><td>While you're out next week, is it OK if we keep running counted blocks under the same rule (weekdays 13:00-21:00 UTC, notice here, the RUNNING file)? And who should we contact if the host needs attention?</td><td>He asks for permission to continue without Jibin, and for a contact.</td><td>""" + TODOQ + """ A12. Jibin answers both (item 2 of the reply): yes, same rule, proposed; the contact's name and channel are Jibin's to fill in.</td></tr>
</table>
""")
A(fig("fig_lateness_budget", "Figure 8. Where churn-r1's mean lateness came from (left) and how late each logits-row pass may be (right). Left: 2,132 of the 37,275 passes wrote a logits row and were late, the other 35,143 were on time (Jeremy's data, 22 October). Right: the measured 105 to 111 µs per late pass at 1.6 GHz, the estimate for the performance governor alone (51 µs if the write scales with the clock, 109 µs if it does not), and the estimate with the 12× faster write (inside the 26.6 µs window, so not late). The dashed red line is the budget: 43.7 µs per late pass keeps the mean at 2.5 µs. The governor alone cannot reach it. The estimates assume the window is 26.6 µs on Phoenix too."))
A("""<table><tr><th style="width:44%">Quantity</th><th class="num">Value</th><th>How it is known</th></tr>
<tr><td>Passes in churn-r1 (Jeremy's count: 2,132 late + 35,143 on time)</td><td class="num">37,275</td><td>Jeremy, 22 Oct. The record's bind summary counts 37,282, seven more; the difference does not change the result.</td></tr>
<tr><td>Mean lateness of one logits-row pass, 6.25 µs × 37,275 / 2,132</td><td class="num">109.3 µs</td><td>Computed; Jeremy says 105 to 111 µs, so the two agree.</td></tr>
<tr><td>Budget per late pass for a 2.5 µs mean, 2.5 µs × 37,275 / 2,132</td><td class="num">43.7 µs</td><td>Computed, assuming every other pass stays on time.</td></tr>
<tr><td>Lateness per late pass at 2.8 GHz, governor alone</td><td class="num">51 to 109 µs est.</td><td>Lower bound: the write (26.6 + 109.3 = 135.9 µs) scales with the clock, 135.9 × 1.6 / 2.8 = 77.6 µs, minus the window. Upper bound: no scaling. Mean 2.9 to 6.25 µs: void either way.</td></tr>
<tr><td>Write time with the 12× faster code on Phoenix</td><td class="num">6 to 11 µs est.</td><td>135.9 / 12 and 77.6 / 12. Both inside the 26.6 µs window, so these passes stop being late. Measured on LSF hosts: about 5 µs (Jeremy).</td></tr>
</table>
<h3>Reply to Jeremy (to send today, before Jibin logs out)</h3>
<p>It acknowledges the Friday block, answers his five questions (items 1 to 5), says what stays as it is during the away week, and gives him the arithmetic above. Two places marked <code>&lt;&lt;Jibin: …&gt;&gt;</code> need Jibin's words: the contact's name and the channel (A12). Everything else is ready. The same text is saved as <code>reply-to-jeremy-2026-10-22.txt</code> in the evidence folder.</p>
<blockquote><pre>""" + html.escape(REPLY) + """</pre></blockquote>
<h3>Note to the other users of phoenix-crb (to send today)</h3>
<p>For the engineers who use the <code>arm</code> account (A14). One place to fill in: the channel where Jeremy announces his blocks, and the contact (A12). Saved as <code>note-to-arm-users-2026-10-22.txt</code>.</p>
<blockquote><pre>""" + html.escape(NOTE) + """</pre></blockquote>
</section>""")''')

# ---------------------------------------------------------------- section 5.3 and 5.7
rep('''Measurement: hiccup with and without the slack, then the SDK change (D5).</li>
</ul>
""")''',
'''Measurement: hiccup with and without the slack, then the SDK change (D5).</li>
</ul>
<div class="callout"><strong>Settled on 22 October by Jeremy's data.</strong> H3 is the cause: all of churn-r1's lateness came from the 2,132 passes that write a logits row, each 105 to 111 µs late at 1.6 GHz, and none of the other 35,143 passes was late. H2 and H4 did not contribute to the mean (they can still add tail latency, which the pin to 126 and the 1 µs slack address). The arithmetic and the budget per late pass are in Figure 8 (section 4). The write is 12× faster on main and not yet on Phoenix, so the clock alone cannot make a run count (2.9 µs mean est. at best).</div>
""")''')
rep('''<tr><td>Not present</td><td>No ctest or pytest log (test 2 unverified).''',
'''<tr><td>runs/phxship-fa7f715f5f86, work/fa7f715f5f86, runs/measure, measure/, tools/fio-3.43, runs/phx-isol.py (22 Oct 16:19–16:48 UTC)</td><td>Seen on 22 October after Jeremy's first reply, read-only: a new tree at commit <code>fa7f715f</code> built on CPUs 0–95 at nice 10 with 32 jobs by <code>build-job.sh</code>, which refuses to start while the RUNNING file exists and stops the build if it appears (log ends <code>BUILD-DONE rc=0</code>). A measurement job with groups A, C and B: an import-hf build and a timing table run through <code>timed_compile.py</code>, memory-bandwidth, hashing and <code>fio</code> disk steps (direct I/O, io_uring), then the churn run. Two smoke runs on CPUs 0–7 at 16:23 and 16:30 UTC passed; their summary records the clock rule (“delivered MHz ≥ 2772 on every measured CPU, one CPPC pair before and after the block”), the RUNNING file and the block end. Their setup log puts a block's peak disk use at about 39 GB (32 GiB of fio files plus 6.6 GB of artifacts) against 1,690 GiB free. <code>phx-isol.py</code> is isol.py changed to read no per-CPU sysfs file of CPUs 120–127 during a run, because such a read can interrupt the isolated core (the effect this check measured as two IPIs per counter read). No positron-perf process was running at 17:56 UTC [verification-2026-10-22/state-1756.txt].</td></tr>
<tr><td>Not present</td><td>No ctest or pytest log (test 2 unverified).''')

# ---------------------------------------------------------------- section 6
rep('<h2>6. Action plan</h2>', '<h2>6. Action plan, revised 22 October after Jeremy\'s replies</h2>')
rep('"Figure 5. Timeline from 21 October to the 5 November demo, as built. The live root changes (about 05:25–05:36 UTC) and the reboot (05:43 UTC) were done on 22 October, one day before the Friday deadline. The kernel rebuild runs in parallel and does not block Friday. The bottom row marks the host timers, which fired until they were paused at 05:30 UTC on 22 October (gray marks show when they would have fired), the two weekly fstrim runs (paused), and the US clock change on Sunday 1 November."',
    '"Figure 5. Timeline from 21 October to the 5 November demo, revised 22 October. The live root changes and the reboot were done on 22 October, the message went out and Jeremy replied the same day, and his side built new code on the host that afternoon. His first counted block is Friday 23 October 13:00–16:00 UTC, his device-thread change aims at Monday 26 October, and his remaining blocks fall between then and the demo. Jibin is away from 22 to about 29 October (dates approximate). The kernel rebuild is deferred to after the demo. The bottom row marks the host timers, paused since 22 October 05:30 UTC (gray marks show when they would have fired), and the US clock change on Sunday 1 November."')
rep('<h3>P0. 21 October evening (PDT): decide and write (done, except the message)</h3>', '<h3>P0. Done 21 to 22 October: decide, write, send</h3>')
rep('<li>Send Jeremy the draft message in section 4 (status, corrections, six questions with defaults).</li>',
    '<li>The message in section 4 was sent on 22 October, and Jeremy answered the same day, taking every default.</li>')
rep('<h3>P3. 22 to 23 October: validate (host checks passed 22 Oct 05:44 UTC), then hand off</h3><div class="meta">Owner: Jibin with Jeremy. Deadline: Friday 23 October 21:00 UTC (Jeremy\'s end of day).</div>',
    '<h3>P3. Done 22 October: validation and the hand-off message</h3><div class="meta">Owner: Jibin with Jeremy. The Friday deadline was met on 22 October: the host checks passed at 05:44 UTC, the message went out, and Jeremy replied the same day. The notes below stay for the record.</div>')
rep('<li>Run Jeremy\'s job again on the isolated setup (<code>govtest-2</code>, only if Jeremy offers it, since Q6 was dropped from the message), with the launch line changed so that nothing lands on an isolated CPU by chance. The current line 24 of <code>ev3-churn-job.sh</code> and its replacement:</li>',
    '<li>No re-run by Jibin: Jeremy\'s own blocks are the runs on the as-built host (D6 closed). The launch line below is the one his next run uses; the inner set widens to 120–127 once the device thread pins itself (A16):</li>')
rep('<h3>P4. In parallel: a kernel with nohz_full</h3><div class="meta">Owner: Jibin, once Arm grants the GitHub access that Dan requested on 22 October (path A below), then the administrator for the install. Reboot: a second one. Target: before 5 November if D2 says the perf lane counts, otherwise after the demo.</div>',
    '<h3>P4. Deferred to after the demo: a kernel with nohz_full, only when Jeremy asks for the tools/perf host-timing gate</h3><div class="meta">Owner: Jibin, once Arm grants the GitHub access that Dan requested on 22 October (path A below), then the administrator for the install. Reboot: a second one. Target: after 5 November. Jeremy said on 22 October that tools/perf is the only user of nohz_full, is not needed for the demo, and that he will say before they need it (Q2). Nothing here runs during the away week.</div>')
rep('"Figure 7. Friday\'s hand-off runs on the current kernel. nohz_full needs one of three kernel paths.',
    '"Figure 7. The counted runs use the current kernel. nohz_full, deferred on 22 October until Jeremy asks for the tools/perf gate, needs one of three kernel paths.')
cut('<div class="phase"><h3>P5. Monday 26 October to Thursday 5 November: counted runs</h3>',
    'expect an immediate apt catch-up run, and decide whether to keep the governor and isolation.</li>\n</ul>""")',
'''<div class="phase"><h3>P5. Thursday 22 October, before Jibin logs out: reply, note, record</h3><div class="meta">Owner: Jibin. Needs: nothing on the host. The host is in its final state for the demo, and nothing expires while Jibin is away.</div>
<ul>
<li>Send Jeremy the reply at the end of section 4. It acknowledges the Friday block, answers his five questions, and names the contact for next week (A12: Jibin fills in the name and the channel).</li>
<li>Send the note at the end of section 4 to the other <code>arm</code> users (A14): the Friday block, the weekday windows, the RUNNING-file rule, the isolated cores, and what not to change while Jibin is away.</li>
<li>Done 17:56 UTC, read-only as positron-perf: boot line, isolated list, 128 × performance, rcu_normal 1, timers off, netserver gone, no RUNNING file, zero interrupts on 126–127 in 10 s, Jeremy's build finished (<code>BUILD-DONE rc=0</code>), no positron-perf process [verification-2026-10-22/state-1756.txt].</li>
<li>Arm's GitHub access (A6): no action. It matters only for P4.</li>
</ul></div>
<div class="phase"><h3>P6. Friday 23 October 13:00–16:00 UTC (06:00–09:00 PDT, 09:00–12:00 EDT): Jeremy's first counted block, Jibin absent</h3><div class="meta">Owner: Jeremy. Host: unattended, nothing to do. Nobody else on the host for the whole block.</div>
<ul>
<li>What runs, from his notice and his measurement plan on the host: CPU, memory and disk measurements on CPUs 0–125 (an import-hf build and timing table, memory bandwidth, hashing, <code>fio</code> with up to 32 GiB of temporary files under his home, deleted at the end), then one churn latency run. The RUNNING file is present throughout, and his script refuses to start a run that would end after 21:00 UTC.</li>
<li>Disk: 1.7 TB free on the root file system. His own setup log puts the block's peak at about 39 GB. The root file system discards freed blocks online, so the deletion costs nothing later.</li>
<li>Cores 126–127 stay untouched by the measurements. The churn run uses the double taskset line unless the device-thread pin is already on Phoenix, in which case the device thread goes to 126.</li>
<li>What to read afterwards (Jeremy's side, or Jibin on return): the judge verdict and the <code>void</code> flag, the device's <code>late_mean_s</code> against the band, which passes were late (the logits-row passes again, or none), and the clock pair on 126 and 127 (≥ 2,772 MHz). A void from the logits-row write is expected until the 12× faster write is on Phoenix (Figure 8).</li>
</ul></div>
<div class="phase"><h3>P7. 23 to about 29 October: Jibin away, Jeremy's blocks continue under the rule</h3><div class="meta">Owner: Jeremy for the runs, the other <code>arm</code> users for anything else, the contact named in the reply for problems. Host: unattended.</div>
<ul>
<li>Jeremy's side, by his reply: the device thread pinned to 126 with 1 µs slack (aim: before Monday 26 October, else 126 stays idle), the RUNNING-file script (in place, seen on the host), the rebuilt tree (done 22 October 16:19 UTC), one block of counted runs next week announced 2 h ahead, builds and untimed tests on cores 0–95 outside the blocks.</li>
<li>The other <code>arm</code> users: run <code>ls /tmp/positron-perf.RUNNING</code> before any work. If the file exists, stay off the host (even a login sends two interrupts to every core). Do not change boot settings, install packages, re-enable timers or reboot. If a reboot is unavoidable, the settings persist (they are on the boot line and in enabled units), but it kills any run in progress.</li>
<li>If the host needs attention: the <code>arm</code> users have root for anything that does not need the console. The BMC console is Jibin's only (A3), so a kernel or boot problem waits for Jibin, and the contact (A12) decides whether to reach Jibin.</li>
<li>No action for Jibin and none for this analysis. Read-only checks resume on request after Jibin returns.</li>
</ul></div>
<div class="phase"><h3>P8. About 29 October to Thursday 5 November: Jibin back, the last blocks, the demo</h3><div class="meta">Owner: Jeremy runs. Jibin keeps the host ready and reviews.</div>
<ul>
<li>On return: read Jeremy's block results (verdicts, void reasons, clock pairs) and the host's login record for the away week, then re-run the read-only state check and save it next to <code>state-1756.txt</code>.</li>
<li>Jeremy's one or two remaining blocks before 5 November, same rule. The checklist in section 7 stays valid for anyone who runs on the host.</li>
<li>Windows (D4): Mon–Fri 13:00–21:00 UTC. That is 06:00–14:00 PDT and 09:00–17:00 EDT until 31 October, and 05:00–13:00 PST and 08:00–16:00 EST from 2 November. The second weekly fstrim would fall on Mon 2 Nov 00:00–02:40 UTC; it stays disabled.</li>
<li>Thursday 5 November: the demo. Nothing on the host changes before it.</li>
</ul></div>
<div class="phase"><h3>P9. After Friday 6 November: restore the host</h3><div class="meta">Owner: Jibin, outside any run window.</div>
<ul>
<li>Re-enable the timers and netperf (or leave netperf off), expect an immediate apt catch-up run, and decide with Jeremy whether the governor and the isolation stay. They cost nothing while nobody needs cores 126–127, and the tools/perf gate would later need the nohz_full kernel of P4 as well.</li>
</ul>""")''')

# ---------------------------------------------------------------- section 7
rep('""" + PARTQ + """ 128 × performance verified. The counter pair around a run is still pending (needs Jeremy\'s run).</td></tr>',
    '""" + PARTQ + """ 128 × performance verified (again 17:56 UTC). The counter pair comes from Jeremy\'s own script on 126 and 127 around each block, first on Fri 23 Oct.</td></tr>')
rep('""" + PARTQ + """ Idle host: zero interrupts on 126-127 in 10 s. The run-time difference is pending.</td></tr>',
    '""" + PARTQ + """ Idle host: zero interrupts on 126-127 in 10 s (05:46 and 17:56 UTC). The run-time difference comes from Jeremy\'s phx-isol.py samples of his blocks.</td></tr>')
rep('""" + OPENQ + """ Pending: needs Jeremy\'s own run on the new setup.</td></tr>',
    '""" + OPENQ + """ Pending: Jeremy\'s Friday block. His sampler phx-isol.py records thread placement without reading per-CPU files of 120–127.</td></tr>')
rep('""" + OPENQ + """ Pending: Jeremy\'s first run next week.</td></tr>',
    '""" + OPENQ + """ Pending: the churn run in the Friday block, then the first run with the 12× faster write on Phoenix. Expectation from his data: void until that write lands (Figure 8).</td></tr>')
rep('""" + OPENQ + """ Text approved by Jibin (A11), not yet sent.</td></tr>',
    '""" + DONE + """ Sent 22 Oct; Jeremy replied the same day and accepted every default. Today\'s reply adds the contact and the answers to his questions.</td></tr>')
rep('<h3>Before each counted run (Monday onward, two minutes, no root)</h3>', '<h3>Before each counted run (from Friday 23 October onward, two minutes, no root; Jeremy\'s script covers most of it)</h3>')

# ---------------------------------------------------------------- section 8
rep('''</ul>
<li>As-built verification, 22 October 05:26–05:52 UTC: read-only checks ran from <code>positron-perf</code> after each of Jibin's changes. The post-reboot results are saved as <code>verification-2026-10-22/postreboot-0545.txt</code> and <code>ipi-attribution-0552.txt</code>.</li>
<h3>Insufficient data</h3>''',
'''<li>As-built verification, 22 October 05:26–05:52 UTC: read-only checks ran from <code>positron-perf</code> after each of Jibin's changes. The post-reboot results are saved as <code>verification-2026-10-22/postreboot-0545.txt</code> and <code>ipi-attribution-0552.txt</code>. A further read-only check at 17:56 UTC, after Jeremy's replies, is saved as <code>state-1756.txt</code> (zero interrupts on 126–127 in 10 s, Jeremy's build log ending in <code>BUILD-DONE rc=0</code>, no RUNNING file, no positron-perf process). Jeremy's two replies are quoted in section 4 and kept in <code>requests.txt</code> as messages 4 and 5.</li>
</ul>
<h3>Insufficient data</h3>''')
rep('<li>Whether the performance governor plus a pinned device thread brings the device\'s mean lateness under 2.5 µs. Measurement: govtest-1 and govtest-2, then a run with the SDK-side change (D5).</li>',
    '<li>Whether the 12× faster logits-row write brings the device\'s mean lateness under 2.5 µs on Phoenix (the governor alone cannot, Figure 8). Measurement: the first churn run with that write on Phoenix. Whether commit <code>fa7f715f</code>, built on the host on 22 October, carries it is not stated.</li>')
rep('<li>Clock stability over a full run under the performance governor. Measurement: the feedback-counter pair in P3 around a 3-minute run.</li>',
    '<li>Clock stability over a full run under the performance governor. Measurement: Jeremy\'s counter pairs on 126 and 127 around the Friday block.</li>')
rep('<li>That alpha\'s sessions were Jeremy\'s agents is Jibin\'s inference from timing, not a log entry (A10 closed the key question: both of Jeremy\'s keys logged in). Source that would settle it: Jeremy\'s reply to item 1 of the message.</li>\n<li>Whether the sampling unit tests were ever run on the host, and the timed compile\'s wall time. Source: Jeremy (Q9).</li>',
    '<li>What “the twins” are (Jeremy\'s term for churn runs without a device thread), and whether the Friday block\'s <code>timed_compile.py</code> steps are the test-3 timed compile. Source: Jeremy.</li>\n<li>Who the contact is while Jibin is away, and in which channel Jeremy\'s block announcements are visible to the other users. Source: Jibin, in the reply and the note (A12, A14).</li>')

# ---------------------------------------------------------------- footer and the table of contents
rep('<footer>Prepared for Jibin on 21 October 2026, revised 22 October 02:40, 05:05, 06:00 (as-built) and 06:20 UTC.',
    '<footer>Prepared for Jibin on 21 October 2026, revised 22 October 02:40, 05:05, 06:00 (as-built), 06:20 and about 18:30 UTC (Jeremy\'s replies, the revised plan, the table of contents).')
rep('No message has been sent to Jeremy by this document. The draft in section 4 is for Jibin to send.</footer>',
    'No message is sent by this document. The reply and the note in section 4 are for Jibin to send.</footer>')
rep('''doc = "<!doctype html>\\n<html lang=\\"en\\"><head><meta charset=\\"utf-8\\"><meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\"><title>Jeremy's phoenix-crb tasks: plan</title><style>" + CSS + "</style></head><body><main>" + "\\n".join(parts) + "</main></body></html>\\n"''',
'''import re
def add_toc(body):
    """Give every h3 an id, collect the h2 and h3 titles, and put the table of contents at the placeholder."""
    items, state = [], {"sec": None, "n3": 0}
    strip = lambda t: re.sub(r"<[^>]+>", "", t)
    def sub(m):
        if m.group(1):
            state["sec"], state["n3"] = m.group(1), 0
            return m.group(0)
        if m.group(2) is not None:
            items.append((2, state["sec"], strip(m.group(2))))
            return m.group(0)
        state["n3"] += 1
        hid = f'{state["sec"]}-{state["n3"]}'
        items.append((3, hid, strip(m.group(3))))
        return f'<h3 id="{hid}">{m.group(3)}</h3>'
    body = re.sub(r'<section id="([^"]+)"[^>]*>|<h2>(.*?)</h2>|<h3>(.*?)</h3>', sub, body, flags=re.S)
    out = ['<nav class="contents" aria-label="Table of contents"><h2>Contents</h2><ol>', '<li><a href="#short">Short version</a></li>']
    open2 = open3 = False
    for lvl, hid, title in items:
        if lvl == 2:
            if open3: out.append("</ol>"); open3 = False
            if open2: out.append("</li>")
            out.append(f'<li><a href="#{hid}">{title}</a>'); open2 = True
        else:
            if not open3: out.append("<ol>"); open3 = True
            out.append(f'<li><a href="#{hid}">{title}</a></li>')
    if open3: out.append("</ol>")
    if open2: out.append("</li>")
    out.append("</ol></nav>")
    assert body.count("<!--TOC-->") == 1
    return body.replace("<!--TOC-->", "".join(out))

body = add_toc("\\n".join(parts))
doc = "<!doctype html>\\n<html lang=\\"en\\"><head><meta charset=\\"utf-8\\"><meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\"><title>Jeremy's phoenix-crb tasks: plan</title><style>" + CSS + "</style></head><body><main>" + body + "</main></body></html>\\n"''')

open(p, "w", encoding="utf-8").write(s)
print("plan replacements:", n)
