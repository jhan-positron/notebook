# Prompt: generate a Claude handoff file and push to notebook

Paste this entire prompt into a Claude Code session — any surface with
filesystem and git access: the Windows app's Code tab, or the Claude Code
CLI on a Linux server. (claude.ai chats / the app's Chat tab cannot run
it.) Edit the Config block first if needed. For a multi-item SCOPE, run
it in the most recent involved session, or in a fresh session on the
machine that holds the transcripts in SCOPE.

## Platforms (added 2026-08-19)

Two platforms actively produce sessions, and this prompt runs on both:
- Windows app on `DESKTOP-CI2JA7M`: sessions listed in the app sidebar;
  store under `C:/Users/jibin/.claude/projects/`.
- Claude Code CLI on any Linux machine (identify with `hostname`; one
  example is `claude-alpha`, but do not assume it — more Linux machines
  may exist): session titles shown by `/resume`; store under
  `~/.claude/projects/`.

The session store layout, the title records, and every step below are
identical on both (verified on claude-alpha 2026-08-19: same
projects/JSONL layout, same `ai-title` records, same
`~/.claude/sessions/<pid>.json` derived-name trap). Detect the current
platform from the environment at run time. Each machine sees ONLY its own
store: the other machine's sessions are case 3 under "local vs remote"
below, and handoffs whose `Transcript:` host is the other machine are
frozen for this run (rule under SCOPE: auto).

## Triggering by reference (no paste needed)

I may also invoke this by URL instead of pasting, in either form:
- `please do per https://github.com/jhan-positron/notebook/blob/main/claude-handoff-generation-prompt.md`
- `please do per <same URL>, add sessions: "projectX/session1", "projectY/session1"`

When triggered this way: clone/pull REPO_URL first (required for Step 5
anyway) and read this file from the clone — do not rely on fetching the
URL directly. Run with the Config below as-is (`SCOPE: auto`); any
`add sessions:` items in my message are SCOPE additions, same semantics as
listing them under SCOPE (quoted `"<project> / <session name>"`, tolerant
of spacing around the `/`).

## Config
- REPO_URL: https://github.com/jhan-positron/notebook
- TARGET_DIR: handoffs/     # dir inside the repo; create if missing; "." = repo root
- SCOPE: auto
   - auto (the default): scan BOTH sides and reconcile them.
     (a) Scan every handoff file already in TARGET_DIR and collect their
     `Claude session:` / `Claude chat:` header lines. (b) Enumerate every
     local Claude Code session on this machine — every session JSONL in
     every project folder under `~/.claude/projects/` — reading each session's
     display name from its `custom-title` record (fallback: `ai-title`;
     see Step 2). Then: a session that already has a handoff gets it
     UPDATED per Step 5 (skipped and reported as unchanged if it has no
     new activity since the handoff's Activity END date — no commit
     churn); a session with NO handoff gets a NEW one. One exception
     (added 2026-09-19): the Step 4b lineage backfill (lineage: Step 4,
     Artifacts item 4) runs for a session without new activity.
     FROZEN-handoff rule
     (added 2026-08-19): a handoff whose `Transcript:` host is NOT this
     machine and is not reachable is frozen for this run — no update, no
     questions; list it in the run report as "not checkable from this
     machine". With two active machines this is the normal cross-machine
     case, not an error; the canonical-missing alarm applies only to
     artifacts (Step 4b), never to transcripts. Sessions with no
     substantive work (aborted starts, a few messages, pure meta-runs of
     this prompt) are not silently skipped — list them at the approval
     gate as proposed skips so I can override.
   - If I ALSO list items under SCOPE, they are ADDED to the scanned set.
     Listing is only needed for items auto cannot see: claude.ai chats
     (the app's Chat tab), sessions on other machines — or to
     supply/override a name.
   - `this session only`: cover just the current session; skip the scan.
   - Whatever appears as the value IS the active scope — Claude must cover
     every item, and must not treat a list as illustrative.
   - List syntax for additions (example only, not active — each line one
     item, `"<project> / <session name>"`):
     - SCOPE: auto
       - Claude session: "story2814:GOF staging buffer / Wade's review comment"
       - Claude session: "debug_3bda_flat_freq / run CI tests"
       - Claude chat: "<chat title>"
         (claude.ai chat: not on disk — Claude will ask me to paste content)
- GRANULARITY: per-session  # how many handoff FILES a multi-item SCOPE yields:
  -   consolidated = ONE file covering all items
  -   per-project  = one file per project, covering its listed sessions
  -   per-session  = one file per listed session/chat
  - GRANULARITY as a whole is ignored when SCOPE is `this session only`.
- PRESERVE_ARTIFACTS: auto  # auto = maintain artifacts/ mirrors (Step 4b); off = skip
- LOCAL_CLONE: auto         # auto = reuse an existing local clone if found; else clone
- EXCLUDE_PROJECTS (added 2026-09-04):
  - `~/self/ai` (Linux project folder `-home-jhan-self-ai`)
  Sessions whose cwd is at or under an excluded path are personal/meta and
  are OUT of scope: `SCOPE: auto` neither creates nor updates handoffs for
  them and does not list them as proposed skips. Handoffs written for such
  sessions before the exclusion was added are left as-is (not deleted, not
  refreshed); mention them in one line of the run report as "excluded
  project". An explicit SCOPE listing overrides the exclusion for that item.

## Terminology: project vs session
- A **project** is the working-directory grouping (Windows app: the small
  header line in the sidebar; Linux CLI: simply the cwd). One project = one
  working directory = one folder under `~/.claude/projects/`. Examples:
  project `debug_3bda_flat_freq` (Windows cwd
  `C:\Users\jibin\Documents\claude_debug_3bda_flat_freq`); project folder
  `-home-jhan-workspace-notebook` (Linux cwd `/home/jhan/workspace/notebook`).
- A **session** is one conversation inside a project — normally one JSONL
  transcript file in that project's folder. Example: project
  `debug_3bda_flat_freq` contains three sessions: "debug flat freq on CI
  machine", "explore best freq combo", and "run CI tests".
  CAUTION: resuming a conversation can create a SECOND JSONL (new
  sessionId) that replays the earlier history and continues from there —
  that is still ONE session (one display entry, one handoff). Detect the
  split by identical `custom-title` records and/or identical opening user
  messages; the handoff's `Transcript:` line points at the newest file and
  notes the earlier one(s).
- SCOPE items therefore name sessions as `"<project> / <session name>"`,
  e.g. `"debug_3bda_flat_freq / run CI tests"`.

## Terminology: local vs remote — the three session cases

What matters to this prompt is where the TRANSCRIPT lives, not where the
work ran:

1. **Local session** — cwd on this machine; project folder name is derived
   from the cwd (`C--Users-jibin-Documents-...` on Windows,
   `-home-jhan-workspace-...` on Linux). Fully automatic:
   discovery, titles, dates, rename detection.
2. **Remote-cwd session driven from this machine** — the `ssh-<uuid>`
   project folders: the work ran on an ssh host, but the Claude app on
   this machine wrote the transcript locally. (A Windows-app usage
   pattern; none observed in the claude-alpha store as of 2026-08-19.)
   **This counts as LOCAL** —
   `SCOPE: auto` discovers it and title/date evidence is local. Honor the
   differences:
   - The project folder name is an opaque `ssh-<uuid>`; the REMOTE cwd is
     recoverable from the `cwd` field inside the transcript records.
     Project display names are not on disk — ask me when one is needed
     for the header.
   - The handoff's `Transcript:` line still names THIS machine (that is
     where the JSONL is). The Environment section must name BOTH hosts,
     and artifacts are host-qualified remote paths.
   - Evidence is local, artifacts are remote: generating/updating the
     handoff always works, but Step 4b canonical fetches need ssh
     reachability to the remote host at run time.
3. **Session on another machine** — Claude Code running on the remote box
   itself (or a different laptop). Nothing about it is in this machine's
   store: `SCOPE: auto` cannot see it; it must be listed under SCOPE, and
   names/dates/content must come from that machine or from me. With both
   the Windows app and one or more Linux machines active, each machine's
   sessions are case 3 from every other machine's viewpoint; their existing handoffs are
   frozen per the SCOPE: auto rule, and generating a NEW handoff for them
   from here needs the content supplied (run the prompt on the machine
   that holds the transcript instead, when possible).

## Goal
Produce markdown handoff file(s) covering ALL items in SCOPE — file count
per GRANULARITY — written so a fresh session (or a human) can resume the
work without this session's context. Then commit and push to REPO_URL under
TARGET_DIR — after my approval.

Pipeline: evidence -> dates -> names -> filename(s) -> file(s) -> approval -> push

Steps 1-4 apply PER OUTPUT FILE (dates/slug/header computed from the items
that file covers). The Step 5 approval gate is shown ONCE listing all files.

## Step 1 — Determine activity dates (NOT today's date)
Filename dates are when the work actually happened; it may span several days.
- TIMEZONE (added 2026-07-26): all dates — in filenames, `Activity dates:`,
  and `Generated by` lines — are calendar dates in US Pacific time
  (America/Los_Angeles: PDT during daylight saving, PST otherwise),
  matching the Slack timestamps and my working hours. Transcript/git
  evidence is usually UTC; convert to Pacific before deriving the
  calendar date.
- Evidence priority:
  1. This session's transcript timestamps under `~/.claude/projects/`
     (or platform equivalent)
  2. Git commit timestamps from work done in the session
  3. mtimes of files created/edited during the work
- START = first activity date, END = last activity date, taken across
  ALL SCOPE items.
- Record which evidence source you used — it goes in the file header.
- If dates cannot be established from evidence: ask me. Do not guess.

## Step 2 — Determine session and chat names
- Find each session's exact display name (the session's display title —
  Windows app: the sidebar entry under the project header; Linux CLI: the
  title shown by `/resume` — see Terminology above). Try in order:
  1. The session JSONL under `~/.claude/projects/<project-dir>/` — the
     `custom-title` record (`{"type":"custom-title","customTitle":"..."}`,
     near the top of the file) IS the display name when I have
     named/renamed the session; the `ai-title` record is the auto-generated
     title used when I have not. Newest record wins. (Titles ARE stored on
     disk — verified 2026-07-10; this supersedes the older observation
     that they were not.) Multiple/differing title records over time
     indicate renames; keep that history.
  2. `~/.claude/sessions/<pid>.json` — CAUTION: its `name` field with
     `"nameSource": "derived"` is an auto-generated internal name (e.g.
     `claude-debug-3bda-flat-freq-76`), NOT the display title. Never use a
     derived name as the session name.
  3. If a transcript has neither title record (old sessions predating the
     feature), ask me for the exact display name. On the Windows app,
     offer to accept a screenshot of the sidebar: the small grey header is
     the project, the list items under it are the sessions, and the
     highlighted item is the current session. On the Linux CLI there is
     no sidebar — ask me to type the title as `/resume` shows it.
- If SCOPE includes other Claude Code sessions, resolve their names the same
  way. For claude.ai chats (not readable locally), ask me for the exact title.
- If any name cannot be verified: ask me. Never paraphrase or invent a name.
- Session renames: if a SCOPE item resolves (by content evidence or my
  confirmation) to a transcript that an existing handoff already points to
  via its `Transcript:` line, that is a RENAME of a covered session, not a
  new session. Update that handoff: put the new name on the
  `Claude session:` line, add a `Formerly named:` line recording the old
  session name AND the old filename, and `git mv` the file to the new slug
  (Step 5). Never create a second file for the same transcript.
  A pure `SCOPE: auto` run detects renames by itself: compare each
  handoff's `Claude session:` name against the newest title record in the
  transcript its `Transcript:` line points to; a mismatch is a rename.
- Multi-item SCOPE handling:
  - Current session: use native context.
  - Fast path: if an existing handoff in TARGET_DIR has a `Transcript:`
    header line, use that path directly — no matching or asking needed.
    This is the normal case for `SCOPE: auto` refresh runs.
  - Other Claude Code sessions (no Transcript line yet): match the display
    title against the transcripts' `custom-title`/`ai-title` records. For
    old transcripts with no title records, fall back to content evidence:
    grep for distinctive terms from the title, then verify by reading the
    opening user request. If a match is uncertain or a title matches no
    transcript, ask me.
  - claude.ai chats (the app's Chat tab) are cloud-side and not readable
    from Claude Code: ask me to paste the relevant content; include only
    what I paste.
- What Claude can and cannot discover on its own: Claude CAN enumerate and
  content-scan every local transcript under `~/.claude/projects/` (all
  projects, all sessions on this machine), including their display
  titles (`custom-title`/`ai-title` records) — I do not need to list paths
  or names for anything local. What is NOT in the local store at all:
  sessions from other machines, and claude.ai chats. Windows-app project
  display names shown in the sidebar are also not on disk (only the
  cwd-derived folder name is); on the Linux CLI the cwd IS the project
  name. Use the cwd path and ask me if a friendlier project name matters
  for the header.

## Step 3 — Filename
- Pattern: `claude_<START>-<END>_<slug>.md`, dates as YYYYMMDD.
  Single-day work: `claude_<DATE>_<slug>.md`.
- Filename MUST start with `claude_` (distinguishes these files from ones
  generated by other tools, e.g. codex).
- `<slug>`: lowercase kebab-case.
  - Preferred: slugified session name; append slugified chat name with `__`
    separator if both fit.
  - Apostrophes cannot appear in filenames. Drop possessive `'s` entirely
    when slugifying: "Wade's review comment" -> `wade-review-comment`
    (not `wades-review-comment`). Drop bare apostrophes the same way
    (e.g. "don't" -> `dont`).
  - If that exceeds ~50 chars, replace with a shorter content-hint slug —
    the full names live inside the file, so the slug only needs to hint at
    the contents.
- Target total filename length <= 80 chars.

## Step 4 — File contents
Open with this header block. Keep the labels verbatim:

    # Handoff: <one-line descriptive title>

    > Generated by Claude (Claude Code) on <YYYY-MM-DD>.

    - Activity dates: <YYYY-MM-DD> to <YYYY-MM-DD>
      (source: transcript timestamps | git log | file mtimes)
    - Claude session: "<full exact session name>"
      (project: <project display name>)
      - Transcript: <host>:<absolute path to the session .jsonl>
        (machine-readable pointer so future `SCOPE: auto` runs can match
        this handoff to its session and check for new activity without
        asking me; update the line if the transcript moves)
      - Formerly named: "<previous name>"; file renamed from
        `<previous filename>` on <YYYY-MM-DD>
        (one line per prior name, newest first — the full rename history of
        both the session and the file must be readable right here, without
        consulting git history)
    - Claude chat: "<full exact chat title>"
      (only if a chat is in SCOPE; same rename rule applies; chats have no
      Transcript line — content must be pasted by me each time)

If SCOPE covers multiple sessions/chats, repeat the `Claude session:` /
`Claude chat:` lines once per item — always those exact labels.

Body sections (omit empty ones):
1. Objective
2. Environment — hostname(s) and working directories where the work ran.
   State the host for every machine touched (ssh remote vs the local
   machine, whether that is the Windows laptop or a Linux machine —
   always the actual `hostname`);
   different projects live on different remote machines, so this is required
   whenever any file path or command appears later in the file.
3. Timeline — what was done, by date
4. Artifacts — full host-qualified locations and file names of everything
   the session produced or that a resumer needs: generated reports,
   summaries, handoff/design docs, scripts and tools, data/output
   directories, plus repo/branch/commit hashes for code changes.
   Write paths as `<host>:<absolute path>` (e.g.
   `delphi-3bda:/scratch/jhan/flat_freq_tests/README.md`). This section is
   mandatory when the session created or modified any file.
   Two kinds of entry are easy to miss (added 2026-09-19):
   - Workflow scripts. A Claude Workflow (the feature that runs a script
     of agent steps) stores its script under
     `~/.claude/projects/<project-dir>/<session-id>/workflows/scripts/`,
     outside the workspace. List that path like any other script.
   - Lineage of report pages. A report page is an HTML or md page that
     shows measured numbers. Its lineage is the set of files it is
     computed from. Under the page's Artifacts line, nest these labels
     verbatim, so Step 4b can find those files:
     - `generator:` the script or Workflow that wrote the page, or
       `none` when a person or an agent wrote it by hand.
     - `input:` the file(s) the generator reads, or `none`. Add the note
       `hand-edited after build` when that applies.
     - `input built by:` the script or Workflow that wrote the input
       from the sources, or `none`.
     - `sources:` the raw result files, or the directories that hold
       them, that the input (or the page, when there is no input) took
       its numbers from.
     - `regenerate:` the exact command, with `<OUT>` as the output path,
       or `none` when there is no generator or the generator is a
       Workflow, or `unavailable (<reason>)` when the generator has no
       output-path argument or reads files outside its `input:` and
       `sources:` (live git history, files under `/var/tmp`). Never
       write a command that lets the generator fall back to a default
       output path: `gen_compare.py ROWS_JSON` with one argument
       overwrites the canonical page.
     A data file listed only under a results directory, with no label
     linking it to the page it feeds, is not enough.
5. Current state — only claims backed by evidence from the session
   (commands, outputs, commit hashes); mark anything unverified as unverified
6. Open items / next steps
7. Gotchas & decisions — anything a fresh session would otherwise
   rediscover the hard way

Style rule for ALL sections (and for artifact READMEs): reference pull
requests and issues by their full web link
(e.g. https://github.com/positron-ai/tron/pull/3070), never a bare
"PR #3070" — bare numbers are ambiguous across repos and not clickable.

Results rule (added 2026-07-16, user directive): every performance test
or experiment the handoff covers MUST carry its measured RESULTS inline —
the headline perf numbers (with baseline and delta) AND the measured
power consumption (mean PkgWatt/RAMWatt under load, via the standard
/scratch/jhan/tools/power_capture.sh summary when available), plus a
perf-per-watt reading where both sides of a comparison have power data.
"See the README for numbers" is not sufficient — a handoff must let a
fresh session (or a human) get the quantitative outcome without opening
other files. Use proper markdown tables (fixed-width plain-text tables
render as jumbled prose on GitHub unless fenced).

## Step 4b — Artifact preservation (when PRESERVE_ARTIFACTS: auto)

Important workspace files get mirrored into `artifacts/<topic>/` in the
repo so accidental workspace deletion cannot destroy them.

- What qualifies (ALL must hold):
  1. Referenced in a handoff's Artifacts section (a session judged it
     necessary for resuming work).
  2. Lives on mutable, non-git storage (workspace NFS, /scratch, /var/tmp,
     /tmp, home dirs). Files already in a git repo are already safe.
  3. Executable knowledge or an irreplaceable document: scripts, tools,
     generators, configs, recipes, analysis/plan docs, distilled-knowledge
     pages (HTML/md), or measurement data that a preserved report page,
     or a handoff's Results table, is computed from (added 2026-09-19).
     Litmus test: if the workspace vanished tonight, would recreating
     this cost hours-to-days, or be impossible? Measurement data is the
     impossible case: a test cannot be re-run into the same numbers once
     the binary, the machine state and the time are gone.
  4. Not bulk or regenerable data. Judge each file by its class and its
     size, never by its location: a file is not excluded for sitting
     inside a result tree (updated 2026-09-19: the old wording excluded
     "benchmark result trees" as a whole).
     - Classes that stay on their storage: server logs (for example
       `rinzler.log`, the inference server's log), raw turbostat
       captures (per-interval output of the Linux CPU power sampler,
       hundreds of lines or more), campaign logs and `.done` markers,
       binaries, CI client logs (`perf*.log`) when the sibling
       `perf*.json` holds the per-request samples, and per-repetition
       logs when a proposed compact result text already holds the lines
       that carry the page's measured numbers (check those lines one by
       one, not by appearance). One override: a file that the page, its
       input, or the handoff's Results table takes a measured number
       from (a rate, a time, a power reading) is a source and is
       proposed, whatever its class, unless a proposed compact text
       holds every such line. A line citation in the input is the usual
       evidence, and for an authored page the `sources:` label is
       enough. Lines used for identity or configuration (version,
       commit, device count, NUMA node, memory footprint) do not trigger
       it.
     - Size: a single file above 5 MiB (5242880 bytes) is not proposed.
       List it at the gate as `left behind (size)` with its byte count,
       and I can approve it there. State every batch's file count and
       total MiB at the gate, plus the clone's `.git` size from `du -sm`.
     - Regenerable means a command rebuilds the file from files already
       in git. A file that can only be rebuilt from unpreserved data, a
       hand-edited file, or a file a Workflow built (agent steps, not
       one deterministic command) is not regenerable. This test is for
       data files: a report page is preserved even when its generator
       and input are in git, so GitHub can render it.
- Computed-from files (added 2026-09-19): when a report page (Step 4,
  Artifacts item 4) is proposed or already registered, propose with it
  every not-yet-preserved file its numbers are computed from. Rule 1 is
  satisfied through the page's lineage labels: present in the handoff,
  written there on approval by the lineage walk below, or, for a FROZEN
  handoff, held in the README entry until the handoff is next updated.
  Rules 2 to 4 still apply to each file. The set is:
  - the generator and its input file(s) (`gen_compare.py` and
    `mirror-vs-vnni-rows.json` for `mirror-vs-VNNI-K.html`).
  - the script or Workflow that built the input from the sources.
  - the source files the input cites, of three kinds:
    - the compact texts that hold the per-request or per-repetition
      measured lines: `rt-results.txt`, `perf-round*.txt`, loose `*.txt`
      outputs of runtron (the command-line test tool), and `perf*.json`
      of the CI harness (the nightly test system).
    - the small records beside them: `summary.{json,md,txt}`,
      `build.txt`, `meta.json`, `proof.txt`, a `power_capture.sh`
      summary, a turbostat summary of a few lines.
    - any notes file the input cites for a value the page shows.
  Left behind, and shown at the gate as `left behind (<reason>)`, one
  reason per file, the first that applies: the rule 4 classes
  (`provenance`), files above the size threshold (`size`), a
  per-repetition log whose measured lines a proposed compact text holds
  (`duplicate (held by <compact text>)`), files already mirrored at
  another repo path (`duplicate (<repo path>)`: register that path
  instead of copying again), and files the page takes no value from
  (`no value used`). Mirror each file at
  `artifacts/<topic>/<path relative to the canonical root>`, the layout
  the `exec/results/perf-round-*` entries already use. A canonical root
  is a folder the topic README maps to a repo prefix, never the
  session's cwd. For intel-amx it is `WS`, that is
  `claude-agentsrv:/home/jhan/workspace/intel-AMX`. A topic may have
  several roots with their own prefixes (`tron-perf-fluctuation` maps a
  workspace root to `workspace/` and a `/scratch` root to
  `alpha-scratch/`). Use the registered mapping. For a file under no
  registered root, propose a prefix at the gate. Never derive a path
  that contains `..`.
  Gate line, one per page: `computed-from: <page> <- <N> files, <M>
  MiB; left behind: <K> files (<reason>: <count>, ...)`, followed by the
  proposed repo paths one per line. I approve paths, not counts.
  History: the 2026-09-18 run preserved `mirror-vs-VNNI-K.html` and its
  generator. It read the old rule 4 phrase "benchmark result trees" as
  excluding the data files in `exec/results/vnnik-20260914/`. So the
  input file and the raw texts behind 24 of the page's 52 tests stayed
  on NFS only. The analysis and the file list are in
  `VNNIed-K-in-place/status/mirror-vs-VNNI-K-data-preservation.md`
  (intel-AMX canonical folder, 2026-09-19, sections 4 to 6).
- Session-store files (added 2026-09-19): a file that exists only under
  `~/.claude/projects/` (a Workflow script is the usual case) has no
  stable canonical location. Its path holds a session id no reader can
  guess, and Claude Code deletes transcripts after `cleanupPeriodDays`
  (default 30 days, check `~/.claude/settings.json`). Whether the
  `workflows/scripts/` files are deleted with them is Insufficient data.
  Treat them as at risk. Propose at the gate
  `relocate: <session-store path> -> <target folder>/<file>`. The target
  is the canonical folder of the script that reads the Workflow's
  output, or, failing that, of the scripts the Workflow drove. For
  `pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` that is
  `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/`,
  the folder of `gen_compare.py`, which reads the file the Workflow
  wrote. When no folder qualifies, or more than one does, the target is
  `<canonical root>/exec/workflows/`, and the `relocate:` line says so.
  On approval: create the target folder if it is missing, `cp -p` the
  file there (stop and ask if a file of that name exists), mirror it
  from there at the layout path, register THAT path as canonical, and
  record the session-store path in the README entry as `origin:` (a
  history note that the refresh loop never fetches). The copy comes from
  the store. When the store has already deleted the file, it comes from
  the repo mirror, the restore that the canonical-missing rule asks for.
  This relocation copy, folder creation included, is the one write into
  a canonical folder this prompt allows, and only on approval. Direction
  otherwise stays canonical -> repo. This supersedes the 2026-09-18
  practice of registering the session-store path itself as canonical;
  the two entries registered that way were relocated on 2026-09-20.
- Registry: each `artifacts/<topic>/README.md` lists every preserved file
  with its canonical `<host>:<absolute path>`, what it is, and related
  handoffs. That README is the source of truth for refresh.
  The README records WHAT is preserved. The qualifying rules live in
  this prompt (added 2026-09-19). Phrases in existing README headers and
  entries such as "bulk result trees stay on the canonical storage"
  (lines 44, 113-114, 202 and 442-444 on 2026-09-19) describe what those
  batches held. They are not a rule: do not apply them, do not repeat
  them in a new batch header, and do not rewrite the old headers. A
  report page's entry carries the five lineage labels from Step 4, with
  `<OUT>` in the `regenerate:` command. Under `sources:` each path or
  directory is marked `preserved` or `left behind (<reason>)`, and a
  directory that is partly preserved lists both by file kind, for
  example `cells/*/: preserved perf.json, meta.json, proof.txt; left
  behind (provenance) rinzler.log, perf.log`. The full inventory goes in
  a companion file `<page mirror path>.lineage.md` beside the page's
  mirror: one line per source with its canonical path, its repo path or
  left-behind reason, its byte size, and for a duplicate the compact
  text that holds its lines. The entry names that file. A new batch
  header lists which cited
  files were left behind and why, so a reader sees a decision, not an
  omission.
- Refresh on EVERY run (any SCOPE): for each registered artifact, fetch
  the canonical file and compare content with the repo copy.
  - Different -> refresh the repo copy (commit as
    `Refresh artifact: <topic>/<file>`).
  - Canonical missing -> NEVER delete the repo copy; alert loudly: the
    repo copy is now the only copy — restore it to the workspace or
    deregister it deliberately.
  - Canonical UNREACHABLE (ssh host down / no route) is NOT the missing
    case: skip the refresh, report those mirrors as unverified this run,
    no alarm. The alarm is for a canonical that is GONE from a reachable
    location.
  - Direction is strictly canonical -> repo. Repo copies are mirrors; do
    not hand-edit them — edit the canonical file and let the next run
    sync.
  - Measurement files (added 2026-09-19): a preserved input or source
    file is a record, not a document. If its canonical copy differs from
    the repo copy (a re-run wrote into the same result directory), do
    not refresh it silently. Show `measurement changed: <file>
    (+<a>/-<b> lines)` at the gate, as one item together with every
    report page, generator and lineage file that changed with it, and
    wait for my answer. Yes: refresh every changed file of that set and
    re-run the regeneration check below. No: add `content frozen:
    <date>` to every entry of the set, the page and generator included,
    so the mirror stays one consistent version, and compare only
    existence on later runs.
- New artifacts: when generating/updating handoffs, propose qualifying
  Artifacts entries at the approval gate; on approval copy them in,
  register them in the topic README (commit as
  `Preserve artifact: <topic>/<file>`), and annotate the handoff's
  Artifacts line with `(preserved: artifacts/<topic>/<file>)`.
  Lineage walk (added 2026-09-19): for every report page proposed this
  run, and for every registered page whose README entry or handoff line
  names a generator (`generated by <script>` or a `generator:` label)
  but whose entry lacks the lineage labels, walk generator -> input ->
  input builder -> cited sources, and propose the not-yet-preserved
  files per the "Computed-from files" bullet. Show the second case at
  the gate as `lineage unknown: <page>`. This backfill runs even when
  the page's session has no new activity (the `SCOPE: auto` no-churn
  skip does not apply to it). Read the labels from the handoff, the
  generator's source (the files it reads and its output-path argument),
  the input's own citations, the page's own citations when it has no
  input, and the session transcripts that ran the generator and built
  the input. If a cited source's host is unreachable, propose the
  reachable files, record `lineage incomplete: <page>: <host>
  unreachable` in the entry, and walk again next run. If a cited file
  is gone from a reachable host, mark it `left behind (missing on
  <date>)` and do not invent a substitute. On approval, write the
  labels into the README entry and nest them under the page's line in
  the handoff's Artifacts section, in the same commit as the
  `(preserved: ...)` annotation. Regeneration check: at a page's first
  preservation, and again when a file of its lineage is refreshed, run
  the `regenerate:` command once with `<OUT>` in the scratch directory
  and only the preserved copies as input. Record `regenerate verified
  <date>` or `regenerate unverified (<reason>)` in the entry. Do not
  run it on other passes. A backfill edits only those Artifacts
  lines: the header dates and the filename stay, and the gate lists the
  handoff as `UPDATE (lineage labels only)`. For a FROZEN handoff, write
  the labels into the README entry only and show `lineage labels
  pending: <handoff>` at the gate. For a batch, commit as `Preserve
  artifact: <topic>/<page> lineage (<N> files, <M> MiB)`.
- HTML artifacts: GitHub's normal blob view does not render standalone
  HTML. When preserving or generating an `.html` file in this notebook
  repo, add rendered-view links using this exact pattern (updated
  2026-08-19 to match the deployed files, e.g.
  artifacts/common-knowledge/*.html), after substituting the final
  repo-relative path — a comment block placed ABOVE the doctype, no
  visible in-page link needed:

      <!--
        Rendered page (open in browser):
        https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/<repo-relative-path>
        Backup renderer:
        https://raw.githack.com/jhan-positron/notebook/main/<repo-relative-path>
      -->
      <!DOCTYPE html>

  If an artifact README links to that HTML file, include the primary
  rendered-view URL there too so GitHub readers can open the page
  directly. If the file later MOVES within the repo, update both URLs in
  the comment to the new path.
- Do NOT place artifacts in handoffs/ — the SCOPE auto scan parses every
  file there as a handoff.

## Step 5 — Git workflow with approval gate
1. Locate or clone the repo per LOCAL_CLONE; `git pull` before adding
   the file.
2. For each output file, first check TARGET_DIR for an existing handoff
   already covering the same session(s): match on the `Claude session:` /
   `Claude chat:` header lines (project + exact name), NOT on the filename
   (dates in filenames drift as work continues).
   - If one exists: UPDATE that file in place — merge the new activity into
     the existing sections, refresh the "Generated by" date, and extend the
     Activity dates END. If the date range OR the session name changed
     (rename detected per Step 2), `git mv` the file to the new
     `claude_<START>-<END>_<slug>.md` name in the same commit so the
     filename stays truthful, and record the old filename on the
     `Formerly named:` header line. Never create a second file for a
     session that already has one. Exception (added 2026-09-19): a
     lineage backfill (Step 4b) edits only the page's Artifacts lines,
     keeps the header dates and the filename, and is committed in the
     `Preserve artifact:` commit, not as `Update Claude handoff:`.
   - If none exists: write a new file. If an unrelated file with the same
     name is somehow present, stop and ask before overwriting.
3. APPROVAL GATE — show me, for every output file: whether it is NEW or an
   UPDATE of an existing handoff (old -> new name if renamed), final path +
   filename, the full header block, and a <=10-line body summary (for
   updates: what changed). Also list artifact actions from Step 4b
   (preserved / refreshed / canonical-missing alerts), plus (added
   2026-09-19) the `computed-from:`, `lineage unknown:`, `lineage
   incomplete:`, `lineage labels pending:`, `relocate:`, `measurement
   changed:` and `left behind` lines, each batch's file count and total
   MiB, and the clone's `.git` size in MiB. Wait for my explicit
   approval.
4. On approval: commit with message
   `Add Claude handoff: <slug> (<START>..<END>)` for new files, or
   `Update Claude handoff: <slug> (<START>..<END>)` for updates, then push.
   After a push that carries a `Preserve artifact:` or `Refresh
   artifact:` commit, run `git fetch origin` and compare, for every
   file the commit touched (mirrors, README, handoffs), the blob id
   from `git ls-tree -r origin/main <path>` with `git hash-object
   <local path>`. Report `on origin/main: <N> of <N> files, contents
   match`, and name any file whose id differs or is missing. A name
   check alone would pass a README-only push that left a changed mirror
   unstaged (added 2026-09-19).
5. If push fails (auth, permissions, non-fast-forward): stop, show the
   exact error, and ask. No force-push, no credential changes.
