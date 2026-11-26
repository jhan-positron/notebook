import json,sys
S="/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
a=json.load(open(sys.argv[1])); b=json.load(open(S+"/facts.json"))
h=b["meta"]["hardware_error_records"]
print(json.dumps({k:v for k,v in h.items() if k!="processes"},indent=1)[:5000])
for p in h["processes"]:
    print(p["dataset"],p["tag"],p["launch"],p["rc"],p["n_records"],[(r["journal_line"],r["utc"][11:19],r["offset_s"],r["kind"]) for r in p["records"]])
print("===== meta.fields.q2_rows"); print(json.dumps(b["meta"]["fields"]["q2_rows"],indent=1))
print("===== checks"); 
for c in b["meta"]["checks"][-2:]: print(json.dumps(c)[:1500])
print("===== insufficient_data new"); 
for x in b["verdicts"]["insufficient_data"][len(a["verdicts"]["insufficient_data"]):]: print("-",x)
print("===== q2_rows changed notes")
for i,(x,y) in enumerate(zip(a["verdicts"]["q2_rows"],b["verdicts"]["q2_rows"])):
    if x.get("note")!=y.get("note"): print(i,"OLD:",x.get("note"),"\n   NEW:",y.get("note"))
for i,y in enumerate(b["verdicts"]["q2_rows"]):
    print(i,y.get("row_7200"),"|",y.get("row_7200_label"),"||",y.get("scope_8000"),"|",y.get("scope_8000_label"),"|",y.get("wording"),y.get("decides"))
print("===== short_version")
for i,s in enumerate(b["verdicts"]["short_version"]["sentences"]): print(i,s)
for i,s in enumerate(b["verdicts"]["short_version"]["detail"]): print("d",i,s)
print("===== verdict keys", list(b["verdicts"].keys()))
print("q2_old_read == in q2:", b["verdicts"]["q2_old_read"] in b["verdicts"]["q2"], b["verdicts"]["q2_new_read"] in b["verdicts"]["q2"])
