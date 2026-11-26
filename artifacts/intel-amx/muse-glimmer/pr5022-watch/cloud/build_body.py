#!/usr/bin/env python3
"""Build the prompt and the request body of the cloud task from the template and check_pr.py.
Writes task-prompt.txt and task-body.json beside this file. Sends nothing.
The body fits both a create and an update of the task: it attaches no connector."""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(HERE, "check_pr.py")).read()
template = open(os.path.join(HERE, "task-prompt.template.txt")).read()

# The cloud agent types the script from the prompt, so keep it easy to copy and easy to verify.
assert script.isascii() and template.isascii(), "non-ASCII character"
assert script.endswith("\n") and not script.endswith("\n\n"), "script must end with exactly one newline"
assert all(line == line.rstrip() for line in script.splitlines()), "trailing whitespace in the script"
assert "\t" not in script, "tab in the script"
digest = hashlib.sha256(script.encode()).hexdigest()
prompt = template.replace("@@SHA256@@", digest).replace("@@SCRIPT@@\n", script).rstrip("\n") + "\n"
assert "@@" not in prompt, "unfilled placeholder"
assert '"' not in prompt and "\\" not in prompt, "double quote or backslash in the prompt"

body = {
    "name": "PR 5022 review watch",
    "cron_expression": "17 * * * *",
    "enabled": True,
    "clear_mcp_connections": True,
    "job_config": {"ccr": {
        "environment_id": "env_01C7AzpvcJZvdySwQw8VpJAa",
        "session_context": {
            "model": "claude-sonnet-5-5",
            "sources": [{"git_repository": {"url": "https://github.com/positron-ai/tron"}}],
            "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        },
        "events": [{"data": {
            "uuid": sys.argv[1], "session_id": "", "type": "user", "parent_tool_use_id": None,
            "message": {"content": prompt, "role": "user"},
        }}],
    }},
}
open(os.path.join(HERE, "task-prompt.txt"), "w").write(prompt)
json.dump(body, open(os.path.join(HERE, "task-body.json"), "w"), indent=1)
print("script sha256", digest)
print("prompt: %d characters, %d lines" % (len(prompt), prompt.count("\n")))
