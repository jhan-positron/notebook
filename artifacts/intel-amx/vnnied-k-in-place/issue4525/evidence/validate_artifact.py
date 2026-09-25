#!/usr/bin/env python3
"""Validate the revised design without replacing its historical evidence."""

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "tron-VNNIed-K"
REPORT = ROOT / "issue4525/status/design-new-tensor-type.html"
EVIDENCE = REPORT.parent.parent / "evidence"
MAIN = "f46e48bab498c0c07825f3e3d38d6ffa42d4af9b"
CHILD = "30c4ac82cbb6959f7e4f66b29efb36f5e0749b48"
RECORDED_MAIN = "98bb8cb22f947574c6a2f36abd807e1e747d4916"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True)


def main():
    content = REPORT.read_text()
    soup = BeautifulSoup(content, "html.parser")
    ids = [node["id"] for node in soup.select("[id]")]
    assert len(ids) == len(set(ids)), "duplicate HTML id"
    assert soup.html["lang"] == "en"
    assert soup.title
    assert soup.find("meta", attrs={"name": "color-scheme"})["content"] == "light"
    assert not soup.select("script[src], link[rel=stylesheet], img[src^=http]")
    blobs = {}
    source_links = []
    pinned_commits = set()
    local_links = []
    linked_html_ids = {REPORT: set(ids)}
    for anchor in soup.select("a[href]"):
        href = anchor["href"]
        parsed = urlparse(href)
        if not parsed.scheme:
            target = (REPORT.parent / unquote(parsed.path)).resolve() if parsed.path else REPORT
            # This script writes its own result after validation.
            if target != EVIDENCE / "design-revision-artifact-validation.json":
                assert target.exists(), str(target)
            if parsed.fragment and target.suffix.lower() in (".html", ".htm"):
                if target not in linked_html_ids:
                    linked_soup = BeautifulSoup(target.read_text(), "html.parser")
                    linked_html_ids[target] = {
                        node["id"] for node in linked_soup.select("[id]")
                    }
                assert unquote(parsed.fragment) in linked_html_ids[target], href
            local_links.append(href)
        elif parsed.netloc == "github.com" and "/blob/" in parsed.path:
            _, owner, repo_name, kind, commit, file_path = parsed.path.split("/", 5)
            assert (owner, repo_name, kind) == ("positron-ai", "tron", "blob")
            assert re.fullmatch(r"[0-9a-f]{40}", commit), commit
            if commit not in pinned_commits:
                assert git("rev-parse", f"{commit}^{{commit}}").strip() == commit
                pinned_commits.add(commit)
            key = (commit, file_path)
            if key not in blobs:
                blobs[key] = git("show", f"{commit}:{file_path}")
            n_lines = len(blobs[key].splitlines())
            match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", parsed.fragment)
            assert match, href
            first, last = int(match[1]), int(match[2] or match[1])
            assert 1 <= first <= last <= n_lines, href
            source_links.append({"url": href, "source_lines": n_lines})
    result = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "report_bytes": len(content.encode()),
        "unique_html_ids": len(ids),
        "local_links_checked": len(local_links),
        "pinned_source_links_checked": len(source_links),
        "pinned_commits_checked": sorted(pinned_commits),
        "linked_html_documents_checked": len(linked_html_ids),
        "unique_source_files_at_revisions": len(blobs),
        "checks_passed": True,
        "scope": "HTML structure, local links and HTML fragments, pinned git commits, file paths and line bounds; not source-claim or C++ verification",
        "source_links": source_links,
    }
    (EVIDENCE / "design-revision-artifact-validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "source_links"}, indent=2))


if __name__ == "__main__":
    ancestor = git("merge-base", MAIN, CHILD).strip()
    cache_diff = git("diff", ancestor, MAIN, "--", "h/tron/models/kv_cache.hpp")
    recorded_main_cache_diff = git(
        "diff", MAIN, RECORDED_MAIN, "--", "h/tron/models/kv_cache.hpp"
    )
    audit = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Local git snapshot; origin/main is a local tracking reference, not a live remote-tip check",
        "original_design_main_snapshot": MAIN,
        "reviewed_child_snapshot": CHILD,
        "main_tip_recorded_by_review": RECORDED_MAIN,
        "merge_base": ancestor,
        "cache_header_unchanged_from_common_ancestor_to_main": cache_diff == "",
        "original_main_is_ancestor_of_recorded_main": git(
            "merge-base", MAIN, RECORDED_MAIN
        ).strip() == MAIN,
        "commits_from_original_main_to_recorded_main": int(
            git("rev-list", "--count", f"{MAIN}..{RECORDED_MAIN}").strip()
        ),
        "cache_header_unchanged_from_original_to_recorded_main": recorded_main_cache_diff == "",
        "working_tree_status": git("status", "--short"),
        "local_head": git("rev-parse", "HEAD").strip(),
        "local_origin_main": git("rev-parse", "origin/main").strip(),
        "main_cache_sha256": hashlib.sha256(
            git("show", f"{MAIN}:h/tron/models/kv_cache.hpp").encode()).hexdigest(),
    }
    assert audit["cache_header_unchanged_from_common_ancestor_to_main"]
    assert audit["original_main_is_ancestor_of_recorded_main"]
    assert audit["cache_header_unchanged_from_original_to_recorded_main"]
    (EVIDENCE / "design-revision-source-audit.json").write_text(
        json.dumps(audit, indent=2) + "\n"
    )
    main()
