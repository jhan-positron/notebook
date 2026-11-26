#!/usr/bin/env python3
"""tron PR 5022 after the s_pages commit e863b27272: refresh the description, post the note to the reviewer, request his review.

Usage: post.py check | save-body | post-note | request-review
  check          : reads GitHub, builds body-final.md and note-final.md in this folder, prints the changes. Writes nothing to GitHub.
  save-body      : replaces the PR description with body-final.md and reads it back.
  post-note      : posts note-final.md as one conversation comment, reads it back and prints its link.
  request-review : requests a review from the reviewer and checks the timeline event.
Every write step runs the checks of `check` first. jhan's go of 2026-11-24: update the PR, post the note with the
reason for the review request, and request the review. No merge.
"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO, PR = "positron-ai/tron", 5022
HEAD = "e863b27272c13eded2f5c991f6201a1bc66cbfb6"
NIX_RUN, CMAKE_RUN = 45524881415, 45524884960
REVIEWER = "ishapira-positron"
HERE = Path(__file__).resolve().parent
RUN_URL = "https://github.com/positron-ai/tron/actions/runs/{}"


def gh(args, payload=None, raw=False):
    p = subprocess.run(["gh", "api"] + args, input=None if payload is None else json.dumps(payload), capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"gh api {args[:3]} failed: {p.stderr[:400]}")
    return p.stdout if raw else json.loads(p.stdout)


def same(a, b):
    """Equal, where newlines at the very end do not count (GitHub may trim them on save)."""
    return a.rstrip("\n") == b.rstrip("\n")


def job_log(job_id):
    out = gh(["--allow-escape-sequences", f"repos/{REPO}/actions/jobs/{job_id}/logs"], raw=True)
    return re.sub(r"\x1b\[[0-9;]*m", "", out)


def ci_facts():
    facts = {}
    for name, run in (("nix", NIX_RUN), ("cmake", CMAKE_RUN)):
        r = gh([f"repos/{REPO}/actions/runs/{run}"])
        assert r["head_sha"] == HEAD, (name, r["head_sha"])
        assert r["status"] == "completed" and r["conclusion"] == "success", f"{name} run {run}: {r['status']} {r['conclusion']}"
        attempt = r["run_attempt"]
        jobs = gh([f"repos/{REPO}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100"])["jobs"]
        bad = [j["name"] for j in jobs if j["conclusion"] not in ("success", "skipped")]
        assert not bad, (name, bad)
        facts[name] = {"attempt": attempt, "jobs": {j["name"]: j for j in jobs}}
    host = facts["cmake"]["jobs"]["test-host"]
    assert host["runner_name"].startswith("delphi-"), f"CMake test-host ran on {host['runner_name']}: rerun the job to reach a runner with AMX"
    log = job_log(host["id"])
    m = re.search(r"(\d+) passed, (\d+) skipped, (\d+) failed", log)
    assert m and m.group(2) == "0" and m.group(3) == "0", m and m.group(0)
    for t in ("t_amx_numerics", "t_amx_dispatch_dtype"):
        assert re.search(rf"passed\s+(\[new\]\s+)?{t}\b", log), f"{t} is not listed as passed in the CMake test-host log"
    facts["cmake_runner"], facts["cmake_passed"], facts["cmake_attempt"] = host["runner_name"], int(m.group(1)), host["run_attempt"]
    nix_host = facts["nix"]["jobs"]["Test host"]
    nlog = job_log(nix_host["id"])
    for t in ("t_amx_numerics", "t_amx_dispatch_dtype"):
        assert re.search(rf"passed\s+(\[new\]\s+)?{t}\b", nlog), f"{t} is not listed as passed in the GCP Nix Test host log"
    lint = job_log(facts["nix"]["jobs"]["Lint"]["id"])
    assert "TRON_LINT_PASSED: C++ formatting (clang-format)" in lint
    facts["nix_runner"] = nix_host["runner_name"]
    return facts


def activity():
    pr = gh([f"repos/{REPO}/pulls/{PR}"])
    assert pr["state"] == "open" and pr["head"]["sha"] == HEAD, (pr["state"], pr["head"]["sha"])
    reviews = gh([f"repos/{REPO}/pulls/{PR}/reviews?per_page=100"])
    inline = gh([f"repos/{REPO}/pulls/{PR}/comments?per_page=100"])
    conv = gh([f"repos/{REPO}/issues/{PR}/comments?per_page=100"])
    q = """query{repository(owner:"positron-ai",name:"tron"){pullRequest(number:5022){reviewDecision mergeStateStatus
      reviewThreads(first:100){totalCount nodes{isResolved}}}}}"""
    g = json.loads(subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True, check=True).stdout)
    g = g["data"]["repository"]["pullRequest"]
    new = [f"{r['user']['login']} {r['state']} {r['submitted_at']}" for r in reviews if r.get("commit_id") == HEAD]
    new += [f"inline {c['user']['login']} {c['created_at']}" for c in inline if c["created_at"] > "2026-11-25T01:19:00Z"]
    new += [f"comment {c['user']['login']} {c['created_at']}" for c in conv if c["created_at"] > "2026-11-25T01:19:00Z"]
    unresolved = sum(not t["isResolved"] for t in g["reviewThreads"]["nodes"])
    print(f"PR: head {HEAD[:10]}, decision {g['reviewDecision']}, merge state {g['mergeStateStatus']}, threads {g['reviewThreads']['totalCount']}, "
          f"unresolved {unresolved}; reviews {len(reviews)}, inline comments {len(inline)}, conversation comments {len(conv)}")
    print("activity since the push of the head:", new or "none")
    return pr, new, unresolved


def build(pr, f):
    live = pr["body"]
    before = HERE / "body-live-before.md"
    if not before.exists():
        before.write_text(live + "\n", encoding="utf-8")
    saved = HERE / "body-final.md"
    already_saved = saved.exists() and same(saved.read_text(encoding="utf-8"), live)
    if already_saved:
        live = before.read_text(encoding="utf-8").rstrip("\n")   # the description is saved: rebuild from the copy, to compare
    assert same(before.read_text(encoding="utf-8"), live), "the live description changed since the copy was taken"
    attempt = "" if f["cmake_attempt"] == 1 else f", attempt {f['cmake_attempt']}"
    edits = [
        ("Tests run at the head `90a9110be5` on delphi-3b35, a Xeon 6962P host with AMX, on 2026-11-24 (`pr5606-check-20261123`).",
         "Tests run at the head `e863b27272` on delphi-3b35, a Xeon 6962P host with AMX, on 2026-11-25 (`pr5022-optb-20261124`).", 1),
        ("The head also contains main up to `3bea58b788`, which", "The head also contains main up to `cef7aab2f9`, which", 1),
        # The test build at the head has BUILD_INGEST_MODELS=ON too (results/pr5022-optb-20261124/build-b.txt).
        ("RelWithDebInfo and `TRON_AMX_DISPATCH=ON`. Only the measurement builds set `BUILD_INGEST_MODELS=ON`.",
         "RelWithDebInfo, `TRON_AMX_DISPATCH=ON` and `BUILD_INGEST_MODELS=ON`.", 1),
        ("`t_llama_unit`: 265,564 / 75 pass", "`t_llama_unit`: 265,801 / 85 pass", 2),
        ("CI run [45461355215](https://github.com/positron-ai/tron/actions/runs/45461355215)", f"CI run [{NIX_RUN}]({RUN_URL.format(NIX_RUN)})", 1),
        ("Run [45461357302](https://github.com/positron-ai/tron/actions/runs/45461357302), test-host on runner delphi-3bd6-0 (Xeon 6962P, attempt 2)",
         f"Run [{CMAKE_RUN}]({RUN_URL.format(CMAKE_RUN)}), test-host on runner {f['cmake_runner']} (Xeon 6962P{attempt})", 1),
        ("test-host: 106 of 106 tests pass.", f"test-host: {f['cmake_passed']} of {f['cmake_passed']} tests pass.", 1),
        ("Clang-format 19.1.7 and `git diff --check` pass at the head.", "Clang-format (CI Lint) and `git diff --check` pass at the head.", 1),
    ]
    final = live
    for old, new, n in edits:
        assert final.count(old) == n, f"expected {n} of: {old[:70]} (found {final.count(old)})"
        final = final.replace(old, new)
    for stale in ("90a9110be5", "3bea58b788", "45461355215", "45461357302", "pr5606-check-20261123"):
        assert stale not in final, f"stale text left in the description: {stale}"
    body_no_words = re.sub(r"(?ms)^## Words used here.*?(?=^## )", "", final)
    words = len(body_no_words.split())
    assert words < 2000, words
    if already_saved:
        assert same(saved.read_text(encoding="utf-8"), final), "the saved description differs from a fresh build"
    saved.write_text(final + "\n", encoding="utf-8")
    note = (HERE / "note-to-reviewer.md").read_text(encoding="utf-8").rstrip("\n")
    ci = (f"Both CI pipelines pass at the head: the default one ([run {NIX_RUN}]({RUN_URL.format(NIX_RUN)})) and the CMake workflow with the option ON "
          f"([run {CMAKE_RUN}]({RUN_URL.format(CMAKE_RUN)}), test-host on {f['cmake_runner']}, {f['cmake_passed']} of {f['cmake_passed']} tests pass).")
    assert note.count("CI_SENTENCE") == 1
    note = note.replace("CI_SENTENCE", ci)
    (HERE / "note-final.md").write_text(note + "\n", encoding="utf-8")
    diff = list(difflib.unified_diff(live.splitlines(), final.splitlines(), "description now", "description after", lineterm="", n=0))
    print(f"description: {words} words after the edit, {sum(1 for d in diff if d.startswith('+') and not d.startswith('+++'))} changed lines")
    for d in diff:
        print("  " + d[:260])
    print(f"note: {len(note.split())} words; last paragraph: {note.splitlines()[-1][:400]}")
    return final, note


def main():
    mode = sys.argv[1]
    pr, new, unresolved = activity()
    facts = ci_facts()
    print(f"CI: both runs pass; CMake test-host on {facts['cmake_runner']} (attempt {facts['cmake_attempt']}): {facts['cmake_passed']} passed; "
          f"GCP Nix Test host on {facts['nix_runner']}")
    final, note = build(pr, facts)
    if mode == "check":
        return
    assert unresolved == 0, "an unresolved review thread exists: read it first"
    if mode == "save-body":
        got = gh(["-X", "PATCH", f"repos/{REPO}/pulls/{PR}", "--input", "-"], {"body": final})
        back = gh([f"repos/{REPO}/pulls/{PR}"])["body"]
        assert same(back, final), "read-back of the description differs"
        print(f"description saved and read back: equal; updated_at {got['updated_at']}")
    elif mode == "post-note":
        got = gh(["-X", "POST", f"repos/{REPO}/issues/{PR}/comments", "--input", "-"], {"body": note})
        back = gh([f"repos/{REPO}/issues/comments/{got['id']}"])
        assert same(back["body"], note), "read-back of the note differs"
        (HERE / "posted-note.json").write_text(json.dumps({"id": got["id"], "url": got["html_url"], "created_at": got["created_at"]}, indent=1))
        print(f"note posted and read back: equal; {got['html_url']}")
    elif mode == "request-review":
        gh(["-X", "POST", f"repos/{REPO}/pulls/{PR}/requested_reviewers", "--input", "-"], {"reviewers": [REVIEWER]})
        events = gh([f"repos/{REPO}/issues/{PR}/timeline?per_page=100&page=1"]) + gh([f"repos/{REPO}/issues/{PR}/timeline?per_page=100&page=2"])
        req = [e for e in events if e.get("event") == "review_requested" and (e.get("requested_reviewer") or {}).get("login") == REVIEWER]
        listed = [u["login"] for u in gh([f"repos/{REPO}/pulls/{PR}/requested_reviewers"])["users"]]
        print(f"requested reviewers now: {listed}; last review_requested event for {REVIEWER}: {req[-1]['created_at'] if req else 'not found in the timeline'}")
        assert REVIEWER in listed
    else:
        raise SystemExit("unknown mode")


main()
