# Mock-review pipeline for PR #3879 (Alexey persona)

Files
- gen_review4.py            generator for the latest round (HTML + Markdown twin); copy to gen_review5.py for the next round
- r4/round3_comments.json   open items entering round 4 (id, file, line, snippet range, text, tag, blocker, r3 status)
- r4/status.json            per-id status at the reviewed tree (FIXED / PARTIAL / NOT_ADDRESSED, new anchor, evidence)
- r4/round4_data.py         round-authored data: verdict body, TAKE, NEW comments, FOLLOWUP sentences, FIX suggestions, CLEAN rows
- r4/build_status.py        merges the workflow journal into status.json
- ../../PR3879/triage.json  THE DECISION RECORD (author's decisions per review id). Source of truth across rounds.

How a round runs (recipe that worked, 2026-08-25)
1. Diff the tree since the previous round's head; only items anchored in changed files can change status.
2. Read PR3879/triage.json. For every open item pass its triage (if any) to the status verifier:
   - done/partial: the verifier checks the claim against the tree (commit named in the entry) and reports FIXED / PARTIAL.
   - ignore/defer: the verifier does NOT re-raise the comment. It writes, in the persona's voice, how he would reply to the
     author's stated reason (accept and resolve, or push back with one sentence), and the generator lists the item in a
     "Declined or deferred by the author" table with that predicted reply, instead of among the open comments.
   - question: the item stays open; the verifier answers the author's question if the tree can.
3. Independent finder over the delta (new items), one adversarial refuter per verifier/finder.
4. Merge into status.json (build_status.py), author roundN_data.py, run gen_reviewN.py, archive the previous alexey-review.html as alexey-review-(N-1).html.
5. Hand-inserted response blocks (e.g. the R1-47 / R1-48 boxes in round 4) are NOT regenerated: move their content into the
   data file (FOLLOWUP or a RESPONSES dict) before regenerating, or re-insert.

Decision vocabulary (triage.json): done | partial | ignore | defer | question. Always record reason + commit + date + by.
