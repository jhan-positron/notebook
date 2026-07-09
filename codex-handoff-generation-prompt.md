# Prompt: generate a Codex handoff file and push to notebook

Paste this entire prompt into a Codex Windows app chat. It needs filesystem
and git access, so run it in the Codex app with Default permissions unless the
repo or transcript paths require narrower approvals. Edit the Config block
first if needed. For a multi-item SCOPE, run it in the most recent involved
chat, or in a fresh Codex app chat on the same machine.

## Triggering by reference (no paste needed)

I may also invoke this by URL instead of pasting, in either form:
- `please do per https://github.com/jhan-positron/notebook/blob/main/codex-handoff-generation-prompt.md`
- `please do per <same URL>, add chats: "Generate Codex handoff prompt", "debug_3bda / root cause flat freq not working"`

When triggered this way: clone/pull REPO_URL first (required for Step 5
anyway) and read this file from the clone -- do not rely on fetching the URL
directly. If my message names no specific chats, run with the Config below
as-is (`SCOPE: auto`). If my message includes `add chats:` or older
`add threads:`, treat the quoted items as the explicit active scope for this
run, even though the phrase says "add". Treat quoted items as exact chat names
unless they include ` / `, in which case the left side is a Codex app Project
name or project path hint and the right side is the chat name.

## Config
- REPO_URL: https://github.com/jhan-positron/notebook
- TARGET_DIR: handoffs/     # dir inside the repo; create if missing; "." = repo root
- SCOPE: auto
   - auto (the default): derive the scope from Codex itself, not from GitHub.
     Use the Codex app's Project/chat inventory as the source of truth: list
     Codex Projects and chats across the local host and connected remote hosts,
     including projectless chats and any extra host/cwd groups Codex returns.
     For every chat, collect the visible Project name when available, host,
     cwd, exact chat title, thread id, app link, and transcript path when
     readable. This inventory step determines scope and identity only; it is
     not enough evidence for a handoff body.
   - The notebook repo is used after scope discovery, not before it. Once the
     Codex chat list is known, scan TARGET_DIR for existing Codex handoff files
     and match them by stable identity: `Thread id:`, `Transcript:`, `App link:`,
     then `Project:` + `Codex chat:` as a last fallback. Existing handoffs are
     UPDATED per Step 5; chats without an existing handoff get their first
     handoff. A chat with no new activity since its handoff's Activity END date
     is skipped (report it as unchanged; no commit churn).
   - If I list items under SCOPE, or invoke the URL with `add chats:` /
     `add threads:`, use those listed items as the explicit active scope for
     this run instead of the full auto-discovered Codex list. This is how I ask
     for only a specific subset of chats to be updated or created.
   - `this chat only`: cover just the current Codex chat; skip the scan.
     Accept `this thread only` as an older alias for the same thing.
   - Whatever appears as the value IS the active scope -- Codex must cover every
     item, and must not treat a list as illustrative.
   - List syntax for additions (example only, not active -- each line one item):
     - SCOPE: auto
       - Codex chat: "Generate Codex handoff prompt"
       - Codex chat: "debug_3bda / root cause flat freq not working"
       - Codex chat: "C:\Users\jibin\Documents\myrepo / Fix Windows transcription"
       - External chat: "<chat title>"
         (not stored in local Codex state -- Codex will ask me to paste content)
- GRANULARITY: per-chat  # how many handoff FILES a multi-item SCOPE yields:
  - consolidated = ONE file covering all items
  - per-project   = one file per Codex app Project, covering its listed chats
  - per-chat      = one file per listed Codex chat or external chat
  - GRANULARITY as a whole is ignored when SCOPE is `this chat only`.
- PRESERVE_ARTIFACTS: auto  # auto = maintain artifacts/ mirrors (Step 4b); off = skip
- LOCAL_CLONE: auto         # auto = reuse an existing local clone if found; else clone

## Terminology: Project vs chat vs thread id
- A **Project** is the visible grouping in the Codex app sidebar. It is usually
  a local or remote project folder, repo, or worktree. The app shows chat titles
  underneath each Project. The transcript metadata records the working directory
  as `session_meta.payload.cwd`; use that path as evidence for the Project when
  the UI name is ambiguous.
- A **chat** is the visible conversation row under a Project in the Codex app
  sidebar, such as `root cause flat freq not working`. Use "chat" for
  user-facing names and handoff headers.
- A **thread** is Codex's internal/manual/API term for that same conversation
  unit. Keep it when referring to machine identifiers, transcript metadata,
  app-server APIs, deep links, or manual terminology. Do not use "thread" as the
  primary user-facing label when a Codex app sidebar name is meant.
- A **transcript** is the local Codex JSONL rollout file for a chat/thread. On the
  Windows app, Codex home is normally `%USERPROFILE%\.codex` unless `CODEX_HOME`
  is set. Local transcripts are typically under:
  `%CODEX_HOME%\sessions\YYYY\MM\DD\rollout-<timestamp>-<thread-id>.jsonl`
- A **thread id** is the UUID-like internal id used by Codex to resume/open a
  chat. It appears in transcript metadata and can be opened with
  `codex://threads/<id>`.
- `session_index.jsonl` under Codex home records chat display names over time:
  each line has an `id`, `thread_name`, and `updated_at`. Repeated entries for
  the same id indicate renames or title updates; use the newest matching line as
  the current display name and keep old names as rename history when relevant.
- Ignore subagent, approval-review, and other helper rollout files unless they
  are needed as evidence or artifacts for the main chat. In transcript
  metadata, helper threads may have `thread_source: "subagent"` or a
  `parent_thread_id`.

## Goal
Produce markdown handoff file(s) covering ALL items in SCOPE -- file count per
GRANULARITY -- written so a fresh Codex chat (or a human) can resume the work
without this chat's context. Then commit and push to REPO_URL under TARGET_DIR
-- after my approval.

Pipeline: evidence -> dates -> names -> filename(s) -> file(s) -> approval -> push

Steps 1-4 apply PER OUTPUT FILE (dates/slug/header computed from the items that
file covers). The Step 5 approval gate is shown ONCE listing all files.

## Quality bar -- no inventory-only stubs
Every generated handoff must contain meaningful, transcript-backed content about
what happened in the chat. Codex app inventory, `session_index.jsonl`, thread
ids, app links, titles, cwd, and timestamps are identity/date evidence; they are
not sufficient to write Objective, Timeline, Artifacts, Current state, or Next
steps.

- For every scoped Codex chat, read the transcript content when a transcript is
  readable. At minimum, extract the user's substantive prompts, assistant final
  answers, tool commands/results that affected state, file edits, generated
  artifacts, commits, and explicit next steps.
- If a transcript is too large, process it incrementally or in chunks. Do not
  replace transcript summarization with an identity-only placeholder.
- If a transcript is unreadable, remote-only, missing, or too large to process
  in the current run, do not create or refresh that chat's handoff with generic
  filler. Report that chat as BLOCKED/SKIPPED at the approval gate and state the
  exact missing evidence or access needed.
- If `SCOPE: auto` expands to too much work for one reliable run, ask me to
  approve a smaller batch or an explicit `add chats:` scope. Do not silently
  downgrade to first-pass stubs.
- A valid handoff body should let a fresh chat resume the actual task, not just
  reopen the old chat. If the only available facts are title, dates, cwd,
  thread id, and app link, the handoff is not ready.

## Step 1 -- Determine activity dates (NOT today's date)
Filename dates are when the work actually happened; it may span several days.
- Evidence priority:
  1. Codex transcript timestamps under `%CODEX_HOME%\sessions\`
  2. `session_index.jsonl` `updated_at` timestamps for title/chat updates
  3. Git commit timestamps from work done in the chat
  4. mtimes of files created/edited during the work
- START = first activity date, END = last activity date, taken across ALL SCOPE
  items.
- Codex transcript timestamps are UTC ISO strings. Convert them to the user's
  current/local timezone for filename dates when the timezone is available;
  otherwise use the host local date and state that choice in the header.
- Record which evidence source and timezone you used -- it goes in the file
  header.
- If dates cannot be established from evidence: ask me. Do not guess.

## Step 2 -- Determine Project and chat names
- Find this chat's exact display name (the title shown under its Project in the
  Codex app sidebar). Try in order:
  1. `%CODEX_HOME%\session_index.jsonl`: match by thread id, then use the newest
     `thread_name`. Multiple lines for the same id indicate renames; keep that
     history.
  2. The session JSONL under `%CODEX_HOME%\sessions\...`: match on
     `session_meta.payload.session_id` / `id`, `cwd`, timestamps, and distinctive
     user prompt text. Use this to find the thread id and transcript path.
  3. Codex app UI: if local state cannot verify the display name, ask me for the
     exact name as shown in the sidebar. Offer to accept a screenshot.
- Resolve the Project name from the Codex app UI when visible, from an explicit
  SCOPE prefix, or from the transcript `cwd`/remote host when the UI name is not
  otherwise available. If the UI Project name matters and cannot be verified,
  ask me.
- For the current chat, use native context plus local transcript evidence. If
  the current thread id is not directly visible, find the newest non-helper
  rollout file whose `cwd` matches the current Project/workspace and whose content
  contains the current user request or recent distinctive prompt text.
- For other local Codex app chats, resolve their names the same way. If a title
  is ambiguous, use the Project/cwd hint if provided; otherwise ask me.
- For remote SSH-host Codex chats, the transcript lives on the remote host's
  Codex home, not necessarily the Windows host. Inspect that remote only if it is
  already accessible in the current environment or I authorize it; otherwise ask
  me for the transcript or a pasted summary.
- For cloud chats or external chats that are not readable locally, ask me to
  paste the relevant content or provide an export. Include only what I provide.
- If any name cannot be verified: ask me. Never paraphrase or invent a name.
- Chat renames: if a SCOPE item resolves (by transcript id/path or my
  confirmation) to the same identity as an existing handoff, that is a RENAME
  of a covered chat, not a new chat. Identity matching must use this priority:
  1. exact `Thread id:` match
  2. exact `Transcript:` match, normalized for host and path separators
  3. exact `App link:` / `codex://threads/<thread-id>` match
  4. Project + exact chat name match, only as a fallback when no stable id exists
  Update that handoff: put the new name on the `Codex chat:` line, add a
  `Formerly named:` line recording the old chat name AND the old filename, and
  `git mv` the file to the new slug in Step 5. Never create a second file for
  the same transcript/thread id, even if the chat title changed completely.
- Multi-item SCOPE handling:
  - Current chat: use native context and transcript evidence.
  - Fast path: if an existing handoff in TARGET_DIR has a `Transcript:` header
    line, use that path directly -- no matching or asking needed. This is the
    normal case for `SCOPE: auto` refresh runs.
  - Other Codex chats without a Transcript line yet: chat titles may be
    present in `session_index.jsonl`, but search transcripts for distinctive
    terms from the title and verify by reading the opening user request.
  - External chats are not readable from Codex local state: ask me to paste the
    relevant content and include only what I paste.

## Step 3 -- Filename
- Pattern: `codex_<START>-<END>_<slug>.md`, dates as YYYYMMDD.
  Single-day work: `codex_<DATE>_<slug>.md`.
- Filename MUST start with `codex_` (distinguishes these files from ones
  generated by other tools, e.g. Claude).
- `<slug>`: lowercase kebab-case.
  - Preferred: slugified Codex chat name; append slugified external chat name
    with `__` separator if both fit.
  - Apostrophes cannot appear in filenames. Drop possessive `'s` entirely when
    slugifying: "Wade's review comment" -> `wade-review-comment` (not
    `wades-review-comment`). Drop bare apostrophes the same way (e.g. "don't"
    -> `dont`).
  - If that exceeds ~50 chars, replace with a shorter content-hint slug -- the
    full names live inside the file, so the slug only needs to hint at the
    contents.
- Target total filename length <= 80 chars.

## Step 4 -- File contents
Open with this header block. Keep the labels verbatim:

    # Handoff: <one-line descriptive title>

    > Generated by Codex (Windows app) on <YYYY-MM-DD>.

    - Activity dates: <YYYY-MM-DD> to <YYYY-MM-DD>
      (source: Codex transcript timestamps | session index | git log | file mtimes; timezone: <timezone>)
    - Codex chat: "<full exact chat name>"
      (Project: <exact Project name or "projectless">; cwd: <host>:<absolute cwd or "projectless">; source: local Windows app | WSL | SSH remote | cloud/pasted)
      - Thread id: <uuid>
      - Transcript: <host>:<absolute path to the rollout .jsonl>
        (machine-readable pointer so future `SCOPE: auto` runs can match this
        handoff to its chat/thread id and check for new activity without asking me;
        update the line if the transcript moves)
      - App link: codex://threads/<thread-id>
      - Formerly named: "<previous name>"; file renamed from
        `<previous filename>` on <YYYY-MM-DD>
        (one line per prior name, newest first -- the full rename history of
        both the chat and the file must be readable right here, without
        consulting git history)
    - External chat: "<full exact chat title>"
      (only if a non-Codex/local-unreadable chat is in SCOPE; same rename rule
      applies; external chats have no Transcript line -- content must be pasted
      by me each time)

If SCOPE covers multiple chats, repeat the `Codex chat:` /
`External chat:` lines once per item -- always those exact labels.

Body sections (omit empty ones):
1. Objective
2. Environment -- hostname(s), OS/shells, Projects, cwd/project directories, worktrees, and
   remote hosts where the work ran. State the host for every machine touched
   (local Windows vs WSL vs SSH remote vs cloud); this is required whenever any
   file path or command appears later in the file.
3. Timeline -- what was done, by date
4. Artifacts -- full host-qualified locations and file names of everything the
   chat produced or that a resumer needs: generated reports, summaries,
   handoff/design docs, scripts and tools, data/output directories, plus
   repo/branch/commit hashes for code changes. Write paths as
   `<host>:<absolute path>` (for example
   `WINDOWS-HOST:C:\Users\jibin\Documents\repo\README.md` or
   `delphi-3bda:/scratch/jhan/flat_freq_tests/README.md`). This section is
   mandatory when the chat created or modified any file.
5. Current state -- only claims backed by evidence from the chat (commands,
   outputs, commit hashes, generated files); mark anything unverified as
   unverified. Do not use generic text such as "open the app link and inspect
   the latest turns" as a substitute for summarizing what the transcript shows.
6. Open items / next steps
7. Gotchas & decisions -- anything a fresh chat would otherwise rediscover the
   hard way

Style rule for ALL sections (and for artifact READMEs): reference pull
requests and issues by their full web link
(e.g. https://github.com/positron-ai/tron/pull/3070), never a bare
"PR #3070" -- bare numbers are ambiguous across repos and not clickable.

## Step 4b -- Artifact preservation (when PRESERVE_ARTIFACTS: auto)

Important workspace files get mirrored into `artifacts/<topic>/` in the repo so
accidental workspace deletion cannot destroy them.

- What qualifies (ALL must hold):
  1. Referenced in a handoff's Artifacts section (a chat judged it necessary for
     resuming work).
  2. Lives on mutable, non-git storage (Codex workspaces, remote workspaces,
     projectless Codex-managed working directories, /scratch, /var/tmp, /tmp,
     home dirs, NFS workspaces). Files already in a git repo are already safe.
  3. Executable knowledge or an irreplaceable document: scripts, tools,
     generators, configs, recipes, analysis/plan docs, distilled-knowledge pages
     (HTML/md). Litmus test: if the workspace vanished tonight, would
     recreating this cost hours-to-days?
  4. Not bulk or regenerable data (benchmark result trees, raw logs, large trace
     files, turbostat captures, and raw command dumps stay on their storage).
- Registry: each `artifacts/<topic>/README.md` lists every preserved file with
  its canonical `<host>:<absolute path>`, what it is, and related Codex
  handoffs. That README is the source of truth for refresh.
- Refresh on EVERY run (any SCOPE): for each registered artifact, fetch the
  canonical file and compare content with the repo copy.
  - Different -> refresh the repo copy and report it at the approval gate.
  - Canonical missing or inaccessible -> NEVER delete the repo copy; alert
    loudly: the repo copy may be the only copy, or Codex needs access to the
    canonical host/path. Restore it to the workspace, grant access, or
    deregister it deliberately.
  - Direction is strictly canonical -> repo. Repo copies are mirrors; do not
    hand-edit them -- edit the canonical file and let the next run sync.
- New artifacts: when generating/updating handoffs, propose qualifying
  Artifacts entries at the approval gate; on approval copy them in, register
  them in the topic README, and annotate the handoff's Artifacts line with
  `(preserved: artifacts/<topic>/<file>)`.
- Commit wording for artifact-only changes should be `Preserve artifact:
  <topic>/<file>` or `Refresh artifact: <topic>/<file>`. If artifact changes
  are bundled with an approved Codex handoff update, the approval gate must say
  that explicitly before committing.
- Do NOT place artifacts in `handoffs/` -- the SCOPE auto scan parses every file
  there as a handoff.

## Step 5 -- Git workflow with approval gate
1. Locate or clone the repo per LOCAL_CLONE; `git pull` before adding the file.
   If `git` is unavailable on PATH in the Windows app, use the bundled Codex Git
   if visible in the current runtime, or ask me before installing tools.
2. For each output file, first check TARGET_DIR for an existing handoff already
   covering the same chat(s). Do not start with filenames or chat titles; first
   resolve each scoped chat to a stable identity from the Codex app/thread list,
   session index, transcript metadata, or my confirmation. Then match existing
   handoffs by identity in this order:
   1. `Thread id:` line
   2. `Transcript:` line
   3. `App link:` line
   4. `Project:` + `Codex chat:` exact title
   Also accept older `Codex thread:` header lines and older parenthetical
   `thread id:` fields as aliases when refreshing existing handoffs. Do NOT
   match on the filename; dates and slugs in filenames drift as work continues.
   - If one exists: UPDATE that file in place -- merge the new activity into the
     existing sections, refresh the "Generated by" date, and extend the Activity
     dates END. If the date range OR the chat name changed (rename detected per
     Step 2), `git mv` the file to the new `codex_<START>-<END>_<slug>.md` name
     in the same commit so the filename stays truthful, and record the old
     filename on the `Formerly named:` header line. Never create a second file
     for a chat that already has one.
   - If none exists: write a new file. If an unrelated file with the same name is
     somehow present, stop and ask before overwriting.
3. APPROVAL GATE -- show me, for every scoped chat and every output file:
   whether it is NEW, UPDATE, UNCHANGED, or BLOCKED/SKIPPED. For files, show the
   old -> new name if renamed, final path + filename, the full header block, a
   <=10-line body summary (for updates: what changed), and an evidence coverage
   line that states which transcript(s) or pasted sources were read. For
   BLOCKED/SKIPPED chats, show the exact reason, such as "remote transcript not
   readable", "transcript missing", or "scope too large; needs batching". Also
   list artifact actions from Step 4b (preserved / refreshed /
   canonical-missing-or-inaccessible alerts). Wait for my explicit approval.
4. On approval: commit with message
   `Add Codex handoff: <slug> (<START>..<END>)` for new files, or
   `Update Codex handoff: <slug> (<START>..<END>)` for updates, then push.
5. If push fails (auth, permissions, non-fast-forward): stop, show the exact
   error, and ask. No force-push, no credential changes.
