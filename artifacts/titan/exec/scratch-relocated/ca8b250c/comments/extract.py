import json, sys, os, glob, datetime, re
roots = ["/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf",
         "/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-asimov",
         "/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb"]
def to_pst(ts):
    try:
        d = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
        return (d - datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M PST")
    except Exception:
        return ts
skip_re = re.compile(r"^(<command-name>|<local-command|<command-message|<system-reminder>|\[Request interrupted|This session is being continued|Caveat:|<cross-session|\[Cross-session|<task-notification|\[Cross-session)")
summary = []
for root in roots:
    for f in sorted(glob.glob(root + "/*.jsonl")):
        sid = os.path.basename(f)[:8]
        out = []
        first = last = None
        cwd = None
        with open(f, errors="replace") as fh:
            for line in fh:
                try: o = json.loads(line)
                except Exception: continue
                if o.get("type") == "attachment":
                    a = o.get("attachment", {})
                    if a.get("type") != "queued_command" or a.get("origin", {}).get("kind") != "human": continue
                    c = a.get("prompt", "")
                elif o.get("type") != "user": continue
                else:
                    if o.get("isMeta") or o.get("isCompactSummary"): continue
                    m = o.get("message", {})
                    c = m.get("content")
                texts = []
                if isinstance(c, str): texts = [c]
                elif isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "text": texts.append(b["text"])
                if not texts: continue
                t = "\n".join(texts).strip()
                if not t or skip_re.match(t): continue
                if "<local-command-stdout>" in t or "<command-name>" in t: continue
                ts = o.get("timestamp","")
                cwd = o.get("cwd", cwd)
                first = first or ts; last = ts
                out.append((to_pst(ts), t))
        out.sort(key=lambda x: x[0])
        seen=set(); out=[x for x in out if not (x[1] in seen or seen.add(x[1]))]
        if out:
            name = f"{os.path.basename(root).split('cache-perf')[-1] or '-root'}-{sid}.md"
            with open(name, "w") as w:
                w.write(f"# {f}\ncwd={cwd}\n{len(out)} user messages, {to_pst(first)} .. {to_pst(last)}\n\n")
                for ts, t in out:
                    w.write(f"## [{ts}]\n{t}\n\n")
            summary.append((name, len(out), to_pst(first), to_pst(last), cwd))
for s in summary: print(s)
