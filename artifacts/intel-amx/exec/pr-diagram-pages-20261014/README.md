# pr-diagram-pages-20261014

Walk-through pages for the four PRs that split tron PR 4424 (one page per PR), built 2026-10-14.
Each page copies the base diagrams of the three PR 4424 pages
(PR3879/new-PRs/merge-4737-2-4424/diagramming-code-changes-{kv_cache,k_vnni,model}.hpp.html)
verbatim and adds prose: Short version, Words used here, what the PR adds, a walk-through order,
per-diagram status boxes (in this PR / already there / lands in a later PR), the code-change
sections of the source pages that land in the PR, and gaps.

Output pages: PR3879/new-PRs/split-4424/diagrams-PR{1-4868,2-4887,3-4898,4-4901}.html

Layout of this record (the builder expects it):
- tools/build_pr_page.py  : spec JSON -> HTML page (copies blocks/<id>.html verbatim)
- tools/check_pages.py    : structural checks of built pages (run: python3 -I tools/check_pages.py <out dir>)
- tools/dump_text.py      : SVG-free text dump of a source page
- tools/pr-diagram-pages-map-*.js, tools/pr-diagram-pages-qa-*.js : the two Workflow scripts
  (map: 4 mappers, 12 verifiers, 4 revisers; qa: 4 reader checks, 4 citation checks, 4 fixers)
- spec/pr<n>-<number>.json       : the final page spec (after the qa fixers)
- spec/pr<n>-<number>-full.json  : spec v1, the three verifier reviews, the reviser's applied/rejected lists
- spec/qa-results.json           : the qa findings and fixer outcomes
- blocks/<id>.html : the 16 base-diagram blocks extracted from the source pages (h3 .. </figure>)
- blocks/diagrams.txt, blocks/hits.txt, src/changes.txt : the text extracts the agents read
- src/head-kv_cache.html : the source pages' <head> (shared stylesheet)
- inputs/ : the PR bodies, file lists, commit lists and the split-plan excerpt as read on 2026-10-14

Rebuild: python3 -I tools/build_pr_page.py spec/pr1-4868.json out/diagrams-PR1-4868.html (and so on), then
python3 -I tools/check_pages.py out
