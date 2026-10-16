#!/usr/bin/env python3
"""Resume this conversation once Claude opens the PR-3 pull request."""

import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parent
THREAD = "01a12d80-b713-7f72-b834-23872a415bfb"
STATE = ROOT / "state.json"
BRANCH = "jhan-vnnik-3-shared-save"


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
                    "--head", BRANCH, "--state", "open",
                    "--json", "number,url,title,state,isDraft,headRefOid,baseRefName",
                ])
                if result.returncode:
                    record("github_check_failed", error=result.stderr.strip())
                else:
                    prs = json.loads(result.stdout)
                    if not prs:
                        record("waiting", branch=BRANCH, thread=THREAD)
                    elif len(prs) != 1:
                        record("ambiguous_prs", prs=prs)
                    else:
                        pr = prs[0]
                        message = (
                            "Automatic continuation of the user's authorized PR-3 review. "
                            f"The monitor found {pr['url']} on {BRANCH}. "
                            f"Observed head: {pr['headRefOid']}. "
                            "The user asked: after Claude opens the new PR by executing "
                            "PR3-handoff.md, perform PR review and add comments to the PR. "
                            "Now complete that review and post the comments. "
                            "Re-fetch the live PR, PR3-handoff.md, and split-status.md. "
                            "The user's additional instruction is mandatory: perform "
                            "the normal review FIRST. Then apply tron-code-review, "
                            "wade-code-review, and ben-review INDIVIDUALLY, as separate "
                            "review passes in that order. Finally use plain-english "
                            "to review the PR description. Record each pass's results "
                            "separately, including when it finds no issues. Also apply "
                            "positron-code-review and cpp-coding-guide where relevant. "
                            "Read the complete applicable skills before reviewing. "
                            "Do not spawn other agents. Review the actual base and head, "
                            "full changed files, immediate callers, generated helper code, "
                            "tests, CI configuration, commits, body, and complete paginated "
                            "discussion. Trace shared-save ownership, memory ordering, "
                            "worker/window counts, publication, and completion. "
                            "Check the disabled option, row-major path, enabled option, "
                            "AMX-disabled path, partial blocks, mixed batches, and tp4. "
                            "Verify claims against available test and measurement records. "
                            "Respect the handoff's recorded CI exception and deferred PR-4 "
                            "scope. Distinguish code inspection from tests actually run. "
                            "Do not modify Claude's working tree or launch competing DUT "
                            "work. Use an isolated snapshot if local review checks need it. "
                            "Re-check the PR head and existing comments immediately before "
                            "posting. Review new changes if the head moved. Post only "
                            "verified, non-duplicate findings, or a scoped review summary "
                            "if no actionable findings remain. The user already explicitly "
                            "authorized posting review comments. Name and link the review "
                            "skills used. Do not edit the PR description, merge, promote, "
                            "or change labels. Report the reviewed commit, posted review "
                            "links, and limitations. Record completion in the watcher "
                            "state without losing the queue receipt. This monitor has "
                            "only resumed this same conversation; it has not reviewed "
                            f"code or posted to GitHub. Watcher files: {ROOT}."
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
