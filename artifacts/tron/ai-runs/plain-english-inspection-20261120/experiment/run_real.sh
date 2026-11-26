#!/bin/bash
# usage: run_real.sh PROMPT_FILE TASK ARM REP   -> out/TASK_ARM_REP.json
# One run in the normal mode of the command line: the installed CLAUDE.md and skills are loaded,
# so the current plain-english skill is in context and the new skill can be invoked by name.
# Only the Skill tool is on. No MCP servers. The herdr variables are unset so that the
# SessionStart hook does not report this run to herdr.
E=/home/jhan/workspace/ai-runs/plain-english-inspection-20261120/experiment
W=${REALMODE_DIR:-/tmp/plain-english-realmode}
prompt=$1; task=$2; arm=$3; rep=$4
out=$E/out/${task}_${arm}_${rep}.json
[ -s "$out" ] && exit 0
mkdir -p "$W" && cd "$W" || exit 1
raw=$W/${task}_${arm}_${rep}.jsonl
env -u HERDR_ENV -u HERDR_SOCKET_PATH -u HERDR_PANE_ID timeout 900 claude -p --model claude-fable-5-2 \
  --no-session-persistence --strict-mcp-config --tools "Skill" --allowedTools "Skill" \
  --output-format stream-json --verbose < "$prompt" > "$raw" 2> "${raw%.jsonl}.err"
python3 - "$raw" "$out" <<'PY'
import json, sys
raw, out = sys.argv[1:3]
res, skills = None, []
for line in open(raw, errors='replace'):
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get('type') == 'assistant':
        for b in (d.get('message') or {}).get('content') or []:
            if b.get('type') == 'tool_use' and b.get('name') == 'Skill':
                skills.append((b.get('input') or {}).get('skill'))
    if d.get('type') == 'user':
        c = (d.get('message') or {}).get('content')
        if isinstance(c, list):
            for b in c:
                if b.get('type') == 'text' and 'Base directory for this skill:' in b.get('text', '')[:60]:
                    skills.append('loaded:' + b['text'].split('\n')[0].rsplit('/', 1)[-1])
    if d.get('type') == 'result':
        res = d
if res:
    res['skills_seen'] = skills
    json.dump(res, open(out, 'w'))
    print(f"{out.rsplit('/',1)[-1]} cost={res.get('total_cost_usd')} skills={skills}")
else:
    print('NO RESULT', raw)
PY
