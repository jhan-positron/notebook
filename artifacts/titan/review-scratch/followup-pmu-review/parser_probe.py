import ast,re
from pathlib import Path
src=ast.parse(Path('/home/jhan/workspace/titan/cache-perf/asimov/gen_run3.py').read_text())
fn=next(node for node in src.body if isinstance(node,ast.FunctionDef) and node.name=='lat_rows')
ns={'re':re};exec(compile(ast.Module(body=[fn],type_ignores=[]),'gen_run3.py','exec'),ns)
base_header='mem,size_bytes,mode,rep,loads,ns_per_load,cycles_per_load,l1d_refill_per_load,l2d_refill_per_load,l3d_refill_rd_per_load'
base_row='dram,4096,repeat,0,100,2.000,4.00,1.0000,2.0000,3.0000'
cases={
 'legacy_no_cov':(base_header,base_row),
 'legacy_with_cov':(base_header+',perf_cov',base_row+',1.0000'),
 'new_valid':(base_header+',l1d_refill_hwprf_per_load,l2d_refill_hwprf_per_load,perf_cov',base_row+',0.1000,0.2000,1.0000'),
 'new_second_optional_missing':(base_header+',l1d_refill_hwprf_per_load,l2d_refill_hwprf_per_load,perf_cov',base_row+',0.1000,-,1.0000'),
 'new_all_invalid':(base_header+',l1d_refill_hwprf_per_load,l2d_refill_hwprf_per_load,perf_cov','dram,4096,repeat,0,100,2.000,-,-,-,-,-,-,-'),
 'new_truncated':(base_header+',l1d_refill_hwprf_per_load,l2d_refill_hwprf_per_load,perf_cov',base_row+',1.0000'),
}
for name,(header,row) in cases.items():
 p=Path('/tmp/followup-pmu-review')/(name+'.csv');p.write_text('# latency: cme=0\n'+header+'\n'+row+'\n')
 try:
  d=ns['lat_rows'](p)[0]
  print(name,'ACCEPTED',d)
 except Exception as e:print(name,'ERROR',type(e).__name__,str(e))
