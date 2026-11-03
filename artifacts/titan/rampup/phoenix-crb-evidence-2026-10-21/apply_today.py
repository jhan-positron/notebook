p = "build_plan.py"; s = open(p, encoding="utf-8").read(); n = 0
def rep(old, new):
    global s, n
    c = s.count(old); assert c == 1, (c, old[:80]); s = s.replace(old, new); n += 1
rep('''# ----------------------------------------------------------------------------------------------- content
parts = []''',
'''# ----------------------------------------------------------------------------------------------- today's actions (shown twice: top of page and P5)
TODAY = ("""<table><tr><th style="width:4%">#</th><th>Action</th><th style="width:9%">Owner</th><th style="width:10%">On the host?</th><th style="width:17%">Status</th></tr>
<tr><td>T1</td><td>Send Jeremy the reply (section 4, Jibin's version) with two corrections: say that <code>arm</code> has sudo and positron-perf does not, and do not share the positron-perf login. Add one line asking him to post each block's times in the phoenix-crb channel.</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T2</td><td>Post the note (section 4) in the phoenix-crb channel: the Friday block, the weekday windows, the RUNNING-file rule, the isolated cores, what not to change, the away dates.</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T3</td><td>Post the <code>arm</code> login details and the BMC access in the phoenix-crb channel (item 2 of the reply). Not the positron-perf login.</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T4</td><td>Send Jeremy the summary doc <code>phoenix-crb-for-jeremy-2026-10-22.html</code> (host record, rules, answers, the 21 October arithmetic, open items, checks he can run).</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr><td>T5</td><td>Make sure Jeremy's block notices reach the phoenix-crb channel while Jibin is away: add him to the channel, or rely on the line added in T1.</td><td>Jibin</td><td>no</td><td>""" + TODOQ + """</td></tr>
<tr class="sep"><td>T6</td><td>On the host: nothing. No root step, no reboot, no file to create. The state was re-verified read-only at 17:56 UTC (boot line, isolated list, 128 × performance, rcu_normal, timers off, no RUNNING file, zero interrupts on 126–127 in 10 s). Friday's block needs nothing from Jibin.</td><td>nobody</td><td>no</td><td>""" + DONE + """ verified 17:56 UTC</td></tr>
<tr><td>T7</td><td>Kernel rebuild and Arm's GitHub access (A6): no action. Deferred to after the demo (P4).</td><td>Jibin, later</td><td>no</td><td>""" + NA + """</td></tr>
<tr><td>T8</td><td>Record: Jeremy's two replies, the reply, the note, the generator sources and the host check are saved in the evidence folder, and this page and the summary doc are rebuilt.</td><td>agent</td><td>no</td><td>""" + DONE + """</td></tr>
</table>""")

# ----------------------------------------------------------------------------------------------- content
parts = []''')
rep('''and today's two items are the reply at the end of section 4 (Jibin's version, with two corrections suggested) and the note to the phoenix-crb channel, where the other <code>arm</code> users are.</p>
</section>
<div class="danger"><strong>Security finding,''',
'''and today's actions are in the table right below: five messages for Jibin to send, none of them on the host.</p>
</section>
<section id="today"><h2>Today, Thursday 22 October: what to do before Jibin logs out</h2>
<p>Nothing on the host. The five items for Jibin are messages. T1 to T4 have their texts ready in section 4 and in the evidence folder. The same table is phase P5 in section 6.</p>
""" + TODAY + """
</section>
<div class="danger"><strong>Security finding,''')
rep('''<div class="phase"><h3>P5. Thursday 22 October, before Jibin logs out: reply, note, record</h3><div class="meta">Owner: Jibin. Needs: nothing on the host. The host is in its final state for the demo, and nothing expires while Jibin is away.</div>
<ul>
<li>Send Jeremy the reply at the end of section 4 (Jibin's version; two corrections are suggested there). It acknowledges the Friday block, answers his five questions, and names the phoenix-crb channel as the contact for next week (A12).</li>
<li>Post the note at the end of section 4 in the phoenix-crb channel (A14): the Friday block, the weekday windows, the RUNNING-file rule, the isolated cores, what not to change while Jibin is away, and that the arm login details and the BMC access follow there.</li>
<li>Done 17:56 UTC, read-only as positron-perf: boot line, isolated list, 128 × performance, rcu_normal 1, timers off, netserver gone, no RUNNING file, zero interrupts on 126–127 in 10 s, Jeremy's build finished (<code>BUILD-DONE rc=0</code>), no positron-perf process [verification-2026-10-22/state-1756.txt].</li>
<li>Arm's GitHub access (A6): no action. It matters only for P4.</li>
</ul></div>''',
'''<div class="phase"><h3>P5. Thursday 22 October, before Jibin logs out: five messages, nothing on the host</h3><div class="meta">Owner: Jibin. Needs: nothing on the host. The host is in its final state for the demo, and nothing expires while Jibin is away. The host check of 17:56 UTC is saved as <code>verification-2026-10-22/state-1756.txt</code> (Jeremy's build finished with <code>BUILD-DONE rc=0</code>, no positron-perf process).</div>
""" + TODAY + """
</div>''')
open(p, "w", encoding="utf-8").write(s); print("replacements:", n)
