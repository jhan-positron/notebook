#!/usr/bin/env bash
# measure.sh WIDTH [HEIGHT] [extra-css] - dump geometry of a copy of the page (with measure.js appended) at a window width
V=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r3
P=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html
W=$1; H=${2:-1000}
python3 - "$P" "$V/work/measure-copy.html" "$V/measure.js" <<'PY'
import sys
t=open(sys.argv[1]).read(); js=open(sys.argv[3]).read()
assert t.count('</body>')==1
open(sys.argv[2],'w').write(t.replace('</body>','<script>'+js+'</script></body>'))
PY
$V/chrome.sh --window-size=$W,$H --dump-dom "file://$V/work/measure-copy.html" > $V/work/dom-$W.html
python3 - "$V/work/dom-$W.html" "$V/work/measure-$W.json" <<'PY'
import sys,re,html
t=open(sys.argv[1]).read()
m=re.search(r'<pre id="r3m">(.*?)</pre>',t,re.S)
open(sys.argv[2],'w').write(html.unescape(m.group(1)))
print('ok',len(m.group(1)))
PY
