# ---- 4.1.1 why kv_mul 3/5/8 are not served + forced-gate failure diagram ----
def gate_fail_411():
    HB, HH = 34, 22
    X0 = 168
    rows = [
        ("kv_mul 4", "qwen-3-4b / llama-3.1-8b / mixtral", 4,
         "served: the window IS the group"),
        ("kv_mul 3", "llama-3.2-3b", 3,
         "window overshoots into the NEXT group&#x27;s head"),
        ("kv_mul 5", "qwen-2.5-32b", 5,
         "5th head left out: never computed, never updated"),
        ("kv_mul 8", "llama-3.3-70b", 8, "half the group left out"),
    ]
    parts = []
    y = 46
    for name, models, km, verdict in rows:
        parts.append(f'<text x="8" y="{y+15}" font-size="11.5" font-weight="600" fill="#0b0b0b">{name}</text>')
        parts.append(f'<text x="8" y="{y+29}" font-size="9.5" fill="#898781">{models}</text>')
        for i in range(2 * km):
            x = X0 + i * (HB + 2)
            grp = i // km
            in_window = i < 4
            if in_window and grp == 0:
                fill, stroke = "#e4f2ed", "#1b9e77"   # correctly this group
            elif in_window and grp > 0:
                fill, stroke = "#fbe3d5", "#d95f02"   # wrong-group read
            elif grp == 0:
                fill, stroke = "#eeedea", "#898781"   # this group, skipped
            else:
                fill, stroke = "#ffffff", "#d8d6d0"
            parts.append(f'<rect x="{x}" y="{y}" width="{HB}" height="{HH}" fill="{fill}" stroke="{stroke}"/>')
            parts.append(f'<text x="{x+HB/2:.0f}" y="{y+15}" font-size="10" fill="#52514e" text-anchor="middle">q{i}</text>')
        xdiv = X0 + km * (HB + 2) - 1
        parts.append(f'<line x1="{xdiv}" y1="{y-6}" x2="{xdiv}" y2="{y+HH+6}" stroke="#0b0b0b" stroke-width="1.6"/>')
        parts.append(f'<text x="{X0}" y="{y-8}" font-size="9.5" fill="#898781">K/V head 0&#x27;s group</text>')
        parts.append(f'<text x="{xdiv+6}" y="{y-8}" font-size="9.5" fill="#898781">K/V head 1&#x27;s group</text>')
        parts.append(f'<rect x="{X0-3}" y="{y-3}" width="{4*(HB+2)+2}" height="{HH+6}" fill="none" stroke="#7570b3" stroke-width="2.4"/>')
        parts.append(f'<text x="{X0 + 16*(HB+2) + 14}" y="{y+15}" font-size="10.5" fill="#0b0b0b">{verdict}</text>')
        y += 62
    parts.append(f'<text x="{X0-3}" y="{y-14}" font-size="10.5" fill="#7570b3" font-weight="600">violet frame = the 128x4 kernels&#x27; fixed 4-head window (pack, tiles, epilogue)</text>')
    y += 16
    parts.append(f'<text x="8" y="{y+14}" font-size="11.5" font-weight="600" fill="#0b0b0b">and the epilogue&#x27;s stride:</text>')
    parts.append(f'<text x="8" y="{y+28}" font-size="9.5" fill="#898781">sp[kv_head * 4 + offset]</text>')
    SB = 17
    for i in range(24):
        x = X0 + i * (SB + 1)
        parts.append(f'<rect x="{x}" y="{y}" width="{SB}" height="18" fill="#ffffff" stroke="#d8d6d0"/>')
    for i in range(24, 32):
        x = X0 + i * (SB + 1)
        parts.append(f'<rect x="{x}" y="{y}" width="{SB}" height="18" fill="none" stroke="#d95f02" stroke-dasharray="3,2"/>')
    parts.append(f'<rect x="{X0+28*(SB+1)}" y="{y}" width="{4*(SB+1)-1}" height="18" fill="#fbe3d5" stroke="#d95f02"/>')
    parts.append(f'<text x="{X0}" y="{y+32}" font-size="9.5" fill="#898781">llama-3.2-3b has 24 query heads = 24 scratchpad entries</text>')
    parts.append(f'<text x="{X0+22*(SB+1)}" y="{y+32}" font-size="10" fill="#d95f02">K/V head 7 &#x2192; slots 28&#x2013;31: past the end (out-of-bounds write)</text>')
    h = y + 46
    svg = ('<figure><svg viewBox="0 0 980 ' + str(h) + '" width="980" height="' + str(h) + '" role="img" '
           'aria-label="What the fixed 4-head kernel window would read for kv_mul 4, 3, 5 and 8, and where the epilogue stride would write" '
           'font-family="system-ui,sans-serif">'
           '<text x="8" y="20" font-size="12.5" font-weight="600" fill="#0b0b0b">If the gate were forced open: what the fixed 4-head window would touch</text>'
           + "".join(parts) + '</svg>'
           '<figcaption>Two K/V groups shown per geometry. Green = heads the kernel would compute'
           ' correctly; orange = a NEIGHBORING group&#x27;s head read as if it were ours; grey ='
           ' heads of this group the kernel would silently skip. Bottom strip: the epilogue&#x27;s'
           ' hard-coded &#xD7;4 stride against llama-3.2-3b&#x27;s 24-entry scratchpad.</figcaption></figure>')

    text_a = """
<h3 id="gate-fail" style="font-size:14px;">4.1.1 Why the kv_mul 3 / 5 / 8 models are not served
&#x2014; and what would break if the gate were simply forced open</h3>
<p>From the nightly-CI list, llama-3.2-3b (3 query heads per K/V head), qwen-2.5-32b (5) and
llama-3.3-70b (8) all have 128-wide heads but fail the <code>kv_mul() == 4</code> half of the
gate. <b>As shipped, nothing fails on them</b>: the gate is compile-time
(<code>if constexpr</code>), so for these models the AMX branch is not even compiled into their
plugin instantiation &#x2014; they run the unchanged AVX path (that is the measured
&quot;ineligible shape&quot; class: gpt-oss showed &#x2212;0.3..&#x2212;1.6%, run-to-run noise).</p>
<p>The interesting question is what the gate is protecting against. The <code>*_128x4</code>
kernels hard-code the number 4 in three load-bearing places: the Q pack reads exactly 4
consecutive query heads starting at <code>kv_head &#xD7; kv_mul &#xD7; 128</code>; the tile
kernels compute exactly those 4 rows; and the epilogue writes exactly scratchpad entries
<code>sp[kv_head &#xD7; 4 + offset]</code>, then returns early so the AVX loop never revisits the
page. Run that machinery on a group that is not 4 heads wide and, per geometry:</p>
"""
    text_b = """
<ul>
<li><b>kv_mul 3 (llama-3.2-3b):</b> the 4-head window reads one head PAST the group &#x2014; the
next K/V head&#x27;s first query is scored against the wrong K/V data (silently wrong attention),
and for the last K/V head the pack reads past the end of the query tensor while the &#xD7;4
epilogue stride writes scratchpad slots 28&#x2013;31 of a 24-entry array: out-of-bounds read AND
write, i.e. memory corruption, not just wrong numbers.</li>
<li><b>kv_mul 5 (qwen-2.5-32b):</b> the window covers 4 of the 5 heads; the 5th head is never
computed &#x2014; and because the AMX branch returns early, the AVX loop never fills it either, so
1 in 5 heads remains uncomputed and its scratchpad entry is not updated. From the second group on,
the &#xD7;4 stride (correct would be
&#xD7;5) lands every update on the WRONG head&#x27;s scratchpad entry: in-bounds, silent, wrong.</li>
<li><b>kv_mul 8 (llama-3.3-70b):</b> half of every group is skipped, and the &#xD7;4-vs-&#xD7;8
stride mis-addresses every group after the first. (This shape could use TWO full query tiles
rather than one, but it requires a width-8 kernel variant and a generalized stride &#x2014; not
a gate bypass.)</li>
</ul>
<p>That is the design point: the gate makes the unsupported case <i>impossible by construction</i>
rather than checked at runtime, and the failure modes above are why widening support means new
per-width kernels plus a <code>kv_mul</code>-derived stride (the planned actual-width bucketing),
never just deleting the check.</p>
"""
    return text_a + svg + text_b
