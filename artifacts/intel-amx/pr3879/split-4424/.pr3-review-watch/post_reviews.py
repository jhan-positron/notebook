"""Post the user's authorized review, checking the revision before each write."""

import datetime
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "review-80bce9a08d"
EXPECTED = json.loads((ROOT / "pre-post.json").read_text())
RECEIPTS = OUT / "posted.json"


def gh(*args):
    result = subprocess.run(["gh", *args], text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


posted = json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else []
for name in ["post-1-normal", "post-2-tron", "post-3-wade", "post-4-ben", "post-5-plain", "post-description-draft"]:
    if any(row["name"] == name for row in posted):
        continue
    live = gh("pr", "view", "4898", "--repo", "positron-ai/tron", "--json", "headRefOid,baseRefOid,body,state")
    for field in ["headRefOid", "baseRefOid", "body"]:
        if live[field] != EXPECTED[field]:
            raise RuntimeError(f"PR {field} changed; stop and review the change before posting")
    if live["state"] != "OPEN":
        raise RuntimeError("PR is no longer open")
    payload = json.loads((OUT / (name + ".json")).read_text())
    endpoint = "issues/4898/comments" if name == "post-description-draft" else "pulls/4898/reviews"
    existing = gh("api", "--paginate", "--slurp", "repos/positron-ai/tron/" + endpoint)
    existing = [row for page in existing for row in page]
    matches = [row for row in existing if row.get("body") == payload["body"]]
    if matches:
        result = matches[0]
    else:
        result = gh("api", "repos/positron-ai/tron/" + endpoint, "--method", "POST", "--input", str(OUT / (name + ".json")))
    row = {"name": name, "id": result["id"], "url": result["html_url"], "commit_id": result.get("commit_id"), "time": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    posted.append(row)
    save(RECEIPTS, posted)
    print(json.dumps(row), flush=True)

state = json.loads((ROOT / "state.json").read_text())
state["review_completion"] = {
    "status": "complete",
    "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "head": EXPECTED["headRefOid"],
    "base": EXPECTED["baseRefOid"],
    "reviews_and_comments": posted,
    "description_edited": False,
    "source_edited": False,
    "product_tests_rerun": False,
    "artifact": str(OUT / "review.html"),
}
save(ROOT / "state.json", state)
