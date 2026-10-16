from pathlib import Path
import subprocess, concurrent.futures, json
root=Path('/tmp/pr3-handoff-review.t0c2og3n')
out=root/'catch-filter'; out.mkdir(exist_ok=True)
deps=Path('/home/jhan/workspace/ai-runs/lcheck/mirror/var/tmp/jhan/tron-issue4525/gen/_deps')
src=deps/'catch2-src/src'
gen=deps/'catch2-build/generated-includes'
fixture=out/'fixture.cpp'
fixture.write_text('''#include <catch2/catch_test_macros.hpp>
TEST_CASE("VNNI K block save equals the per-token row store, bit for bit") { SUCCEED(); }
TEST_CASE("save_k stores every token's K row once, grouped by page block, alone or with helper threads") { SUCCEED(); }
''')
sources=list(src.rglob('*.cpp'))+[fixture]
def compile_one(p):
 obj=out/(p.stem+'.o')
 r=subprocess.run(['g++','-std=c++17','-O0','-pthread','-I'+str(src),'-I'+str(gen),'-c',str(p),'-o',str(obj)],capture_output=True,text=True)
 return str(p),r.returncode,r.stdout+r.stderr,str(obj)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 results=list(pool.map(compile_one,sources))
(out/'build-results.json').write_text(json.dumps(results,indent=2))
errors=[r for r in results if r[1]]
if errors:
 print(errors[:3]); raise SystemExit(1)
binary=out/'fixture'
r=subprocess.run(['g++','-pthread',*[r[3] for r in results],'-o',str(binary)],capture_output=True,text=True)
if r.returncode: print(r.stderr); raise SystemExit(r.returncode)
names=['VNNI K block save equals the per-token row store, bit for bit',"save_k stores every token's K row once, grouped by page block, alone or with helper threads"]
tests=[]
for name in names:
 for escaped in [False,True]:
  filt=name.replace(',',r'\,') if escaped else name
  r=subprocess.run([str(binary),filt],capture_output=True,text=True)
  tests.append({'filter':filt,'escaped':escaped,'rc':r.returncode,'output':r.stdout+r.stderr})
(out/'results.json').write_text(json.dumps(tests,indent=2))
print(json.dumps(tests,indent=2))
