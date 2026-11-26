---
name: cloud-scheduled-task-facts
description: "What a Claude Code cloud scheduled task (routine) can and cannot do, measured on 2026-11-20: REST-only GitHub, a PushNotification tool, no state between runs, connector limits, large API responses; probe with a test run before designing around the documentation"
metadata:
  node_type: memory
  type: reference
  originSessionId: a5b17f22-2551-4a33-9291-7580059b7d40
  modified: 2026-11-21T05:21:40.563Z
---

Measured on 2026-11-20 while building [[pr5022-cloud-watch]]. Sources: the run log of the task, and https://code.claude.com/docs/en/routines and https://code.claude.com/docs/en/cloud-environments.

What a cloud run has:
- `gh` is installed. `gh api repos/<owner>/<repo>/...` (REST) works without a token for a repository attached to the task. jhan's account reaches the private repository positron-ai/tron.
- GitHub GraphQL is blocked (documented): no `gh pr`, no resolved-thread state, no `reviewDecision`. Use REST lists and timestamps.
- A `PushNotification` tool. The run used it without being told, and the tool answered "Mobile push requested". The documentation pages do not mention it for cloud runs.
- No state between runs: each run is a fresh virtual machine. A stateless design: let each run report the window that ends at the latest scheduled minute, so windows touch and do not overlap.
- A run of a small check takes about 30 seconds; the clone of tron (0.9 GB on GitHub) took 4 seconds.
- A scheduled run starts after its scheduled minute, not before it: 48 seconds and 72 seconds late in the 2 runs measured (cron minute 17, session start 04:17:48Z and 05:18:12Z on 2026-11-21).
- The cloud agent wrapped its push text in `<routine_summary>` tags and passed `status: proactive`. How the phone shows that text is not known to me.
- Limits (documented): schedules no tighter than hourly; 100 scheduled runs per hour per account; GitHub event triggers exist for pull request, release and issue events, not for reviews or comments.

Connectors:
- A connector acts as jhan. A Slack or Gmail message from jhan to jhan is unlikely to raise an alert (web sources, not tested).
- The Google Calendar connector on jhan's account lists events and cannot create them ("missing a permission").
- A create without `mcp_connections` attaches every connector of the account. Pass the needed ones, or `clear_mcp_connections: true`.

Working with the RemoteTrigger tool:
- Every create, update and run response repeats the prompt four times (about 40 KB for a 9 KB prompt). Keep these calls few. `list_runs` and `get_run_log` are small.
- The prompt is typed again by the cloud agent when it saves an embedded script. Put a SHA-256 hash of the script in the prompt and let the run verify its copy. A script without double quotes and backslashes sits in the JSON string unchanged.
- A scheduled run can serve as the test of an update: read its log afterwards.

**How to apply:** before asking jhan to choose between workarounds for a cloud limit, start one cheap test run and read its log (tools found, errors). On 2026-11-20 I told jhan from the documentation that a cloud run has no built-in alert, jhan chose a calendar workaround, and the first run showed both that the workaround lacked permission and that a push tool existed.
