# pr5022-watch: hourly watch of tron PR 5022 for review activity

Short version: a cloud scheduled task named "PR 5022 review watch" checks pull request 5022 of the repository
positron-ai/tron once an hour, at minute 17. When someone other than jhan-positron acts on the pull request, the
task sends a push notification through the Claude mobile app. `watch_pr.py` is a second, local check that prints an
exact difference against its last run; it is run by hand. Both were set up on 2026-11-20.

Words used here:
- Cloud scheduled task (older name: routine): a saved prompt that Anthropic's cloud runs on a schedule. Each run is
  a new Claude Code session on a fresh virtual machine with a clone of the repository.
- Run: one execution of the task. Its transcript stays in the task's history on the web page.
- REST and GraphQL: the two interfaces of GitHub. Cloud sessions can use REST (`gh api repos/...`) and cannot use
  GraphQL. GraphQL is the only interface that reports resolved review threads.
- Window: the hour that one run reports. It ends at the latest minute 17 before the run.
- Own activity: anything done by the GitHub user jhan-positron. It never causes an alert.

## The cloud task

| Item | Value |
|---|---|
| Page | https://claude.ai/code/routines/trig_01GVEL2kVKy4FwLGZXcG7At9 |
| Id | `trig_01GVEL2kVKy4FwLGZXcG7At9` |
| Schedule | cron `17 * * * *` (the hour does not matter, so UTC and local time agree) |
| Model | claude-sonnet-5-5 |
| Repository attached | positron-ai/tron (needed: the cloud's GitHub access covers attached repositories) |
| Connectors | none |
| Alert | the cloud session's own `PushNotification` tool |

What one run does:
1. It saves the script `cloud/check_pr.py` from its prompt and compares the SHA-256 hash with the one in the prompt.
2. It runs the script. The script reads reviews, inline comments, conversation comments, timeline events and the
   state of the pull request through REST, and lists what falls into the window.
3. `RESULT: ALERT`: one push notification, and a final message with one bullet per item. `RESULT: NOTHING TO
   REPORT`: no notification. `RESULT: FETCH FAILED`: one push notification that says the check failed.

Limits:
- It has no memory between runs. If a run does not happen (usage limit reached, GitHub connection lost), the
  activity of that hour is not reported later. `watch_pr.py` shows it.
- It cannot see resolved threads or reactions (GraphQL only).
- A merge conflict is reported once a day, in the run of 17:17 UTC, for as long as it lasts.
- An edit of the summary comment of cursor[bot] causes no alert. That bot rewrites the comment at every push.
- A run started by hand ("Run now") reports the same window as the last scheduled run.

## Files

| File | What it is |
|---|---|
| `watch_pr.py` | Local check. Takes a snapshot of the pull request (REST and GraphQL), compares it with `state.json`, prints one line per difference, and stores the new snapshot. `--peek` stores nothing. |
| `state.json`, `log.txt`, `changes/` | Snapshot, run log and full texts of new items of `watch_pr.py`. |
| `cloud/check_pr.py` | The script that the cloud task runs. No double quotes and no backslashes, so that it sits in a JSON string unchanged. An optional argument sets the window start, for tests. |
| `cloud/task-prompt.template.txt` | The prompt of the cloud task, with placeholders for the script and its hash. |
| `cloud/build_body.py` | Builds `task-prompt.txt` and `task-body.json` from the two files above. Sends nothing. |
| `cloud/task-prompt.txt`, `cloud/task-body.json` | The prompt and the request body as last built. |

## Changing or stopping the cloud task

- To change the script or the prompt: edit `cloud/check_pr.py` or the template, run
  `python3 cloud/build_body.py <new uuid>`, and send `task-body.json` as an update of the task (in Claude Code:
  the `/schedule` command, or the RemoteTrigger tool with action `update`). The hash in the prompt changes with
  the script, so a run with a wrong copy stops and reports a failure.
- The constant `MINUTE` in `cloud/check_pr.py` must equal the minute of the cron expression.
- To pause or delete the task: use the switch or the menu on its page. The task does not stop by itself when the
  pull request is merged.

## Facts learned on 2026-11-20

- The first version alerted through a Google Calendar event. The run could read the calendar, and the creation of
  an event failed with "The Google Calendar connector is missing a permission that this action needs".
- In the same run the cloud session used a `PushNotification` tool on its own, and the tool answered "Mobile push
  requested". The second version uses that tool.
- A cloud run needs about 30 seconds: 6 seconds to start and clone, the rest for the check.
