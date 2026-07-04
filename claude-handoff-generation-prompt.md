# Prompt: generate a Claude handoff file and push to notebook

Paste this entire prompt into a Claude Code session (Code tab — it needs
filesystem and git access, so not the Chat tab). Edit the Config block
first if needed. For a multi-item SCOPE, run it in the most recent
involved session, or in a fresh Code session on the same machine.

## Config
- REPO_URL: https://github.com/jhan-positron/notebook
- TARGET_DIR: handoffs/     # dir inside the repo; create if missing; "." = repo root
- SCOPE: this session only
   - SCOPE takes EITHER the literal `this session only` OR a list of items.
   - Whatever appears as the value IS the active scope — Claude must cover
     every listed item, and must not treat a list as illustrative.
   - List syntax (example only, not active — each line one item,
     `"<project> / <session name>"`):
     - SCOPE:
       - Claude session: "story2814:GOF staging buffer / Wade's review comment"
       - Claude session: "debug_3bda_flat_freq / run CI tests"
       - Claude chat: "<chat title>"
         (Chat-tab chat: not on disk — Claude will ask me to paste content)
- GRANULARITY: per-session  # how many handoff FILES a multi-item SCOPE yields:
  -   consolidated = ONE file covering all items
  -   per-project  = one file per project, covering its listed sessions
  -   per-session  = one file per listed session/chat
  - GRANULARITY as a whole is ignored when SCOPE is `this session only`.
- LOCAL_CLONE: auto         # auto = reuse an existing local clone if found; else clone

## Terminology: project vs session
- A **project** is the working-directory grouping shown as the small header
  line in the Claude app sidebar. One project = one working directory = one
  folder under `~/.claude/projects/`. Example: project `debug_3bda_flat_freq`
  (cwd `C:\Users\jibin\Documents\claude_debug_3bda_flat_freq`).
- A **session** is one conversation inside a project — one JSONL transcript
  file in that project's folder. Example: project `debug_3bda_flat_freq`
  contains three sessions: "debug flat freq on CI machine",
  "explore best freq combo", and "run CI tests".
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
- Find this session's exact display name (the title shown in the app
  sidebar under the project header — see Terminology above). Try in order:
  1. The session JSONL under `~/.claude/projects/<project-dir>/` —
     title/summary records, if present. Multiple title records over time
     indicate renames; keep that history.
  2. `~/.claude/sessions/<pid>.json` — CAUTION: its `name` field with
     `"nameSource": "derived"` is an auto-generated internal name (e.g.
     `claude-debug-3bda-flat-freq-76`), NOT the display title. Never use a
     derived name as the session name.
  3. If no store yields a display title (common — verified 2026-07-04),
     ask me for the exact name as shown in the sidebar. Offer to accept a
     screenshot of the sidebar: the small grey header is the project, the
     list items under it are the sessions, and the highlighted item is the
     current session.
- If SCOPE includes other Claude Code sessions, resolve their names the same
  way. For claude.ai chats (not readable locally), ask me for the exact title.
- If any name cannot be verified: ask me. Never paraphrase or invent a name.
- Multi-item SCOPE handling:
  - Current session: use native context.
  - Other Claude Code sessions: session titles do NOT appear inside the
    transcripts, so grepping for the title text usually fails. Instead,
    match by content evidence: grep transcripts for distinctive terms from
    the title, then verify by reading the opening user request. If a match
    is uncertain or a title matches no transcript, ask me.
  - Claude chats (Chat tab) are cloud-side and not readable from Claude
    Code: ask me to paste the relevant content; include only what I paste.
- What Claude can and cannot discover on its own: Claude CAN enumerate and
  content-scan every local transcript under `~/.claude/projects/` (all
  projects, all sessions on this machine) and propose candidates with
  dates and topics — I do not need to list paths. What Claude CANNOT get
  from disk is the sidebar display titles (only derived internal names are
  stored), so I must supply/confirm exact names. Sessions from other
  machines and Chat-tab chats are not in the local store at all.

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
      - Formerly named: "<previous name>"
        (only if renamed and verifiable; one line per prior name)
    - Claude chat: "<full exact chat title>"
      (only if a chat is in SCOPE; same rename rule applies)

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

## Step 5 — Git workflow with approval gate
1. Locate or clone the repo per LOCAL_CLONE; `git pull` before adding
   the file.
2. For each output file, first check TARGET_DIR for an existing handoff
   already covering the same session(s): match on the `Claude session:` /
   `Claude chat:` header lines (project + exact name), NOT on the filename
   (dates in filenames drift as work continues).
   - If one exists: UPDATE that file in place — merge the new activity into
     the existing sections, refresh the "Generated by" date, and extend the
     Activity dates END. If the date range changed, `git mv` the file to
     the new `claude_<START>-<END>_<slug>.md` name in the same commit so
     the filename stays truthful. Never create a second file for a session
     that already has one.
   - If none exists: write a new file. If an unrelated file with the same
     name is somehow present, stop and ask before overwriting.
3. APPROVAL GATE — show me, for every output file: whether it is NEW or an
   UPDATE of an existing handoff (old -> new name if renamed), final path +
   filename, the full header block, and a <=10-line body summary (for
   updates: what changed). Wait for my explicit approval.
4. On approval: commit with message
   `Add Claude handoff: <slug> (<START>..<END>)` for new files, or
   `Update Claude handoff: <slug> (<START>..<END>)` for updates, then push.
5. If push fails (auth, permissions, non-fast-forward): stop, show the
   exact error, and ask. No force-push, no credential changes.
