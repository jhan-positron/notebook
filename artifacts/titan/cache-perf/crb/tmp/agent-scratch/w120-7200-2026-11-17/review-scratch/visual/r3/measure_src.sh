#!/usr/bin/env bash
# measure_src.sh SRC.html WIDTH NAME [chrome flags] - geometry of any copy of the page; result in work/measure-NAME.json
V=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r3
SRC=$1; W=$2; N=$3; shift 3
python3 - "$SRC" "$V/work/mcopy-$N.html" "$V/measure.js" <<'PY'
import sys
t=open(sys.argv[1]).read(); js=open(sys.argv[3]).read()
assert t.count('</body>')==1
open(sys.argv[2],'w').write(t.replace('</body>','<script>'+js+'</script></body>'))
PY
$V/chrome.sh --window-size=$W,1000 "$@" --dump-dom "file://$V/work/mcopy-$N.html" > $V/work/dom-$N.html
python3 - "$V/work/dom-$N.html" "$V/work/measure-$N.json" <<'PY'
import sys,re,html
t=open(sys.argv[1]).read()
i=t.rfind('<pre id="r3m">'); j=t.find('</pre>',i)
open(sys.argv[2],'w').write(html.unescape(t[i+14:j]))
PY
