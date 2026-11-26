import re,html
L=open('now.html',encoding='utf-8').read().split('\n')
FX=[
('RE1',425,'In those runs each pair read 62.9 to 63.7 GB/s at the loops, not 78 GB/s.',
 'In the runs of these two counts the four cores together read 126.0 to 126.2 GB/s at the loops. That is 63.0 to 63.1 GB/s for one pair on average, not 78 GB/s.'),
('RE2',425,'So that count is from another load.',
 'These runs have two busy pairs. They are not runs of hypothesis 2. So that count does not give the share for two partner cores alone.'),
('RE3',429,'With that loop two partner cores write 75.6 GB/s at 8 MiB, and one core alone writes 44.8 GB/s at 8 MiB and at 1 GiB [results/20261030T193108Z/bandwidth.csv].',
 'With that loop two partner cores write 75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB, and one core alone writes 44.8 GB/s at 8 MiB and at 1 GiB [results/20261030T193108Z/bandwidth.csv].'),
('RE4opt',437,'Two partner cores together wrote 63.2 GB/s at 1 GiB (each core wrote its own buffer of 1 GiB). One core alone wrote 63.0 GB/s.',
 'With the asm loop two partner cores together wrote 63.2 GB/s at 1 GiB (each core wrote its own buffer of 1 GiB). One core alone wrote 63.0 GB/s with the same loop.'),
('RE5',132,'For the last two rows of the table this holds on average (est.).',
 'The rates of the loop in the last two rows of the table are estimates (est.).'),
('RE6',132,'<td>Dispatch: three groups of integer and branch pipelines (3 limits)</td>',
 '<td>Dispatch: operations for three groups of integer and branch pipelines (3 limits)</td>'),
('RE7',132,'<p>How the loop is counted:</p>','<p>The table uses these terms and counts:</p>'),
('RE8',131,'<p><b>Source code.</b> This loop is the C function <code>k_read</code>',
 '<p><b>Source code.</b> The read loop compiled from C is the function <code>k_read</code>'),
('RE8b-not-applied',132,'The section lists eight of them.','Section 4.1 of the guide lists eight of them.'),
('RE9',52,'(system level cache, the shared cache in the on-chip mesh interconnect, which Linux lists as L3)',
 '(system level cache, the shared cache that Linux lists as L3 and that sits in the on-chip mesh interconnect)'),
('RE9-checker',52,'a 128 MiB SLC (system level cache, the shared cache in the on-chip mesh interconnect, which Linux lists as L3) at about 30 ns',
 'a 128 MiB SLC (system level cache: the shared cache that Linux lists as L3, located in the on-chip mesh interconnect) at about 30 ns'),
('RE7-checker',132,'<p>How the loop is counted:</p><ul><li>The dispatch step handles at most 10 instructions per cycle. The guide counts instructions after decoding and calls them MOPs (macro-operations).</li>',
 'x'),
('RE14opt',49,'Earlier versions of this report said "mesh cache".</div>',
 'Earlier versions of this report said "mesh cache". Also changed on 2026-11-12: the passage on the read loop compiled from C now has its own heading and three code listings. Three statements in "Open items" were corrected: the runs of hypothesis 2, the share counted with four busy cores, and the write runs of the loop compiled from C.</div>'),
('X-49',49,'is now called SLC (system level cache, Arm\'s name).','is now called SLC (Arm\'s name).'),
('RE2-423opt',423,'The third item also holds one run with two busy pairs, at 0.88 of the allowed rate (est.). It is not one of the runs of hypothesis 2.','x'),
('RE11-anchor',131,'<li>So the three loops compiled from C were very probably the same.</li></ul>','x'),
]
for id_,n,old,new in FX:
    print(id_,n,'count in line:',L[n-1].count(old),'| count in file:',sum(x.count(old) for x in L))
M=list(L)
for id_,n,old,new in FX:
    if id_ in('RE8b-not-applied','RE9-checker','RE7-checker','RE2-423opt','RE11-anchor','X-49'): continue
    assert M[n-1].count(old)==1,(id_)
    assert '\n' not in new
    M[n-1]=M[n-1].replace(old,new)
assert len(M)==len(L)
open('fixed.html','w',encoding='utf-8').write('\n'.join(M))
def plain(s):
    s=re.sub(r'<pre>.*?</pre>',' [LISTING] ',s,flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>',' ',s))
for n in (49,52):
    print('----',n); print(plain(M[n-1]))
t=plain(M[424]); i=t.find('No run counted the share'); print('---- 425 tail'); print(t[i-120:])
t=plain(M[428]); i=t.find('The write runs'); print('---- 429'); print(t[i-60:i+420])
t=plain(M[131]); i=t.find('This report calls'); print('---- 132'); print(t[i:i+900]); j=t.find('So the loop stays'); print(t[j-200:j+420])
