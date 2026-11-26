import re
b=open('body.txt').read(); s=open('svg.txt').read(); t=open('titles.txt').read()
allt=re.sub(r'\s+',' ',b+'\n'+s+'\n'+t)
Q=[
'Against the earlier 8000 MT/s runs, the old read kernel gives "no difference seen" in two of the three tests of the rerun (parts A and C) and "differs between the 8000 MT/s boot and the 7200 MT/s boot" in the third (part L): there its lowest-to-highest range lay 1.24 GB/s (0.3 %) below the 8000 MT/s range, its median was 6.27 GB/s (1.3 %) lower, and the data do not show the cause.',
'Sentence 3: each memory speed has only 1 boot (one run of the machine between two restarts), and F72d12 (earlier run of the same boot, not part of the rerun) gave 301.90 to 302.78 GB/s for the load-only loop with the test line of part L.',
'In this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".',
'By its name it prints kernel messages to the serial console ttyAMA.',
'the kernel thread pr/ttyAMA-1 at 51.6 %CPU',
'It also holds the kernel line "This system has 12 DIMM sockets"',
'kernel line with the module count',
'The 3 sessions ran within 10 min 9 s of the 7200 MT/s boot.',
'All 4 fall into A-2: 2 at 20:50:58 UTC, the second in which the bw_new read process of round 1 was launched, and 2 at 20:51:10 UTC, 2 s after the launch of a bw_new write process that this page does not use',
'It is less exact than parts L and C: its rates change in jumps of whole buffer passes',
'The orange dot (load-only loop) is left of the blue dot (old read kernel) in every row: its rate is lower.',
'In these rows the blue dot is at nearly the same place: its intervals span 7.59 GB/s (461.61 to 469.20 GB/s). The orange dot is not: its intervals span 26.03 GB/s (301.90 to 327.93 GB/s).',
'The bold text under a row name says where the row lies against the band.',
'process a6456', 'process p1nop', 'process p2add','process thp','process st1','(tag onebuf-ms500-1)',
'row L-2 (8000 MT/s), process p1nop',
'The command sudo dmidecode -t 17 would resolve it (needs root).',
'The one-thread phase of the test of 2026-11-13 was not repeated.',
'The records hold a bwx12 rate rounded to 0.001 GB/s. So the script sums the 120 thread rows that the record names.',
'The data of both figures come from the facts file',
'Rate, total',
'886 of the 1490 entries show no readable value in both lists (883 show ValueUnavailable, 3 show VStoreError). "On record" means the 4 files named set.txt in the results folder. Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. No full list was saved in that boot. A settings list saved in that boot would resolve it (needs root).',
'Dumbbell chart: whole-chip read rate of the old read kernel and of the load-only loop, one row per process, 21 rows',
'This interval ran from about 18:54:51 to 18:54:55 UTC on the same day',
'The lowest asmread value of the 8000 MT/s pool comes from an interval with such records',
'The same test line ran in 6 rows of the 7200 MT/s boot',
'Rows L-1 to L-4: the journal of the 8000 MT/s boot holds such records during two of the four rows: 2 during L-1, and 5 and 4 during the two processes of L-2. It holds 0 during L-3 and L-4',
]
for q in Q:
    print('OK ' if q in allt else 'MISSING', q[:100])
# word counts of Table 5 cells
import html
src=open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',encoding='utf-8').read()
m=re.search(r'<table class="state">.*?</table>',src,flags=re.S)
rows=re.findall(r'<tr>(.*?)</tr>',m.group(0),flags=re.S)
for r in rows:
    cells=re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',r,flags=re.S)
    txt=[html.unescape(re.sub(r'<[^>]+>','',c)) for c in cells]
    if len(txt)==3:
        def sc(x): return len(re.findall(r'[.!?](?:\s|$)', re.sub(r'\[Ref\d+\]','',x)))
        print(f'{txt[0][:55]:55s} proof {len(txt[1].split()):4d} words / {sc(txt[1])} sent ; limit {len(txt[2].split()):3d} words / {sc(txt[2])} sent ; <br>/<ul> in proof: {"<br" in cells[1] or "<ul" in cells[1]}')
