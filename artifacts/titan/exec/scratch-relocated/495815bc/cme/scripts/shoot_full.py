"""shoot_full.py [SLICE_PX] [FIRST [LAST]]: screenshots of asimov-cme-perf.html in slices of SLICE_PX (default 1800)
into ../shots/full-NN.png.  Prints the page height.  Needs the Bash sandbox off."""
import os, re, subprocess, sys
SRC = '/home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf.html'
SHOTS = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/shots/'
CHROME = '/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell'
BASE = [CHROME, '--no-sandbox', '--in-process-gpu', '--headless']
slice_px = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
page = open(SRC, encoding='utf-8').read()
tmp = SHOTS + '_full_slice.html'

def run(args, timeout=40):
    for attempt in range(4):
        try:
            return subprocess.run(BASE + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout).stdout
        except subprocess.TimeoutExpired:
            print('timeout, attempt', attempt)
    return b''

# page height and tables wider than the column
probe = page.replace('</body>', '<script>var w=[];document.querySelectorAll(".tablewrap").forEach(function(e){'
                     'if(e.scrollWidth>e.clientWidth+1)w.push(e.id+":"+e.scrollWidth+">"+e.clientWidth);});'
                     'var f=[];document.querySelectorAll("figure svg").forEach(function(e){var r=e.getBoundingClientRect();'
                     'if(r.width>e.parentNode.clientWidth+1)f.push(e.parentNode.id+":"+Math.round(r.width));});'
                     'document.title="H="+document.documentElement.scrollHeight+" WIDE="+w.join(",")+" FIG="+f.join(",")+" BODYW="+document.body.scrollWidth;</script></body>')
open(tmp, 'w', encoding='utf-8').write(probe)
dom = run(['--window-size=1100,2000', '--dump-dom', 'file://' + tmp]).decode('utf-8', 'replace')
m = re.search(r'<title>(H=(\d+)[^<]*)</title>', dom)
print(m.group(1) if m else 'no height')
height = int(m.group(2))
n = (height + slice_px - 1) // slice_px
first = int(sys.argv[2]) if len(sys.argv) > 2 else 0
last = int(sys.argv[3]) if len(sys.argv) > 3 else n - 1
for i in range(first, min(last, n - 1) + 1):
    open(tmp, 'w', encoding='utf-8').write(page.replace('</style>', 'body{margin-top:-%dpx}</style>' % (i * slice_px), 1))
    png = SHOTS + 'full-%02d.png' % i
    run(['--window-size=1100,%d' % slice_px, '--screenshot=' + png, 'file://' + tmp])
os.remove(tmp)
print('slices', n, 'of', slice_px, 'px; wrote', first, 'to', min(last, n - 1))
