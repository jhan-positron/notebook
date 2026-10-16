#!/usr/bin/env python3
"""Resume the existing review conversation when Claude publishes PR-2."""

import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parent
THREAD = "01a1289f-ed7c-77c2-aa61-f6495ec313b2"
STATE = ROOT / "state.json"


def record(status, **details):
    entry = {
        "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        **details,
    }
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(entry, indent=2) + "\n")
    temporary.replace(STATE)
    print(json.dumps(entry), flush=True)


def run(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=60)


def main():
    with (ROOT / "watch.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if STATE.exists() and json.loads(STATE.read_text())["status"] == "queued":
            return
        while True:
            try:
                result = run([
                    "gh", "pr", "list", "--repo", "positron-ai/tron",
                    "--head", "jhan-vnnik-2-amx", "--state", "all",
                    "--json", "number,url,title,state,isDraft,headRefOid,baseRefName",
                ])
                if result.returncode:
                    record("github_check_failed", error=result.stderr.strip())
                else:
                    prs = json.loads(result.stdout)
                    if not prs:
                        record("waiting", branch="jhan-vnnik-2-amx")
                    else:
                        pr = prs[0]
                        message = (
                            "Automatic continuation of the user's authorized PR-2 review. "
                            f"The monitor found {pr['url']} on jhan-vnnik-2-amx. "
                            f"Observed head: {pr['headRefOid']}; state: {pr['state']}. "
                            "Re-fetch the live PR and confirm the completed handoff in "
                            "PR2-handoff.md and split-status.md before reviewing. "
                            "Run three separate review passes using tron-code-review, "
                            "ben-review, and wade-code-review. Do not spawn other agents. "
                            "Use plain-english to check the PR description and write comments. "
                            "The user explicitly authorized posting review comments. "
                            "Review the actual base and final head, full changed files, callers, "
                            "tests, CI, commits, and complete paginated discussion. "
                            "Distinguish inspected code from tests actually run. "
                            "Respect the recorded CI exception and known deferred items. "
                            "Do not change Claude's source tree or launch competing DUT work. "
                            "Re-check the head and existing comments immediately before posting. "
                            "Post only verified, non-duplicate findings, with skill attribution; "
                            "record separate results even when a pass finds no issues. "
                            "Re-fetch the live description before any authorized description edit. "
                            "Report the reviewed commit, review/comment links, and limitations. "
                            "Do not merge or promote the draft. "
                            "This monitor only resumes this same conversation; it has not "
                            "reviewed code or posted to GitHub. Watcher files: "
                            f"{ROOT}."
                        )
                        queued = run([
                            "/home/jhan/.local/bin/codex", "queue",
                            "--thread", THREAD, "--message", message,
                        ])
                        if queued.returncode == 0:
                            record("queued", pr=pr, receipt=queued.stdout.strip())
                            return
                        record("queue_failed", pr=pr, error=queued.stderr.strip())
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                record("check_failed", error=str(error))
            time.sleep(300)


if __name__ == "__main__":
    main()
