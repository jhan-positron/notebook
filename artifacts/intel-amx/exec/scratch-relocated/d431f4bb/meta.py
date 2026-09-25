import json
R="/home/jhan/workspace/intel-AMX/exec/results"
for camp,tag in [('q4b-swattn-20260919','check-8u-p8192'),('q4b-swattn-20260919','canon-pass1'),('q4b-fpga-20260921','fpgacanon-cold-p8192'),('q4b-fpga-20260921','fpgabase-pass1'),('q4b-fpga-20260921','canon-pass1'),('q4b-fpga-20260921','fpgacanon-pass1')]:
    d=json.load(open(f"{R}/{camp}/{tag}/perf.json"))
    print("=====",camp,tag)
    for k in ('openai_host','client_host','ssh_user','installed_sha_env','stop','require_hwattn0','fuse_limits','deviations','talos_stub','perf_minutes'):
        print(' ',k,'=',json.dumps(d.get(k))[:300])
    print('  versions =',json.dumps(d.get('versions'))[:400])
    print('  configs =',json.dumps(d.get('configs'))[:600])
    cj=d.get('configs_json')
    print('  configs_json =',json.dumps(cj)[:900])
    print('  hwattn_checks =',json.dumps(d.get('hwattn_checks'))[:500])
    print('  binary_checks =',json.dumps(d.get('binary_checks'))[:300])
    print('  env =',json.dumps(d.get('env'))[:400])
    print('  client_path_timing =',json.dumps(d.get('client_path_timing'))[:300])
    print('  snapshots keys =',list(d.get('snapshots',{}).keys())[:10] if isinstance(d.get('snapshots'),dict) else str(d.get('snapshots'))[:200])
    raw=d.get('raw',[])
    for r in raw:
        keys=[k for k in r.keys() if k not in ('ttfts_ms','prompt_tokens','cached_tokens')]
        print('  raw cell',r.get('name'),{k:(r[k] if not isinstance(r[k],(list,dict)) or len(json.dumps(r[k]))<120 else str(r[k])[:120]) for k in keys})
        break
