---
name: pr5022-cloud-watch
description: "Cloud scheduled task that watched tron PR 5022 hourly (set up 2026-11-20); the PR merged 2026-11-25, jhan was told to turn the task off, not confirmed yet; its id, page and local files"
metadata:
  node_type: memory
  type: project
  originSessionId: a5b17f22-2551-4a33-9291-7580059b7d40
  modified: 2026-11-21T04:07:28.674Z
---

On 2026-11-20 jhan asked for an hourly watch of tron PR 5022 with a notification on new review activity. Offered a session loop or a cloud schedule, jhan chose the cloud schedule, declined an extra session loop ("No, cloud only"), and chose the model Sonnet 5.5.

The task: "PR 5022 review watch", id `trig_01GVEL2kVKy4FwLGZXcG7At9`, page https://claude.ai/code/routines/trig_01GVEL2kVKy4FwLGZXcG7At9, cron `17 * * * *`, repository positron-ai/tron attached, no connectors. Each run saves a REST-only script from its prompt, checks the script's SHA-256 hash, runs it, and sends one push notification (the cloud session's own `PushNotification` tool) when someone other than jhan-positron acted in the last schedule window.

Local files: `/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-watch/` (README.md there). `watch_pr.py` is a local snapshot-and-diff check with exact results (it also sees resolved threads and reactions); `cloud/` holds the cloud script, the prompt template and the builder of the request body.

**Why:** jhan wanted the watch to survive a closed session.

**How to apply:**
- To answer "did anything happen on PR 5022", run `python3 -B pr5022-watch/watch_pr.py` (it stores a new snapshot) or with `--peek`.
- To change the cloud task: edit `cloud/check_pr.py` or the template, run `cloud/build_body.py <uuid>`, send `task-body.json` with RemoteTrigger `update`. The routine API cannot delete a task; jhan deletes or pauses it on its page.
- The task does not stop by itself. PR 5022 merged on 2026-11-25 at 18:33 UTC (commit 67a380d9c0 on main). I told jhan that day to turn the task off on its page. Not confirmed yet that it is off. When jhan confirms, or the page shows it paused or deleted, delete this memory and its line in MEMORY.md. Until then, remind jhan once when PR 5022 or the watch comes up.
- jhan first chose a Google Calendar popup as the alert. It failed: the Calendar connector on jhan's account can read and cannot create events. Do not rebuild the calendar path unless jhan reconnects that connector and asks.
- Not verified by me: that the push reaches jhan's phone. The tool answered "Mobile push requested". Ask jhan if it matters.

Related: [[cloud-scheduled-task-facts]], [[isaac-reviews-are-agent-pipeline]], [[tron-pr-push-triggers-bot-review]].
