# Prompt: generate a Codex handoff file and push to notebook

Paste this entire prompt into a Codex session on any surface with filesystem
and git access: the Codex Windows app, or the Codex CLI on a Linux server. Use
permissions that allow the repo and transcript paths needed by the run. Edit
the Config block first if needed. For a multi-item SCOPE, run it in the most
recent involved chat, or in a fresh session on the machine that holds the
transcripts in SCOPE.

## Platforms (added 2026-08-19)

Two platform types actively produce chats, and this prompt runs on both:
- Windows app on `DESKTOP-CI2JA7M`: Projects and chats are listed in the app
  sidebar; Codex home is normally `C:/Users/jibin/.codex/`.
- Codex CLI on any Linux machine: chats are listed by `codex resume`; Codex
  home is normally `~/.codex/`. Do not assume a hostname; detect it at run
  time. (`claude-alpha` is one example, not the only Linux host.)

Both use `sessions/YYYY/MM/DD/rollout-*.jsonl` transcripts and
`session_index.jsonl` title records under Codex home (verified on
`claude-alpha` 2026-08-19). Detect the current platform and Codex home from the
environment at run time; honor `CODEX_HOME` when set. Each machine's local
store contains only the chats recorded there. Handoffs whose `Transcript:` host
is another machine and is not reachable are frozen for this run (rule under
`SCOPE: auto` below).

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
unless they include ` / `, in which case the left side is a Codex Project
name or project path hint and the right side is the chat name.

## Config
- REPO_URL: https://github.com/jhan-positron/notebook
- TARGET_DIR: handoffs/     # dir inside the repo; create if missing; "." = repo root
- EXCLUDE_CWDS: [~/self/ai]
  - Exclude chats whose recorded working directory is `~/self/ai` or any of
    its subdirectories. Expand `~` using the user's home on the machine where
    the work ran, and compare normalized path components.
  - Apply this filter to every SCOPE mode, including explicit chat lists and
    `this chat only`, unless I explicitly override the exclusion for that run.
    Use Project/cwd metadata before reading substantive transcript content;
    the exclusion follows the recorded cwd even if the transcript has moved.
  - Report these chats as `SKIPPED — excluded cwd`. Leave their existing
    handoffs unchanged and unstaged, and omit their content and new artifact
    proposals from the run.
- SCOPE: auto
   - auto (the default): derive the scope from Codex itself, not from GitHub.
     Use the current Codex surface and its local state as the source of truth.
     On the Windows app, list Projects and chats across the local host and any
     connected remote hosts the app returns. On the Linux CLI, enumerate every
     non-helper rollout under the current Codex home and reconcile it with
     `session_index.jsonl` (the `codex resume` inventory). Include projectless
     chats and every host/cwd group visible from the current surface, subject
     to EXCLUDE_CWDS above.
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
     is skipped (report it as unchanged; no commit churn). One exception
     (added 2026-09-20): the Step 4b lineage backfill (lineage: Step 4,
     Artifacts item 4) runs for a chat without new activity. It does not
     override EXCLUDE_CWDS or the FROZEN/BLOCKED handoff protections.
   - FROZEN-handoff rule (added 2026-08-19): a handoff whose `Transcript:` host
     is NOT this machine and is not reachable is frozen for this run -- no
     update and no questions. List it in the run report as "not checkable from
     this machine". With chats on multiple machines this is a normal
     cross-machine case, not an error; the canonical-missing alarm applies only
     to artifacts (Step 4b), never to transcripts.
   - If I list items under SCOPE, or invoke the URL with `add chats:` /
     `add threads:`, use those listed items as the explicit active scope for
     this run instead of the full auto-discovered Codex list. This is how I ask
     for only a specific subset of chats to be updated or created.
   - `this chat only`: cover just the current Codex chat; skip the scan.
     Accept `this thread only` as an older alias for the same thing.
   - Whatever appears as the value IS the active scope after EXCLUDE_CWDS is
     applied -- Codex must cover every remaining item, and must not treat a
     list as illustrative.
   - List syntax for additions (example only, not active -- each line one item):
     - SCOPE: auto
       - Codex chat: "Generate Codex handoff prompt"
       - Codex chat: "debug_3bda / root cause flat freq not working"
       - Codex chat: "C:\Users\jibin\Documents\myrepo / Fix Windows transcription"
       - External chat: "<chat title>"
         (not stored in local Codex state -- Codex will ask me to paste content)
- GRANULARITY: per-chat  # how many handoff FILES a multi-item SCOPE yields:
  - consolidated = ONE file covering all items
  - per-project   = one file per Codex Project, covering its listed chats
  - per-chat      = one file per listed Codex chat or external chat
  - GRANULARITY as a whole is ignored when SCOPE is `this chat only`.
- PRESERVE_ARTIFACTS: auto  # auto = maintain artifacts/ mirrors (Step 4b); off = skip
- LOCAL_CLONE: auto         # auto = reuse an existing local clone if found; else clone

## Terminology: Project vs chat vs thread id
- A **Project** is the working-directory grouping (Windows app: the visible
  grouping in the sidebar; Linux CLI: the cwd). It is usually a local or remote
  project folder, repo, or worktree. The transcript metadata records the
  working directory as `session_meta.payload.cwd`; use that path as evidence
  for the Project when the UI name is ambiguous or no UI Project name exists.
- A **chat** is one visible conversation (Windows app: a row under a Project in
  the sidebar; Linux CLI: an entry in `codex resume`), such as
  `root cause flat freq not working`. Use "chat" for user-facing names and
  handoff headers.
- A **thread** is Codex's internal/manual/API term for that same conversation
  unit. Keep it when referring to machine identifiers, transcript metadata,
  app-server APIs, deep links, or manual terminology. Do not use "thread" as the
  primary user-facing label when a Codex display name is meant.
- A **transcript** is the local Codex JSONL rollout file for a chat/thread. Codex
  home is normally `%USERPROFILE%\.codex` on Windows or `~/.codex` on Linux,
  unless `CODEX_HOME` is set. Local transcripts are typically under
  `<CODEX_HOME>/sessions/YYYY/MM/DD/rollout-<timestamp>-<thread-id>.jsonl`
  (with native path separators).
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

## Terminology: local vs remote chat state

What matters to this prompt is where the TRANSCRIPT lives, not where the work
ran:

1. **Local chat** -- the current machine's Codex process wrote the transcript
   under its Codex home. This is fully automatic on both platforms: discovery,
   titles, dates, content, and rename detection.
2. **Connected remote chat visible from the Windows app** -- the app may show a
   remote host/cwd group, while the rollout lives under that remote host's Codex
   home. Use app inventory for identity, but read the remote transcript only
   when it is reachable from the current environment. The Environment and
   Artifacts sections must name the host on which each path and command lives.
3. **Chat on another machine, not visible or reachable here** -- nothing about
   it is available in the current local store. `SCOPE: auto` cannot discover a
   new one. An existing handoff for it is frozen by the rule above; creating a
   new handoff requires running this prompt on that machine or supplying the
   transcript/content explicitly.

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
what happened in the chat. Codex inventory, `session_index.jsonl`, thread
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
- TIMEZONE (added 2026-07-26): all dates -- in filenames, `Activity dates:`,
  and `Generated by` lines -- are calendar dates in US Pacific time
  (America/Los_Angeles: PDT during daylight saving, PST otherwise),
  matching the Slack timestamps and my working hours. Transcript/git
  evidence is usually UTC; convert to Pacific before deriving the
  calendar date.
- Evidence priority:
  1. Codex transcript timestamps under the current
     `<CODEX_HOME>/sessions/` (with native path separators)
  2. `session_index.jsonl` `updated_at` timestamps for title/chat updates
  3. Git commit timestamps from work done in the chat
  4. mtimes of files created/edited during the work
- START = first activity date, END = last activity date, taken across ALL SCOPE
  items.
- Codex transcript timestamps are UTC ISO strings. Convert them to US Pacific
  calendar dates before deriving filenames or header dates.
- Record which evidence source and timezone you used -- it goes in the file
  header.
- If dates cannot be established from evidence: ask me. Do not guess.

## Step 2 -- Determine Project and chat names
- Find this chat's exact display name (Windows app: the title shown under its
  Project in the sidebar; Linux CLI: the title shown by `codex resume`). Try in
  order:
  1. `<CODEX_HOME>/session_index.jsonl`: match by thread id, then use the newest
     `thread_name`. Multiple lines for the same id indicate renames; keep that
     history.
  2. The session JSONL under `<CODEX_HOME>/sessions/...`: match on
     `session_meta.payload.session_id` / `id`, `cwd`, timestamps, and distinctive
     user prompt text. Use this to find the thread id and transcript path.
  3. If local state cannot verify the display name, ask me for the exact name.
     On the Windows app, offer to accept a sidebar screenshot. On the Linux CLI,
     ask me to type the title as `codex resume` shows it.
- Resolve the Project name from the Windows app UI when visible, from an
  explicit SCOPE prefix, or from the transcript `cwd`/remote host. On the Linux
  CLI, the cwd is the Project. If a friendlier Windows UI Project name matters
  and cannot be verified, ask me.
- For the current chat, use native context plus local transcript evidence. If
  the current thread id is not directly visible, find the newest non-helper
  rollout file whose `cwd` matches the current Project/workspace and whose content
  contains the current user request or recent distinctive prompt text.
- For other local Codex chats, resolve their names the same way. If a title is
  ambiguous, use the Project/cwd hint if provided; otherwise ask me.
- For remote SSH-host Codex chats, the transcript lives on the remote host's
  Codex home, not necessarily the current host. Inspect that remote only if it
  is already accessible in the current environment or I authorize it;
  otherwise ask me for the transcript or a pasted summary.
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

    > Generated by Codex (<Windows app | Linux CLI>) on <YYYY-MM-DD>.

    - Activity dates: <YYYY-MM-DD> to <YYYY-MM-DD>
      (source: Codex transcript timestamps | session index | git log | file mtimes; timezone: <timezone>)
    - Codex chat: "<full exact chat name>"
      (Project: <exact Project name or "projectless">; cwd: <host>:<absolute cwd or "projectless">; source: local Windows app | local Linux CLI | WSL | SSH remote | cloud/pasted)
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
2. Environment -- hostname(s), OS/shells, Projects, cwd/project directories,
   worktrees, and remote hosts where the work ran. State the host for every
   machine touched (local Windows app host vs local Linux CLI host vs WSL vs SSH
   remote vs cloud); this is required whenever any file path or command appears
   later in the file.
3. Timeline -- what was done, by date
4. Artifacts -- full host-qualified locations and file names of everything the
   chat produced or that a resumer needs: generated reports, summaries,
   handoff/design docs, scripts and tools, data/output directories, plus
   repo/branch/commit hashes for code changes. Write paths as
   `<host>:<absolute path>` (for example
   `WINDOWS-HOST:C:\Users\jibin\Documents\repo\README.md` or
   `delphi-3bda:/scratch/jhan/flat_freq_tests/README.md`). This section is
   mandatory when the chat created or modified any file.
   Two kinds of entry are easy to miss (added 2026-09-20):
   - Session-store scripts. List any script needed to resume the work that
     lives in a tool's session store rather than the workspace. A Claude
     Workflow (a script of agent steps) may be one such dependency under
     `~/.claude/projects/<project-dir>/<session-id>/workflows/scripts/`.
     For Codex-created scripts, use their observed paths. Do not infer a
     Workflow directory layout under Codex home.
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
     generators, configs, recipes, analysis/plan docs, distilled-knowledge
     pages (HTML/md), or measurement data that a preserved report page,
     or a handoff's Results table, is computed from (added 2026-09-20).
     Litmus test: if the workspace vanished tonight, would recreating
     this cost hours-to-days, or be impossible? Measurement data is the
     impossible case: a test cannot be re-run into the same numbers once
     the binary, the machine state and the time are gone.
  4. Not bulk or regenerable data. Judge each file by its class and its
     size, never by its location: a file is not excluded for sitting
     inside a result tree (updated 2026-09-20: the old wording excluded
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
       total MiB at the gate, plus the clone's `.git` size from `du -sm`
       or a native disk-usage equivalent reporting MiB.
     - Regenerable means a command rebuilds the file from files already
       in git. A file that can only be rebuilt from unpreserved data, a
       hand-edited file, or a file a Workflow built (agent steps, not
       one deterministic command) is not regenerable. This test is for
       data files: a report page is preserved even when its generator
       and input are in git, so GitHub can render it.
- Computed-from files (added 2026-09-20): when a report page (Step 4,
  Artifacts item 4) is proposed or already registered, propose with it
  every not-yet-preserved file its numbers are computed from. Rule 1 is
  satisfied through the page's lineage labels: present in the handoff,
  written there on approval by the lineage walk below, or, for a FROZEN
  or BLOCKED/SKIPPED handoff, held in the README entry until the handoff
  is next updated.
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
  chat's cwd. For intel-amx it is `WS`, that is
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
- Session-store files (added 2026-09-20): a needed artifact that exists
  only in a tool's session store has no stable canonical location. This
  includes scripts found under Codex home or `~/.claude/projects/`.
  Use the observed path and host. Retention is Insufficient data unless
  verified for that tool and store. Treat these files as at risk.
  Propose at the gate
  `relocate: <session-store path> -> <target folder>/<file>`. The target
  is the canonical folder of the script that reads the artifact's
  output, or, failing that, of the scripts it drove. For
  `pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` that is
  `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/`,
  the folder of `gen_compare.py`, which reads the file the Workflow
  wrote. When no folder qualifies, or more than one does, the target is
  `<canonical root>/exec/workflows/` under the relevant registered root.
  The `relocate:` line says so.
  On approval: create the target folder if it is missing. Stop and ask
  if a file of that name exists. Copy the file there with `cp -p` or a
  native equivalent that preserves timestamps. Mirror it from there at
  the layout path and register THAT path as canonical. Record the
  session-store path in the README entry as `origin:` (a
  history note that the refresh loop never fetches). The copy comes from
  the store. When the store has already deleted the file, it comes from
  the repo mirror, the restore that the canonical-missing rule asks for.
  This relocation copy, folder creation included, is the one write into
  a canonical folder this prompt allows, and only on approval. Direction
  otherwise stays canonical -> repo. This supersedes the 2026-09-18
  practice of registering the session-store path itself as canonical
  (`artifacts/intel-amx/README.md` lines 722-725 on 2026-09-19).
- Registry: each `artifacts/<topic>/README.md` lists every preserved file with
  its canonical `<host>:<absolute path>`, what it is, and related Codex
  handoffs. That README is the source of truth for refresh.
  The README records WHAT is preserved. The qualifying rules live in
  this prompt (added 2026-09-20). Phrases in existing README headers and
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
  header lists which cited files were left behind and why, so a reader
  sees a decision, not an omission.
- Refresh on EVERY run (any SCOPE): for each registered artifact, fetch the
  canonical file and compare content with the repo copy.
  - Different -> propose refreshing the repo copy at the approval gate,
    subject to the measurement-file and content-frozen rules below.
  - Canonical missing -> NEVER delete the repo copy; alert loudly: the
    repo copy is now the only copy -- restore it to the workspace or
    deregister it deliberately.
  - Canonical UNREACHABLE (ssh host down / no route) is NOT the missing
    case: skip the refresh, report those mirrors as unverified this run,
    no alarm. The alarm is for a canonical that is GONE from a reachable
    location.
  - Direction is strictly canonical -> repo. Repo copies are mirrors; do not
    hand-edit them -- edit the canonical file and let the next run sync.
  - Measurement files (added 2026-09-20): a preserved input or source
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
  Artifacts entries at the approval gate; on approval copy them in, register
  them in the topic README, and annotate the handoff's Artifacts line with
  `(preserved: artifacts/<topic>/<file>)`.
  Lineage walk (added 2026-09-20): for every report page proposed this
  run, and for every registered page whose README entry or handoff line
  names a generator (`generated by <script>` or a `generator:` label)
  but whose entry lacks the lineage labels, walk generator -> input ->
  input builder -> cited sources, and propose the not-yet-preserved
  files per the "Computed-from files" bullet. Show the second case at
  the gate as `lineage unknown: <page>`. This backfill runs even when
  the page's chat has no new activity (the `SCOPE: auto` no-churn
  skip does not apply to it). EXCLUDE_CWDS still applies to new
  artifact and lineage proposals. Read the labels from the handoff, the
  generator's source (the files it reads and its output-path argument),
  the input's own citations, the page's own citations when it has no
  input, and the chat transcripts that ran the generator and built
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
  and only the preserved copies as input. If the command is `none` or
  `unavailable (<reason>)`, record the reason instead of running it.
  Record `regenerate verified <date>` or
  `regenerate unverified (<reason>)` in the entry. Do not run it on
  other passes. A backfill edits only those Artifacts
  lines: the header dates and the filename stay, and the gate lists the
  handoff as `UPDATE (lineage labels only)`. For a FROZEN or
  BLOCKED/SKIPPED handoff, write the labels into the README entry only
  and show `lineage labels pending: <handoff>` at the gate. For a batch,
  commit as `Preserve artifact: <topic>/<page> lineage (<N> files, <M> MiB)`.
- HTML artifacts: GitHub's normal blob view does not render standalone HTML.
  When preserving or generating an `.html` file in this notebook repo, add
  rendered-view links using this exact pattern (updated 2026-08-19 to match the
  deployed files, e.g. `artifacts/common-knowledge/*.html`), after substituting
  the final repo-relative path -- a comment block placed ABOVE the doctype, no
  visible in-page link needed:

      <!--
        Rendered page (open in browser):
        https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/<repo-relative-path>
        Backup renderer:
        https://raw.githack.com/jhan-positron/notebook/main/<repo-relative-path>
      -->
      <!DOCTYPE html>

  If an artifact README links to that HTML file, include the primary
  rendered-view URL there too so GitHub readers can open the page directly. If
  the file later MOVES within the repo, update both URLs in the comment to the
  new path.
- Commit wording for artifact-only changes should be `Preserve artifact:
  <topic>/<file>` or `Refresh artifact: <topic>/<file>`. If artifact changes
  are bundled with an approved Codex handoff update, the approval gate must say
  that explicitly before committing.
- Do NOT place artifacts in `handoffs/` -- the SCOPE auto scan parses every file
  there as a handoff.

## Step 5 -- Git workflow with approval gate
1. Locate or clone the repo per LOCAL_CLONE; `git pull` before adding the file.
   If `git` is unavailable on PATH, use the bundled Codex Git when running in
   the Windows app if it is visible in the current runtime; otherwise ask me
   before installing tools.
2. For each output file, first check TARGET_DIR for an existing handoff already
   covering the same chat(s). Do not start with filenames or chat titles; first
   resolve each scoped chat to a stable identity from the Codex chat/thread list,
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
     for a chat that already has one. Exception (added 2026-09-20): a
     lineage backfill (Step 4b) edits only the page's Artifacts lines,
     keeps the header dates and the filename, and is committed in the
     `Preserve artifact:` commit, not as `Update Codex handoff:`.
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
   canonical-missing alerts / unreachable mirrors unverified this run),
   plus (added 2026-09-20) the `computed-from:`, `lineage unknown:`,
   `lineage incomplete:`, `lineage labels pending:`, `relocate:`,
   `measurement changed:` and `left behind` lines, each batch's file
   count and total MiB, and the clone's `.git` size in MiB. Wait for my
   explicit approval.
4. On approval: commit with message
   `Add Codex handoff: <slug> (<START>..<END>)` for new files, or
   `Update Codex handoff: <slug> (<START>..<END>)` for updates, then push.
   After a push that carries artifact preservation or refresh actions,
   including actions bundled with a handoff commit, run `git fetch
   origin`. For every approved file (mirrors, lineage inventories,
   README, handoffs), compare the blob id (Git's identifier for file
   contents) from `git ls-tree -r origin/main <path>` with
   `git hash-object <local path>`. Include approved files even if they
   were accidentally omitted from the commit. Check the final local
   files after adding HTML rendering comments. Report `on origin/main:
   <N> of <N> files, contents match`, and name any file whose id differs
   or is missing. A name check alone would pass a README-only push that
   left a changed mirror unstaged (added 2026-09-20).
5. If push fails (auth, permissions, non-fast-forward): stop, show the exact
   error, and ask. No force-push, no credential changes.
