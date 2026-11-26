import re,sys
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
src=open(S+"/make_report.py").read()
src=src.replace('''print("self-check list of make_report.py")''','''
import re as _re
tot=0
for t in PROSE:
    n=len([w for w in _re.findall(r"\\S+", strip_tags(t)) if _re.search(r"[A-Za-z0-9]", w)]); tot+=n
    print(f"{n:4d} {strip_tags(t)[:150]}")
print("TOTAL",tot)
sys.exit(0)
print("self-check list of make_report.py")''')
exec(compile(src,"gen","exec"))
