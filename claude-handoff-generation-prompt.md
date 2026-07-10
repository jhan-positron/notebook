# Prompt: generate a Claude handoff file and push to notebook

Paste this entire prompt into a Claude Code session (Code tab — it needs
filesystem and git access, so not the Chat tab). Edit the Config block
first if needed. For a multi-item SCOPE, run it in the most recent
involved session, or in a fresh Code session on the same machine.

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
     local Code-tab session on this machine — every session JSONL in every
     project folder under `~/.claude/projects/` — reading each session's
     display name from its `custom-title` record (fallback: `ai-title`;
     see Step 2). Then: a session that already has a handoff gets it
     UPDATED per Step 5 (skipped and reported as unchanged if it has no
     new activity since the handoff's Activity END date — no commit
     churn); a session with NO handoff gets a NEW one. Sessions with no
     substantive work (aborted starts, a few messages, pure meta-runs of
     this prompt) are not silently skipped — list them at the approval
     gate as proposed skips so I can override.
   - If I ALSO list items under SCOPE, they are ADDED to the scanned set.
     Listing is only needed for items auto cannot see: Chat-tab chats,
     sessions on other machines — or to supply/override a name.
   - `this session only`: cover just the current session; skip the scan.
   - Whatever appears as the value IS the active scope — Claude must cover
     every item, and must not treat a list as illustrative.
   - List syntax for additions (example only, not active — each line one
     item, `"<project> / <session name>"`):
     - SCOPE: auto
       - Claude session: "story2814:GOF staging buffer / Wade's review comment"
       - Claude session: "debug_3bda_flat_freq / run CI tests"
       - Claude chat: "<chat title>"
         (Chat-tab chat: not on disk — Claude will ask me to paste content)
- GRANULARITY: per-session  # how many handoff FILES a multi-item SCOPE yields:
  -   consolidated = ONE file covering all items
  -   per-project  = one file per project, covering its listed sessions
  -   per-session  = one file per listed session/chat
  - GRANULARITY as a whole is ignored when SCOPE is `this session only`.
- PRESERVE_ARTIFACTS: auto  # auto = maintain artifacts/ mirrors (Step 4b); off = skip
- LOCAL_CLONE: auto         # auto = reuse an existing local clone if found; else clone

## Terminology: project vs session
- A **project** is the working-directory grouping shown as the small header
  line in the Claude app sidebar. One project = one working directory = one
  folder under `~/.claude/projects/`. Example: project `debug_3bda_flat_freq`
  (cwd `C:\Users\jibin\Documents\claude_debug_3bda_flat_freq`).
- A **session** is one conversation inside a project — normally one JSONL
  transcript file in that project's folder. Example: project
  `debug_3bda_flat_freq` contains three sessions: "debug flat freq on CI
  machine", "explore best freq combo", and "run CI tests".
  CAUTION: resuming a conversation can create a SECOND JSONL (new
  sessionId) that replays the earlier history and continues from there —
  that is still ONE session (one sidebar entry, one handoff). Detect the
  split by identical `custom-title` records and/or identical opening user
  messages; the handoff's `Transcript:` line points at the newest file and
  notes the earlier one(s).
- SCOPE items therefore name sessions as `"<project> / <session name>"`,
  e.g. `"debug_3bda_flat_freq / run CI tests"`.

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
- Find each session's exact display name (the title shown in the app
  sidebar under the project header — see Terminology above). Try in order:
  1. The session JSONL under `~/.claude/projects/<project-dir>/` — the
     `custom-title` record (`{"type":"custom-title","customTitle":"..."}`,
     near the top of the file) IS the sidebar display name when I have
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
     feature), ask me for the exact name as shown in the sidebar. Offer to
     accept a screenshot of the sidebar: the small grey header is the
     project, the list items under it are the sessions, and the
     highlighted item is the current session.
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
  - Other Claude Code sessions (no Transcript line yet): match the sidebar
    title against the transcripts' `custom-title`/`ai-title` records. For
    old transcripts with no title records, fall back to content evidence:
    grep for distinctive terms from the title, then verify by reading the
    opening user request. If a match is uncertain or a title matches no
    transcript, ask me.
  - Claude chats (Chat tab) are cloud-side and not readable from Claude
    Code: ask me to paste the relevant content; include only what I paste.
- What Claude can and cannot discover on its own: Claude CAN enumerate and
  content-scan every local transcript under `~/.claude/projects/` (all
  projects, all sessions on this machine), including their sidebar display
  titles (`custom-title`/`ai-title` records) — I do not need to list paths
  or names for anything local. What is NOT in the local store at all:
  sessions from other machines, and Chat-tab chats. Project display names
  shown in the sidebar are also not on disk (only the cwd-derived folder
  name is); use the cwd path and ask me if a friendlier project name
  matters for the header.

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
   State the host for every machine touched (ssh remote vs local Windows);
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
5. Current state — only claims backed by evidence from the session
   (commands, outputs, commit hashes); mark anything unverified as unverified
6. Open items / next steps
7. Gotchas & decisions — anything a fresh session would otherwise
   rediscover the hard way

Style rule for ALL sections (and for artifact READMEs): reference pull
requests and issues by their full web link
(e.g. https://github.com/positron-ai/tron/pull/3070), never a bare
"PR #3070" — bare numbers are ambiguous across repos and not clickable.

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
     pages (HTML/md). Litmus test: if the workspace vanished tonight,
     would recreating this cost hours-to-days?
  4. Not bulk or regenerable data (benchmark result trees, turbostat
     captures, raw logs stay on their storage).
- Registry: each `artifacts/<topic>/README.md` lists every preserved file
  with its canonical `<host>:<absolute path>`, what it is, and related
  handoffs. That README is the source of truth for refresh.
- Refresh on EVERY run (any SCOPE): for each registered artifact, fetch
  the canonical file and compare content with the repo copy.
  - Different -> refresh the repo copy (commit as
    `Refresh artifact: <topic>/<file>`).
  - Canonical missing -> NEVER delete the repo copy; alert loudly: the
    repo copy is now the only copy — restore it to the workspace or
    deregister it deliberately.
  - Direction is strictly canonical -> repo. Repo copies are mirrors; do
    not hand-edit them — edit the canonical file and let the next run
    sync.
- New artifacts: when generating/updating handoffs, propose qualifying
  Artifacts entries at the approval gate; on approval copy them in,
  register them in the topic README (commit as
  `Preserve artifact: <topic>/<file>`), and annotate the handoff's
  Artifacts line with `(preserved: artifacts/<topic>/<file>)`.
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
     session that already has one.
   - If none exists: write a new file. If an unrelated file with the same
     name is somehow present, stop and ask before overwriting.
3. APPROVAL GATE — show me, for every output file: whether it is NEW or an
   UPDATE of an existing handoff (old -> new name if renamed), final path +
   filename, the full header block, and a <=10-line body summary (for
   updates: what changed). Also list artifact actions from Step 4b
   (preserved / refreshed / canonical-missing alerts). Wait for my
   explicit approval.
4. On approval: commit with message
   `Add Claude handoff: <slug> (<START>..<END>)` for new files, or
   `Update Claude handoff: <slug> (<START>..<END>)` for updates, then push.
5. If push fails (auth, permissions, non-fast-forward): stop, show the
   exact error, and ask. No force-push, no credential changes.
